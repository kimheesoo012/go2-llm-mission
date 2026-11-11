"""Sustained lying posture over time.

posture_rules.classify_posture judges ONE frame. A single "lying" frame also
happens when someone bends down or the pose model slips, so one frame must not
raise an alert. This tracker follows each person box across frames and reports
when the lying posture has been observed continuously for `sustain` seconds.

It reports what was observed ("누운 자세 지속 관측"). It does not decide a fall,
an injury or unconsciousness.

Input per analysed frame: the same detection dicts vision.infer builds
    dict(target='person', xyxy=[x1, y1, x2, y2], posture=dict(code='lying', ...))
`now` is time.monotonic() of that frame.
"""

LYING, UPRIGHT = 'lying', ('standing', 'sitting')


def iou(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - w * h
    return w * h / union if union > 0 else 0.


class LyingTracker:
    def __init__(self, sustain=15., gap=2., reset=1., min_iou=.2, min_ratio=.6):
        # sustain    seconds of lying before the event fires
        # gap        lying may go unseen (unknown posture, missed detection) this long
        # reset      standing/sitting must last this long to end the lying span
        # min_ratio  share of frames in the span that must be lying
        self.sustain, self.gap, self.reset = sustain, gap, reset
        self.min_iou, self.min_ratio = min_iou, min_ratio
        self.tracks = []
        self.next_id = 1

    def _new(self, now, box):
        t = dict(id=self.next_id, box=list(box), seen=now, since=None, last_lying=None,
                 upright_since=None, lying=0, other=0, alerted=False)
        self.next_id += 1
        self.tracks.append(t)
        return t

    def _end(self, track, now, events, why):
        if track['alerted']:
            events.append(dict(event='lying_ended', track=track['id'], reason=why,
                               seconds=round(track['last_lying'] - track['since'], 1)))
        track.update(since=None, last_lying=None, upright_since=None, lying=0, other=0, alerted=False)

    def update(self, now, detections):
        """Feed one analysed frame. Returns a list of events (usually empty)."""
        events = []
        people = [d for d in detections or [] if d.get('target', 'person') == 'person' and len(d.get('xyxy') or []) == 4]
        # Drop tracks that have not been seen for longer than the gap.
        for t in [t for t in self.tracks if now - t['seen'] > self.gap]:
            self._end(t, now, events, '화면에서 사라짐')
            self.tracks.remove(t)
        # Greedy match by overlap, best pairs first.
        pairs = sorted(((iou(t['box'], d['xyxy']), ti, di) for ti, t in enumerate(self.tracks)
                        for di, d in enumerate(people)), reverse=True)
        used_t, used_d, matched = set(), set(), []
        for score, ti, di in pairs:
            if score < self.min_iou:
                break
            if ti in used_t or di in used_d:
                continue
            used_t.add(ti); used_d.add(di); matched.append((self.tracks[ti], people[di]))
        # The robot turned and boxes no longer overlap: if exactly one lying track and
        # exactly one lying person are left over, treat them as the same person.
        left_t = [t for i, t in enumerate(self.tracks) if i not in used_t and t['since'] is not None]
        left_d = [i for i, d in enumerate(people) if i not in used_d and (d.get('posture') or {}).get('code') == LYING]
        if len(left_t) == 1 and len(left_d) == 1:
            used_d.add(left_d[0]); matched.append((left_t[0], people[left_d[0]]))
        for i, d in enumerate(people):
            if i not in used_d:
                matched.append((self._new(now, d['xyxy']), d))

        for t, d in matched:
            t.update(box=list(d['xyxy']), seen=now)
            code = (d.get('posture') or {}).get('code', 'unknown')
            if code == LYING:
                if t['since'] is None:
                    t.update(since=now, lying=0, other=0)
                t.update(last_lying=now, upright_since=None)
                t['lying'] += 1
            elif t['since'] is not None:
                t['other'] += 1
                if code in UPRIGHT:
                    if t['upright_since'] is None:
                        t['upright_since'] = now
                    if now - t['upright_since'] >= self.reset:
                        self._end(t, now, events, '서 있음·앉아 있음으로 바뀜')
                        continue
                if now - t['last_lying'] > self.gap:
                    self._end(t, now, events, '누운 자세가 이어지지 않음')
                    continue
            if t['since'] is not None and not t['alerted']:
                seconds = t['last_lying'] - t['since']
                ratio = t['lying'] / max(1, t['lying'] + t['other'])
                if seconds >= self.sustain and ratio >= self.min_ratio:
                    t['alerted'] = True
                    events.append(dict(event='lying_sustained', track=t['id'], seconds=round(seconds, 1),
                                       ratio=round(ratio, 2), xyxy=list(t['box']),
                                       label='누운 자세 지속',
                                       message=f'누운 자세가 {int(self.sustain)}초 이상 이어서 관측됨'))
        return events

    def status(self):
        """For the status API: people currently in a lying span."""
        return [dict(track=t['id'], seconds=round(t['last_lying'] - t['since'], 1), sustained=t['alerted'],
                     xyxy=list(t['box'])) for t in self.tracks if t['since'] is not None]

    def clear(self):
        self.tracks.clear()

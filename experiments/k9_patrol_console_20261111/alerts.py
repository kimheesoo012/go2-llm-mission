"""Operator alerts from rule results (no LLM).

Until now the console only stored records; the operator had to open them to
notice anything. AlertCenter turns two rule results into alerts for the screen:

    speech   help_request.find_help_request(transcript)
    lying    lying_tracker.LyingTracker events

Levels
    3 긴급 확인   help phrase in the transcript, or lying sustained together with
                 a help / suspect phrase in the same time window
    2 확인 필요   lying sustained alone, or a suspect phrase that repeats
    1 참고       a suspect phrase once

The speaker of a phrase is unknown, so a phrase and a lying person are only
described as observed in the same time window, never as the same person.
"""
import threading
import uuid
from datetime import datetime, timezone

LEVELS = {3: '긴급 확인', 2: '확인 필요', 1: '참고'}


class AlertCenter:
    def __init__(self, link_window=30., repeat_window=60., cooldown=30., keep=50):
        # link_window    speech and lying this close in time raise each other
        # repeat_window  suspect phrases in separate records this close count as a repetition
        # cooldown       the same kind of alert is merged instead of shown again
        self.link_window, self.repeat_window, self.cooldown, self.keep = link_window, repeat_window, cooldown, keep
        self.lock = threading.Lock()
        self.alerts = []          # newest last
        self.speech_times = []    # (now, code)
        self.lying_times = []

    def _raise(self, now, kind, level, title, message, record_id=None):
        last = next((a for a in reversed(self.alerts) if a['kind'] == kind and not a['acked']
                     and now - a['now'] <= self.cooldown), None)
        if last:
            last['count'] += 1
            last['now'] = now
            if record_id and record_id not in last['record_ids']:
                last['record_ids'].append(record_id)
            if level > last['level']:
                last.update(level=level, label=LEVELS[level], title=title, message=message, sound=level >= 2, new=True)
            else:
                last['new'] = False
            return dict(last)
        alert = dict(id=uuid.uuid4().hex[:12], kind=kind, level=level, label=LEVELS[level], title=title,
                     message=message, time=datetime.now(timezone.utc).isoformat(), now=now, count=1,
                     record_ids=[record_id] if record_id else [], acked=False, sound=level >= 2, new=True)
        self.alerts.append(alert)
        del self.alerts[:-self.keep]
        return dict(alert)

    def speech(self, now, result, record_id=None):
        """result: find_help_request(...). Returns the alert, or None when there is nothing to flag."""
        if not result or result.get('code') not in ('help', 'suspect'):
            return None
        with self.lock:
            self.speech_times = [(t, c) for t, c in self.speech_times if now - t <= self.repeat_window]
            earlier = len(self.speech_times)
            self.speech_times.append((now, result['code']))
            lying = any(now - t <= self.link_window for t in self.lying_times)
            if result['code'] == 'help':
                level, title = 3, '도움 요청 발화'
            else:
                level = 2 if result.get('priority', 1) >= 2 or earlier else 1
                title = '도움 요청 의심 발화'
            message = result.get('reason', '')
            if result['code'] == 'suspect' and earlier and result.get('priority', 1) < 2:
                message += f' · 최근 {int(self.repeat_window)}초 안에 유사 발화 기록 {earlier + 1}건'
            if lying:
                level = 3
                message += ' · 같은 시간대에 누운 자세 지속 관측 (발화자 미확인)'
            return self._raise(now, 'speech', level, title, message, record_id)

    def lying(self, now, event, record_id=None):
        """event: a 'lying_sustained' event from LyingTracker. Other events are ignored."""
        if not event or event.get('event') != 'lying_sustained':
            return None
        with self.lock:
            self.lying_times = [t for t in self.lying_times if now - t <= self.link_window] + [now]
            heard = [c for t, c in self.speech_times if now - t <= self.link_window]
            level, message = 2, event.get('message', '누운 자세 지속 관측')
            if heard:
                level = 3
                kind = '도움 요청 발화' if 'help' in heard else '도움 요청 의심 발화'
                message += f' · 같은 시간대에 {kind} 기록 (발화자 미확인)'
            return self._raise(now, 'lying', level, '누운 자세 지속', message, record_id)

    def active(self):
        """Unacknowledged alerts, highest level first, then newest."""
        with self.lock:
            rows = [dict(a) for a in self.alerts if not a['acked']]
        return sorted(rows, key=lambda a: (-a['level'], -a['now']))

    def ack(self, alert_id):
        with self.lock:
            for a in self.alerts:
                if a['id'] == alert_id:
                    a['acked'] = True
                    return True
        return False

    def history(self):
        with self.lock:
            return [dict(a) for a in reversed(self.alerts)]

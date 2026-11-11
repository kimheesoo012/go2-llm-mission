"""Replay a scripted 60-second scene through the rule modules (no robot, no model).

Shows how the pieces connect: posture per frame -> LyingTracker -> AlertCenter,
STT text per record -> find_help_request -> AlertCenter, records -> patrol report.

Usage (from this folder's parent):  python demo/replay_demo.py
The scene is made up for the demo. It is not a measurement.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from alerts import AlertCenter  # noqa: E402
from help_request import find_help_request  # noqa: E402
from lying_tracker import LyingTracker  # noqa: E402
from patrol_report import make_report  # noqa: E402

FPS = 5
BOX = [200, 320, 620, 430]
# (start second, posture code of the one person in view)
POSTURES = [(0, 'standing'), (10, 'lying'), (18, 'unknown'), (19, 'lying'), (40, 'sitting'), (45, 'standing')]
# (second, record id, STT text of the record saved at that moment)
SPEECH = [(5, 'a1', '안녕하세요'), (22, 'b2', '사랑해주세요 사랑해주세요 사랑해주세요 사랑해주세요'), (30, 'c3', '살려주세요 살려주세요')]


def posture_at(second):
    return [code for start, code in POSTURES if start <= second][-1]


def replay(sustain=15.):
    tracker, center, log = LyingTracker(sustain=sustain), AlertCenter(), []
    speech = {round(t * FPS): (rid, text) for t, rid, text in SPEECH}
    for frame in range(60 * FPS + 1):
        now = frame / FPS
        for event in tracker.update(now, [dict(target='person', xyxy=BOX, posture=dict(code=posture_at(now)))]):
            alert = center.lying(now, event)
            log.append((now, event['event'], alert))
        if frame in speech:
            rid, text = speech[frame]
            alert = center.speech(now, find_help_request(text), rid)
            log.append((now, 'speech', alert))
    return log, center


def observations():
    base = '2026-11-11T05:00:{:02d}+00:00'
    out = [dict(record_id=rid, time=base.format(t), transcript=text, person_seen=True, person_count=1,
                postures=[dict(frame_person_index=1, label={'standing': '서 있음', 'lying': '누워 있음', 'sitting': '앉아 있음',
                                                            'unknown': '판단 불가'}[posture_at(t)])]) for t, rid, text in SPEECH]
    return out


def main():
    log, center = replay()
    print('시각(초)  사건              알림')
    for now, name, alert in log:
        shown = '-' if alert is None else f"[{alert['label']}] {alert['title']} — {alert['message']}" + ('' if alert['new'] else ' (기존 알림에 합침)')
        print(f'{now:6.1f}  {name:16s}  {shown}')
    print('\n확인하지 않은 알림:')
    for a in center.active():
        print(f"  [{a['label']}] {a['title']} ×{a['count']} · 기록 {', '.join(a['record_ids']) or '-'}")
    print('\n' + make_report(observations())['markdown'])


if __name__ == '__main__':
    main()

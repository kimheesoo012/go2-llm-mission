import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'demo'))
import replay_demo  # noqa: E402
from patrol_report import make_report  # noqa: E402


def test_scripted_scene():
    log, center = replay_demo.replay()
    seen = [(now, name, alert and (alert['level'], alert['kind'], alert['new'])) for now, name, alert in log]
    assert seen == [
        (5.0, 'speech', None),                          # 안녕하세요: nothing
        (22.0, 'speech', (2, 'speech', True)),          # misheard x4 -> 확인 필요
        (25.0, 'lying_sustained', (3, 'lying', True)),  # 15 s of lying, speech 3 s earlier -> 긴급 확인
        (30.0, 'speech', (3, 'speech', True)),          # help phrase -> same speech alert upgraded
        (41.0, 'lying_ended', None),
    ]
    active = center.active()
    assert [(a['kind'], a['level'], a['count']) for a in active] == [('speech', 3, 2), ('lying', 3, 1)]
    assert active[0]['record_ids'] == ['b2', 'c3']


def test_shorter_threshold_for_a_live_demo():
    log, _ = replay_demo.replay(sustain=5.)
    assert [(now, name) for now, name, _ in log if name == 'lying_sustained'] == [(15.0, 'lying_sustained')]


def test_report_from_the_same_records():
    r = make_report(replay_demo.observations())
    f = r['facts']
    assert (f['records'], f['help_records'], f['suspect_records'], f['lying_records']) == (3, 1, 1, 2)
    assert f['start'] == '14:00' and '도움 요청 발화 + 누운 자세 후보' in r['markdown']

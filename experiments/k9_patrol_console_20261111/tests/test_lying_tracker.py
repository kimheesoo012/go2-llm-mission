from lying_tracker import LyingTracker, iou

BOX = [100, 300, 400, 380]


def det(code, box=BOX):
    return dict(target='person', xyxy=list(box), posture=dict(code=code))


def run(tracker, frames, fps=5, start=0.):
    """frames: list of detection lists. Returns [(time, event), ...]."""
    out = []
    for i, dets in enumerate(frames):
        now = start + i / fps
        out += [(now, e) for e in tracker.update(now, dets)]
    return out


def names(events):
    return [e['event'] for _, e in events]


def test_iou():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0
    assert round(iou([0, 0, 10, 10], [5, 0, 15, 10]), 3) == 0.333


def test_one_lying_frame_is_not_an_event():
    t = LyingTracker(sustain=5)
    ev = run(t, [[det('standing')]] * 10 + [[det('lying')]] + [[det('standing')]] * 10)
    assert ev == []


def test_sustained_lying_fires_once_at_the_threshold():
    t = LyingTracker(sustain=5)
    ev = run(t, [[det('lying')]] * 60)  # 12 s
    assert names(ev) == ['lying_sustained']
    when, e = ev[0]
    assert when == 5.0 and e['seconds'] == 5.0 and e['ratio'] == 1.0
    assert '쓰러' not in e['message'] and '낙상' not in e['message']


def test_short_lying_does_not_fire():
    t = LyingTracker(sustain=5)
    assert run(t, [[det('lying')]] * 20 + [[det('standing')]] * 20) == []  # 4 s lying


def test_unknown_frames_inside_the_gap_are_tolerated():
    t = LyingTracker(sustain=5, gap=2)
    frames = ([[det('lying')]] * 10 + [[det('unknown')]] * 5) * 3  # 1 s unknown in every 3 s
    assert names(run(t, frames)) == ['lying_sustained']


def test_missed_detections_inside_the_gap_are_tolerated():
    t = LyingTracker(sustain=5, gap=2)
    frames = [[det('lying')]] * 10 + [[]] * 7 + [[det('lying')]] * 30
    ev = run(t, frames)
    assert names(ev) == ['lying_sustained'] and ev[0][0] < 6


def test_long_unknown_ends_the_span():
    t = LyingTracker(sustain=5, gap=2)
    frames = [[det('lying')]] * 15 + [[det('unknown')]] * 15 + [[det('lying')]] * 15  # 3 s, 3 s unknown, 3 s
    assert run(t, frames) == []


def test_mostly_unknown_does_not_fire():
    # Lying is seen only once per 1.8 s: the span survives the gap but the ratio is too low.
    t = LyingTracker(sustain=5, gap=2)
    frames = ([[det('lying')]] + [[det('unknown')]] * 8) * 6
    assert run(t, frames) == []


def test_standing_up_ends_the_span_and_reports_it():
    t = LyingTracker(sustain=5, reset=1)
    ev = run(t, [[det('lying')]] * 30 + [[det('standing')]] * 10)
    assert names(ev) == ['lying_sustained', 'lying_ended']
    assert ev[1][1]['reason'] == '서 있음·앉아 있음으로 바뀜'


def test_one_upright_frame_does_not_reset():
    t = LyingTracker(sustain=5, reset=1)
    frames = [[det('lying')]] * 12 + [[det('sitting')]] + [[det('lying')]] * 20
    ev = run(t, frames)
    assert names(ev) == ['lying_sustained'] and ev[0][0] == 5.0


def test_fires_again_after_getting_up_and_lying_down_again():
    t = LyingTracker(sustain=5)
    frames = [[det('lying')]] * 30 + [[det('standing')]] * 10 + [[det('lying')]] * 30
    assert names(run(t, frames)) == ['lying_sustained', 'lying_ended', 'lying_sustained']


def test_two_people_are_followed_separately():
    t = LyingTracker(sustain=5)
    other = [600, 100, 700, 400]
    frames = [[det('lying'), det('standing', other)]] * 30
    ev = run(t, frames)
    assert names(ev) == ['lying_sustained']
    assert [s['track'] for s in t.status()] == [ev[0][1]['track']]


def test_passerby_overlapping_does_not_take_over_the_lying_span():
    t = LyingTracker(sustain=5)
    walker = [[x, 100, x + 100, 420] for x in range(0, 600, 20)]
    frames = [[det('lying'), det('standing', w)] for w in walker]
    assert names(run(t, frames)) == ['lying_sustained']


def test_camera_turn_keeps_the_single_lying_person():
    t = LyingTracker(sustain=5)
    frames = [[det('lying', [100, 300, 400, 380])]] * 15 + [[det('lying', [520, 300, 820, 380])]] * 15
    assert names(run(t, frames)) == ['lying_sustained']


def test_person_leaving_the_frame_drops_the_track():
    t = LyingTracker(sustain=5, gap=2)
    ev = run(t, [[det('lying')]] * 30 + [[]] * 15)
    assert names(ev) == ['lying_sustained', 'lying_ended'] and t.tracks == []


def test_non_person_and_bad_detections_are_ignored():
    t = LyingTracker(sustain=1)
    frames = [[dict(target='backpack', xyxy=BOX, posture=dict(code='lying')), dict(target='person'), dict(target='person', xyxy=[1, 2])]] * 20
    assert run(t, frames) == [] and t.tracks == []


def test_detection_without_posture_counts_as_unknown():
    t = LyingTracker(sustain=5, gap=2)
    frames = [[det('lying')]] * 10 + [[dict(target='person', xyxy=BOX)]] * 20
    assert run(t, frames) == []


def test_default_threshold_is_15_seconds():
    t = LyingTracker()
    ev = run(t, [[det('lying')]] * 100)
    assert ev[0][0] == 15.0 and '15초' in ev[0][1]['message']

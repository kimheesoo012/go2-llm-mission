from alerts import AlertCenter
from help_request import find_help_request

LYING = dict(event='lying_sustained', track=1, seconds=15.0, message='누운 자세가 15초 이상 이어서 관측됨')


def test_help_phrase_is_urgent():
    c = AlertCenter()
    a = c.speech(0, find_help_request('살려주세요 살려주세요'), 'rec1')
    assert (a['level'], a['label'], a['title'], a['sound']) == (3, '긴급 확인', '도움 요청 발화', True)
    assert a['record_ids'] == ['rec1'] and "'살려주세요' 2회" in a['message']


def test_nothing_to_flag_makes_no_alert():
    c = AlertCenter()
    assert c.speech(0, find_help_request('안녕하세요')) is None
    assert c.speech(0, None) is None and c.lying(0, dict(event='lying_ended')) is None
    assert c.active() == []


def test_single_suspect_is_a_note_without_sound():
    c = AlertCenter()
    a = c.speech(0, find_help_request('살려조세요'))
    assert (a['level'], a['label'], a['sound']) == (1, '참고', False)


def test_repeated_suspect_in_one_record_needs_checking():
    c = AlertCenter()
    a = c.speech(0, find_help_request('사랑해주세요 ' * 4))
    assert (a['level'], a['title']) == (2, '도움 요청 의심 발화') and '원본 음성 확인 필요' in a['message']


def test_suspect_in_two_records_close_in_time_is_raised():
    c = AlertCenter(cooldown=0)
    one = find_help_request('사랑해주세요 사랑해주세요')
    assert c.speech(0, one, 'a')['level'] == 1
    b = c.speech(20, one, 'b')
    assert b['level'] == 2 and '유사 발화 기록 2건' in b['message']
    assert c.speech(200, one, 'c')['level'] == 1  # outside the 60 s window


def test_lying_alone_needs_checking():
    c = AlertCenter()
    a = c.lying(0, LYING)
    assert (a['level'], a['title']) == (2, '누운 자세 지속')
    assert '쓰러' not in a['message'] and '의식' not in a['message']


def test_lying_after_help_phrase_is_urgent_and_does_not_claim_the_speaker():
    c = AlertCenter()
    c.speech(0, find_help_request('살려주세요'))
    a = c.lying(10, LYING)
    assert a['level'] == 3 and '같은 시간대에 도움 요청 발화 기록 (발화자 미확인)' in a['message']


def test_suspect_after_lying_is_urgent():
    c = AlertCenter()
    c.lying(0, LYING)
    a = c.speech(10, find_help_request('살려조세요'))
    assert a['level'] == 3 and '누운 자세 지속 관측 (발화자 미확인)' in a['message']


def test_far_apart_in_time_is_not_linked():
    c = AlertCenter()
    c.speech(0, find_help_request('살려조세요'))
    assert c.lying(100, LYING)['level'] == 2


def test_same_kind_inside_cooldown_is_merged():
    c = AlertCenter(cooldown=30)
    first = c.speech(0, find_help_request('살려주세요'), 'a')
    again = c.speech(10, find_help_request('도와주세요'), 'b')
    assert again['id'] == first['id'] and again['count'] == 2 and again['new'] is False
    assert again['record_ids'] == ['a', 'b'] and len(c.active()) == 1
    assert c.speech(100, find_help_request('살려주세요'))['id'] != first['id']


def test_merge_upgrades_the_level():
    c = AlertCenter()
    low = c.speech(0, find_help_request('살려조세요'))
    high = c.speech(5, find_help_request('살려주세요'))
    assert high['id'] == low['id'] and high['level'] == 3 and high['new'] is True and high['sound'] is True


def test_ack_removes_from_active_and_next_one_is_new():
    c = AlertCenter()
    a = c.speech(0, find_help_request('살려주세요'))
    assert c.ack(a['id']) is True and c.active() == [] and c.ack('nope') is False
    b = c.speech(5, find_help_request('살려주세요'))
    assert b['id'] != a['id'] and len(c.history()) == 2


def test_active_is_sorted_by_level_then_newest():
    c = AlertCenter()
    c.lying(0, LYING)
    c.speech(100, find_help_request('살려조세요'))
    c.speech(200, find_help_request('살려주세요'))  # cooldown passed -> separate alert
    assert [a['level'] for a in c.active()] == [3, 2, 1]


def test_keep_limit():
    c = AlertCenter(cooldown=0, keep=5)
    for i in range(20):
        c.speech(i * 100, find_help_request('살려주세요'))
    assert len(c.history()) == 5

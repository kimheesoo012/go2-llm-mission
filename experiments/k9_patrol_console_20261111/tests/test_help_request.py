import pytest
from help_request import find_help_request, similarity, jamo_distance, tokens


def code(text):
    return find_help_request(text)['code']


# --- exact help phrases -------------------------------------------------
@pytest.mark.parametrize('text', [
    '살려주세요', '살려 주세요', '살려주세요! 살려주세요!', '도와주세요', '도와 주세요', '도와줘', '살려줘요',
    '사람 살려', '살려', '사람살려주세요', '제발 좀 도와주세요', '여기 구해주세요', '구해 줘', '119 불러주세요',
    '구급차 좀 불러주세요', '살려주세요\n도와주세요\n살려주세요',
])
def test_help(text):
    r = find_help_request(text)
    assert r['code'] == 'help' and r['priority'] == 3 and r['label'] == '도움 요청'


# --- must NOT be help: same stems in ordinary sentences -----------------
@pytest.mark.parametrize('text', [
    '도와주셔서 감사합니다', '도와줘서 고마워', '도와드릴까요', '제가 도와줄게요', '분위기를 살려야 해요',
    '친구 해주세요', '친구해줘', '그 책은 어디서 구해요', '1190원입니다', '안녕하세요', '', '   ', None, 123,
])
def test_not_help(text):
    assert code(text) == 'none'


# --- real 11/05 records --------------------------------------------------
def test_1105_misheard_four_times():
    r = find_help_request('사랑해주세요 사랑해주세요 사랑해주세요 사랑해주세요')
    assert r['code'] == 'suspect' and r['priority'] == 2
    hit = r['hits'][0]
    assert (hit['text'], hit['kind'], hit['target'], hit['count']) == ('사랑해주세요', 'repeat', '살려주세요', 4)
    assert '원본 음성 확인 필요' in r['reason']


def test_1105_help_with_misheard_tail():
    r = find_help_request('살려주세요 살려주세요 눈 와주세요 눈 와주세요')
    assert r['code'] == 'help'
    assert [(h['text'], h['count']) for h in r['hits']] == [('살려주세요', 2), ('와주세요', 2)]


def test_misheard_tail_alone_is_suspect():
    r = find_help_request('눈 와주세요 눈 와주세요')
    assert r['code'] == 'suspect' and r['hits'][0]['target'] == '도와주세요'


# --- suspect: one jamo away, not a word ----------------------------------
@pytest.mark.parametrize('text', ['살려조세요', '도와주세오', '살러주세요', '더와주세요'])
def test_near_once(text):
    r = find_help_request(text)
    assert r['code'] == 'suspect' and r['priority'] == 1 and r['hits'][0]['kind'] == 'near'


# --- ordinary requests said once are not flagged -------------------------
@pytest.mark.parametrize('text', [
    '사랑해주세요', '길 좀 알려주세요', '이것 좀 보여주세요', '문 좀 열어주세요', '확인 해주세요', '이리 와주세요',
    '잠깐만 기다려주세요', '여기서 내려주세요', '조용히 해주세요', '사진 좀 봐주세요', '좀 비켜주세요',
])
def test_similar_once_is_not_flagged(text):
    r = find_help_request(text)
    assert r['code'] == 'none'


def test_single_similar_is_kept_as_weak():
    r = find_help_request('사랑해주세요')
    assert r['weak'] and r['weak'][0]['text'] == '사랑해주세요' and r['hits'] == []


def test_ordinary_lookalike_needs_repetition():
    assert code('알려주세요') == 'none'
    assert code('알려주세요 알려주세요') == 'suspect'


def test_different_ordinary_requests_do_not_add_up():
    # Two different requests are not a repetition.
    assert code('이것 좀 보여주세요 그리고 저기서 내려주세요') == 'none'


def test_repeat_priority():
    assert find_help_request('사랑해주세요 사랑해주세요')['priority'] == 1
    assert find_help_request('사랑해주세요 사랑해주세요 사랑해주세요')['priority'] == 2


def test_transcript_is_not_rewritten():
    r = find_help_request('사랑해주세요, 사랑해주세요.')
    assert r['hits'][0]['text'] == '사랑해주세요'  # as written, never "살려주세요"


def test_similarity_values_used_in_notes():
    assert round(similarity('사랑해주세요', '살려주세요'), 2) == 0.75
    assert round(similarity('안녕하세요', '살려주세요'), 2) == 0.52
    assert jamo_distance('살려조세요', '살려주세요') == 1
    assert jamo_distance('사랑해주세요', '살려주세요') > 1
    assert tokens('살려주세요!! (큰 소리) help 119') == ['살려주세요', '큰', '소리', '119']


def test_split_help_phrase_is_one_hit():
    r = find_help_request('살려 주세요 살려 주세요')
    assert r['code'] == 'help' and [(h['text'], h['count']) for h in r['hits']] == [('살려주세요', 2)] and r['weak'] == []
    assert find_help_request('사람 살려 주세요')['hits'][0]['text'] == '살려주세요'


def test_bare_ending_is_not_a_candidate():
    for text in ('물 주세요 물 주세요', '이거 주세요 저거 주세요 그것도 주세요', '줘 줘 줘'):
        r = find_help_request(text)
        assert r['code'] == 'none' and r['weak'] == []

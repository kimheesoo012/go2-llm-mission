import json
import pytest
from patrol_report import build_facts, rule_overview, check_overview, make_report


def obs(i, time, transcript='', count=1, labels=()):
    return dict(record_id=f'{i:032x}', time=time, transcript=transcript, person_seen=count is not None,
                person_count=count, postures=[dict(frame_person_index=n, label=l) for n, l in enumerate(labels, 1)])


RECORDS = [
    obs(1, '2026-11-05T10:01:38+00:00', labels=['서 있음']),
    obs(2, '2026-11-05T10:03:10+00:00', labels=['앉아 있음', '판단 불가'], count=2),
    obs(3, '2026-11-05T10:05:00+00:00', '사랑해주세요 사랑해주세요 사랑해주세요 사랑해주세요', labels=['누워 있음']),
    obs(4, '2026-11-05T10:06:20+00:00', '살려주세요 살려주세요 눈 와주세요 눈 와주세요', labels=['누워 있음']),
    obs(5, '2026-11-05T10:09:00+00:00', '안녕하세요', count=None),
    obs(6, '2026-11-05T10:12:00Z', labels=['앉아 있음']),
]


def fake_chat(text):
    def chat(payload):
        chat.payload = payload
        return {'message': {'content': json.dumps({'overview': text}, ensure_ascii=False)}}
    return chat


def test_facts():
    f = build_facts(list(reversed(RECORDS)))  # order of input does not matter
    assert (f['date'], f['start'], f['end'], f['minutes']) == ('2026-11-05', '19:01', '19:12', 10)  # KST
    assert (f['records'], f['person_records'], f['max_people_in_frame'], f['speech_records']) == (6, 5, 2, 3)
    assert (f['help_records'], f['suspect_records'], f['lying_records']) == (1, 1, 2)
    assert f['postures'] == {'앉아 있음': 2, '누워 있음': 2, '서 있음': 1, '판단 불가': 1}
    assert [(e['time'], e['kinds']) for e in f['events']] == [
        ('19:05:00', ['도움 요청 의심 발화', '누운 자세 후보']), ('19:06:20', ['도움 요청 발화', '누운 자세 후보'])]
    assert f['position'] == '미수신'


def test_no_records():
    for empty in ([], None, [dict(time='not a time')], [dict(transcript='x')]):
        with pytest.raises(ValueError):
            build_facts(empty)


def test_rule_overview_with_and_without_flags():
    text = rule_overview(build_facts(RECORDS))
    assert '기록 6건' in text and '도움 요청 발화 1건, 도움 요청 의심 발화 1건, 누운 자세 후보 2건' in text and '원본 영상·음성 확인' in text
    quiet = rule_overview(build_facts(RECORDS[:2]))
    assert '표시된 기록은 없습니다' in quiet


def test_report_without_llm():
    r = make_report(RECORDS)
    assert r['overview_source'] == 'rule' and r['llm_error'] == ''
    md = r['markdown']
    assert '# 순찰 보고서 · 2026-11-05' in md and '위치: 미수신' in md and '| 19:06:20 | 도움 요청 발화 + 누운 자세 후보 |' in md
    assert "'사랑해주세요' 4회 반복" in md and '총평 작성: 규칙 문장' in md


def test_report_uses_valid_llm_text():
    chat = fake_chat('19:01부터 19:12까지 기록 6건이 저장되었습니다. 도움 요청 발화 1건과 누운 자세 후보 2건은 원본 확인이 필요합니다.')
    r = make_report(RECORDS, 'qwen3.5:4b', chat)
    assert r['overview_source'] == 'llm' and r['overview'].startswith('19:01부터')
    p = chat.payload
    assert p['think'] is False and p['options']['temperature'] == 0 and p['format']['required'] == ['overview']
    sent = json.loads(p['messages'][1]['content'])
    assert sent['records'] == 6 and 'transcript' not in json.dumps(sent)  # only computed facts go to the LLM


@pytest.mark.parametrize('text,why', [
    ('기록 7건이 저장되었고 사람이 탐지되었습니다.', '집계에 없는 숫자'),
    ('기록 6건 중 한 명이 쓰러져 있었던 것으로 보입니다.', '단정 표현'),
    ('누운 사람은 의식이 없는 것으로 추정됩니다. 기록 6건.', '단정 표현'),
    ('짧음', '총평 길이'),
])
def test_bad_llm_text_falls_back_to_rules(text, why):
    r = make_report(RECORDS, 'qwen3.5:4b', fake_chat(text))
    assert r['overview_source'] == 'rule' and why in r['llm_error'] and '기록 6건' in r['overview']


def test_llm_failure_falls_back_to_rules():
    def down(payload):
        raise ConnectionError('Ollama 연결 실패')
    r = make_report(RECORDS, 'qwen3.5:4b', down)
    assert r['overview_source'] == 'rule' and 'ConnectionError' in r['llm_error'] and r['markdown']

    def wrong_shape(payload):
        return {'message': {'content': '{"overview":"기록 6건 저장.","extra":1}'}}
    assert 'ValueError' in make_report(RECORDS, 'm', wrong_shape)['llm_error']


def test_check_overview_accepts_times_and_counts_from_facts():
    f = build_facts(RECORDS)
    assert check_overview('2026-11-05 19:01~19:12, 약 10분 동안 기록 6건, 사람 탐지 5건.', f)

from review_priority import rule_priority, rule_selection, merge_selection, row_from_source


def row(i, speech='', pose='', person='관찰됨 · 프레임 탐지 1명'):
    r = dict(id=f'r{i}', time='2026-11-05T10:01:00')
    if speech: r['speech'] = speech
    if pose: r['pose'] = pose
    if person: r['person'] = person
    return r


def test_scores():
    assert rule_priority(row(1, '살려주세요'))['score'] == 3
    assert rule_priority(row(1, '사랑해주세요 ' * 4))['score'] == 2
    assert rule_priority(row(1, '사랑해주세요 사랑해주세요'))['score'] == 1
    assert rule_priority(row(1, pose='#1 누워 있음'))['score'] == 2
    assert rule_priority(row(1, '살려주세요', '#1 누워 있음'))['score'] == 4
    assert rule_priority(row(1, '살려조세요', '#1 누워 있음 · #2 서 있음'))['score'] == 2
    for ordinary in (row(1), row(1, '안녕하세요'), row(1, pose='#1 앉아 있음'), row(1, pose='#1 판단 불가'), dict(id='r1')):
        assert rule_priority(ordinary)['score'] == 0


def test_evidence_keys_match_the_selection_schema():
    p = rule_priority(row(1, '살려주세요', '#1 누워 있음'))
    assert p['evidence'] == ['speech', 'pose'] and '누워 있음 자세 후보' in p['reason']


def test_rule_selection_order_and_overflow():
    rows = [row(1, pose='#1 누워 있음'), row(2), row(3, '살려주세요'), row(4, '도와주세요', '#1 누워 있음'), row(5, '사랑해주세요 ' * 3)]
    picked, overflow = rule_selection(rows, 5)
    assert [x['id'] for x in picked] == ['r4', 'r3', 'r1', 'r5'] and overflow == 0
    picked, overflow = rule_selection(rows, 2)
    assert [x['id'] for x in picked] == ['r4', 'r3'] and overflow == 2


def test_llm_cannot_drop_a_rule_pick():
    rows = [row(1, '살려주세요'), row(2, pose='#1 누워 있음'), row(3, pose='#1 앉아 있음')]
    out, overflow = merge_selection(rows, [], 5)
    assert [(x['id'], x['source']) for x in out] == [('r1', 'rule'), ('r2', 'rule')] and overflow == 0
    assert out[0]['reason'].startswith('도움 요청 표현')


def test_llm_reason_is_used_for_rule_picks_and_additions_follow():
    rows = [row(1, '살려주세요'), row(2, pose='#1 누워 있음'), row(3, pose='#1 판단 불가'), row(4)]
    llm = [dict(id='r3', reason='자세 판단 불가 기록이라 원본 확인 필요', evidence=['pose']),
           dict(id='r1', reason="'살려주세요' 발화가 있어 원본 확인 필요", evidence=['speech', 'person'])]
    out, _ = merge_selection(rows, llm, 5)
    assert [(x['id'], x['source']) for x in out] == [('r1', 'rule+llm'), ('r2', 'rule'), ('r3', 'llm')]
    assert out[0]['reason'].startswith("'살려주세요' 발화") and out[0]['rule_reason'].startswith('도움 요청 표현')
    assert out[0]['evidence'] == ['person', 'speech']


def test_llm_additions_stop_at_the_limit_and_never_push_out_rule_picks():
    rows = [row(1, '살려주세요'), row(2, pose='#1 누워 있음')] + [row(i) for i in range(3, 9)]
    llm = [dict(id=f'r{i}', reason='x', evidence=['person']) for i in range(3, 9)]
    out, _ = merge_selection(rows, llm, 3)
    assert [x['id'] for x in out] == ['r1', 'r2', 'r3']


def test_row_from_source():
    source = dict(record_id='abc', evidence=[dict(id='time', label='기록 시각', text='2026-11-05T10:01:00', truncated=False),
                                             dict(id='speech', label='STT', text='살려주세요', truncated=False)])
    assert row_from_source(source) == dict(id='abc', time='2026-11-05T10:01:00', speech='살려주세요')

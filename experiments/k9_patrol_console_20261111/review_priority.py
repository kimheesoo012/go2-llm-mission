"""Rule priority for the important-record selection.

Agreed principle: rules decide the clear cases first; the LLM explains them and
may ADD ambiguous records, but it may not drop a record the rules marked.
(On 11/07 the faster LLM call returned 2 records instead of 5. With rules in
front, whether a clear record is shown no longer depends on the model's mood.)

Works on the compact rows highlights.compact() sends to the LLM:
    dict(id='r1', time=..., speech='STT 원문', person='관찰됨 · ...', pose='#1 누워 있음 · #2 서 있음')
"""
from help_request import find_help_request

MUST = 2  # score at or above this is always shown


def rule_priority(row):
    """Score one record. 0 = nothing the rules can point at."""
    speech = find_help_request(row.get('speech') or '')
    lying = '누워' in (row.get('pose') or '')
    score, reasons = 0, []
    if speech['code'] == 'help':
        score = 3
        reasons.append(speech['reason'])
    elif speech['code'] == 'suspect':
        score = 2 if speech['priority'] >= 2 else 1
        reasons.append(speech['reason'])
    if lying:
        reasons.append('누워 있음 자세 후보')
        # Lying together with a help / suspect phrase in the same record ranks above either alone.
        score = score + 1 if score else 2
    evidence = (['speech'] if speech['code'] != 'none' else []) + (['pose'] if lying else [])
    return dict(score=score, reason=' · '.join(reasons), evidence=evidence, speech=speech['code'], lying=lying)


def row_from_source(source):
    """highlights.make_source(record) -> compact row."""
    row = {'id': source['record_id']}
    for e in source['evidence']:
        row[e['id']] = e['text']
    return row


def rule_selection(rows, limit):
    """Records the rules mark, highest score first, input order kept inside a score."""
    scored = [(rule_priority(r), r) for r in rows]
    picked = [dict(id=r['id'], score=p['score'], reason=p['reason'], evidence=p['evidence'])
              for p, r in scored if p['score'] >= MUST]
    picked.sort(key=lambda x: -x['score'])
    return picked[:limit], max(0, len(picked) - limit)


def merge_selection(rows, llm_items, limit):
    """Rule picks first, then the LLM's additions. The LLM cannot remove a rule pick.

    llm_items: [dict(id=..., reason=..., evidence=[...])] in the LLM's order.
    Returns (items, overflow). Each item has source 'rule', 'rule+llm' or 'llm'.
    overflow = rule picks that did not fit into `limit` (the caller should say so on screen).
    """
    rule_items, overflow = rule_selection(rows, limit)
    by_id = {x['id']: x for x in llm_items}
    out = []
    for item in rule_items:
        llm = by_id.get(item['id'])
        out.append(dict(id=item['id'], source='rule+llm' if llm else 'rule', rule_reason=item['reason'],
                        reason=llm['reason'] if llm else item['reason'],
                        evidence=sorted(set(item['evidence']) | set(llm['evidence'] if llm else []))))
    taken = {x['id'] for x in out}
    for item in llm_items:
        if len(out) >= limit:
            break
        if item['id'] not in taken:
            out.append(dict(id=item['id'], source='llm', rule_reason='', reason=item['reason'],
                            evidence=list(item['evidence'])))
            taken.add(item['id'])
    return out, overflow

"""Score the important-record selection on labelled scenarios.

    --mode rule    review_priority.rule_selection only (no LLM)
    --mode llm     the console's own highlights code and prompt (Ollama must be running)
    --mode merged  rule picks first, then the LLM's additions (review_priority.merge_selection)

Usage (from this folder's parent):
    python eval/selection_eval.py --mode rule
    python eval/selection_eval.py --mode llm    --console /path/to/k9_patrol_console [--model qwen3.5:4b]
    python eval/selection_eval.py --mode merged --console /path/to/k9_patrol_console

llm / merged call highlights.HighlightsService._select directly, so nothing is written to the DB.
A scenario passes when every `must` record is selected, no `must_not` record is selected,
and `first` (if set) is ranked first.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from review_priority import merge_selection, rule_selection  # noqa: E402

LABELS = dict(time='기록 시각', speech='STT 발화 원문 · 발화자 미확인', person='사람 등장·탐지 기록', pose='규칙 기반 자세 후보')


def sources(rows):
    """Compact rows -> the make_source() shape highlights._select expects."""
    return [dict(record_id=r['id'], evidence=[dict(id=k, label=LABELS[k], text=r[k], truncated=False)
                                               for k in ('time', 'speech', 'person', 'pose') if r.get(k)]) for r in rows]


def llm_select(highlights, rows, model, limit):
    picked = highlights.HighlightsService._select(None, sources(rows), model, limit)
    return [dict(id=x['record_id'], reason=x['reason'], evidence=x['evidence_ids']) for x in picked]


def score(scenario, ids):
    missed = [x for x in scenario['must'] if x not in ids]
    wrong = [x for x in ids if x in scenario['must_not']]
    first_ok = not scenario.get('first') or (ids[:1] == [scenario['first']])
    return dict(missed=missed, wrong=wrong, first_ok=first_ok, passed=not missed and not wrong and first_ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['rule', 'llm', 'merged'], default='rule')
    ap.add_argument('--console', default='')
    ap.add_argument('--model', default='qwen3.5:4b')
    ap.add_argument('--scenarios', default=str(ROOT / 'eval' / 'selection_scenarios.json'))
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    highlights = None
    if args.mode != 'rule':
        if not args.console:
            sys.exit('--console 에 k9_patrol_console 폴더 경로를 지정하세요.')
        sys.path.insert(0, str(Path(args.console).resolve()))
        import highlights  # noqa: E402
        try:
            import ollama_connection
            ollama_connection.start_background()
        except Exception as exc:  # older console versions have no such helper
            print('ollama_connection.start_background 생략:', exc)
    with open(args.scenarios, encoding='utf-8') as f:
        scenarios = json.load(f)['scenarios']

    lines = [f'# 중요 장면 선정 시나리오 채점 · mode={args.mode}' + (f' · model={args.model}' if highlights else ''), '',
             '| # | 시나리오 | 기록 | 필수 | 선정 결과 | 놓침 | 불필요 선정 | 1순위 | 시간(초) | 판정 |', '|---|---|---|---|---|---|---|---|---|---|']
    passed, reasons = 0, []
    for n, s in enumerate(scenarios, 1):
        t = time.monotonic()
        error = ''
        try:
            if args.mode == 'rule':
                items = rule_selection(s['records'], s['limit'])[0]
            else:
                items = llm_select(highlights, s['records'], args.model, s['limit'])
                if args.mode == 'merged':
                    items = merge_selection(s['records'], items, s['limit'])[0]
        except Exception as exc:
            items, error = [], f'{type(exc).__name__}: {exc}'
        seconds = time.monotonic() - t
        ids = [x['id'] for x in items]
        r = score(s, ids)
        ok = r['passed'] and not error
        passed += ok
        lines.append(f"| {n} | {s['name']} | {len(s['records'])} | {', '.join(s['must']) or '없음'} | {', '.join(ids) or '없음'} | "
                     f"{', '.join(r['missed']) or '-'} | {', '.join(r['wrong']) or '-'} | "
                     f"{'-' if not s.get('first') else 'O' if r['first_ok'] else 'X'} | {seconds:.1f} | {'오류: ' + error if error else 'O' if ok else 'X'} |")
        reasons += [f"- {n}. {x['id']} ({x.get('source', args.mode)}): {x['reason']}" for x in items]
    lines += ['', f'통과 {passed}/{len(scenarios)}', '', '## 선정 이유'] + reasons
    text = '\n'.join(lines) + '\n'
    out = Path(args.out or ROOT / 'eval' / f'selection_result_{args.mode}.md')
    out.write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()

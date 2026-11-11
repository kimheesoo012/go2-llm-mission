"""Compare help-request detection on stored transcripts.

    baseline  the transcript contains 살려주세요 or 도와주세요 as written
    rules     help_request.find_help_request (help or suspect counts as flagged)

Usage (from this folder's parent):  python eval/keyword_eval.py [--csv eval/transcripts.csv]
The CSV has three real records (11/02, 11/05) and ordinary sentences written for this check.
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from help_request import find_help_request  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=str(ROOT / 'eval' / 'transcripts.csv'))
    ap.add_argument('--out', default=str(ROOT / 'eval' / 'keyword_eval_result.md'))
    args = ap.parse_args()
    with open(args.csv, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    table, detail = Counter(), []
    for r in rows:
        base = any(k in r['transcript'].replace(' ', '') for k in ('살려주세요', '도와주세요'))
        found = find_help_request(r['transcript'])
        table[r['said'], 'baseline', base] += 1
        table[r['said'], 'rules', found['code']] += 1
        detail.append((r, base, found))
    n_help = sum(r['said'] == 'help' for r in rows)
    n_ord = len(rows) - n_help
    lines = ['# 도움 요청 판정 비교', '',
             f'기록 {len(rows)}건: 실제 도움 요청 발화 기록 {n_help}건, 일상 문장(직접 작성) {n_ord}건', '',
             '| | 기준: 원문 그대로 일치 | 규칙: 도움 요청 | 규칙: 의심 | 규칙: 표시 안 함 |', '|---|---|---|---|---|',
             f"| 실제 도움 요청 {n_help}건 | {table['help', 'baseline', True]} | {table['help', 'rules', 'help']} | "
             f"{table['help', 'rules', 'suspect']} | {table['help', 'rules', 'none']} |",
             f"| 일상 문장 {n_ord}건 | {table['ordinary', 'baseline', True]} | {table['ordinary', 'rules', 'help']} | "
             f"{table['ordinary', 'rules', 'suspect']} | {table['ordinary', 'rules', 'none']} |", '',
             '## 기록별 결과', '| 실제 | 출처 | STT 원문 | 기준 | 규칙 | 근거 |', '|---|---|---|---|---|---|']
    for r, base, found in detail:
        mark = {'help': '도움 요청', 'suspect': '의심', 'none': '-'}[found['code']]
        lines.append(f"| {'도움 요청' if r['said'] == 'help' else '일상'} | {r['source']} | {r['transcript']} | "
                     f"{'일치' if base else '-'} | {mark} | {found['reason']} |")
    text = '\n'.join(lines) + '\n'
    Path(args.out).write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()

"""Jamo similarity of phrases to the help phrases. Shows why similarity alone is not enough.

Usage:  python eval/similarity_table.py   -> eval/similarity_table.md
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from help_request import TARGETS, jamo_distance, similarity  # noqa: E402

GROUPS = [
    ('11/05 실제 오인식', ['사랑해주세요', '눈와주세요', '와주세요']),
    ('자모 1개 차이 (가정한 오인식)', ['살려조세요', '살러주세요', '도와주세오', '더와주세요']),
    ('자모 1개 차이인 실제 단어', ['알려주세요', '말려주세요', '날려주세요', '살펴주세요']),
    ('일상 부탁 표현', ['보여주세요', '봐주세요', '내려주세요', '빌려주세요', '기다려주세요', '열어주세요', '비켜주세요', '해주세요']),
    ('일상 표현', ['안녕하세요', '사랑해요', '괜찮아요', '감사합니다']),
]


def main():
    lines = ['# 도움 요청 표현과의 자모 유사도', '',
             '자모로 풀어 쓴 뒤 `difflib.SequenceMatcher` 비율로 계산. 가장 가까운 표현 기준.', '',
             '| 구분 | 표현 | 가장 가까운 표현 | 유사도 | 자모 차이 |', '|---|---|---|---|---|']
    for group, words in GROUPS:
        for w in words:
            score, target = max((similarity(w, t), t) for t in TARGETS)
            lines.append(f'| {group} | {w} | {target} | {score:.2f} | {jamo_distance(w, target)} |')
    span = lambda words: '{:.2f}~{:.2f}'.format(*(f(max(similarity(w, t) for t in TARGETS) for w in words) for f in (min, max)))
    lines += ['', f'- 실제 오인식({span(GROUPS[0][1])})과 일상 부탁 표현({span(GROUPS[3][1])})의 유사도 범위가 겹친다.',
              '- 그래서 유사도만으로 의심을 붙이지 않고, 같은 표현이 한 기록에서 2회 이상 반복될 때만 의심으로 올린다.',
              '- 자모 1개 차이는 1회만 나와도 의심으로 올리되, 실제 단어(알려주세요 등)는 반복될 때만 올린다.']
    out = ROOT / 'eval' / 'similarity_table.md'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(out.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()

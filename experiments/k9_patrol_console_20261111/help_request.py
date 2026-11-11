"""Help-request detection on STT transcripts (rule based, no LLM).

STT output is not reliable on the robot microphone: on 11/05 a spoken
"살려주세요" was stored as "사랑해주세요" (x4) and as "눈 와주세요" (x2).
This module never rewrites the transcript. It only attaches a level:

    help     a help phrase is in the transcript as written
    suspect  the transcript does not say it, but looks like a misheard help phrase
             -> the operator should listen to the original audio
    none     nothing to flag

Suspect has two separate conditions, because phonetic similarity alone cannot
tell "사랑해주세요" from an ordinary request such as "보여주세요"
(both are about as close to a help phrase; see eval/similarity_table.md):

    near    one jamo away from a help phrase and not an ordinary word
            (살려조세요, 도와주세여)
    repeat  a similar phrase (ratio >= LOOSE) said REPEAT_MIN times or more in
            one record (사랑해주세요 x4). Ordinary speech rarely repeats one
            short request several times in a row.

A single loosely similar phrase is not flagged; it is returned under `weak`.
"""
import difflib
import re
import unicodedata

METHOD = 'help_keywords_v1'
LABELS = {'help': '도움 요청', 'suspect': '도움 요청 의심', 'none': ''}

# Request endings. A help phrase must END with one, so that
# "도와주셔서 감사합니다" or "도와줘서 고마워" do not match.
_END = r'(?:주세요|주세여|주십시오|주십쇼|주시오|줘요|줘|주라)'
_BARE_END = re.compile(r'^' + _END + r'$')
_KEYWORDS = [
    # 살려 / 도와 may follow other syllables in the same word (사람살려주세요, 좀도와주세요)
    ('살려주세요', re.compile(r'살려' + _END + r'$')),
    ('도와주세요', re.compile(r'도와' + _END + r'$')),
    # 구해 only at the start of a word: "친구 해주세요" must not match
    ('구해주세요', re.compile(r'^구해' + _END + r'$')),
    ('살려', re.compile(r'^(?:사람)?살려$')),
    ('119', re.compile(r'(?<!\d)119(?!\d)')),
    ('구급차', re.compile(r'구급차')),
]
# Phrases compared by sound. 구해주세요 is left out on purpose: "해주세요" alone
# scores 0.89 against it, so every "~해주세요" would be a candidate.
TARGETS = ('살려주세요', '살려줘', '도와주세요', '도와줘')
# Real words that are one jamo away from a target. They count only when repeated.
ORDINARY = frozenset('알려주세요 말려주세요 날려주세요 살펴주세요 알려줘 말려줘 날려줘 달려줘 살펴줘'.split())
LOOSE = 0.70      # tentative: chosen so that both 11/05 cases (0.75, 0.76 / 0.89) are kept
REPEAT_MIN = 2    # same similar phrase this many times in one record -> suspect
PRIORITY_REPEAT = 3


def jamo(text):
    """Hangul syllables -> conjoining jamo (살 -> ㅅㅏㄹ). Other characters are dropped."""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if 'ᄀ' <= c <= 'ᇿ')


def similarity(a, b):
    """0..1, on jamo. 사랑해주세요 vs 살려주세요 = 0.75."""
    return difflib.SequenceMatcher(None, jamo(a), jamo(b), autojunk=False).ratio()


def jamo_distance(a, b):
    """Edit distance on jamo (insert / delete / substitute = 1)."""
    a, b = jamo(a), jamo(b)
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def tokens(transcript):
    """Words with punctuation removed. Only Hangul and digits are kept."""
    text = unicodedata.normalize('NFC', transcript or '')
    out = []
    for raw in re.split(r'\s+', text):
        word = ''.join(c for c in raw if '가' <= c <= '힣' or c.isdigit())
        if word:
            out.append(word)
    return out


def _keyword(word):
    for name, pattern in _KEYWORDS:
        if pattern.search(word):
            return name
    return None


def _best_target(word):
    return max(((similarity(word, t), t) for t in TARGETS), key=lambda x: x[0])


def _near(word):
    """One jamo away from a target with the same number of syllables."""
    for t in TARGETS:
        if len(word) == len(t) and jamo_distance(word, t) == 1:
            return t
    return None


def find_help_request(transcript):
    """Classify one record's transcript. Returns a dict, never raises on bad input."""
    result = dict(code='none', label='', priority=0, reason='', hits=[], weak=[], method=METHOD)
    if not isinstance(transcript, str) or not transcript.strip():
        return result
    words = tokens(transcript)
    exact, similar = {}, {}
    i = 0
    while i < len(words):
        single = words[i]
        pair = single + words[i + 1] if i + 1 < len(words) else None
        # "살려 주세요" / "도와 줘" are split by STT: prefer the joined form when it is a full help phrase.
        name = _keyword(single)
        if name in (None, '살려') and pair and not _keyword(words[i + 1]) and _keyword(pair) in TARGETS + ('구해주세요',):
            name, single, i = _keyword(pair), pair, i + 1
        if name:
            hit = exact.setdefault(single, dict(text=single, kind='keyword', target=name, score=1.0, count=0))
            hit['count'] += 1
            i += 1
            continue
        # Similar by sound: the single word, or two words joined ("눈 와주세요").
        score, target = _best_target(single)
        text = single
        if pair and len(pair) <= 7 and not _keyword(words[i + 1]):
            pair_score, pair_target = _best_target(pair)
            # Join only when the joined form is closer than either word alone.
            if pair_score > max(score, _best_target(words[i + 1])[0]):
                score, target, text = pair_score, pair_target, pair
        near = _near(text)
        # A bare ending ("물 주세요") is not a candidate: it is close to every target.
        if (score >= LOOSE or near) and not _BARE_END.match(text):
            hit = similar.setdefault(text, dict(text=text, kind='', target=near or target,
                                                score=round(similarity(text, near or target), 2), count=0,
                                                near=bool(near), ordinary=text in ORDINARY))
            hit['count'] += 1
            if text is pair:
                i += 1
        i += 1

    quote = lambda h: f"'{h['text']}'" + (f" {h['count']}회" if h['count'] > 1 else '')
    if exact:
        hits = list(exact.values())
        result.update(code='help', label=LABELS['help'], priority=3, hits=hits,
                      reason='도움 요청 표현 ' + ', '.join(quote(h) for h in hits))
    suspects = []
    for hit in similar.values():
        near, ordinary = hit.pop('near'), hit.pop('ordinary')
        if hit['count'] >= REPEAT_MIN:
            hit['kind'] = 'repeat'
        elif near and not ordinary:
            hit['kind'] = 'near'
        else:
            hit['kind'] = 'weak'
            result['weak'].append(hit)
            continue
        suspects.append(hit)
    if suspects and not exact:
        repeat = max(h['count'] for h in suspects)
        parts = [f"{quote(h)}{' 반복' if h['count'] > 1 else ''} · '{h['target']}'와 유사({h['score']:.2f})"
                 for h in suspects]
        result.update(code='suspect', label=LABELS['suspect'], priority=2 if repeat >= PRIORITY_REPEAT else 1,
                      hits=suspects, reason=' / '.join(parts) + ' · 원본 음성 확인 필요')
    elif suspects:
        # Already a help request: keep the similar phrases as supporting hits.
        result['hits'] += suspects
    return result

"""A/B: does an initial prompt with the help phrases change what the STT writes?

NOT RUN YET. Written against faster-whisper; if the console uses another STT
library, only transcribe() below needs to change.

Usage:
    python eval/stt_prompt_ab.py recording1.wav recording2.wav [--model small] [--language ko]
For each file it prints the transcript without a prompt, with the prompt, and the
help-request level of both. Use recordings where the spoken words are known
(for example the 11/05 "살려주세요" recordings) and also ordinary speech, because a
prompt can make the model write the help phrase when it was not said.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from help_request import find_help_request  # noqa: E402

PROMPT = '살려주세요. 도와주세요. 구해주세요.'


def transcribe(model, path, language, prompt):
    segments, _ = model.transcribe(str(path), language=language, initial_prompt=prompt or None,
                                   condition_on_previous_text=False, vad_filter=True)
    return ' '.join(s.text.strip() for s in segments)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--model', default='small')
    ap.add_argument('--language', default='ko')
    args = ap.parse_args()
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device='auto', compute_type='int8')
    print('| 파일 | 프롬프트 없음 | 판정 | 프롬프트 있음 | 판정 |\n|---|---|---|---|---|')
    for path in args.files:
        plain = transcribe(model, path, args.language, '')
        primed = transcribe(model, path, args.language, PROMPT)
        level = lambda text: find_help_request(text)['label'] or '-'
        print(f'| {Path(path).name} | {plain} | {level(plain)} | {primed} | {level(primed)} |')


if __name__ == '__main__':
    main()

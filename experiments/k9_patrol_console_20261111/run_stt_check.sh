#!/bin/bash
# STT initial-prompt comparison. Finds a Python that already has faster-whisper;
# if there is none, makes a temporary one under OUT. Results go to OUT.
set -u
OUT="${OUT:-$HOME/Downloads/k9_stt_20261112}"
BASE=https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-help-request-alerts-20261111/experiments/k9_patrol_console_20261111
rm -rf "$OUT"; mkdir -p "$OUT/work"; LOG="$OUT/log.txt"; : > "$LOG"
has() { "$1" -c "import faster_whisper" >/dev/null 2>&1; }
PY=""
echo "[1/3] faster-whisper가 설치된 Python 찾는 중"
for c in python3 python; do command -v $c >/dev/null 2>&1 && has "$(command -v $c)" && PY="$(command -v $c)" && break; done
if [ -z "$PY" ]; then
  while IFS= read -r d; do
    for p in "$d/../../../bin/python" "$d/../../../bin/python3" "$d/../../Scripts/python.exe"; do
      [ -x "$p" ] && has "$p" && PY="$p" && break 2
    done
  done < <(find "$HOME" -maxdepth 8 -type d -name faster_whisper -path '*site-packages*' \
             -not -path "$HOME/Library/*" -not -path "$HOME/Pictures/*" -not -path "$HOME/Music/*" -not -path "$HOME/Movies/*" 2>/dev/null)
fi
if [ -z "$PY" ]; then
  echo "      없음 → 임시 환경을 만들어 설치합니다 (몇 분 걸릴 수 있음)"
  for c in python3.12 python3.11 python3.13 python3.10 python3; do
    command -v $c >/dev/null 2>&1 || continue
    rm -rf "$OUT/venv"; $c -m venv "$OUT/venv" >>"$LOG" 2>&1 || continue
    "$OUT/venv/bin/python" -m pip install -q faster-whisper >>"$LOG" 2>&1 && has "$OUT/venv/bin/python" && PY="$OUT/venv/bin/python" && break
    echo "      $c 로는 설치 실패" | tee -a "$LOG"
  done
fi
if [ -z "$PY" ]; then echo "faster-whisper를 쓸 수 있는 Python을 준비하지 못했습니다. $LOG 확인" | tee "$OUT/ERROR.txt"; exit 1; fi
{ echo "python: $PY"; "$PY" --version; "$PY" -c "import faster_whisper;print('faster-whisper', faster_whisper.__version__)"; } >> "$LOG" 2>&1
echo "      사용: $PY"
echo "[2/3] 콘솔 코드 준비"
cd "$OUT/work" && git clone -q https://github.com/daryung/capstone.git && cd capstone && curl -sL "$BASE/k9-help-request-alerts.patch" | git apply \
  || { echo "코드 준비 실패" | tee "$OUT/ERROR.txt"; exit 1; }
cd k9_patrol_console
echo "[3/3] STT 비교 (모델을 처음 받으면 시간이 걸립니다)"
"$PY" eval/stt_prompt_ab.py data/media/*.wav recordings/test.wav > "$OUT/stt_prompt_ab.md" 2>>"$LOG" || { echo "STT 실행 실패. $LOG 확인" | tee "$OUT/ERROR.txt"; }
cd "$OUT" && rm -rf "$OUT/work" "$OUT/venv"
echo "끝. 결과: $OUT"

#!/bin/bash
# STT 구조 요청 단어 힌트 적용 전후 비교 (맥에서 실행). 11/14 Go2 녹음 20개를 그대로 쓴다.
# faster-whisper 가 이미 설치된 Python만 찾아 쓰고, 새로 설치하지 않는다. 결과는 ~/Downloads/k9_stt_hotwords 에 남는다.
set -u
OUT="$HOME/Downloads/k9_stt_hotwords"; mkdir -p "$OUT/work/eval" "$OUT/wav"
B=https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-shoot-1121/experiments/k9_patrol_console_20261121
L=https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-help-request-alerts-20261111/experiments/k9_patrol_console_20261111
M=https://raw.githubusercontent.com/daryung/capstone/main/k9_patrol_console/data/media
has() { "$1" -c "import faster_whisper, numpy" >/dev/null 2>&1; }
PY=""
for c in python3 python; do command -v $c >/dev/null && has "$(command -v $c)" && PY="$(command -v $c)" && break; done
if [ -z "$PY" ]; then
  while IFS= read -r d; do for p in "$d/../../../bin/python" "$d/../../../bin/python3"; do [ -x "$p" ] && has "$p" && PY="$p" && break 2; done
  done < <(find "$HOME" -maxdepth 8 -type d -name faster_whisper -path '*site-packages*' -not -path "$HOME/Library/*" 2>/dev/null)
fi
[ -z "$PY" ] && { echo "faster-whisper가 설치된 Python을 찾지 못했습니다 (새로 설치하지 않았습니다)." | tee "$OUT/ERROR.txt"; exit 1; }
echo "사용: $PY"
curl -sfL "$B/stt_hotwords_ab.py" -o "$OUT/work/eval/stt_hotwords_ab.py" && curl -sfL "$B/stt_labels_20261114.csv" -o "$OUT/labels.csv" \
  && curl -sfL "https://raw.githubusercontent.com/daryung/capstone/main/k9_patrol_console/help_request.py" -o "$OUT/work/help_request.py" 2>/dev/null \
  || curl -sfL "$B/help_request.py" -o "$OUT/work/help_request.py" || { echo "파일 받기 실패" | tee "$OUT/ERROR.txt"; exit 1; }
tail -n +2 "$OUT/labels.csv" | cut -d, -f1 | while read f; do [ -s "$OUT/wav/$f" ] || curl -sfL "$M/$f" -o "$OUT/wav/$f"; done
echo "녹음 $(ls "$OUT/wav" | wc -l | tr -d ' ')개 · 비교 중 (몇 분 걸립니다)"
cd "$OUT/work" && "$PY" eval/stt_hotwords_ab.py "$OUT/wav" "$OUT/labels.csv" --out "$OUT/result.md" > "$OUT/log.txt" 2>&1
tail -12 "$OUT/log.txt"; echo "끝. 결과: $OUT/result.md"

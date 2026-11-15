#!/bin/bash
# 11/07 96프레임 세트와 저장된 영상에 새 자세 규칙을 다시 돌린다 (포즈 모델 필요).
# ultralytics가 이미 설치된 Python을 찾아 쓰고, 없으면 설치하지 않고 멈춘다. 결과는 OUT에 남는다.
set -u
OUT="${OUT:-$HOME/Downloads/k9_posture_20261115}"
BASE=https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-posture-rules-v3-20261115/experiments/k9_patrol_console_20261115
rm -rf "$OUT"; mkdir -p "$OUT/work"; LOG="$OUT/log.txt"; : > "$LOG"
has() { "$1" -c "import ultralytics, cv2" >/dev/null 2>&1; }
PY=""
echo "[1/3] ultralytics가 설치된 Python 찾는 중"
for c in python3 python; do command -v $c >/dev/null 2>&1 && has "$(command -v $c)" && PY="$(command -v $c)" && break; done
if [ -z "$PY" ]; then
  while IFS= read -r d; do
    for p in "$d/../../../bin/python" "$d/../../../bin/python3"; do
      [ -x "$p" ] && has "$p" && PY="$p" && break 2
    done
  done < <(find "$HOME" -maxdepth 8 -type d -name ultralytics -path '*site-packages*' \
             -not -path "$HOME/Library/*" -not -path "$HOME/Pictures/*" -not -path "$HOME/Music/*" -not -path "$HOME/Movies/*" 2>/dev/null)
fi
if [ -z "$PY" ]; then echo "ultralytics가 설치된 Python을 찾지 못했습니다 (새로 설치하지 않았습니다)." | tee "$OUT/ERROR.txt"; exit 1; fi
{ echo "python: $PY"; "$PY" --version; "$PY" -c "import ultralytics;print('ultralytics', ultralytics.__version__)"; } >> "$LOG" 2>&1
echo "      사용: $PY"
echo "[2/3] 콘솔 코드 준비"
cd "$OUT/work" && git clone -q --depth 1 https://github.com/daryung/capstone.git && cd capstone/k9_patrol_console \
  || { echo "코드 준비 실패" | tee "$OUT/ERROR.txt"; exit 1; }
echo "[3/3] 자세 판별 (기존 규칙 → 새 규칙, 몇 분 걸릴 수 있습니다)"
"$PY" eval/posture_eval.py --out "$OUT/before" >>"$LOG" 2>&1 || echo "기존 규칙 실행 실패" | tee -a "$OUT/ERROR.txt"
(cd .. && curl -sL "$BASE/k9-posture-rules-v3.patch" | git apply) || { echo "패치 적용 실패" | tee -a "$OUT/ERROR.txt"; exit 1; }
"$PY" eval/posture_eval.py --out "$OUT/after_v3" >>"$LOG" 2>&1 || echo "새 규칙 실행 실패" | tee -a "$OUT/ERROR.txt"
"$PY" -m unittest tests/test_posture_rules.py >>"$LOG" 2>&1
rm -rf "$OUT/before/img"; cd "$OUT" && rm -rf "$OUT/work"
echo "끝. 결과: $OUT"

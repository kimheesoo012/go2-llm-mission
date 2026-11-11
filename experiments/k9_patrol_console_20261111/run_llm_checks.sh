#!/bin/bash
# Runs the checks that need a local LLM / STT model, on a fresh copy of the console.
# Nothing in an existing console folder or its data is touched; results go to OUT.
#   bash run_llm_checks.sh            (Ollama running, model qwen3.5:4b pulled)
set -u
OUT="${OUT:-$HOME/Downloads/k9_checks_20261112}"
MODEL="${MODEL:-qwen3.5:4b}"
PY="${PY:-python3}"
BASE=https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-help-request-alerts-20261111/experiments/k9_patrol_console_20261111
rm -rf "$OUT/work"; mkdir -p "$OUT/work"; cd "$OUT/work" || exit 1
git clone -q https://github.com/daryung/capstone.git || { echo "clone 실패" | tee "$OUT/ERROR.txt"; exit 1; }
cd capstone && curl -sL "$BASE/k9-help-request-alerts.patch" | git apply || { echo "패치 적용 실패" | tee "$OUT/ERROR.txt"; exit 1; }
cd k9_patrol_console
{ echo "date: $(date)"; echo "model: $MODEL"; $PY --version; uname -sm; } > "$OUT/env.txt" 2>&1
echo "[1/4] 선정 시나리오: LLM만"
$PY eval/selection_eval.py --mode llm --model "$MODEL" --out "$OUT/selection_llm.md" > "$OUT/selection_llm.log" 2>&1
echo "[2/4] 선정 시나리오: 규칙 우선 + LLM"
$PY eval/selection_eval.py --mode merged --model "$MODEL" --out "$OUT/selection_merged.md" > "$OUT/selection_merged.log" 2>&1
echo "[3/4] 순찰 보고서 LLM 총평 (저장 기록 사본)"
cp -r data "$OUT/work/data_copy"
$PY - "$OUT" "$MODEL" > "$OUT/report_llm.log" 2>&1 <<'PYEOF'
import sys, time
out, model = sys.argv[1], sys.argv[2]
import ollama_connection
from storage import Store
from patrol_report import ReportService
ollama_connection.start_background()
store = Store(out + '/work/data_copy')
text = []
for label, pick in (('전체 기록', lambda r: True), ('11/05 기록', lambda r: r['time'].startswith('2026-11-05'))):
    svc = ReportService(store)
    t = time.monotonic()
    svc.generate([r for r in store.list() if pick(r)], model, True, label)
    info = svc.status()
    r = info['result'] or {}
    text += [f"## {label}", f"- 걸린 시간: {time.monotonic() - t:.1f}초", f"- 총평 작성: {r.get('overview_source')}",
             f"- LLM 오류/거부 사유: {r.get('llm_error') or info['error'] or '없음'}", '', r.get('markdown', ''), '']
open(out + '/report_llm.md', 'w', encoding='utf-8').write('\n'.join(text))
PYEOF
echo "[4/4] STT 초기 프롬프트 비교 (faster-whisper 필요)"
$PY eval/stt_prompt_ab.py data/media/*.wav recordings/test.wav > "$OUT/stt_prompt_ab.md" 2> "$OUT/stt_prompt_ab.log" || echo "STT 비교는 건너뜀 (stt_prompt_ab.log 확인)"
rm -rf "$OUT/work"
echo "끝. 결과: $OUT"

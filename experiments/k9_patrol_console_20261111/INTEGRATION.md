# 콘솔 연결 위치

**주의:** 11/07 패치에 포함된 `highlights.py`·`posture_rules.py`와 10/31 공개 코드(`vision.py`, `app.py`, `storage.py`)를 기준으로 적었습니다. STT 저장 코드 등 그 이후 변경은 보지 못했으므로, 함수 이름과 위치는 실제 코드에 맞춰 확인이 필요합니다. 아래 코드는 연결 예시이며 실행해 보지 않았습니다.

다섯 파일(`help_request.py`, `lying_tracker.py`, `alerts.py`, `review_priority.py`, `patrol_report.py`)을 `k9_patrol_console/`에 복사하면 됩니다. 추가 설치는 없습니다.

## 1. 음성 기록 저장 시점 → 도움 요청 판정

STT 결과를 기록에 저장하는 곳에서:

```python
from help_request import find_help_request

found = find_help_request(transcript)          # transcript: STT 원문 문자열
metadata['help_request'] = found               # code, label, priority, reason, hits
alert_center.speech(time.monotonic(), found, record_id)
```

기록 목록 화면에서는 `metadata.help_request.label`("도움 요청" / "도움 요청 의심")을 태그로 표시할 수 있습니다.

## 2. 탐지 루프 → 누운 자세 지속

`vision.py`의 `detect()`에서 `infer()` 결과(`det`)를 받은 직후:

```python
# __init__
self.lying = LyingTracker(sustain=15.)         # 시연 때는 5~8초로 낮출 수 있음
# detect() 루프 안, det 계산 뒤
for event in self.lying.update(now, det):      # det 항목에 posture가 들어 있어야 함
    alert_center.lying(now, event)
```

`attach()`에서 연결을 새로 시작할 때 `self.lying.clear()`를 부릅니다.

## 3. 상태 API → 알림 표시

`app.py`:

```python
alert_center = AlertCenter()
# GET /api/status
self.reply(200, dict(robot=..., vision=..., llm=..., alerts=alert_center.active()))
# POST /api/alert_ack
elif self.path == '/api/alert_ack': alert_center.ack(str(data['id']))
```

화면 쪽은 `demo/alert_demo.html`의 `renderAlerts(alerts)`와 `beep(level)` 두 함수, `.alert` 스타일을 옮기면 됩니다. STT 원문이 알림 문구에 들어가므로 `innerHTML`이 아니라 `textContent`로 넣습니다.

## 4. 중요 장면 선정 → 규칙 우선 병합

`highlights.py`의 `generate()`에서 최종 `_select` 호출 뒤:

```python
from review_priority import merge_selection, row_from_source

rows = self._select(sources, model, limit) if sources else []
all_rows = [row_from_source(s) for s in all_sources.values()]      # 후보 선별 전 전체 기록
merged, overflow = merge_selection(
    all_rows, [dict(id=r['record_id'], reason=r['reason'], evidence=r['evidence_ids']) for r in rows], limit)
rows = [dict(record_id=m['id'], reason=m['reason'], evidence_ids=m['evidence']) for m in merged]
```

- 규칙이 고른 기록은 LLM이 고르지 않아도 들어가고, 이유는 규칙 문장(예: `도움 요청 표현 '살려주세요' 2회`)이 됩니다.
- 기록이 40건을 넘어 후보 선별을 거치는 경우에도 전체 기록 기준으로 규칙을 적용하므로, 선별 단계에서 빠진 기록도 복구됩니다.
- `overflow`가 0보다 크면 규칙이 고른 기록이 선정 개수보다 많다는 뜻이므로 화면에 알려 주는 것이 좋습니다.

## 5. 순찰 보고서

```python
from patrol_report import make_report
from highlights import observation_data
from ollama_connection import chat

observations = [dict(observation_data(r), record_id=r['id']) for r in records]
report = make_report(observations, model, chat)     # chat=None이면 규칙 문장만
report['markdown']                                   # 화면 표시·다운로드용
```

기존 선정 기능과 같은 방식(백그라운드 스레드 + 상태 조회)으로 호출하는 것을 권장합니다. LLM 호출은 한 번이고 입력은 집계 결과뿐이라 기록 수와 관계없이 짧습니다.

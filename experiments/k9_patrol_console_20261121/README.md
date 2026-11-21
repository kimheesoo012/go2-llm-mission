# 11/21–22 Go2 촬영 준비 (교수님 11/18 보고 피드백 반영)

팀장님 저장소(`daryung/capstone`)에는 반영하지 않았고, 아래 패치로만 전달합니다.

## 적용 방법

11/17에 패치 3개(자세 규칙, 도움 요청·알림, 자세 안정화)를 적용한 콘솔 폴더에서 아래 한 줄입니다.

```bash
curl -L https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-shoot-1121/experiments/k9_patrol_console_20261121/k9-shoot-1121.patch | git am
```

되돌리기: `git reset --hard HEAD~1`. 확인: 팀장님 `main` + 패치 4개 순서대로 적용, 테스트 150개 통과.

## 바뀌는 것

| 항목 | 내용 | 설정 |
|---|---|---|
| FPS 표시·기록 | 탐지 상태 칸에 `처리 N FPS · N ms/장 · 회전 N%` 표시. `data/perf_log.csv`에 10초마다 한 줄 기록 | 자동 |
| 회전 검출 조건 | `always` 매 프레임 / `unknown` 자세가 판단 불가인 사람이 있을 때만 / `unknown_or_empty` 판단 불가이거나 사람이 아무도 안 잡혔을 때 (기본) | `K9_ROTATE_WHEN` |
| 회전 검출 켬·끔 | `0` 끔 / `1` 켬 (기본) | `K9_ROTATE_DETECT` |
| 다리만 보일 때 | 판단 불가가 기본 (11/17 팀 결정) | `K9_SHIN_ONLY=1`이면 이전처럼 서 있음 |
| STT 단어 힌트 | 비워 두면 기존과 같음 | `K9_STT_HOTWORDS` |

**`unknown`만 쓰지 않고 `unknown_or_empty`를 기본으로 둔 이유**: 누운 사람은 원본 영상에서 아예 사람으로 검출되지 않는 경우가 많습니다. 11/14 영상으로 계산하면 누운 장면 33장 중 누움 판단이 `always` 23장, `unknown` 10장, `unknown_or_empty` 23장입니다. 회전 검출이 돈 프레임은 `always` 653장, `unknown` 31장, `unknown_or_empty` 399장입니다(사람이 없는 프레임 포함).

## 촬영 순서

### 1. FPS 측정 (촬영 시작 전, 각 2분)

콘솔을 끄고 아래 설정으로 다시 켠 뒤, 사람이 화면에 있는 상태로 2분씩 둡니다. 결과는 `data/perf_log.csv`에 설정과 함께 남습니다.

| 순서 | 실행 설정 |
|---|---|
| ① 회전 끔 | `K9_ROTATE_DETECT=0` |
| ② 회전 매 프레임 | `K9_ROTATE_WHEN=always` |
| ③ 판단 불가·사람 없음일 때만 | `K9_ROTATE_WHEN=unknown_or_empty` |
| ④ 판단 불가일 때만 | `K9_ROTATE_WHEN=unknown` |

예: `K9_ROTATE_DETECT=0 python app.py` (평소 실행 명령 앞에 붙임). ③으로 실시간이 괜찮으면 촬영은 ③으로 합니다.

### 2. 자세 촬영 (거리 2 m·4 m, 각 5초 이상)

조작하는 사람은 로봇 머리보다 뒤에 서서 화면 양 끝에 팔·다리가 보이지 않게 합니다.

| 자세 | 방향 |
|---|---|
| 서 있음 | 정면, 옆, 뒤 |
| 의자 앉음 | 정면, 옆 |
| 바닥 앉음 | 다리 뻗음, 무릎 세움, 양반다리 |
| 누움 | 옆으로, 발이 카메라 쪽 (시연 중심) |
| 누움 (한계 확인용) | 머리가 카메라 쪽 1회만 |
| **오답 재확인 ①** | 멀리(4 m 이상) 서 있는 사람이 의자·책상에 하체가 가려진 장면 |
| **오답 재확인 ②** | 멀리(4 m 이상) 쪼그려 앉은 장면 |

### 3. 녹음 (STT 단어 힌트 비교용)

- 구조 요청: "살려주세요", "도와주세요", "도와" 짧게, "구해주세요" (각 2~3회)
- 일상 발화: "여기 아무도 없어요", "괜찮아요", "잠깐만요", "도와줄게", "살살 해" 같은 비슷한 소리가 섞인 말 포함 5개 이상
- 녹음마다 실제로 말한 문장을 메모해 두면 정답으로 씁니다.

### 4. 통합 시연

누움(옆·발 방향) + "살려주세요" → 관제자 알림 → LLM 중요 장면 선정까지 화면 녹화.

## 촬영 후 채점 (최종 수치)

```bash
python eval/score_shoot.py frames --date 2026-11-21 --out eval/shoot_20261121
# eval/shoot_20261121/sheets/*.jpg 를 보고 labels.csv 의 truth 칸에 standing/sitting/lying/part 기입
python eval/score_shoot.py score --out eval/shoot_20261121
```

회전 검출 켬·끔 결과가 같은 표에 나옵니다. 기록 DB(`data/records.sqlite3`)와 `data/media`를 주시면 정답 기입과 채점은 제가 하겠습니다.

## STT 단어 힌트 비교 (지금 바로 가능)

맥 터미널에 붙여 넣으면 11/14 Go2 녹음 20개로 힌트 적용 전후를 비교합니다. faster-whisper가 설치된 Python만 찾아 쓰고 새로 설치하지 않습니다.

```bash
curl -sL https://raw.githubusercontent.com/kimheesoo012/go2-llm-mission/feature/k9-shoot-1121/experiments/k9_patrol_console_20261121/run_stt_hotwords.sh | bash
```

`stt_labels_20261114.csv`의 정답(구조 요청 / 일상 발화)은 11/05 녹음 2개와 "도와" 녹음 1개만 확인된 상태입니다. 나머지는 녹음을 들은 사람이 채워야 오탐 수를 셀 수 있습니다. 11/21 녹음이 추가되면 같은 스크립트로 다시 돌립니다.

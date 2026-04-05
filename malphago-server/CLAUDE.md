# MalPhaGo Server - 경마 예측 AI 서버

## 프로젝트 개요
한국마사회(KRA) 경마 데이터 수집 + ML 예측 + REST API 서버

## 기술 스택
- **서버**: FastAPI (Python 3.10) + uvicorn
- **DB**: PostgreSQL (운영) / SQLite (로컬 개발: `malphago_dev.db`)
- **ML**: LightGBM + XGBoost (이진 분류: 3위 이내 예측)
- **ORM**: SQLAlchemy 2.0 (async)
- **배포**: Docker Compose → Oracle Cloud ARM / AMD

## 디렉토리 구조
```
app/
  api/           # FastAPI 라우터 (races, horses, jockeys, predictions, sync, analysis)
  core/          # config, security
  db/            # session, base
  models/        # SQLAlchemy 모델 (race, race_entry, horse, jockey, trainer, ...)
  schemas/       # Pydantic 응답 스키마
  services/      # 비즈니스 로직
    kra_api.py   # data.go.kr 공공 API 클라이언트 (핵심)
    prediction.py # 가중 선형 예측 (20개 요인)
    horse_factors.py / jockey_factors.py  # 요인 계산
  ml/
    feature_extractor.py  # ML 피처 추출 (22개 피처)
    trainer.py           # LightGBM/XGBoost 학습 + TSCV
    train_cli.py         # CLI: dataset/train/evaluate/compare/all
scripts/
  collect_kra.py    # data.go.kr API 단일 수집
  collect_all.py    # 전체 기간 배치 수집
  enrich_data.py    # race_interval 계산 + 데이터 품질 리포트
  post_collect.py   # 수집 후 후처리 + ML 재학습 파이프라인
  migrate_sqlite.py # malphago.db → PostgreSQL 마이그레이션
ml_models/          # 학습된 모델 (.joblib)
ml_data/            # 학습 데이터셋 (.csv)
```

## 현재 상태 (2026-04-05)

### 데이터
- **수집 완료**: 2020-01 ~ 2025-04-05 (7,998 경주, 88K entries with odds)
- **수집 남음**: 2025-04-06 ~ 2026-04-03 (API 일일 한도로 내일 재개)
- **데이터 소스**: data.go.kr API214_1 (경주성적정보) - 배당률, 마체중, 주로상태, 날씨
- **API 키**: `.env`의 `DATA_GO_KR_SERVICE_KEY` (URL-encoded)

### ML 모델
- **현재 모델**: LightGBM v3 (AUC 0.9429, 22 features, 53K samples)
- **전체 데이터 재학습 진행 중**: 103K+ samples 예상
- **TSCV**: Leave-One-Date-Out 시계열 교차검증
- **피처 22개**: horse_win_rate, distance_aptitude, form_index, class_movement, gate_position, jockey_win_rate, jockey_fatigue, trainer_synergy, horse_jockey_synergy, rest_period, running_style_match, class_trick, race_interval, horse_number, total_entries, distance, favor_ranking, odds_win, odds_place, horse_weight, horse_weight_change, rating

### 서버 배포
- **Oracle Cloud**: AMD 인스턴스 확보 (오사카), ARM 확보 대기 중
- **역할 분담**: 서버(API+DB+스케줄러) / 로컬(ML학습+크롤링)

## 주요 명령어
```bash
# 로컬 개발 서버
uvicorn app.main:app --reload

# 데이터 수집 (data.go.kr)
python scripts/collect_all.py

# ML 전체 파이프라인
python -m app.ml.train_cli --action all

# 수집 후 후처리 + ML 재학습
python scripts/post_collect.py

# race_interval 재계산만
python -c "... scripts/enrich_data.py calc_race_intervals ..."
```

## 주의사항
- data.go.kr API는 **일일 요청 한도**가 있음 (자정 KST 리셋)
- ServiceKey는 URL에 직접 삽입 (httpx params에 넣으면 이중 인코딩 → 401)
- SQLite 로컬 개발 시 동시 접근 주의 (database is locked)
- ML 학습은 메모리 많이 사용 → 서버(1GB)에서 불가, 로컬에서 실행

## 관련 프로젝트
- **Android 앱**: `C:/claude/malphago-app/` (Kotlin + Jetpack Compose)
- **기존 코드**: `C:/claude/MalPhaGo/` (C# WinForms), `C:/claude/hracing/` (Python)
- **Notion WBS**: MalPhaGo (말파고) - 경마 예측 앱

# MalPhaGo Android - 경마 예측 앱 기획서

| 항목 | 내용 |
|------|------|
| 프로젝트명 | MalPhaGo (말파고) |
| 문서버전 | v1.0 |
| 작성일 | 2026-04-03 |
| 플랫폼 | Android |
| 배포 대상 | Google Play Store |

---

## 1. 프로젝트 개요

### 1.1 목적
한국마사회(KRA)와 검빛(Gumbit)의 경마 데이터를 자동 수집하여 말/기수/조교사의 특성을 분석하고, 이들의 시너지를 기반으로 다음 경주 결과를 예측하는 안드로이드 앱을 개발한다.

### 1.2 배경
- 기존에 C#으로 개발된 MalPhaGo 데스크톱 앱과 Python으로 포팅된 hracing 크롤러가 존재
- 기수-조교사 시너지 분석 로직(4개 지표)이 이미 구현되어 있으나 데스크톱 전용
- 모바일 환경에서 실시간 변경사항 확인 및 예측 기능에 대한 니즈 존재

### 1.3 핵심 가치
1. **자동 데이터 수집**: KRA/Gumbit에서 경마 데이터를 자동으로 크롤링하여 DB 구축
2. **다차원 분석**: 말/기수/조교사 개별 특성 및 조합 시너지 분석
3. **예측**: 통계 및 ML 기반 경주 결과 예측
4. **실시간 대응**: 경주 직전까지 발생하는 기수/말 변경을 즉시 감지하고 재예측

### 1.4 운영 환경
| 항목 | 내용 |
|------|------|
| 서버 | Oracle Cloud Free Tier (ARM Ampere A1) |
| 배포 | Google Play Store |
| 인증 | 초기에는 회원가입 없이 운영 |
| 수익모델 | 광고(AdMob), Play Store 구독, 정기 SMS 예측 전송 |
| 개발방식 | 서버 + 앱 동시 병렬 개발 |

---

## 2. 시스템 아키텍처

### 2.1 전체 구성도
```
┌──────────────────────┐       HTTPS/JSON       ┌─────────────────────────┐
│   Android App        │ <===================>  │   FastAPI Server         │
│                      │       REST API          │                         │
│  - Kotlin/Compose    │                         │  - Python 3.12+         │
│  - Room DB (캐시)    │                         │  - PostgreSQL            │
│  - Offline 지원      │                         │  - APScheduler           │
│  - FCM 수신          │                         │  - Playwright (크롤링)   │
└──────────────────────┘                         │  - Docker Compose        │
                                                 └────────────┬────────────┘
                                                              │
                                               ┌──────────────┼──────────────┐
                                               │              │              │
                                        ┌──────┴──────┐ ┌────┴─────┐ ┌─────┴─────┐
                                        │ KRA 공식    │ │ Gumbit   │ │ FCM       │
                                        │ race.kra.   │ │ gumvit.  │ │ Firebase  │
                                        │ co.kr       │ │ com      │ │ 푸시 알림  │
                                        └─────────────┘ └──────────┘ └───────────┘
```

### 2.2 역할 분담

| 구분 | 서버 (FastAPI) | 클라이언트 (Android) |
|------|---------------|---------------------|
| 크롤링 | KRA/Gumbit 웹 스크래핑 | X (불가) |
| DB | PostgreSQL (원본 데이터) | Room (캐시) |
| 분석/예측 | 통계 계산, 예측 모델 실행 | 결과 표시, 수동 시뮬레이션 요청 |
| 변경 감지 | 10분 간격 자동 크롤링 | FCM 푸시 수신, 수동 새로고침 |
| 오프라인 | - | Room DB 기반 오프라인 열람 |

### 2.3 왜 서버가 필요한가
웹 크롤링(Playwright/Selenium)은 브라우저 엔진이 필요하므로 모바일에서 직접 실행 불가. 기존 MalPhaGo도 WebCrawling(데스크톱) → WebServer(ASP.NET) → MalPhaGoClient(Xamarin) 구조로 분리되어 있었으며, 이 패턴을 현대화한다.

---

## 3. 기술 스택

### 3.1 Android 클라이언트
| 항목 | 기술 | 선정 사유 |
|------|------|----------|
| 언어 | Kotlin | 구글 공식 Android 개발 언어 |
| UI | Jetpack Compose + Material 3 | 선언형 UI, 최신 디자인 시스템 |
| 아키텍처 | MVVM + Clean Architecture | 테스트 용이성, 계층 분리 |
| DI | Hilt | Compose와 원활한 통합 |
| 네트워크 | Retrofit2 + OkHttp + Kotlin Serialization | 타입 안전 API 클라이언트 |
| 로컬 DB | Room | SQLite 래퍼, 기존 malphago.db 마이그레이션 용이 |
| 비동기 | Coroutines + Flow | 반응형 데이터 스트림 |
| 차트 | Vico | Compose 네이티브 차트 라이브러리 |
| 백그라운드 | WorkManager | 주기적 서버 동기화 |
| 알림 | Firebase Cloud Messaging (FCM) | 서버 → 앱 실시간 푸시 |
| Min SDK | 26 (Android 8.0) | 전체 디바이스의 약 95% 커버 |

### 3.2 백엔드 서버
| 항목 | 기술 | 선정 사유 |
|------|------|----------|
| 프레임워크 | FastAPI | 비동기, 자동 OpenAPI 문서, 빠른 JSON 직렬화 |
| 크롤링 | Playwright (async) | 기존 kra_crawler.py 기반, 동적 페이지 처리 |
| DB | PostgreSQL | 복잡한 분석 쿼리, JSONB 지원 |
| ORM | SQLAlchemy 2.0 (async) | Python 표준 ORM, 비동기 지원 |
| 스케줄러 | APScheduler | 단일 서버 환경에서 Redis 없이 운영 가능 |
| 배포 | Docker Compose | 컨테이너화, 환경 일관성 |
| 호스팅 | Oracle Cloud Free Tier (ARM A1) | 무료, 4 OCPU / 24GB RAM |

---

## 4. 데이터 소스

### 4.1 한국마사회 (KRA) - race.kra.co.kr
| 데이터 | URL | 설명 |
|--------|-----|------|
| 공식 성적표 | `race.kra.co.kr/raceScore/ScoretableScoreList.do?meet={1,2,3}` | 과거 경주 결과 + 구간 기록 |
| 성적표 상세 | `race.kra.co.kr/raceScore/ScoretableDetailList.do` | S1F, G3F, G1F 구간기록, 코너순위 |
| 출마표 | `race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?meet={1,2,3}` | 당일 출주 정보 |
| 마체중 | `race.kra.co.kr` (출전마체중 API) | 당일 실측 마체중 + 증감 |
| 분석용 성적 | `studbook.kra.co.kr` | 구간기록 포함 상세 경주성적 |
| meet 코드 | 1=서울, 2=제주, 3=부산 | |

### 4.2 검빛 (Gumbit) - www.gumvit.com
| 데이터 | URL | 설명 |
|--------|-----|------|
| 기수별 기록 | `gumvit.com/statv40/jockeys.html?loc={S,B,J}` | 기수별 과거 전적 상세 |
| 출마 상세 | `gumvit.com/statv40/chulma_detail.html?type={1~7}` | 경주일별 출마 상세 + 전문가 예상 |
| **기록비교** | **`gumvit.com/statv40/chulma_record.html`** | **S1F/G3F/G1F, 3C/4C 통과순위 비교** |
| **경주력분석** | **`gumvit.com/statv40/horse_power_anal.html`** | **다경주 이력 + 구간기록 + 마체중** |
| **상금/전적** | **`gumvit.com/statv40/chulma_prize.html`** | **기수/조교사/마주 종합 통계** |
| **조교사정보** | **`gumvit.com/statv40/trainers.html`** | **복승율, 평균상금, 월별 전적** |
| loc 코드 | S=서울, B=부산, J=제주 | |
| type 코드 | 1=서울토, 2=서울일, 3=부산금, 5=부산일, 6=제주금, 7=제주토 | |

### 4.3 경마 스케줄
| 경마장 | 경주일 |
|--------|--------|
| 서울 | 토요일, 일요일 |
| 부산 | 금요일, 일요일 |
| 제주 | 금요일, 토요일 |

---

## 5. 데이터 모델

### 5.1 핵심 엔티티 (기존 MalPhaGo에서 계승 + 정규화)

#### track (경마장)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| code | VARCHAR(1) | S, B, J |
| name_ko | VARCHAR(20) | 서울경마, 부산경마, 제주경마 |
| meet_code | INTEGER | KRA meet 코드 (1, 3, 2) |

#### horse (말)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| name | VARCHAR(100) | 마명 |
| nationality | VARCHAR(20) | 산지 (한국, 외국 등) |
| sex | VARCHAR(10) | 수, 암, 거 |
| birth_year | INTEGER | 출생년도 |
| current_rating | INTEGER | 현재 레이팅 |
| owner | VARCHAR(100) | 마주명 |

#### jockey (기수)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| name | VARCHAR(50) | 기수명 |
| track_id | FK(track) | 소속 경마장 |
| active | BOOLEAN | 활동 여부 |

#### trainer (조교사)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| name | VARCHAR(50) | 조교사명 |
| track_id | FK(track) | 소속 경마장 |

#### race (경주)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| track_id | FK(track) | 경마장 |
| race_date | DATE | 경주일 |
| race_number | INTEGER | 경주 회차 |
| race_name | VARCHAR(100) | 경주명 |
| race_level | VARCHAR(20) | 등급 |
| race_distance | INTEGER | 거리 (m) |
| weather | VARCHAR(20) | 날씨 |
| track_condition | VARCHAR(20) | 주로상태 (우량상태) |
| track_moisture_pct | DECIMAL(5,2) | 함수율 |
| prize_1st ~ prize_5th | BIGINT | 상금 1~5위 |
| entry_count | INTEGER | 출주두수 |

#### race_entry (출주 기록)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| race_id | FK(race) | 경주 |
| horse_id | FK(horse) | 말 |
| jockey_id | FK(jockey) | 기수 |
| trainer_id | FK(trainer) | 조교사 |
| gate_number | INTEGER | 마번 |
| horse_weight | DECIMAL(5,1) | 마체중 |
| weight_change | DECIMAL(5,1) | 증감 |
| carried_weight | DECIMAL(5,1) | 부담중량 |
| horse_rating | INTEGER | 경주 당일 레이팅 |
| race_interval | INTEGER | 출전주기 (일) |
| finishing_position | INTEGER | 순위 (미경주 시 NULL) |
| favorite_ranking | INTEGER | 인기순위 |
| odds_win | DECIMAL(8,2) | 단승 배당 |
| odds_place | DECIMAL(8,2) | 연승 배당 |
| **jockey_ride_seq** | **INTEGER** | **당일 기수의 몇 번째 기승인지 (피로도)** |
| **arrival_margin** | **VARCHAR(20)** | **착차 (선두마와 거리)** |
| **equipment** | **VARCHAR(100)** | **장구 현황 (망사눈가리개, 차안대 등)** |
| **burden_type** | **VARCHAR(20)** | **부담구분 (정량/별정/핸디캡)** |
| **apprentice_allowance** | **INTEGER** | **수습기수 감량 (kg)** |

#### race_timing (구간 기록)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| race_entry_id | FK(race_entry) | |
| s_1f | DECIMAL(5,2) | 스타트 ~ 1F |
| corner1 ~ corner4 | DECIMAL(5,2) | 코너 통과 순위 (서울) |
| corner_g_3f, corner_g_1f | DECIMAL(5,2) | 선두 차이 (서울) |
| f_10_8 ~ f_1_g | DECIMAL(5,2) | 구간별 시간 (부산) |
| final_time | DECIMAL(6,2) | 최종 기록 |

### 5.2 분석 테이블 (신규)

#### jockey_stats (기수 통계)
| 필드 | 타입 | 설명 |
|------|------|------|
| jockey_id | FK | 기수 |
| track_id | FK | 경마장 |
| period | VARCHAR(20) | all, last_90d, last_30d, this_year |
| total_rides | INTEGER | 총 기승 수 |
| wins / places | INTEGER | 1위 / 3위이내 |
| win_rate / place_rate | DECIMAL(5,2) | 승률 / 연대율 |
| wins_short / wins_mid / wins_long | INTEGER | 거리별 승수 |
| wins_dry / wins_wet | INTEGER | 주로상태별 승수 |

#### horse_stats (말 통계)
| 필드 | 타입 | 설명 |
|------|------|------|
| horse_id | FK | 말 |
| best_distance | INTEGER | 최적 거리 |
| wins_by_distance | JSONB | 거리별 승수 맵 |
| optimal_rest_days | INTEGER | 최적 휴식일 |
| recent_form | VARCHAR(20) | 최근 5경주 순위 (예: 1-3-2-5-1) |
| form_trend | VARCHAR(10) | improving / declining / stable |
| **running_style** | **VARCHAR(10)** | **각질: 도주/선행/선입/추입/자재** |
| **avg_s1f** | **DECIMAL(5,2)** | **평균 S1F 기록 (선행력)** |
| **avg_g3f** | **DECIMAL(5,2)** | **평균 G3F 기록 (후반력)** |
| **avg_g1f** | **DECIMAL(5,2)** | **평균 G1F 기록 (마무리 스퍼트)** |
| **front_half_avg** | **DECIMAL(5,2)** | **전반 평균 기록** |
| **back_half_avg** | **DECIMAL(5,2)** | **후반 평균 기록** |
| **class_history** | **JSONB** | **등급 변동 이력 [{date, class, rating}]** |
| **equipment** | **VARCHAR(100)** | **장구 현황 (눈가리개, 차안대 등)** |

#### synergy_stats (시너지 통계)
| 필드 | 타입 | 설명 |
|------|------|------|
| horse_id | FK | 말 |
| jockey_id | FK | 기수 |
| trainer_id | FK | 조교사 |
| hj_total_rides / hj_wins | INTEGER | 말-기수 직접 조합 기승/승 |
| hj_win_rate | DECIMAL(5,2) | 말-기수 승률 |
| jt_total_rides / jt_wins | INTEGER | 기수-조교사 조합 |
| best_record_rate | DECIMAL(5,2) | 기수 Top-3 입상률 (기존 지표 1) |
| best_record_trainer_rate | DECIMAL(5,2) | 조교사 동반 입상률 (기존 지표 2) |
| high_dividend_record_rate | DECIMAL(5,2) | 이변 입상률 (기존 지표 3) |
| high_dividend_record_trainer_rate | DECIMAL(5,2) | 조교사 동반 이변률 (기존 지표 4) |

#### prediction (예측 결과)
| 필드 | 타입 | 설명 |
|------|------|------|
| race_entry_id | FK | 출주 |
| predicted_rank | INTEGER | 예측 순위 |
| composite_score | DECIMAL(8,4) | 종합 점수 |
| confidence | DECIMAL(5,2) | 신뢰도 (0~100%) |
| factor_scores | JSONB | 요인별 점수 분해 |
| actual_position | INTEGER | 실제 결과 (경주 후 입력) |

#### entry_change_log (변경 이력)
| 필드 | 타입 | 설명 |
|------|------|------|
| race_entry_id | FK | 출주 |
| change_type | VARCHAR(20) | jockey_change, horse_scratch, weight_change |
| old_value | VARCHAR(100) | 변경 전 |
| new_value | VARCHAR(100) | 변경 후 |
| detected_at | TIMESTAMP | 감지 시각 |
| source | VARCHAR(20) | auto_scrape / manual_override |

---

## 6. 앱 화면 설계

### 6.1 네비게이션 구조
```
[메인 대시보드] ─── Bottom Navigation (4탭)
  │
  ├── [경주일 탭]
  │     ├── 경마장 선택 (서울/부산/제주)
  │     ├── 날짜 선택
  │     ├── 경주 목록
  │     └── [경주 상세]
  │           ├── 출주표 (확장 가능)
  │           ├── 기수 변경 (수동)
  │           ├── 예측 실행
  │           └── [출주마 상세]
  │                 ├── 말 탭 (기본 정보 + 차트)
  │                 ├── 기수 탭 (통계 + 차트)
  │                 └── 시너지 탭 (조합 분석)
  │
  ├── [분석 탭]
  │     ├── 말 분석 (검색/필터/정렬)
  │     ├── 기수 분석 (검색/필터/정렬)
  │     └── 시너지 분석 (조합 선택 → 점수 분해)
  │
  ├── [예측 탭]
  │     ├── 경주별 예측 순위
  │     ├── 비교 모드 (2~3두)
  │     └── 과거 적중률 이력
  │
  └── [설정 탭]
        ├── 서버 URL 설정
        ├── 동기화 주기
        ├── 알림 설정 (경마장/경주 선택)
        ├── 캐시 관리
        └── 구독 관리
```

### 6.2 화면 상세

#### 메인 대시보드
- 경마장별 오늘/다음 경주 카드 (서울/부산/제주)
- 각 카드: 경주 수, 다음 경주 시각, Top 3 예측 요약
- 기수/말 변경 알림 배너 (실시간 업데이트)
- 마지막 동기화 시각 + 수동 새로고침 버튼

#### 경주 상세
- 헤더: 경주명, 등급, 거리, 날씨, 주로상태(함수율)
- 출주표 테이블: 마번 | 마명 | 기수 | 조교사 | 레이팅 | 중량 | 인기
- 각 행 확장 시: 시너지 점수, 최근 전적, 예측 순위
- **기수 변경**: 기수명 탭 → 드롭다운에서 다른 기수 선택 → 재예측
- **변경 이력 표시**: 변경된 기수/말은 빨간색 하이라이트 + 이전 값 취소선

#### 출주마 상세 (3탭)
- **말 탭**: 기본 정보, 거리별 성적(막대 차트), 주로상태별 성적, 최근 10경주 결과 테이블
- **기수 탭**: 종합 승률, 트랙별 특화도(레이더 차트), 거리별 특화도, 최근 폼(라인 차트)
- **시너지 탭**: 말-기수 직접 조합 이력, 조교사-기수 이력, 4개 기존 지표 + 신규 지표 게이지

---

## 7. 예측 알고리즘

### 7.1 기존 4개 지표 (MalPhaGo 계승)
기존 `Form1.cs:654-691`의 `startRaceReport()` 로직을 Python으로 이식:

| # | 지표 | 계산 방법 | 의미 |
|---|------|----------|------|
| 1 | bestRecordRate | (기수 3위이내 횟수) / (총 기승) × 100 | 기수 입상률 |
| 2 | bestRecordTrainerRate | (해당 조교사와 3위이내) / (3위이내 총횟수) × 100 | 조교사-기수 시너지 |
| 3 | highDividendRecordRate | (인기4위이하에서 3위이내) / (총 기승) × 100 | 이변 입상률 |
| 4 | highDividendRecordTrainerRate | (해당 조교사와 이변) / (이변 총횟수) × 100 | 조교사 동반 이변률 |

### 7.2 신규 분석 요인

**말 요인 (10개)**
| 요인 | 산출 방법 | 점수 범위 |
|------|----------|----------|
| 거리 적성 | 해당 거리 승률 / 전체 승률 | 0~100 |
| 주로상태 적성 | 건조/습윤 시 성적 비교 (당일 주로상태 매칭) | 0~100 |
| 휴식기간 | 최적 출전주기 대비 현재 휴식일 편차 | 0~100 |
| 클래스 이동 | 등급 상승/하락 시 성적 변화 분석 | 0~100 |
| 게이트 포지션 | 해당 트랙+거리에서의 마번별 통계적 유불리 | 0~100 |
| 최근 폼 | 최근 5경주 순위의 가중 평균 (최근일수록 높은 가중치) | 0~100 |
| **각질 (주행 스타일)** | **코너순위 패턴으로 자동 분류 (도주/선행/선입/추입/자재)** | **분류값** |
| **전반력 (S1F)** | **S1F 평균 기록 → 초반 스피드 지표** | **0~100** |
| **후반력 (G3F/G1F)** | **G3F~결승 구간 기록 → 마무리 스퍼트 지표** | **0~100** |
| **마체중 변동** | **최근 마체중 증감 추이 (급격한 변화 시 감점)** | **0~100** |

> **각질 자동 분류 로직**: KRA에는 각질 필드가 직접 없으므로, 코너순위(1C-2C-3C-4C)와 S1F/G1F 데이터로 역산:
> - **도주**: 1C 1위, 최종까지 선두 유지
> - **선행**: 1C 1~3위권, 전반 리드
> - **선입**: 중반부에서 순위 상승
> - **추입**: 후반 직선에서 급상승 (G1F 빠름, 1C 후미)
> - **자재**: 일정한 순위 유지형

**기수 요인 (5개)**
| 요인 | 산출 방법 | 점수 범위 |
|------|----------|----------|
| 트랙 특화도 | 해당 경마장 승률 vs 전체 승률 | 0~100 |
| 거리 특화도 | 해당 거리 구간 승률 vs 전체 승률 | 0~100 |
| 최근 30일 폼 | 최근 30일 승률 vs 전체 승률 | 0~100 |
| **당일 기승 순서 (피로도)** | **당일 몇 번째 기승인지 → 후반 경주일수록 감점** | **0~100** |
| **수습기수 여부** | **수습기수 감량 적용 시 부담중량 보정** | **보정값** |

> **기수 피로도 로직**: 한 기수가 당일 여러 경주에 출전하면, 후반 경주일수록 체력/집중력 저하 예상. 당일 기승 횟수가 5회 이상이면 후반 경주에 감점 적용.

**시너지 요인 (3개, 신규)**
| 요인 | 산출 방법 | 점수 범위 |
|------|----------|----------|
| 말-기수 직접 조합 | 이 말과 이 기수가 직접 함께한 전적의 승률 | 0~100 |
| 말-조교사 친화도 | 이 말이 이 조교사 소속일 때의 성적 | 0~100 |
| 첫 조합 보정 | 말-기수 첫 조합 시 통계적 보정값 | -10~+10 |

**전략 감지 요인 (2개, 신규)**
| 요인 | 산출 방법 | 점수 범위 |
|------|----------|----------|
| **등급 꼼수 감지** | **능력 대비 의도적으로 하위 등급 체류 패턴 감지** | **플래그** |
| **각질 매칭** | **말의 각질과 기수의 선호 전법 일치도** | **0~100** |

> **등급 꼼수 감지 로직**: 상위 등급 승격 가능한 실력(최근 레이팅, 상금 누적)이면서 의도적으로 하위 등급에 머무르는 패턴:
> - 최근 3경주 중 2회 이상 3위 이내 입상 → 승급 대상
> - 그런데도 등급 변동 없이 같은 등급 유지
> - 해당 등급 내 레이팅이 상위 20% 이내
> - 이 경우 "강등급 강자" 플래그 부여 → 예측 점수 가산

### 7.3 종합 점수 산출

**Phase 1 (MVP): 가중 선형 모델**
```
종합점수 = Σ(Wi × Fi)

가중치 배분:
  말 기본 승률       (0.10) +
  거리 적성         (0.08) +
  주로상태 적성      (0.05) +
  최근 폼 지수       (0.08) +
  클래스 이동        (0.05) +
  게이트 포지션       (0.03) +
  전반력/후반력       (0.08) +  ← 신규
  마체중 변동        (0.03) +  ← 신규
  기수 승률          (0.08) +
  기수 트랙 특화      (0.05) +
  기수 피로도        (0.04) +  ← 신규
  조교사 시너지       (0.08) +
  말-기수 시너지      (0.08) +
  각질 매칭          (0.07) +  ← 신규
  등급 꼼수 보너스     (0.05) +  ← 신규
  휴식기간           (0.05)
  ─────────────────────────
  합계               1.00
```

**Phase 2: ML 모델 (LightGBM/XGBoost)**
- 위 요인들을 feature로, 3위 이내 여부를 target으로 이진 분류
- 각질(도주/선행/선입/추입/자재)을 one-hot encoding으로 feature화
- 기수 당일 기승 순서를 수치 feature로 포함
- 과거 데이터로 학습, 주간 재학습
- 예측 신뢰도를 Platt scaling으로 보정

---

## 8. 실시간 변경 감지 시스템

### 8.1 왜 중요한가
경마에서 기수/말 변경은 **경주 직전까지** 발생한다. 변경 사유:
- 기수 부상/질병
- 말 컨디션 불량으로 출전취소
- 기수 교체 (조교사 판단)
- 마체중 변화

### 8.2 3단계 감지 체계

| 단계 | 시점 | 주기 | 목적 |
|------|------|------|------|
| 1단계: 사전감지 | D-2~3 | 1일 1회 | 출주표 확정 후 초기 데이터 수집 |
| 2단계: 조기감지 | 당일 06:00~09:00 | 2시간마다 | 아침 변경사항 감지 |
| **3단계: 실시간** | **당일 09:00~17:00** | **10분마다** | **경기 직전 변경 즉시 감지** |

### 8.3 변경 감지 파이프라인
```
[스케줄러] → [KRA 크롤링] → [이전 출주표와 diff 비교]
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
             변경 없음          변경 감지           출전 취소
                    │                 │                 │
                  종료         entry_change_log     race_entry
                               기록                  상태 업데이트
                                      │
                               ┌──────┼──────┐
                               │             │
                          자동 재예측    FCM 푸시 알림
                               │        "3R 기수 변경:
                          prediction     김동수 → 김성현"
                          테이블 갱신          │
                                         앱에서 탭 →
                                         경주 상세로 이동
```

### 8.4 앱측 수동 변경 (시뮬레이션)
1. 경주 상세 화면에서 기수명 탭 → 기수 선택 드롭다운
2. `POST /api/predictions/override` 호출
3. 원본 예측 vs 변경 후 예측 **비교 뷰** 표시
4. "원래대로 복원" 버튼으로 원래 출주표 예측 복귀

---

## 9. 서버 스케줄링

| 작업 | 주기 | 시각 (KST) | 비고 |
|------|------|-----------|------|
| 전체 과거기록 크롤링 | 주 1회 | 월 02:00 | Record + RecordOfficial |
| 출주표 크롤링 | 수~금 | 10:00 | TodayPlayer |
| 당일 조기 감지 | 금/토/일 | 06:00, 08:00 | 2시간 간격 |
| **당일 실시간 감지** | **금/토/일** | **09:00~17:00 (10분)** | **경기 직전 변경** |
| 경주결과 수집 | 금/토/일 | 18:00 | 실제 순위 반영 |
| 통계 재계산 | 매일 | 03:00 | jockey/horse/synergy_stats |
| 예측 정확도 갱신 | 금/토/일 | 19:00 | 실제 vs 예측 비교 |

---

## 10. API 설계

### 10.1 엔드포인트 목록

| Method | Path | 설명 |
|--------|------|------|
| **경주** | | |
| GET | `/api/tracks` | 경마장 목록 |
| GET | `/api/races?track={S\|B\|J}&date={yyyy-MM-dd}` | 경주 목록 |
| GET | `/api/races/{id}` | 경주 상세 (출주표 포함) |
| GET | `/api/races/{id}/entries` | 출주표 (통계 포함) |
| GET | `/api/races/upcoming` | 다음 경주일 출주표 |
| **말** | | |
| GET | `/api/horses?search={name}` | 말 검색 |
| GET | `/api/horses/{id}` | 말 상세 |
| GET | `/api/horses/{id}/stats` | 말 통계 |
| GET | `/api/horses/{id}/records` | 말 과거 전적 |
| **기수** | | |
| GET | `/api/jockeys?search={name}&track={S\|B\|J}` | 기수 검색 |
| GET | `/api/jockeys/{id}` | 기수 상세 |
| GET | `/api/jockeys/{id}/stats` | 기수 통계 |
| GET | `/api/jockeys/{id}/records` | 기수 과거 전적 |
| **분석** | | |
| GET | `/api/synergy?horseId={}&jockeyId={}&trainerId={}` | 시너지 분석 |
| GET | `/api/analysis/horse/{id}` | 말 종합 분석 |
| GET | `/api/analysis/jockey/{id}` | 기수 종합 분석 |
| **예측** | | |
| GET | `/api/predictions/race/{id}` | 경주 예측 결과 |
| POST | `/api/predictions/override` | 수동 기수 변경 재예측 |
| GET | `/api/predictions/accuracy` | 과거 적중률 |
| **동기화** | | |
| GET | `/api/sync/delta?since={timestamp}` | 증분 동기화 |
| GET | `/api/sync/full` | 전체 동기화 (초기 로드) |
| **알림** | | |
| POST | `/api/notifications/subscribe` | 변경 알림 구독 |
| DELETE | `/api/notifications/unsubscribe` | 구독 해제 |
| **변경 이력** | | |
| GET | `/api/changes?raceId={id}` | 특정 경주 변경 이력 |
| GET | `/api/changes/recent` | 최근 변경 목록 |

### 10.2 주요 Response 예시

**GET /api/races/{id}/entries**
```json
{
  "race": {
    "id": 1234,
    "track": "서울",
    "date": "2026-04-04",
    "number": 3,
    "level": "국5",
    "distance": 1400,
    "weather": "맑음",
    "trackCondition": "양호",
    "moisturePct": 1.2
  },
  "entries": [
    {
      "gateNumber": 1,
      "horse": { "id": 101, "name": "바람의검", "rating": 52 },
      "jockey": { "id": 201, "name": "김동수" },
      "trainer": { "id": 301, "name": "박훈련" },
      "weight": 55.0,
      "prediction": {
        "rank": 1,
        "score": 78.5,
        "confidence": 72.3
      },
      "synergy": {
        "hjWinRate": 33.3,
        "bestRecordTrainerRate": 45.2
      },
      "changed": false
    }
  ],
  "changes": []
}
```

---

## 11. 수익 모델

| 모델 | 설명 | 적용 시기 |
|------|------|----------|
| AdMob 광고 | 배너 + 인터스티셜 광고 | Phase 2 |
| Play Store 구독 | 프리미엄: 광고 제거 + 상세 분석 + 실시간 알림 | Phase 2 |
| SMS 예측 전송 | 경주일 예측 결과를 문자로 자동 발송 (유료 구독) | Phase 2 |

### 무료 vs 프리미엄
| 기능 | 무료 | 프리미엄 |
|------|------|---------|
| 경주 목록/출주표 | O | O |
| 기본 예측 (Top 3) | O | O |
| 상세 분석 (차트, 시너지) | 일부 제한 | 전체 |
| 실시간 변경 알림 | X | O |
| 기수 수동 변경 시뮬레이션 | 1일 3회 | 무제한 |
| 광고 | 있음 | 없음 |
| SMS 예측 전송 | X | O |

---

## 12. Oracle Cloud Free Tier 고려사항

| 항목 | 스펙 | 비고 |
|------|------|------|
| 인스턴스 | ARM Ampere A1 | 최대 4 OCPU / 24GB RAM |
| 스토리지 | 200GB 블록 볼륨 | PostgreSQL + 데이터 충분 |
| 네트워크 | 10TB/월 아웃바운드 | |
| Playwright | ARM Chromium 빌드 필요 | Docker 이미지에서 ARM 태그 사용 |
| 스케줄러 | APScheduler 사용 | Redis 없이 단일 프로세스 |
| 방화벽 | OCI Security List | HTTPS(443) 포트 오픈 |
| 도메인 | duckdns.org 또는 무료 도메인 | Let's Encrypt SSL |

---

## 13. 참조 자료

### 기존 코드베이스
| 파일 | 역할 |
|------|------|
| `MalPhaGo/WebCrawling/WebCrawling/Form1.cs` | 크롤링 로직 + 시너지 분석 (654-691행) |
| `hracing/kra_crawler.py` | KRA Playwright 크롤러 |
| `hracing/gumvit_crawler.py` | Gumbit Selenium 크롤러 |
| `MalPhaGo/WebCrawling/DBClass/DBClass.cs` | SQLite 스키마 정의 |
| `MalPhaGo/WebCrawling/WebServer/DBWebService.asmx.cs` | 기존 API 패턴 |
| `MalPhaGo/WebCrawling/MalPhaGoLib/Server/*.cs` | 데이터 모델 (Horse, Player, Record, RecordOffical, Report) |
| `MalPhaGo/sqlite/malphago.db` | 기존 SQLite DB (77MB, 약 6만건) |

### 기존 DB 통계
| 테이블 | 레코드 수 |
|--------|----------|
| Record | 56,605 |
| RecordOffical | 61,479 |
| TodayPlayer | 1,330 |

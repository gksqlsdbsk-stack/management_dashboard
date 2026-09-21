# 05. 지표 계산식

> **규칙 기반 계산**(외부 AI 미사용). 모든 계산은 백엔드 `analytics` 앱 한 곳에서 수행한다 [NFR-04].
> 이 문서의 공식은 전부 **임시 가정**이다. 근거는 `99-assumptions.md`의 해당 `[A-xx]`. 공식을 바꾸려면 99와 이 문서를 함께 수정한다.

## 1. 계산 원칙

1. **집계 대상**: `SUBMITTED` 보고서의 `ReportValue`만 사용 [A-25]
2. **누적 기간**: 기준 연도 1월 ~ 기준 월. **월별 리포트의 당월**: 기준 월 단독
3. 값 모으기: 각 `ReportValue`의 `item.metric_key`로 분류해 같은 키를 **합산**(A-07). 단 `PIPELINE_WIN_RATE`는 평균
4. **비율은 분자·분모를 각각 합산한 뒤 나눈다.** 월별 비율의 평균을 쓰지 않는다 [A-29]
5. 분모가 0이거나 계산 조건을 만족하지 못하면 결과는 `null`(화면 `-`). 오류를 내지 않는다 [A-36]
6. 결과 반올림은 **표시 단계**에서만 한다(금액 정수, 비율 소수 1자리). 계산 중간에는 반올림하지 않는다
7. 비활성화(논리 삭제)된 항목의 과거 값도 연동 키가 있으면 계산에 포함한다 [A-06]
8. 삭제(비활성)된 부서의 과거 `SUBMITTED` 데이터도 포함한다. 부서가 사라져도 과거 수치는 유지한다 [A-50]
9. **데이터 없음**: 어떤 기간(누적 1~기준 월, 당월, `trend`의 한 달)에 `SUBMITTED` 보고서가 하나도 없으면 그 기간의 값은 **모두 `null`**이다(0이 아님). 보고서가 하나라도 있으면 flow 합계는 값이 없는 키를 0으로 계산한다 [A-50]

## 2. 지표 연동 키와 집계 유형 [A-07, A-26]

| 키 | 의미 | 집계 유형 | 기본 입력 부서 |
|---|---|---|---|
| `REVENUE` | 매출액 | flow | 영업 (프로젝트별) |
| `MATERIAL_COST` | 재료비 | flow | 생산 (프로젝트별) |
| `LABOR_COST` | 노무비 | flow | 생산 (프로젝트별) |
| `EXPENSE_COST` | 경비 | flow | 생산 (프로젝트별) |
| `SGA_EXPENSE` | 판매관리비 | flow | 경영지원 |
| `PURCHASE_AMOUNT` | 매입액 | flow | 구매/자재 |
| `COLLECTION_AMOUNT` | 수금액 | flow | 영업 |
| `RECEIVABLE_BALANCE` | 미수금 잔액 | stock | 영업 |
| `CASH_BALANCE` | 현금 잔액 | stock | 경영지원 |
| `PRODUCTION_QTY` | 생산량 | flow | 생산 |
| `PRODUCTION_CAPACITY` | 생산 능력 | flow | 생산 |
| `HEADCOUNT` | 인원수 | stock | 전 부서 |
| `ORDER_RECEIVED` | 신규 수주액 | flow | 영업 |
| `ORDER_BACKLOG` | 수주 잔고 | stock | 영업 |
| `PIPELINE_AMOUNT` | 파이프라인 금액 | stock | 영업 |
| `PIPELINE_WIN_RATE` | 예상 수주 확률(%) | rate | 영업 |

집계 유형별 기간 값 계산:
- **flow**: 기간(누적이면 1~기준 월, 당월이면 기준 월) 내 월별 합계를 더한다
- **stock**: 기준 월의 값. 기준 월에 값이 없으면 기준 월 이전(같은 연도) 중 **가장 최근에 값이 있는 월**의 값을 쓰고 응답에 `<필드>_as_of_month`를 함께 준다(값이 있는 월이 없으면 값·`as_of_month` 모두 `null`). 같은 월에 여러 값(여러 부서 인원수 등)은 합산
- **rate**: stock처럼 기준 월 값을 쓰되 같은 월 복수 값은 평균
- stock은 시점 값이므로 월별 리포트의 **당월 열과 누적 열이 같은 값**이다(다만 기준 월에 제출된 보고서가 하나도 없으면 §1-9에 따라 당월 열은 전부 `null`).

월별 시계열(`trend`)은 1월~기준 월 각 월을 “당월”로 계산한다. **stock은 그 월에 제출된 값만** 쓰고(이월하지 않음) 값이 없으면 `null`이다. 그 달에 `SUBMITTED` 보고서가 하나도 없으면 §1-9에 따라 그 점의 모든 값이 `null`이다. 그러므로 `trend`의 기준 월 점과 `cumulative`의 stock 값은 다를 수 있다.

## 3. 지표 정의 (응답 키 = snake_case 이름)

표기: `Σ(KEY)` = 해당 기간의 그 키 집계 값.

### 3.1 종합 원가/이익률 — `cost_profit` [A-27]

| 지표 | 공식 |
|---|---|
| `revenue` | Σ(REVENUE) |
| `material_cost` | Σ(MATERIAL_COST) |
| `labor_cost` | Σ(LABOR_COST) |
| `expense_cost` | Σ(EXPENSE_COST) |
| `total_cost` | material_cost + labor_cost + expense_cost |
| `gross_profit` | revenue − total_cost |
| `sga_expense` | Σ(SGA_EXPENSE) |
| `operating_profit` | gross_profit − sga_expense |
| `gross_margin` (%) | gross_profit ÷ revenue × 100 |
| `operating_margin` (%) | operating_profit ÷ revenue × 100 (**이익률**) |

- 재료비·노무비·경비 중 데이터가 전혀 없는 항목은 0으로 계산한다.
- `revenue = 0`이면 두 마진은 `null`.

### 3.2 프로젝트별 원가/이익률 — `projects` [A-28]

- `project_name`이 있는 값(프로젝트별형 항목)을 **프로젝트명별로** 묶어 아래를 계산한다. 배열로 반환, `revenue` 내림차순(같으면 프로젝트명 오름차순).
- 대상은 REVENUE·MATERIAL_COST·LABOR_COST·EXPENSE_COST 값뿐이다. 프로젝트명이 있어도 다른 연동 키의 값은 이 표에 쓰지 않는다. 기간에 제출 데이터가 없으면 빈 배열 [A-50].

| 지표 | 공식 |
|---|---|
| `revenue` | 프로젝트의 REVENUE 합 |
| `material_cost`, `labor_cost`, `expense_cost` | 프로젝트의 각 키 합 |
| `total_cost` | 세 원가의 합 |
| `gross_profit` | revenue − total_cost |
| `gross_margin` (%) | gross_profit ÷ revenue × 100 (revenue 0이면 `null`) |

- 판매관리비는 배부하지 않는다.
- 프로젝트별형이 아닌(월 합계형) 값은 프로젝트 표에 포함되지 않는다. 그러므로 프로젝트 합계는 종합 값과 다를 수 있다(월 합계형 REVENUE/원가 항목을 추가한 경우).

### 3.3 매입·매출·미수금 — `trade` [A-33]

| 지표 | 공식 |
|---|---|
| `revenue` | Σ(REVENUE) |
| `purchase_amount` | Σ(PURCHASE_AMOUNT) |
| `collection_amount` | Σ(COLLECTION_AMOUNT) |
| `receivable_balance` | RECEIVABLE_BALANCE (stock) |
| `receivable_ratio` (%) | receivable_balance ÷ revenue × 100 |

### 3.4 자금 수지 예측 — `cash_forecast` [A-31]

입력: 기준 월 M, 예측 개월 수 N (3~6, 기본 3).

1. **기준 잔액** `base_cash` = CASH_BALANCE (stock, `as_of_month` 포함)
2. **참조 기간** = M−2, M−1, M 중 `SUBMITTED` 데이터가 있는 달(같은 연도 안에서만. 1~2월 기준이면 1월부터). 없으면 `avg_inflow`·`avg_outflow`와 예측 결과가 `null`(기준 잔액은 그대로 보고)
3. 참조 기간의 월별 값으로 평균 계산:
   - `avg_inflow` = 평균( COLLECTION_AMOUNT )
   - `avg_outflow` = 평균( PURCHASE_AMOUNT + LABOR_COST + EXPENSE_COST + SGA_EXPENSE )
   - 월별 값이 없는 키는 그 달 0으로 본다
4. 예측 t = 1 … N (기준 월 다음 달부터):
   - `inflow_t = avg_inflow`, `outflow_t = avg_outflow`
   - `net_t = inflow_t − outflow_t`
   - `projected_cash_t = projected_cash_{t−1} + net_t` (`projected_cash_0 = base_cash`)
   - `shortfall_t = projected_cash_t < 0`
5. 예측 월의 연도는 12월을 넘으면 다음 해로 넘어간다(표시용).
- `base_cash`가 `null`(현금 잔액 데이터 없음)이면 유입·유출·순현금흐름만 계산하고 잔액은 `null`.
- 이 섹션은 대시보드와 월별 리포트에서 동일 값이며 `month`/`cumulative` 구분이 없다.
- 차트용 실적선은 `history`(1월~기준 월의 월별 `CASH_BALANCE`, 이월 없이 그 월 값만)로 낸다. 응답 형태는 `03-api.md` §8.4 [A-50].

### 3.5 손익분기점(BEP) — `bep` [A-30]

| 지표 | 공식 |
|---|---|
| `variable_cost` | material_cost |
| `fixed_cost` | labor_cost + expense_cost + sga_expense |
| `contribution_margin_ratio` (%) | (revenue − variable_cost) ÷ revenue × 100 |
| `bep_revenue` | fixed_cost ÷ (contribution_margin_ratio ÷ 100) |
| `bep_achievement_rate` (%) | revenue ÷ bep_revenue × 100 |

- `revenue = 0` 또는 `contribution_margin_ratio ≤ 0`이면 `bep_revenue`, `bep_achievement_rate`는 `null`(“산출 불가”).
- 값은 3.1과 같은 기간(당월/누적) 기준.

### 3.6 생산량·공장 가동률 — `production` [A-29]

| 지표 | 공식 |
|---|---|
| `production_qty` | Σ(PRODUCTION_QTY) |
| `production_capacity` | Σ(PRODUCTION_CAPACITY) |
| `utilization_rate` (%) | production_qty ÷ production_capacity × 100 |

### 3.7 수주 잔고·영업 파이프라인 — `orders` [A-34]

| 지표 | 공식 |
|---|---|
| `order_received` | Σ(ORDER_RECEIVED) (flow) |
| `order_backlog` | ORDER_BACKLOG (stock) |
| `pipeline_amount` | PIPELINE_AMOUNT (stock) |
| `pipeline_win_rate` (%) | PIPELINE_WIN_RATE (rate) |
| `weighted_pipeline` | pipeline_amount × pipeline_win_rate ÷ 100 |

### 3.8 인당 생산성 — `productivity` [A-32]

| 지표 | 공식 |
|---|---|
| `headcount` | HEADCOUNT (stock, 부서 합계) |
| `revenue_per_head` | revenue ÷ headcount |
| `operating_profit_per_head` | operating_profit ÷ headcount |
| `production_per_head` | production_qty ÷ headcount |

- 누적일 때도 분모는 기준 월(또는 `as_of_month`)의 인원수다.
- `headcount = 0` 또는 없음이면 `null`.

### 3.9 목표 대비 달성률 — `goals` [A-35]

| 목표 지표 키 | 실적(누적) | 단위 |
|---|---|---|
| `REVENUE` | cost_profit.revenue | 원 |
| `OPERATING_MARGIN` | cost_profit.operating_margin | % |
| `UTILIZATION` | production.utilization_rate | % |
| `PRODUCTION_QTY` | production.production_qty | 개 |
| `ORDER_RECEIVED` | orders.order_received | 원 |

- `achievement_rate` (%) = actual ÷ target × 100
- target이 없거나 0이면 `null`(“목표 미설정”). actual이 `null`이면 `null`.
- 월별 리포트에서도 실적은 **누적 기준**이다.

## 4. CSV 다운로드 매핑 [A-43, A-51]

열: `섹션,항목,구분,단위,값`. `03-api.md` §8의 계산 결과를 **세로로 펼친 것**이며, 값은 화면과 같은 계산 결과에 §4.3의 표시 규칙만 적용한다. 행 순서는 아래 정한 대로 고정한다.

### 4.1 섹션과 항목

섹션 순서: **데이터 상태**, 종합 원가/이익률, 프로젝트별, 매입·매출·미수금, 자금 수지 예측, BEP, 생산·가동률, 수주·파이프라인, 인당 생산성, 목표 달성률.

| 섹션 | 항목 = 응답 필드 (단위) | trend 항목 (대시보드만) |
|---|---|---|
| 종합 원가/이익률 | 매출액 `revenue`, 재료비 `material_cost`, 노무비 `labor_cost`, 경비 `expense_cost`, 총원가 `total_cost`, 매출총이익 `gross_profit`, 판매관리비 `sga_expense`, 영업이익 `operating_profit` (모두 원), 매출총이익률 `gross_margin`, 영업이익률 `operating_margin` (%) | 매출액, 영업이익, 영업이익률 |
| 프로젝트별 | (프로젝트 행마다) 매출액, 재료비, 노무비, 경비, 총원가, 매출총이익 (원), 매출총이익률 (%) | — |
| 매입·매출·미수금 | 매출액, 매입액 `purchase_amount`, 수금액 `collection_amount`, 미수금 잔액 `receivable_balance` (원), 미수금 비율 `receivable_ratio` (%) | 매출액, 매입액, 미수금 잔액 |
| 자금 수지 예측 | §4.4 | — |
| BEP | 변동비 `variable_cost`, 고정비 `fixed_cost` (원), 공헌이익률 `contribution_margin_ratio` (%), BEP 매출액 `bep_revenue` (원), BEP 달성률 `bep_achievement_rate` (%) | — |
| 생산·가동률 | 생산량 `production_qty`, 생산 능력 `production_capacity` (개), 가동률 `utilization_rate` (%) | 생산량, 가동률 |
| 수주·파이프라인 | 신규 수주액 `order_received`, 수주 잔고 `order_backlog`, 파이프라인 금액 `pipeline_amount` (원), 예상 수주 확률 `pipeline_win_rate` (%), 가중 파이프라인 `weighted_pipeline` (원) | 수주 잔고 |
| 인당 생산성 | 인원수 `headcount` (명), 인당 매출액 `revenue_per_head`, 인당 영업이익 `operating_profit_per_head` (원), 인당 생산량 `production_per_head` (개/명) | 인당 매출액 |
| 목표 달성률 | §4.5 | — |
| 데이터 상태 | §4.6 | — |

`_as_of_month` 필드는 별도 행으로 내지 않고 §4.2의 `구분` 표기로 나타낸다.

### 4.2 `구분` 열과 행 순서

- **대시보드**: 지표 행의 `구분` = `누적`. trend가 있는 섹션은 누적 행 뒤에 trend 행이 오며 `구분` = `YYYY-MM`(응답의 `year`와 점의 월, 월은 두 자리)이다. trend 행은 월 오름차순이고 한 달 안에서는 위 표의 trend 항목 순서다.
- **월별 리포트**: 지표마다 `당월` 행 다음에 `누적` 행을 붙여 낸다. 항목은 위 표의 순서다.
- **이월된 값**: stock/rate 값이 기준 월 값이 아니라 이전 월에서 이월된 값이면 `구분`에 `(n월 기준)`을 덧붙인다(`누적(8월 기준)`, `당월(8월 기준)`). 값이 `null`이거나 기준 월 값이면 붙이지 않는다. trend 행에는 붙이지 않는다.
- **프로젝트별**: 대시보드는 `구분` = 프로젝트명(응답의 행 순서). 월별 리포트는 `구분` = `프로젝트명 (당월)` 행을 전부 낸 뒤 `프로젝트명 (누적)` 행을 전부 낸다. 프로젝트마다 항목 순서는 위 표와 같다.
- 데이터가 없는 기간은 값이 `null`이므로 행은 그대로 나오고 `값`이 빈 칸이다(행 구조가 항상 같다).

### 4.3 값 표시와 파일 형식

- 값이 `null`이면 빈 칸.
- **반올림은 화면 표시와 같다**: 단위 원·개·명과 정수 값은 정수, `%`와 인당 생산량은 소수 1자리. 반올림은 절반 올림(0에서 먼 쪽)이며 CSV에서 처음 적용한다(API는 반올림하지 않는다).
- 숫자는 천 단위 콤마·단위 문자·지수 표기 없이 `-1234.5` 형태로 쓴다(엑셀이 숫자로 인식).
- 텍스트 셀(섹션·항목·구분·텍스트 값)이 `=`, `+`, `-`, `@`, 탭, 줄바꿈(CR)으로 시작하면 앞에 `'`를 붙인다(프로젝트명 등 사용자 입력이 엑셀 수식으로 실행되는 것을 막음). 숫자 값 셀에는 적용하지 않는다.
- UTF-8 + BOM, 쉼표 구분, 줄바꿈 CRLF, 쉼표·큰따옴표·줄바꿈이 든 셀은 큰따옴표로 감싼다(RFC 4180). 첫 줄은 헤더 `섹션,항목,구분,단위,값`이다.

### 4.4 자금 수지 예측 (대시보드·월별 리포트 동일)

| 항목 | 구분 | 단위 | 값 |
|---|---|---|---|
| 기준 현금 잔액 | `기준 월` (이월이면 `기준 월(n월 기준)`) | 원 | `base_cash` |
| 참조 개월 수 | `참조 기간` | 개월 | `reference_months`의 개수 |
| 월평균 유입 | `참조 기간 평균` | 원 | `avg_inflow` |
| 월평균 유출 | `참조 기간 평균` | 원 | `avg_outflow` |
| 현금 잔액(실적) | `YYYY-MM` — 1월~기준 월 (`history`) | 원 | `cash_balance` |
| 예상 유입 · 예상 유출 · 순현금흐름 · 예상 잔액 | `YYYY-MM` — 예측 월 (`forecast`, 월 오름차순, 월마다 이 4행 순서) | 원 | `inflow` · `outflow` · `net_cash_flow` · `projected_cash` |

### 4.5 목표 달성률

목표 지표마다 3행을 낸다(응답의 `goals` 순서): `구분` = `목표`(값 `target`), `실적(누적)`(`actual`), `달성률`(`achievement_rate`, 단위 `%`). `항목` = 지표명(매출액, 영업이익률, 가동률, 생산량, 신규 수주액), 목표·실적 행의 단위 = 지표 단위(원, %, 개).

### 4.6 데이터 상태

기준 월 기준의 미제출 경고 정보를 함께 내보낸다(부분 데이터로 만든 파일임을 알 수 있게). 2행: `항목` = `제출 부서`, `미제출 부서`, `구분` = 기준 월 `YYYY-MM`, 단위는 빈 칸, `값` = 부서명을 `, `로 이은 텍스트(없으면 빈 칸).

### 4.7 예시 (발췌)

대시보드 (`dashboard_2026-09.csv`):
```
섹션,항목,구분,단위,값
데이터 상태,제출 부서,2026-09,,"영업, 생산"
데이터 상태,미제출 부서,2026-09,,"구매/자재, 경영지원"
종합 원가/이익률,매출액,누적,원,800000000
종합 원가/이익률,영업이익률,누적,%,25.0
종합 원가/이익률,매출액,2026-01,원,80000000
프로젝트별,매출액,A프로젝트,원,500000000
매입·매출·미수금,미수금 잔액,누적(8월 기준),원,500
자금 수지 예측,예상 잔액,2026-12,원,-30000000
목표 달성률,매출액,달성률,%,66.7
```
월별 리포트 (`monthly-report_2026-09.csv`):
```
종합 원가/이익률,매출액,당월,원,120000000
종합 원가/이익률,매출액,누적,원,800000000
프로젝트별,매출액,A프로젝트 (당월),원,90000000
프로젝트별,매출액,A프로젝트 (누적),원,500000000
```

## 5. 검증용 예제 (테스트 작성 시 사용)

가정: 1월 단독 기준, 제출 완료 데이터.

| 입력 | 값 |
|---|---|
| REVENUE(프로젝트 A) | 1,000 |
| MATERIAL_COST(A) / LABOR_COST(A) / EXPENSE_COST(A) | 400 / 200 / 50 |
| SGA_EXPENSE | 150 |
| PRODUCTION_QTY / PRODUCTION_CAPACITY | 80 / 100 |
| HEADCOUNT 합계 | 10 |

기대 결과:
- total_cost = 650, gross_profit = 350, gross_margin = 35.0%
- operating_profit = 200, operating_margin = 20.0%
- utilization_rate = 80.0%
- 프로젝트 A: gross_profit = 350, gross_margin = 35.0%
- BEP: variable_cost = 400, fixed_cost = 400, 공헌이익률 = 60.0%, bep_revenue ≈ 666.67, 달성률 = 150.0%
- revenue_per_head = 100, operating_profit_per_head = 20

### 5.2 stock 이월 · 데이터 없음 (기준 월 9월)

가정: 8월에 영업 제출(REVENUE 프로젝트 A 1,000, RECEIVABLE_BALANCE 500). 9월에는 **생산만** 제출(영업 미제출). 1~7월은 제출 없음.

기대 결과 (대시보드 `trade`, 월별 리포트는 `month`/`cumulative`):
- `cumulative`: revenue = 1,000, receivable_balance = 500, `receivable_balance_as_of_month` = 8, receivable_ratio = 50.0%
- 월별 리포트 `month`(9월): 생산 보고서가 있으므로 블록은 존재한다. revenue = 0, receivable_balance = 500(`as_of_month` 8, 이월), receivable_ratio = `null`(분모 0)
- `trend`: 1~7월 점은 `month`만 있고 나머지 `null`, 8월 receivable_balance = 500, 9월 receivable_balance = `null`(이월 안 함)·revenue = 0
- `data_status`: `missing_departments`에 영업 포함, `has_warning` = true
- 기준 월을 6월로 바꾸면(제출 없음) `month` 블록은 전부 `null`

### 5.3 자금 수지 예측

가정: 기준 월 9월, N = 3. 7·8·9월 모두 제출되었고 매월 COLLECTION_AMOUNT 100, PURCHASE_AMOUNT 100 + LABOR_COST 30 + EXPENSE_COST 10 + SGA_EXPENSE 10. 9월 CASH_BALANCE = 120.

기대 결과: `reference_months` = [7, 8, 9], avg_inflow = 100, avg_outflow = 150, base_cash = 120(`as_of_month` 9)
- 10월: net = −50, projected_cash = 70, shortfall = false
- 11월: projected_cash = 20, shortfall = false
- 12월: projected_cash = −30, shortfall = true

추가 경계:
- 기준 월 11월, N = 3 → 예측 월은 (해당 연도 12월), (다음 해 1월), (다음 해 2월)
- 기준 월 1월 → `reference_months` = [1]
- 7~9월에 제출이 없고 6월에만 있으면 `reference_months` = [], avg_*·예측 값 `null`, base_cash는 6월 값(`as_of_month` 6)
- CASH_BALANCE 데이터가 전혀 없으면 base_cash = `null`, 예측 행의 inflow·outflow·net_cash_flow는 값이 있고 projected_cash·shortfall은 `null`

### 5.4 목표 달성률

- REVENUE 목표 1,200 / 실적 800 → achievement_rate = 66.7%
- UTILIZATION 목표 85 / 실적 80 → 94.1%
- 목표 미설정 또는 0 → `null`, 실적 `null` → `null`

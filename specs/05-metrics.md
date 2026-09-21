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
- **stock**: 기준 월의 값. 기준 월에 값이 없으면 기준 월 이전 중 **가장 최근에 값이 있는 월**의 값을 쓰고 응답에 `as_of_month`를 함께 준다. 같은 월에 여러 값(여러 부서 인원수 등)은 합산
- **rate**: stock처럼 기준 월 값을 쓰되 같은 월 복수 값은 평균

월별 시계열(`trend`)은 1월~기준 월 각 월을 “당월”로 계산한다(stock은 그 월의 값, 제출 데이터가 없는 월은 `null`).

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

- `project_name`이 있는 값(프로젝트별형 항목)을 **프로젝트명별로** 묶어 아래를 계산한다. 배열로 반환, `revenue` 내림차순.

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
2. **참조 기간** = M−2, M−1, M 중 `SUBMITTED` 데이터가 있는 달(같은 연도 안에서만. 1~2월 기준이면 1월부터). 없으면 전체 결과 `null`
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

## 4. CSV 다운로드 매핑 [A-43]

열: `섹션,항목,구분,단위,값`

- 섹션 = 응답 섹션 한글명(종합 원가/이익률, 프로젝트별, 매입·매출·미수금, 자금 수지 예측, BEP, 생산·가동률, 수주·파이프라인, 인당 생산성, 목표 달성률)
- 대시보드: `구분` = `누적` 또는 월(`2026-03`, trend 행), 프로젝트 행은 프로젝트명
- 월별 리포트: `구분` = `당월` / `누적`, 프로젝트 행은 프로젝트명
- 자금 수지 예측: `구분` = 예측 월(`2026-10`), 항목 = 예상 유입/유출/순현금흐름/예상 잔액
- 값이 `null`이면 빈 칸

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

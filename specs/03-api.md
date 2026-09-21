# 03. API 명세

> Django REST Framework, REST/JSON. `[A-xx]`는 `99-assumptions.md` 참조.
> 이 문서는 **계약(contract)** 이다. 구현 중 변경이 필요하면 이 문서를 먼저 고친다.

## 1. 공통 규약 [A-45]

- Base URL: `/api/` (개발 중 Vite 프록시 경유 [A-39])
- 요청/응답: `application/json` (업로드만 `multipart/form-data`, 다운로드만 `text/csv`)
- 인증: `Authorization: Token <key>` [A-12]. 로그인 API 외 모두 인증 필요
- 페이지네이션 없음. 목록은 배열로 반환
- 날짜/시간: ISO 8601 (Asia/Seoul)
- 숫자: 금액·수량은 JSON number로 주고받는다. 계산 불가 값은 `null` [A-36]

### 1.1 오류 응답

```json
{ "code": "validation_error", "detail": "사람이 읽는 한국어 메시지", "errors": { "필드명": ["메시지"] } }
```

| HTTP | code | 상황 |
|---|---|---|
| 400 | `validation_error` | 입력 형식 오류 |
| 400 | `login_failed` | 성명/사번/비밀번호 불일치 [A-10] |
| 400 | `incomplete_required` | 제출 시 필수 항목 미입력 (`errors.missing_items` = 항목 id/이름 목록) [A-20] |
| 400 | `upload_invalid` | 업로드 파일 오류 (`errors.rows` = `[{row, message}]`) [A-24] |
| 401 | `not_authenticated` | 토큰 없음/무효 |
| 403 | `forbidden` | 권한 없음 [A-16] |
| 404 | `not_found` | 대상 없음 |
| 409 | `duplicate_submission` | 이미 제출된 부서·월에 재제출 [A-18] |
| 409 | `report_locked` | 제출된 보고서 수정/업로드 시도 [A-18] |
| 409 | `department_in_use` | 소속 사용자가 있는 부서 삭제 [A-06] |
| 409 | `cannot_delete_user` | 자기 자신/마지막 관리자 삭제 [A-15] |

### 1.2 권한 표기
`관리자` = `ADMIN`만, `직원` = `EMPLOYEE`만, `인증` = 로그인한 누구나.

## 2. 인증

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| POST | `/auth/login/` | 공개 | 로그인 |
| POST | `/auth/logout/` | 인증 | 토큰 삭제, 204 |
| GET | `/auth/me/` | 인증 | 현재 사용자 |

`POST /auth/login/`
```json
// 요청
{ "name": "홍길동", "employee_no": "A001", "password": "..." }
// 응답 200
{ "token": "abc...", "user": { "id": 1, "name": "홍길동", "employee_no": "A001",
  "role": "EMPLOYEE", "department": { "id": 2, "name": "생산" } } }
```
관리자는 `department`가 `null`일 수 있다.

## 3. 사용자 관리 (관리자) [A-09, A-14, A-15]

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/users/` | 목록 (`?department=<id>` 필터 가능) |
| POST | `/users/` | 추가 |
| GET | `/users/{id}/` | 상세 |
| PATCH | `/users/{id}/` | 수정 (성명, 사번, 역할, 부서, 활성 여부, 비밀번호 재설정) |
| DELETE | `/users/{id}/` | 삭제 (204, 제한은 409 `cannot_delete_user`) |

사용자 표현:
```json
{ "id": 3, "name": "김영업", "employee_no": "S001", "role": "EMPLOYEE",
  "department": { "id": 1, "name": "영업" }, "is_active": true }
```
쓰기 요청은 `department_id`, `password`(쓰기 전용, 8자 이상)를 받는다. `role=EMPLOYEE`이면 `department_id` 필수.

## 4. 부서 · 입력 항목 관리

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/departments/` | 인증 | 활성 부서 목록. 직원은 본인 부서만 |
| POST | `/departments/` | 관리자 | 생성 |
| PATCH | `/departments/{id}/` | 관리자 | 수정 (이름, `input_guide`, `sort_order`) |
| DELETE | `/departments/{id}/` | 관리자 | 논리 삭제 [A-06] |
| GET | `/departments/{id}/items/` | 관리자 | 활성 입력 항목 목록 |
| POST | `/departments/{id}/items/` | 관리자 | 항목 생성 |
| PATCH | `/items/{id}/` | 관리자 | 항목 수정 |
| DELETE | `/items/{id}/` | 관리자 | 논리 삭제 |
| GET | `/metric-keys/` | 관리자 | 지표 연동 키 목록(드롭다운용) |

입력 항목 표현:
```json
{ "id": 12, "department": 2, "name": "프로젝트별 재료비", "scope": "PROJECT",
  "unit": "원", "metric_key": "MATERIAL_COST", "help_text": "…", "is_required": true, "sort_order": 1 }
```
- 이미 `ReportValue`가 있는 항목의 `scope` 변경(`PATCH /items/{id}/`)은 400 `validation_error` [A-04]

`GET /metric-keys/` → `[{ "key": "REVENUE", "label": "매출액", "unit": "원", "aggregation": "flow" }, ...]`
(`AnnualGoal`용 5개 키는 `/goals/`에서 별도 제공)

## 5. 월 실적 입력 (직원) [A-17 ~ A-21]

대상은 항상 **로그인한 직원의 소속 부서**다. `{year}`, `{month}`는 경로 변수. 미래 월은 400.

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/my-report/{year}/{month}/` | 직원 | 폼 정의 + 저장된 값 + 상태 + 진행률 |
| PUT | `/my-report/{year}/{month}/` | 직원 | **임시 저장** (값 전체 교체). 레코드가 없으면 `DRAFT`로 생성 |
| POST | `/my-report/{year}/{month}/submit/` | 직원 | **제출** |
| POST | `/my-report/{year}/{month}/upload/` | 직원 | 엑셀/CSV 업로드 반영 (`file` 필드) |

`GET` 응답 (PUT/upload 응답도 같은 형태):
```json
{
  "department": { "id": 2, "name": "생산", "input_guide": "…" },
  "year": 2026, "month": 9,
  "status": "NOT_STARTED",          // NOT_STARTED | DRAFT | SUBMITTED
  "submitted_at": null,
  "progress": { "filled": 3, "required": 6, "percent": 50 },
  "items": [ { "id": 12, "name": "프로젝트별 재료비", "scope": "PROJECT", "unit": "원",
               "help_text": "…", "is_required": true } ],
  "values": [ { "item_id": 12, "project_name": "A프로젝트", "value": 1500000 },
              { "item_id": 15, "project_name": "", "value": 320 } ]
}
```
- `NOT_STARTED`는 저장된 레코드가 없다는 뜻이며 DB `status` 값이 아니다.
- `items`·`values`·진행률은 **활성 항목**만 대상으로 한다. 비활성(삭제)된 항목의 과거 값은 저장되어 있어도 응답에 나오지 않고, PUT이 건드리지 않고 유지한다 [A-06].
- 소속 부서가 없거나 삭제된 직원, 관리자 계정은 이 절의 모든 API에서 403 `forbidden` [A-46].
- 검증 순서: 권한 → 연·월(400) → 잠금(409 `report_locked`) → 요청 본문(400).

`PUT` 요청: `{ "values": [ { "item_id": 12, "project_name": "A프로젝트", "value": 1500000 }, ... ] }`
- 요청의 값 집합이 저장된 값 전체를 교체한다. 빈 값(`null`/생략)은 저장하지 않는다.
- `MONTHLY` 항목에 `project_name`이 있거나 `PROJECT` 항목에 `project_name`이 비면 400.
- 같은 (`item_id`, `project_name`)이 요청에 중복되면 400.
- 다른 부서·비활성·없는 항목 id는 400. 상태가 `SUBMITTED`이면 409 `report_locked`.
- 값이 `null`/생략인 행은 저장하지 않으며, `project_name` 규칙·중복 검사도 값이 있는 행에만 적용한다. `project_name`은 앞뒤 공백을 제거한 뒤 저장·비교한다 [A-04].
- 본문 오류는 `errors.values` = 한국어 메시지 문자열 배열이다. 소수 4자리 초과·자릿수 20 초과는 400 [A-03].

`submit`
- 필수 항목 미입력 → 400 `incomplete_required`, `errors.missing_items` = `[{ "id": 12, "name": "…" }]`. 필수 항목이 0개면 값 없이도 제출 가능 [A-47]
- 이미 `SUBMITTED` → 409 `duplicate_submission`
- 성공 → 200, `status=SUBMITTED`, `submitted_at`, 위 GET과 같은 본문

`upload`: `06-excel-upload.md` 참조. 성공 응답은 `{ "applied_count": 12, "report": <GET 본문> }`.

## 6. 입력 현황 · 상세 조회 (관리자) [FR-A06, A-19, A-20, A-22]

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/status/?year=&month=` | 해당 월 요약 |
| GET | `/status/matrix/?year=` | 연간 월 × 부서 현황표 |
| GET | `/departments/{id}/report/{year}/{month}/` | 상세(입력값 조회). 응답 형태는 `/my-report/…` GET과 동일 |
| POST | `/departments/{id}/report/{year}/{month}/reopen/` | (임시) `SUBMITTED` → `DRAFT` [A-19]. `DRAFT`/없음이면 409 |

`GET /status/`:
```json
{
  "year": 2026, "month": 9,
  "total_departments": 4, "submitted_count": 2, "submitted_percent": 50,
  "departments": [
    { "department_id": 1, "name": "영업", "status": "SUBMITTED", "progress_percent": 100,
      "submitted_at": "2026-09-30T17:20:00+09:00", "submitted_by_name": "김영업" },
    { "department_id": 2, "name": "생산", "status": "DRAFT", "progress_percent": 50,
      "submitted_at": null, "submitted_by_name": null }
  ],
  "unsubmitted": ["생산", "구매/자재"]
}
```
`status`는 `NOT_STARTED | DRAFT | SUBMITTED`. `unsubmitted` = `SUBMITTED`가 아닌 부서명(미제출 모니터링).

`GET /status/matrix/`:
```json
{ "year": 2026, "departments": [{"id":1,"name":"영업"}],
  "months": [ { "month": 1, "statuses": { "1": "SUBMITTED", "2": "DRAFT" } } ] }
```

## 7. 연간 목표 (관리자) [A-35]

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/goals/?year=` | 해당 연도 목표 5개 지표 (미설정은 `target_value: null`) |
| PUT | `/goals/{year}/` | 목표 일괄 저장. `null`이면 해당 지표 목표 삭제 |

```json
{ "year": 2026, "goals": [
  { "metric_key": "REVENUE", "label": "매출액", "unit": "원", "target_value": 1200000000 },
  { "metric_key": "OPERATING_MARGIN", "label": "영업이익률", "unit": "%", "target_value": 12.0 },
  { "metric_key": "UTILIZATION", "label": "가동률", "unit": "%", "target_value": 85.0 },
  { "metric_key": "PRODUCTION_QTY", "label": "생산량", "unit": "개", "target_value": null },
  { "metric_key": "ORDER_RECEIVED", "label": "신규 수주액", "unit": "원", "target_value": null } ] }
```

## 8. 대시보드 · 월별 리포트 · 다운로드 (관리자) [FR-A07 ~ A09]

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/dashboard/?year=&month=&horizon=` | 누적 대시보드 (연초~`month`) |
| GET | `/monthly-report/?year=&month=&horizon=` | 월별 리포트 (당월 + 누적) |
| GET | `/dashboard/export/?year=&month=&horizon=` | 대시보드 CSV 다운로드 |
| GET | `/monthly-report/export/?year=&month=&horizon=` | 월별 리포트 CSV 다운로드 |

- `horizon`: 자금 수지 예측 개월 수 3~6, 기본 3 [A-31]
- 미래 월·`month` 범위 밖은 400
- 모든 계산은 `05-metrics.md`의 규칙을 따른다. 응답은 **계산 결과**만 담는다.

### 8.1 응답 최상위 구조 (공통)

```json
{
  "year": 2026, "month": 9,
  "period": { "from_month": 1, "to_month": 9 },
  "data_status": {
    "submitted_departments": ["영업", "생산"],
    "missing_departments": ["구매/자재", "경영지원"],
    "has_warning": true
  },
  "cost_profit": { … },          // 종합 원가/이익률
  "projects": [ … ],             // 프로젝트별 원가/이익률
  "trade": { … },                // 매입·매출·미수금
  "cash_forecast": { … },        // 자금 수지 예측
  "bep": { … },
  "production": { … },           // 생산량·가동률
  "orders": { … },               // 수주 잔고·파이프라인
  "productivity": { … },         // 인당 생산성
  "goals": [ … ]                 // 목표 대비 달성률
}
```

### 8.2 대시보드 vs 월별 리포트의 차이

- **대시보드**: 각 섹션은 `cumulative`(연초~기준 월) 값을 담고, 추가로 `trend`(1월~기준 월 월별 시계열 — 차트용)를 담는다.
- **월별 리포트**: 각 섹션은 `month`(당월 단독) 값과 `cumulative` 값을 모두 담는다. `trend`는 없다.

섹션 예시 (`cost_profit`, 대시보드):
```json
"cost_profit": {
  "cumulative": { "revenue": 800000000, "material_cost": 300000000, "labor_cost": 150000000,
    "expense_cost": 50000000, "total_cost": 500000000, "gross_profit": 300000000,
    "sga_expense": 100000000, "operating_profit": 200000000,
    "gross_margin": 37.5, "operating_margin": 25.0 },
  "trend": [ { "month": 1, "revenue": 80000000, "operating_profit": 15000000, "operating_margin": 18.8 } ]
}
```
나머지 섹션의 필드는 `05-metrics.md` §3의 지표 이름(snake_case)을 그대로 키로 사용한다. 계산 불가 값은 `null`.

`goals` 섹션 예시:
```json
"goals": [ { "metric_key": "REVENUE", "label": "매출액", "unit": "원",
             "target": 1200000000, "actual": 800000000, "achievement_rate": 66.7 } ]
```
목표 미설정이면 `target: null, achievement_rate: null`.

### 8.3 CSV 다운로드 [A-43]

- `Content-Type: text/csv; charset=utf-8`, UTF-8 BOM 포함, `Content-Disposition: attachment; filename="dashboard_2026-09.csv"` (리포트는 `monthly-report_2026-09.csv`)
- 열: `섹션,항목,구분,단위,값`
- 브라우저는 인증 헤더가 필요하므로 프런트가 `fetch`로 받아 Blob으로 저장한다.

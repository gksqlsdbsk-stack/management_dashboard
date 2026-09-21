# 02. 데이터 모델

> PostgreSQL + Django ORM. `[A-xx]`는 `99-assumptions.md` 참조.

## 1. ER 개요

```
User ──N:1──> Department ──1:N──> InputItem
                  │                   │
                  │ 1:N               │ 1:N
                  v                   v
            MonthlyReport ──1:N──> ReportValue

AnnualGoal (year, metric_key)  ※ 다른 테이블과 FK 없음
```

## 2. 모델 정의

### 2.1 `accounts.User` (AbstractUser 상속) [A-09, A-10]

| 필드 | 타입 | 설명 |
|---|---|---|
| `username` | AbstractUser 기본 | **사번**을 저장. 유니크 |
| `password` | AbstractUser 기본 | Django 해시 |
| `name` | CharField(50) | 성명 |
| `role` | CharField choices | `EMPLOYEE` / `ADMIN` |
| `department` | FK → Department, null, `SET_NULL` | 소속 부서. 관리자는 null 가능 [A-11] |
| `is_active` | AbstractUser 기본 | 그대로 사용(로그인 가능 여부) |

- `AUTH_USER_MODEL = "accounts.User"` (첫 마이그레이션 전에 설정)
- `first_name`, `last_name`, `email`, `is_staff`, `is_superuser`는 사용하지 않음(Django admin 사이트도 사용하지 않음)
- `role=EMPLOYEE`이면 `department` 필수(서버 검증)
- 기본 관리자 자동 생성: [A-13]

### 2.2 `organization.Department`

| 필드 | 타입 | 설명 |
|---|---|---|
| `name` | CharField(50) | 부서명 |
| `input_guide` | TextField, blank | 폼 상단에 표시할 부서 단위 입력 방법 안내 [A-08] |
| `sort_order` | PositiveSmallInteger | 표시 순서 |
| `is_active` | Boolean, default True | 논리 삭제 [A-06] |
| `created_at`, `updated_at` | DateTime | |

- 유니크: `name` (조건 `is_active=True`, 부분 유니크 제약)
- 초기 데이터: [A-01] (데이터 마이그레이션으로 1회 삽입, 앱 시작 시 재생성하지 않음)

### 2.3 `organization.InputItem`

| 필드 | 타입 | 설명 |
|---|---|---|
| `department` | FK → Department, `PROTECT` | |
| `name` | CharField(100) | 항목명(업로드 매칭 기준) [A-24] |
| `scope` | CharField choices | `MONTHLY`(월 합계형) / `PROJECT`(프로젝트별형) [A-04] |
| `unit` | CharField(20), blank | 원, %, 개, 명 등 표시용 |
| `metric_key` | CharField choices, null | 지표 연동 키 [A-07] |
| `help_text` | TextField, blank | 항목 단위 입력 방법 안내 [A-08] |
| `is_required` | Boolean, default True | [A-05] |
| `sort_order` | PositiveSmallInteger | |
| `is_active` | Boolean, default True | 논리 삭제 [A-06] |

- 유니크: (`department`, `name`) 조건 `is_active=True`
- 초기 데이터: [A-02]
- `metric_key` 허용값과 집계 유형은 `05-metrics.md` §2. 코드의 고정 목록(choices)이며 DB 테이블이 아니다.

### 2.4 `reports.MonthlyReport`

| 필드 | 타입 | 설명 |
|---|---|---|
| `department` | FK → Department, `PROTECT` | |
| `year` | PositiveSmallInteger | |
| `month` | PositiveSmallInteger (1~12) | |
| `status` | CharField choices | `DRAFT` / `SUBMITTED` [A-18] |
| `submitted_by` | FK → User, null, `SET_NULL` | [A-15] |
| `submitted_at` | DateTime, null | |
| `created_at`, `updated_at` | DateTime | |

- **유니크: (`department`, `year`, `month`)** → 같은 부서·같은 월 중복 방지 [A-18]
- 레코드가 없는 상태 = 화면상 `미작성`
- 진행률은 저장하지 않고 조회 시 계산 [A-20]

### 2.5 `reports.ReportValue`

| 필드 | 타입 | 설명 |
|---|---|---|
| `report` | FK → MonthlyReport, `CASCADE` | |
| `item` | FK → InputItem, `PROTECT` | |
| `project_name` | CharField(100), default `""` | `PROJECT` 범위 항목만 값을 가짐. `MONTHLY`는 빈 문자열 [A-04] |
| `value` | DecimalField(max_digits=20, decimal_places=4) | 숫자 [A-03] |

- **유니크: (`report`, `item`, `project_name`)**
- 빈 값은 행을 저장하지 않는다 [A-21]

### 2.6 `goals.AnnualGoal` [A-35]

| 필드 | 타입 | 설명 |
|---|---|---|
| `year` | PositiveSmallInteger | |
| `metric_key` | CharField choices | 목표 지표 키 5개: `REVENUE`, `OPERATING_MARGIN`, `UTILIZATION`, `PRODUCTION_QTY`, `ORDER_RECEIVED` |
| `target_value` | DecimalField(20, 4) | 금액=원, 비율=%, 수량=개 |

- 유니크: (`year`, `metric_key`)

## 3. 인덱스 · 제약 요약

- `MonthlyReport (department, year, month)` 유니크
- `ReportValue (report, item, project_name)` 유니크
- `AnnualGoal (year, metric_key)` 유니크
- 조회 성능용 추가 인덱스는 PoC에서는 만들지 않는다(필요해지면 기록 후 추가).

## 4. 초기 데이터 요약

| 대상 | 시점 | 내용 |
|---|---|---|
| 기본 관리자 | 앱 시작 시 (멱등) [A-13] | ADMIN / ADMIN / admin1234! |
| 부서·입력 항목 | 데이터 마이그레이션 (1회) | [A-01], [A-02] |
| 목표 | 없음 | 관리자가 입력 |

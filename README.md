# 경영지표 대시보드 & 리포트 (PoC)

대표자가 현장에 상주하지 않아도 **부서별 월말 간이 입력**과 **엑셀/CSV 업로드**만으로 전사 원가, 이익률, 가동률, 자금 수지 등 핵심 지표를 한눈에 파악하고 목표를 관리할 수 있는 경영 대시보드입니다.

- 목표: 월별 자료 취합 시간 부서당 약 8시간 → **1시간 미만**, 수기 작성 오류 제거
- 지표는 입력 데이터로 **규칙 기반 자동 계산**합니다 (외부 AI API 연동 없음)

## 현재 상태

> **Phase 4(엑셀/CSV 업로드)까지 구현되었습니다.** 로그인·로그아웃, 관리자의 사용자·부서·입력 항목 관리, 직원의 월 실적 입력(임시 저장·제출·엑셀/CSV 업로드)이 동작합니다. 관리자 현황·목표·대시보드는 이후 Phase에서 구현됩니다.

| Phase | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 기반 · 인증 | ✅ 완료 |
| 2 | 관리자 마스터 관리 (사용자·부서·입력 항목) | ✅ 완료 |
| 3 | 월 실적 입력 | ✅ 완료 |
| 4 | 엑셀/CSV 업로드 | ✅ 완료 |
| 5 | 입력 현황 · 연간 목표 | ⬜ 시작 전 |
| 6 | 지표 계산 · 대시보드/월별 리포트 | ⬜ 시작 전 |
| 7 | 다운로드 · 마무리 | ⬜ 시작 전 |

세부 작업과 완료 기준은 [specs/07-phases.md](specs/07-phases.md)를 봅니다.

## 주요 기능

**직원(부서 담당자)**
- 성명·사번·비밀번호 로그인
- 소속 부서 월 실적 입력 (입력 방법 안내 문구 제공), 임시 저장 · 수정 · 제출
- 엑셀/CSV 업로드로 월 실적 반영, 입력 진행률 표시
- 같은 부서·같은 월 중복 제출 방지

**관리자(대표자)**
- 사용자 추가/삭제/수정 및 부서 배정, 부서·부서별 입력 항목 관리
- 연간 목표 설정 (매출, 이익률, 가동률 등)
- 입력 현황 조회 (부서별 미제출 모니터링, 요약/상세)
- 누적 대시보드와 월별 리포트: 종합·프로젝트별 원가/이익률, 매입·매출·미수금, 3~6개월 자금 수지 예측, 손익분기점(BEP) 달성률, 생산량·가동률, 수주 잔고·영업 파이프라인, 인당 생산성, 목표 대비 달성률
- 대시보드/리포트 데이터 CSV 다운로드

**범위 제외 (PoC)**: 그룹웨어 연동(엑셀/CSV 업로드로 대체, 추후 확장 항목), 외부 AI API 연동, 배포

## 기술 스택

```
Vue.js SPA  ──HTTP/JSON──>  Django REST Framework  ──Django ORM──>  PostgreSQL
```

- Frontend: Vue.js 3, Vite, Bootstrap 5.0, HTML5, CSS3, Chart.js (SPA)
- Backend: Python 3, Django, Django REST Framework, openpyxl
- Database: PostgreSQL (로컬 Postgres.app, 포트 5432)

버전과 보조 결정은 [specs/99-assumptions.md](specs/99-assumptions.md)의 임시 가정을 따릅니다.

## 사용 방법 (현재 구현된 범위)

**직원** — 관리자가 사용자 화면에서 부서를 배정한 직원 계정으로 로그인하면 `월 실적 입력` 화면이 열립니다.
1. 연도·월을 고릅니다(현재 월 이하만 선택 가능, 기본은 현재 월).
2. 부서 안내 문구와 항목별 안내를 보고 값을 입력합니다. 프로젝트별 항목은 `+ 프로젝트 행 추가`로 프로젝트명과 값을 한 줄씩 넣습니다.
3. `임시 저장`은 언제든 가능하고 다시 열면 값이 유지됩니다. 같은 부서 직원이 같은 월의 보고서를 이어서 작성할 수 있습니다.
4. 엑셀/CSV로 채우려면 화면 아래 `엑셀/CSV 업로드`에서 파일을 골라 `업로드`합니다(아래 형식 참고). 반영 후 값을 확인하고 필요하면 고칩니다.
5. 진행률이 100%(필수 항목 모두 입력)가 되면 `제출`합니다. 제출 후에는 수정할 수 없고, 같은 부서·월의 재제출은 거부됩니다.

**업로드 파일 형식** — `.xlsx`(첫 번째 시트만) 또는 `.csv`(UTF-8, 쉼표 구분), 최대 5MB·데이터 1,000행. 첫 행은 헤더이며 `항목명`, `프로젝트명`, `값` 열이 있어야 합니다(순서 무관).

| 항목명 | 프로젝트명 | 값 |
|---|---|---|
| 프로젝트별 재료비 | A프로젝트 | 1500000 |
| 프로젝트별 재료비 | B프로젝트 | 820000 |
| 생산량 | | 320 |

- 항목명은 내 부서의 입력 항목과 정확히 같아야 합니다. 월 합계 항목은 프로젝트명을 비우고, 프로젝트별 항목은 프로젝트명이 필요합니다.
- 값은 숫자입니다(`1,500,000`처럼 천 단위 콤마는 가능, 원·₩ 같은 단위 문자는 불가).
- 파일에 있는 (항목, 프로젝트명)은 화면의 값을 덮어쓰고, 파일에 없는 값은 그대로 유지됩니다. 업로드 결과는 작성 중(임시 저장) 상태이며 제출은 따로 합니다.
- 오류가 한 행이라도 있으면 아무것도 반영되지 않고 행별 오류 목록이 표시됩니다. 이미 제출한 월에는 업로드할 수 없습니다.

**관리자** — `사용자`, `부서·항목` 메뉴에서 사용자·부서·입력 항목을 관리합니다. 값이 이미 입력된 항목은 범위(월 합계형↔프로젝트별형)를 바꿀 수 없습니다.

## 기본 관리자 계정

앱 시작 시 관리자 계정이 하나도 없으면 아래 계정이 자동 생성됩니다. **로그인 후 비밀번호를 변경하세요.**

| 성명 | 사번 | 비밀번호 |
|---|---|---|
| ADMIN | ADMIN | admin1234! |

## 실행 방법

```bash
# 1. PostgreSQL (Postgres.app 실행 후. createdb가 PATH에 없으면 Postgres.app의 bin을 추가)
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
createdb management_dashboard

# 2. 백엔드 (http://127.0.0.1:8000)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000

# 3. 프런트엔드 (http://localhost:5173) — 새 터미널
cd frontend
npm install
npm run dev
```

테스트: `cd backend && python manage.py test`, 프런트 빌드 검증: `cd frontend && npm run build`

- 백엔드는 `http://127.0.0.1:8000`에만 열립니다. curl 등으로 직접 호출할 때는 `localhost` 대신 `127.0.0.1`을 쓰세요.
- `migrate` 시 초기 부서 4개(영업, 생산, 구매/자재, 경영지원)와 입력 항목 19개가 1회 등록됩니다. 이후 관리자 화면에서 수정·삭제할 수 있고 서버를 다시 시작해도 재생성되지 않습니다.
- 기본 관리자(ADMIN / ADMIN / admin1234!)는 서버 시작 시 자동 생성되며, `migrate`가 끝난 뒤 `runserver`를 실행하면 만들어집니다.

DB 접속은 환경변수(`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)로 바꿀 수 있으며, 기본값은 Postgres.app 로컬 설정입니다.

## 문서

| 문서 | 설명 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 프로젝트 규칙, 기술 스택, 폴더 구조, 개발 원칙, 실행/테스트 명령 (바이브 코딩 지침) |
| [specs/00-index.md](specs/00-index.md) | specs 문서 색인 |
| [specs/01-requirements.md](specs/01-requirements.md) | 기능 요구 사항 |
| [specs/02-data-model.md](specs/02-data-model.md) | 데이터 모델 |
| [specs/03-api.md](specs/03-api.md) | API 명세 |
| [specs/04-screens.md](specs/04-screens.md) | 화면 구성 |
| [specs/05-metrics.md](specs/05-metrics.md) | 지표 계산식 |
| [specs/06-excel-upload.md](specs/06-excel-upload.md) | 엑셀/CSV 업로드 명세 |
| [specs/07-phases.md](specs/07-phases.md) | 개발 Phase 계획 (1~7) |
| [specs/99-assumptions.md](specs/99-assumptions.md) | **임시 가정 목록 — 사용자가 직접 확인·수정** |

## 변경 이력

- 2026-09-21: 문서 초안 작성 (CLAUDE.md, specs/00~07, specs/99). 코드 없음.
- 2026-09-21: Phase 1 구현 (Django 골격·User/Department 모델·기본 관리자·로그인 API, Vue 골격·로그인 화면). `Department` 모델을 Phase 1로 당기고 입력 항목 범위 변경 방지를 Phase 3으로 이월(07 반영).
- 2026-09-21: Phase 2 구현 (`InputItem` 모델·초기 데이터, 지표 연동 키 16개, 사용자/부서/입력 항목 CRUD API, `/admin/users`·`/admin/departments` 화면). 존재하지 않는 대상 조회 시 오류 응답이 500이 되던 예외 핸들러 버그 수정.
- 2026-09-21: Phase 3 구현 (`MonthlyReport`·`ReportValue` 모델, `/my-report/{year}/{month}/` 조회·임시 저장·제출 API, 진행률, `/entry` 화면, 입력 항목 범위 변경 방지). 99에 A-46(부서 없는 직원 403)·A-47(필수 항목 0개면 진행률 100%) 추가.
- 2026-09-21: Phase 4 구현 (`POST /my-report/{year}/{month}/upload/` — xlsx/CSV 파싱·행별 검증·전체 성공/전체 실패 반영, `/entry` 업로드 영역). 06에 정해지지 않은 세부 규칙을 99에 A-48로 기록.

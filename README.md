# 경영지표 대시보드 & 리포트 (PoC)

대표자가 현장에 상주하지 않아도 **부서별 월말 간이 입력**과 **엑셀/CSV 업로드**만으로 전사 원가, 이익률, 가동률, 자금 수지 등 핵심 지표를 한눈에 파악하고 목표를 관리할 수 있는 경영 대시보드입니다.

- 목표: 월별 자료 취합 시간 부서당 약 8시간 → **1시간 미만**, 수기 작성 오류 제거
- 지표는 입력 데이터로 **규칙 기반 자동 계산**합니다 (외부 AI API 연동 없음)

## 현재 상태

> **Phase 1~7의 구현이 모두 끝났습니다(PoC).** 로그인·로그아웃, 관리자의 사용자·부서·입력 항목 관리, 입력 현황 조회·연간 목표 설정, 누적 대시보드·월별 리포트와 CSV 다운로드, 직원의 월 실적 입력(임시 저장·제출·엑셀/CSV 업로드)이 동작합니다. 알려진 제한 사항은 아래 [알려진 제한 사항](#알려진-제한-사항)을 봅니다.

| Phase | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 기반 · 인증 | ✅ 완료 |
| 2 | 관리자 마스터 관리 (사용자·부서·입력 항목) | ✅ 완료 |
| 3 | 월 실적 입력 | ✅ 완료 |
| 4 | 엑셀/CSV 업로드 | ✅ 완료 |
| 5 | 입력 현황 · 연간 목표 | ✅ 완료 |
| 6 | 지표 계산 · 대시보드/월별 리포트 | ✅ 완료 |
| 7 | 다운로드 · 마무리 | ✅ 완료 |
| 8 | 배포 준비 (Render) | ✅ 코드·안내 준비 완료 (로컬 운영 모드 검증. 실제 Render 배포는 아직 하지 않음) |

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

**범위 제외 (PoC)**: 그룹웨어 연동(엑셀/CSV 업로드로 대체, 추후 확장 항목), 외부 AI API 연동, Render 이외의 배포 방식·CI/CD (Render 배포 준비는 아래 [Render 배포](#render-배포))

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

**관리자**
- `사용자`, `부서·항목` 메뉴에서 사용자·부서·입력 항목을 관리합니다. 값이 이미 입력된 항목은 범위(월 합계형↔프로젝트별형)를 바꿀 수 없습니다.
- `입력 현황`에서 연·월을 고르면 `요약` 탭에 제출 진행 막대, 부서별 상태·진행률·제출자·제출일시, 미제출 부서 강조 박스, 연간 월×부서 현황표가 나옵니다. 부서의 `상세 보기`로 입력값을 읽기 전용으로 볼 수 있고(관리자는 값을 직접 고치지 않습니다), 제출 완료 건은 `초안으로 되돌리기`로 직원이 다시 수정·제출하게 할 수 있습니다(임시 기능, 값은 유지됨).
- `대시보드`(누적)와 `월별 리포트`에서 연도·기준 월·자금 예측 기간(3~6개월)을 고르면 8개 분석 항목이 계산되어 표시됩니다: 종합·프로젝트별 원가/이익률, 매입·매출·미수금, 자금 수지 예측, BEP 달성률, 생산량·가동률, 수주 잔고·영업 파이프라인, 인당 생산성, 목표 대비 달성률. 대시보드는 표와 Chart.js 차트, 월별 리포트는 당월/누적 두 열을 병기한 표를 보여 줍니다.
  - **제출 완료(SUBMITTED)된 보고서만 집계**됩니다. 임시 저장 데이터는 제외되고, 기준 월에 미제출 부서가 있으면 상단에 경고가 나옵니다.
  - 계산할 수 없는 값(0으로 나누기, 데이터 없음)은 `-`로 표시됩니다. 제출된 보고서가 하나도 없는 기간은 0이 아니라 `-`입니다.
  - 미수금 잔액·현금 잔액·수주 잔고·인원수처럼 월말 시점 값은 기준 월 값을 쓰고, 없으면 이전 달 값을 이어 쓰며 `(n월 기준)`으로 표시합니다.
  - 자금 수지 예측은 최근 3개월(기준 월 포함, 제출된 달만) 평균 유입·유출을 예측 기간 내내 같다고 가정한 단순 추정입니다. 예상 잔액이 0 미만인 달은 `자금 부족 예상`으로 강조됩니다.
- 두 화면 오른쪽 위의 `CSV 다운로드`로 현재 선택한 연·월·예측 기간의 결과를 내려받습니다(`dashboard_2026-09.csv`, `monthly-report_2026-09.csv`).
  - 엑셀에서 한글이 깨지지 않는 UTF-8(BOM) 파일이며 열은 `섹션, 항목, 구분, 단위, 값`입니다. 첫 섹션 `데이터 상태`에 제출·미제출 부서가 함께 들어 있어 부분 데이터로 만든 파일인지 알 수 있습니다.
  - 값은 화면과 같은 규칙으로 반올림되어 화면 수치와 일치합니다(금액·수량은 정수, 비율·인당 생산량은 소수 1자리). 계산 불가 값은 빈 칸입니다.
  - 월말 시점 값이 이전 달에서 이월된 경우 `구분`에 `누적(8월 기준)`처럼 표시됩니다. 대시보드는 `누적` 행과 월별(`2026-03`) 행, 월별 리포트는 지표마다 `당월`·`누적` 행이 나옵니다.
  - 프로젝트명처럼 사용자가 입력한 텍스트가 `=`, `+`, `-`, `@`로 시작하면 엑셀 수식으로 실행되지 않도록 앞에 `'`가 붙습니다.
- `연간 목표`에서 연도별로 매출액·영업이익률·가동률·생산량·신규 수주액 목표를 입력합니다. 값을 비우고 저장하면 목표가 삭제됩니다(목표 미설정). 목표 대비 달성률은 대시보드·월별 리포트에서 확인합니다(실적은 누적 기준).

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

DB 접속은 환경변수(`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)로 바꿀 수 있으며, 기본값은 Postgres.app 로컬 설정입니다. `DATABASE_URL`이 있으면 그것이 우선합니다(운영). 환경변수 없이 실행하는 로컬 개발 동작은 변하지 않습니다.

## 사용성 점검 메모 (취합 시간 단축 목표)

목표는 월별 자료 취합 시간을 부서당 약 8시간에서 **1시간 미만**으로 줄이는 것입니다. **실제 사용자 소요 시간은 아직 측정하지 않았습니다**(개발 중에는 자동 시나리오로 흐름만 확인했고, 그 소요 시간은 사람의 작업 시간이 아닙니다). 달성 여부는 현업 시범 운영에서 측정해야 합니다.

**구조상 시간을 줄여 주는 부분**
- 입력 항목이 적고 모두 숫자입니다(초기 데이터: 영업 8, 생산 6, 구매/자재 2, 경영지원 3개 항목, 월 1회).
- 합계·비율·이익률·BEP·자금 예측 등 수기 계산과 취합이 사라지고 대시보드·리포트가 자동 계산됩니다.
- 엑셀/CSV 업로드 한 번으로 여러 항목을 반영하고(예: 생산 부서 7개 값 = 파일 1개), 오류는 행 번호와 함께 한꺼번에 알려 줍니다. 화면 입력과 섞어 써도 값이 유지됩니다.
- 필수 항목 검증·진행률·중복 제출 방지·제출 잠금으로 수기 작성 오류와 재작업을 줄입니다.
- 관리자는 입력 현황(미제출 부서 강조, 월×부서 현황표)으로 독촉 대상을 바로 알 수 있고, 결과를 CSV로 내려받아 보고 자료에 씁니다.

**시범 운영에서 병목이 될 수 있는 지점**
1. **프로젝트별 항목**(영업 매출, 생산 재료비·노무비·경비): 항목마다 프로젝트명을 따로 입력하므로 프로젝트가 N개면 최대 4N줄입니다. 업로드를 권장합니다. 프로젝트 마스터가 없어 프로젝트명 **오타가 다른 프로젝트로 집계**되어도 시스템이 알려 주지 못합니다(A-04).
2. **업로드 양식(템플릿) 다운로드가 없습니다**(요구 사항상 제외). 처음에는 열 이름(`항목명`, `프로젝트명`, `값`)을 직접 만들어야 합니다.
3. **정정은 관리자를 거칩니다.** 제출 후에는 직원이 수정할 수 없고 관리자가 `초안으로 되돌리기`를 해야 하므로 정정 요청이 잦으면 병목이 됩니다.
4. **이전 달 미제출은 경고되지 않습니다.** 미제출 경고는 기준 월 기준이라 누적 지표가 과소 집계되어도 입력 현황의 연간 현황표를 직접 봐야 합니다.
5. 미제출 알림(메일 등)이 없어(범위 밖) 독촉은 수동입니다.

**시범 운영 때 재 볼 것(제안)**: 부서별 입력~제출 소요 시간, 화면 입력 대 업로드 비율, 업로드 오류 건수, 되돌리기 횟수, 마감 후 관리자가 지표를 확인하기까지 걸린 시간.

## Render 배포

백엔드는 **Render Web Service(Python)**, 데이터베이스는 **Render Postgres**, 프런트엔드는 **Render Static Site**에 올립니다. 세 곳의 주소가 서로 달라서 프런트는 빌드 시 받은 `VITE_API_BASE_URL`로 API를 직접 호출하고, 백엔드는 CORS로 프런트 주소만 허용합니다(개발은 종전대로 Vite 프록시). 세부 결정은 [specs/99-assumptions.md](specs/99-assumptions.md)의 A-52입니다.

### 코드에서 준비된 것
- `backend/requirements.txt`에 `gunicorn`(운영 서버)과 `django-cors-headers`(CORS)를 추가했습니다. 정적 파일은 없으므로(JSON API 전용, Django admin 없음) `collectstatic`이나 whitenoise는 쓰지 않습니다.
- `config/settings.py`가 환경변수(`DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`)를 읽습니다. `DEBUG=false`인데 `SECRET_KEY`나 허용 호스트가 없으면 서버가 **시작 단계에서 분명한 오류로 멈춥니다**. Render가 자동으로 넣어 주는 `RENDER_EXTERNAL_HOSTNAME`은 허용 호스트에 자동으로 포함됩니다.
- 초기 관리자 비밀번호를 `DEFAULT_ADMIN_PASSWORD`로 지정할 수 있습니다(공개 저장소에 적힌 `admin1234!`를 운영에 쓰지 않기 위해서입니다).
- 프런트가 CSV 파일명을 읽도록 CORS로 `Content-Disposition`을 노출하고, 운영에서 오류가 Render 로그에 남도록 콘솔 로깅을 설정했습니다.
- 프런트는 빌드 시 `VITE_API_BASE_URL`(끝의 `/`는 무시)이 있으면 `<값>/api`를, 없으면 `/api`(개발 프록시)를 호출합니다.

### Render 대시보드에서 직접 설정할 값

**1) PostgreSQL** (New → PostgreSQL)

| 항목 | 값 |
|---|---|
| Name / Database / User | 자유(예: `management-dashboard-db`) |
| Region | **Web Service와 같은 리전** (내부 주소로 연결하려면 같아야 합니다) |
| 생성 후 복사할 것 | **Internal Database URL** (`postgresql://…@dpg-…/…`) |

**2) Web Service** (New → Web Service → 저장소 연결)

| 항목 | 값 |
|---|---|
| Name | 자유(예: `management-dashboard-api`) → 주소 `https://<이름>.onrender.com` |
| Language / Branch | Python 3 / `main` |
| Region | DB와 같은 리전 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt && python manage.py migrate` |
| Start Command | `gunicorn config.wsgi:application` |
| Health Check Path | **비워 둡니다** (공개 200 응답 경로가 없어 지정하면 실패로 판단될 수 있습니다) |

Environment Variables:

| 키 | 값 |
|---|---|
| `PYTHON_VERSION` | Render가 지원하는 Python 3.12 이상 전체 버전(예: `3.13.5`). 로컬은 3.14로 확인했습니다 |
| `DEBUG` | `false` |
| `SECRET_KEY` | 추측할 수 없는 긴 임의 문자열(Render의 Generate 기능 사용 가능) |
| `DATABASE_URL` | 위에서 복사한 **Internal Database URL** |
| `CORS_ALLOWED_ORIGINS` | Static Site 주소 `https://<프런트 이름>.onrender.com` (여러 개면 쉼표, 경로 없이) |
| `DEFAULT_ADMIN_PASSWORD` | 초기 관리자(ADMIN)의 강한 비밀번호. 관리자가 없을 때 **처음 한 번만** 쓰이며 이후 값을 바꿔도 기존 비밀번호는 바뀌지 않습니다 |
| `ALLOWED_HOSTS` | (선택) 사용자 지정 도메인을 쓸 때만 쉼표로 추가. `onrender.com` 주소는 자동 포함 |

**3) Static Site** (New → Static Site → 같은 저장소)

| 항목 | 값 |
|---|---|
| Branch | `main` |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| Environment `VITE_API_BASE_URL` | Web Service 주소 `https://<백엔드 이름>.onrender.com` (**`/api`는 붙이지 않음**) |
| Environment `NODE_VERSION` | `22.12.0` 이상 (Vite가 Node 20.19 이상 또는 22.12 이상을 요구합니다) |
| Redirects/Rewrites | Source `/*` → Destination `/index.html`, Action **Rewrite** (없으면 `/admin/dashboard` 등을 새로고침·직접 접속할 때 404) |

### 진행 순서
1. PostgreSQL 생성 → Internal Database URL 복사
2. Web Service 생성(위 값 입력). 프런트 주소를 아직 모르면 이름을 미리 정하거나, 배포 후 `CORS_ALLOWED_ORIGINS`를 채워 다시 배포합니다
3. Static Site 생성(`VITE_API_BASE_URL`에 Web Service 주소) → 생성된 프런트 주소를 Web Service의 `CORS_ALLOWED_ORIGINS`에 넣고 백엔드 재배포
4. 프런트 주소에 접속해 `ADMIN` / `ADMIN` / (`DEFAULT_ADMIN_PASSWORD`)로 로그인하고 비밀번호를 바꾼 뒤 사용자를 등록합니다
5. `VITE_*` 값은 **빌드 시점에 번들에 들어가므로**, 바꾸면 프런트를 다시 빌드·배포해야 합니다

### 운영 시 참고
- 마이그레이션은 배포 때마다 빌드 명령에서 실행됩니다(이미 적용된 것은 건너뜀). 초기 부서·입력 항목(부서 4개, 항목 19개)은 첫 마이그레이션에서 한 번만 들어갑니다.
- 기본 gunicorn 설정(워커 1개)으로 시작합니다. 인스턴스 메모리에 여유가 있으면 Start Command에 `--workers 2`를 붙여 볼 수 있습니다.
- `python manage.py check --deploy`의 경고 4개(XFrameOptions, CSRF 미들웨어, HSTS, SSL 리다이렉트)는 의도한 것입니다: 쿠키·세션·화면 렌더링이 없는 토큰 인증 JSON API이고, HTTPS 종료와 리다이렉트는 Render가 합니다(A-52).
- 요금제별 제한(무료 인스턴스의 유휴 슬립·첫 요청 지연, 무료 DB의 보존 기간, 백업 등)은 Render 대시보드의 현재 정책을 확인하세요. 이 저장소는 백업·모니터링을 구성하지 않습니다.
- 운영 모드를 로컬에서 시험하려면(임시 DB에서): `DEBUG=false SECRET_KEY=… ALLOWED_HOSTS=127.0.0.1 DATABASE_URL=postgresql://<사용자>@localhost:5432/<DB> CORS_ALLOWED_ORIGINS=http://localhost:5173 PORT=9000 gunicorn config.wsgi:application`

## 알려진 제한 사항

**범위 밖(만들지 않음)**
- Render 이외의 배포 방식·CI/CD·도메인 설정, 그룹웨어 연동(엑셀/CSV 업로드로 대체), 외부 AI API 연동
- 알림, 결재, 감사 로그, 다국어, 비밀번호 분실 찾기, `.xlsx` 다운로드, 업로드 양식 다운로드

**동작상 제한**
- 같은 부서 직원이 동시에 저장하면 **마지막 저장이 반영**됩니다(동시 편집 충돌 방지 없음, A-11).
- 인증 토큰은 만료되지 않고, 비밀번호는 관리자가 재설정하는 방식만 있습니다(본인 변경 불가). 기본 관리자(ADMIN / admin1234!)의 초기 비밀번호는 반드시 바꾸세요(운영에서는 `DEFAULT_ADMIN_PASSWORD` 환경변수로 처음부터 다른 값을 지정).
- 마지막 남은 관리자의 **삭제**는 막지만, 마지막 관리자를 직원으로 바꾸거나 비활성화하는 것은 막지 않습니다. 이 경우 서버를 다시 시작하면 기본 관리자가 다시 만들어집니다(사번 `ADMIN`이 이미 쓰이고 있으면 만들어지지 않음).
- 지표는 **제출 완료 보고서만** 집계하며, 임시 저장 데이터는 제외됩니다. 미제출 경고는 기준 월 기준입니다. 삭제한 부서의 과거 제출 데이터는 계속 집계됩니다.
- 자금 수지 예측은 최근 3개월(제출된 달만) 평균 유입·유출이 예측 기간 내내 같다고 가정한 **단순 추정**입니다.
- 프로젝트는 별도 마스터 없이 **프로젝트명 문자열**로 식별합니다(부서 간 같은 이름이면 합산).
- 회계연도는 1~12월 달력 연도이고 미래 월은 입력·대시보드 조회를 할 수 없습니다.
- 업로드는 `.xlsx`(첫 시트만)·`.csv`(UTF-8)만, 최대 5MB·1,000행입니다. 값은 소수 4자리까지 저장합니다.
- 목록 API에는 페이지네이션이 없습니다(PoC 데이터 규모 가정). 화면은 데스크톱 브라우저 기준이며 프런트엔드 자동화 테스트는 없습니다(빌드와 수동 확인으로 검증, A-42).
- 사용자 삭제는 실제 삭제이고, 부서·입력 항목 삭제는 논리 삭제(과거 데이터 유지)입니다.

임시로 정한 값과 가정은 모두 [specs/99-assumptions.md](specs/99-assumptions.md)에 있으며, 특히 ⭐ 표시 항목은 업무 확인이 필요합니다.

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
- 2026-09-21: Phase 5 구현 (`/status/`·`/status/matrix/`, 부서 보고서 상세 조회·제출 되돌리기, `AnnualGoal` 모델과 `/goals/` 조회·저장, `/admin/status`·`/admin/goals` 화면). 03 §6·§7에 정해지지 않은 세부 규칙을 99에 A-49로 기록하고 오류 코드 `report_not_submitted`를 03에 추가.
- 2026-09-21: Phase 6 구현 (`analytics` 계산 모듈 `metrics.py`(순수 함수)·`queries.py`·`dashboard.py`, `GET /dashboard/`·`/monthly-report/`, `/admin/dashboard`(KPI·표·Chart.js 차트 9종)·`/admin/report`(당월/누적 표) 화면). 응답 스키마를 03 §8.1~8.4·05·99 A-50으로 먼저 확정.
- 2026-09-21: Phase 7 구현 (`GET /dashboard/export/`·`/monthly-report/export/` UTF-8 BOM CSV, 두 화면의 `CSV 다운로드` 버튼, 화면·CSV 반올림 규칙 통일). CSV 세부 규칙을 05 §4·99 A-51로 먼저 확정. 전체 흐름 점검, 새 환경 기동 검증, 사용성 점검 메모와 알려진 제한 사항 정리.
- 2026-09-21: Phase 8 배포 준비(Render). 환경변수 기반 운영 설정(`DEBUG`·`SECRET_KEY`·`ALLOWED_HOSTS`·`DATABASE_URL`), CORS(`django-cors-headers`), `gunicorn`, 콘솔 로깅, 초기 관리자 비밀번호 환경변수(`DEFAULT_ADMIN_PASSWORD`), 프런트 `VITE_API_BASE_URL`, Render 설정 값 안내. 스펙은 99 A-52로 먼저 기록.

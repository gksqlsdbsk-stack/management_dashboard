# CLAUDE.md — 경영지표 대시보드 & 리포트 (PoC)

이 파일은 Claude가 이 저장소에서 작업할 때 따르는 프로젝트 규칙이다. 상세 요구 사항은 `specs/`에 있다.

## 1. 프로젝트 요약

대표자가 현장에 상주하지 않아도 부서별 월말 간이 입력과 엑셀/CSV 업로드만으로 전사 원가, 이익률, 가동률, 자금 수지 등 핵심 지표를 파악하고 목표를 관리하는 경영 대시보드(PoC). 목표는 월별 자료 취합 시간을 부서당 약 8시간 → 1시간 미만으로 줄이고 수기 작성 오류를 없애는 것.

- 사용자: 직원(부서 담당자) / 관리자(대표자)
- 지표는 입력 데이터로 **규칙 기반 자동 계산** (외부 AI API 없음)
- **PoC 범위 밖**: 그룹웨어 연동(엑셀/CSV 업로드로 대체), 외부 AI API 연동, 배포

## 2. 문서 규칙 (가장 중요)

1. **작업 전에 `specs/00-index.md`를 보고 관련 문서를 읽는다.** 구현은 specs를 따른다.
2. **명시되지 않은 기능·기술·라이브러리를 임의로 추가하지 않는다.** 필요해 보이면 추가하지 말고 사용자에게 제안한다.
3. 사용자가 정하지 않아 임시로 값을 정해야 하면(부서 목록, 입력 항목, 계산 공식, 상수, 제한값 등) **`specs/99-assumptions.md`에 `A-xx`로 추가**하고 다른 문서에서는 `[A-xx]`로 참조한다. 코드에 근거 없이 숫자를 박아 넣지 않는다.
4. `99-assumptions.md`는 사용자가 직접 수정한다. 사용자가 값을 바꾸면 그 문서가 **우선**이며, 참조하는 문서·코드를 맞춘다.
5. 스펙과 다르게 구현해야 하면 **먼저 스펙을 수정**(또는 사용자에게 확인)하고 나서 코드를 바꾼다. 스펙과 코드가 어긋난 채로 두지 않는다.
6. **README.md는 필요할 때마다 갱신**한다. 갱신 시점:
   - Phase 시작/완료 (진행 현황 표)
   - 실행·설치·테스트 명령, 환경변수, 폴더 구조 변경
   - 기능이 실제로 동작하기 시작했을 때 (사용법 추가)
   - `99-assumptions.md`의 확정/변경으로 사용자에게 보이는 동작이 바뀔 때
7. `specs/07-phases.md`의 체크박스는 작업을 마칠 때 갱신한다.

## 3. 기술 스택

```
Vue.js SPA  ──HTTP/JSON──>  Django REST Framework  ──Django ORM──>  PostgreSQL
```

| 영역 | 사용 |
|---|---|
| Frontend | Vue.js 3, Vite, Bootstrap 5.0(**CSS만**), HTML5, CSS3, SPA, Chart.js, Vue Router |
| Backend | Python 3, Django, Django ORM, Django REST Framework, REST/JSON API, openpyxl(엑셀 업로드) |
| Database | PostgreSQL (로컬 Postgres.app, 포트 5432) |
| 인증 | DRF TokenAuthentication |
| 사용자 모델 | `AbstractUser` 상속(`accounts.User`, `role`로 직원/관리자 구분) |

버전과 보조 결정(psycopg 3, Vue Router, fetch 사용, Pinia/axios 미사용, Vite 프록시 등)은 `specs/99-assumptions.md` §6 (A-37 ~ A-42)을 따른다. 위 표에 없는 라이브러리는 추가하지 않는다.

## 4. 폴더 구조

```
management_dashboard/
├── CLAUDE.md
├── README.md
├── specs/                      # 요구 사항 문서 (00-index.md 참조)
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                 # Django 설정, 루트 urls
│   ├── accounts/               # User(AbstractUser), 로그인/로그아웃, 사용자 관리
│   ├── organization/           # Department, InputItem, 지표 연동 키 상수
│   ├── reports/                # MonthlyReport, ReportValue, 입력/제출/업로드
│   ├── goals/                  # AnnualGoal
│   └── analytics/              # 지표 계산(metrics.py 순수 함수), 대시보드/리포트, 입력 현황, CSV 다운로드(export.py)
└── frontend/
    ├── package.json
    ├── vite.config.js          # /api 프록시
    └── src/
        ├── api/                # fetch 래퍼(파일 다운로드 포함)와 API 함수
        ├── router/             # Vue Router, 가드
        ├── views/              # 화면(라우트 단위)
        ├── components/         # 재사용 컴포넌트, 차트 캔버스
        ├── utils/              # 표시 형식(format.js), Chart.js 설정, 표 행 정의
        └── auth.js             # 로그인 상태(토큰), 역할별 홈
```

## 5. 개발 원칙

**공통**
- 한 번에 **한 Phase**만 진행한다(`specs/07-phases.md`). Phase 완료 기준을 만족한 뒤 다음으로 넘어간다.
- 작게 만들고 바로 실행해 확인한다. 요구되지 않은 추상화·설정·기능을 만들지 않는다(PoC).
- 주변 코드와 같은 스타일(주석 밀도, 이름 규칙, 관용구)로 쓴다. 코드 식별자는 영어, **화면 문구·사용자 메시지는 한국어**.
- 비밀번호·DB 접속 정보 등 민감 값을 코드에 커밋하지 않는다(DB는 환경변수, 기본 관리자 자격 증명만 요구 사항에 따라 예외).

**백엔드**
- API 계약은 `specs/03-api.md`를 그대로 따른다(경로, 필드명, 오류 `code`, 상태 코드).
- 입력 검증과 권한 검사는 **서버에서** 한다. 관리자 API는 관리자만, 직원은 **본인 부서** 데이터만.
- 같은 부서·월 중복 방지는 **DB 유니크 제약 + 서버 검증** 둘 다 둔다.
- 지표 계산은 `analytics` 앱의 계산 모듈 **한 곳**에만 둔다. 뷰는 조회·호출·직렬화만 한다. 계산은 순수 함수로 작성해 테스트하기 쉽게 한다.
- 계산식·집계 규칙은 `specs/05-metrics.md`를 따른다. 분모 0은 `null` 반환(예외 아님).
- 모델은 `specs/02-data-model.md`를 따른다. 부서·입력 항목은 논리 삭제(`is_active`).
- 기본 관리자 생성은 앱 시작 시 멱등하게 수행한다(`AppConfig.ready()`, 마이그레이션·DB 미준비 시 건너뜀).
- 마이그레이션 파일은 커밋한다.

**프런트엔드**
- 화면 구성·라우팅은 `specs/04-screens.md`를 따른다. Vue 3 Composition API(`<script setup>`)를 사용한다.
- API 호출은 `src/api/` 한 곳을 통한다. 컴포넌트에서 직접 `fetch` 하지 않는다.
- 계산 로직을 프런트에 두지 않는다(입력 진행률 실시간 표시만 예외). 서버가 준 값을 표시한다.
- 스타일은 Bootstrap 5.0 클래스 위주. Bootstrap JavaScript는 쓰지 않는다.
- 차트는 Chart.js를 직접 사용한다(래퍼 라이브러리 없음).
- 계산 불가(`null`) 값은 `-`로 표시한다.

## 6. 실행 / 테스트 명령

> 아래 명령은 Phase 1에서 실행해 확인했고 Phase 7에서 새 환경(빈 DB, 새 venv, 새 `npm install`) 기준으로 다시 확인했다. 실제와 다르면 즉시 이 절과 README를 고친다.

**최초 준비 (1회)**
```bash
# PostgreSQL: Postgres.app 실행(포트 5432) 후 DB 생성
# (createdb가 PATH에 없으면 Postgres.app의 bin을 PATH에 추가)
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
createdb management_dashboard

# 백엔드
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate

# 프런트엔드
cd ../frontend
npm install
```

**개발 서버 실행 (터미널 2개)**
```bash
# 1) 백엔드 — http://127.0.0.1:8000  (시작 시 기본 관리자 자동 생성)
cd backend && source .venv/bin/activate && python manage.py runserver 8000

# 2) 프런트엔드 — http://localhost:5173  (/api는 8000으로 프록시)
#    (Django는 127.0.0.1에만 열리므로 curl 등으로 직접 호출할 때는 localhost 대신 127.0.0.1 사용)
cd frontend && npm run dev
```

**테스트 / 검증**
```bash
# 백엔드 전체 테스트
cd backend && source .venv/bin/activate && python manage.py test

# 특정 앱만
python manage.py test analytics

# 마이그레이션 누락 확인
python manage.py makemigrations --check --dry-run

# 프런트엔드 빌드 검증 (프런트 자동화 테스트 도구는 도입하지 않음)
cd frontend && npm run build
```

**DB 환경변수 (기본값은 Postgres.app 로컬 설정)**
`DB_NAME`(management_dashboard), `DB_USER`(로컬 OS 사용자), `DB_PASSWORD`(없음), `DB_HOST`(localhost), `DB_PORT`(5432)

## 7. 작업 흐름 (Phase 진행 시)

1. `specs/07-phases.md`에서 현재 Phase의 작업 항목·완료 기준 확인
2. 관련 specs 문서(02~06, 99)를 읽고 착수
3. 백엔드 → 프런트 순으로, 작은 단위로 구현하고 바로 실행·테스트
4. 스펙과 다르게 된 부분이 있으면 스펙 갱신, 새 임시 값은 99에 추가
5. 완료 기준 확인 → `07-phases.md` 체크 → README 진행 현황 갱신
6. 커밋은 사용자가 요청할 때만 한다

## 8. 하지 말 것

- 그룹웨어 연동, 외부 AI API 연동, 배포 관련 작업
- 요구 사항에 없는 기능(알림, 결재, 감사 로그, 다국어, 비밀번호 분실 찾기, .xlsx 다운로드, 업로드 템플릿 다운로드 등)
- 99에 기록하지 않은 임의의 상수·공식·부서/항목
- 스펙을 바꾸지 않고 API 응답 형태·필드명을 바꾸는 것

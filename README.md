# 경영지표 대시보드 & 리포트 (PoC)

대표자가 현장에 상주하지 않아도 **부서별 월말 간이 입력**과 **엑셀/CSV 업로드**만으로 전사 원가, 이익률, 가동률, 자금 수지 등 핵심 지표를 한눈에 파악하고 목표를 관리할 수 있는 경영 대시보드입니다.

- 목표: 월별 자료 취합 시간 부서당 약 8시간 → **1시간 미만**, 수기 작성 오류 제거
- 지표는 입력 데이터로 **규칙 기반 자동 계산**합니다 (외부 AI API 연동 없음)

## 현재 상태

> **Phase 1(프로젝트 기반 · 인증)까지 구현되었습니다.** 로그인·로그아웃과 역할별 홈 이동만 동작하며, 나머지 화면은 이후 Phase에서 구현됩니다.

| Phase | 내용 | 상태 |
|---|---|---|
| 1 | 프로젝트 기반 · 인증 | ✅ 완료 |
| 2 | 관리자 마스터 관리 (사용자·부서·입력 항목) | ⬜ 시작 전 |
| 3 | 월 실적 입력 | ⬜ 시작 전 |
| 4 | 엑셀/CSV 업로드 | ⬜ 시작 전 |
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

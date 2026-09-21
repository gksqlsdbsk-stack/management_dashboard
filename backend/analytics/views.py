from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from config.exceptions import ApiError
from reports.services import validate_period

from . import dashboard as dashboard_service
from . import status as status_service

DEFAULT_HORIZON = 3
HORIZON_RANGE = range(3, 7)  # 자금 수지 예측 3~6개월 [A-31]


def _int_param(request, name):
    value = request.query_params.get(name, "")
    if not value.isdigit():
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.",
            {name: ["숫자로 입력해 주세요."]},
        )
    return int(value)


class StatusView(APIView):
    """`GET /status/?year=&month=` — 해당 월 입력 현황 요약 (관리자)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        year, month = _int_param(request, "year"), _int_param(request, "month")
        validate_period(year, month, allow_future=True)
        return Response(status_service.build_status(year, month))


class StatusMatrixView(APIView):
    """`GET /status/matrix/?year=` — 연간 월 × 부서 현황표 (관리자)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        year = _int_param(request, "year")
        validate_period(year, 1, allow_future=True)
        return Response(status_service.build_matrix(year))


def _dashboard_params(request):
    """`year`, `month`(현재 월 이하), `horizon`(3~6, 기본 3)을 검증해 돌려준다 [03 §8]."""
    year, month = _int_param(request, "year"), _int_param(request, "month")
    validate_period(year, month)
    horizon = DEFAULT_HORIZON
    if "horizon" in request.query_params:
        horizon = _int_param(request, "horizon")
        if horizon not in HORIZON_RANGE:
            raise ApiError(
                status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.",
                {"horizon": ["예측 기간은 3~6개월이어야 합니다."]},
            )
    return year, month, horizon


class DashboardView(APIView):
    """`GET /dashboard/?year=&month=&horizon=` — 누적 대시보드 (관리자)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(dashboard_service.build_dashboard(*_dashboard_params(request)))


class MonthlyReportView(APIView):
    """`GET /monthly-report/?year=&month=&horizon=` — 월별 리포트 (관리자)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(dashboard_service.build_monthly_report(*_dashboard_params(request)))

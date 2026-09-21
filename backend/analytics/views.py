from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from config.exceptions import ApiError
from reports.services import validate_period

from . import status as status_service


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

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from config.exceptions import ApiError

from . import services


class GoalListView(APIView):
    """`GET /goals/?year=` — 해당 연도 목표 5개 지표."""

    permission_classes = [IsAdmin]

    def get(self, request):
        year = request.query_params.get("year", "")
        if not year.isdigit():
            raise ApiError(
                status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.",
                {"year": ["연도를 숫자로 입력해 주세요."]},
            )
        services.validate_year(int(year))
        return Response(services.build_goals_payload(int(year)))


class GoalYearView(APIView):
    """`PUT /goals/{year}/` — 목표 일괄 저장."""

    permission_classes = [IsAdmin]

    def put(self, request, year):
        services.validate_year(year)
        raw_goals = request.data.get("goals") if hasattr(request.data, "get") else None
        services.save_goals(year, services.parse_goals(raw_goals))
        return Response(services.build_goals_payload(year))

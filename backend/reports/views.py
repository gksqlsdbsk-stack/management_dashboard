from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEmployee

from . import services


class MyReportView(APIView):
    """`/my-report/{year}/{month}/` — 로그인한 직원의 소속 부서 보고서."""

    permission_classes = [IsEmployee]

    def get(self, request, year, month):
        department = services.get_employee_department(request.user)
        services.validate_period(year, month)
        report = services.find_report(department, year, month)
        return Response(services.build_report_payload(department, year, month, report))

    def put(self, request, year, month):
        department = services.get_employee_department(request.user)
        services.validate_period(year, month)
        services.check_not_locked(services.find_report(department, year, month))

        items = services.active_items(department)
        parsed = services.parse_values(request.data.get("values") if hasattr(request.data, "get") else None, items)
        report = services.save_values(department, year, month, parsed, items)
        return Response(services.build_report_payload(department, year, month, report))


class MyReportSubmitView(APIView):
    permission_classes = [IsEmployee]

    def post(self, request, year, month):
        department = services.get_employee_department(request.user)
        services.validate_period(year, month)
        report = services.submit_report(department, year, month, request.user)
        return Response(services.build_report_payload(department, year, month, report))

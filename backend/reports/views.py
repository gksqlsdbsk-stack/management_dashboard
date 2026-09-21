from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsEmployee
from config.exceptions import ApiError
from organization.models import Department

from . import services, upload


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


class MyReportUploadView(APIView):
    """`/my-report/{year}/{month}/upload/` — 엑셀/CSV 업로드 반영 [06]."""

    permission_classes = [IsEmployee]

    def post(self, request, year, month):
        department = services.get_employee_department(request.user)
        services.validate_period(year, month)
        services.check_not_locked(services.find_report(department, year, month))

        uploaded = request.data.get("file") if hasattr(request.data, "get") else None
        if uploaded is None or not hasattr(uploaded, "read"):
            raise upload_error("업로드할 파일을 선택해 주세요.")
        items = services.active_items(department)
        try:
            parsed = upload.parse_upload(uploaded.name, uploaded.read(), items)
        except upload.UploadFileError as error:
            raise upload_error(str(error))
        except upload.UploadRowsError as error:
            raise upload_error(f"업로드 파일에 오류가 {len(error.errors)}건 있어 반영하지 않았습니다.", error.errors)

        report, applied_count = services.apply_upload(department, year, month, parsed, items)
        return Response(
            {
                "applied_count": applied_count,
                "report": services.build_report_payload(department, year, month, report),
            }
        )


def upload_error(detail, rows=None):
    return ApiError(status.HTTP_400_BAD_REQUEST, "upload_invalid", detail, {"rows": rows or []})


def _active_department(department_id):
    return get_object_or_404(Department, pk=department_id, is_active=True)


class DepartmentReportView(APIView):
    """`GET /departments/{id}/report/{year}/{month}/` — 부서 입력값 조회(관리자, 읽기 전용) [A-22]."""

    permission_classes = [IsAdmin]

    def get(self, request, department_id, year, month):
        department = _active_department(department_id)
        services.validate_period(year, month, allow_future=True)
        report = services.find_report(department, year, month)
        return Response(services.build_report_payload(department, year, month, report))


class DepartmentReportReopenView(APIView):
    """`POST /departments/{id}/report/{year}/{month}/reopen/` — (임시) 제출 → 초안 [A-19]."""

    permission_classes = [IsAdmin]

    def post(self, request, department_id, year, month):
        department = _active_department(department_id)
        services.validate_period(year, month, allow_future=True)
        report = services.reopen_report(department, year, month)
        return Response(services.build_report_payload(department, year, month, report))

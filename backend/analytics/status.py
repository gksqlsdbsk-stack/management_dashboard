"""입력 현황 집계 [03 §6, FR-A06]. 활성 부서만 대상으로 한다 [A-49]."""

from django.utils import timezone

from organization.models import Department, InputItem
from reports.models import MonthlyReport, ReportValue
from reports.services import calculate_progress

NOT_STARTED = "NOT_STARTED"


def _active_departments():
    return list(Department.objects.filter(is_active=True))  # sort_order, id 순


def build_status(year, month):
    """월별 요약: 부서별 상태·진행률과 미제출 부서 [GET /status/]."""
    departments = _active_departments()
    reports = {
        report.department_id: report
        for report in MonthlyReport.objects.filter(
            department__in=departments, year=year, month=month
        ).select_related("submitted_by")
    }

    required_ids = {department.id: [] for department in departments}
    for item_id, department_id in InputItem.objects.filter(
        department__in=departments, is_active=True, is_required=True
    ).values_list("id", "department_id"):
        required_ids[department_id].append(item_id)

    filled_ids = {report.id: [] for report in reports.values()}
    for report_id, item_id in ReportValue.objects.filter(
        report__in=reports.values(), item__is_active=True
    ).values_list("report_id", "item_id"):
        filled_ids[report_id].append(item_id)

    rows = []
    for department in departments:
        report = reports.get(department.id)
        status = report.status if report else NOT_STARTED
        if status == MonthlyReport.Status.SUBMITTED:
            percent = 100  # 제출 시점에 완성된 것으로 본다 [A-49]
        else:
            filled = filled_ids[report.id] if report else []
            percent = calculate_progress(required_ids[department.id], filled)["percent"]
        rows.append(
            {
                "department_id": department.id,
                "name": department.name,
                "status": status,
                "progress_percent": percent,
                "submitted_at": timezone.localtime(report.submitted_at).isoformat() if report and report.submitted_at else None,
                "submitted_by_name": report.submitted_by.name if report and report.submitted_by else None,
            }
        )

    submitted_count = sum(1 for row in rows if row["status"] == MonthlyReport.Status.SUBMITTED)
    return {
        "year": year,
        "month": month,
        "total_departments": len(rows),
        "submitted_count": submitted_count,
        "submitted_percent": submitted_count * 100 // len(rows) if rows else 0,
        "departments": rows,
        "unsubmitted": [row["name"] for row in rows if row["status"] != MonthlyReport.Status.SUBMITTED],
    }


def build_matrix(year):
    """연간 월 × 부서 현황표 [GET /status/matrix/]."""
    departments = _active_departments()
    statuses = {
        (department_id, month): status
        for department_id, month, status in MonthlyReport.objects.filter(
            department__in=departments, year=year
        ).values_list("department_id", "month", "status")
    }
    return {
        "year": year,
        "departments": [{"id": department.id, "name": department.name} for department in departments],
        "months": [
            {
                "month": month,
                "statuses": {
                    str(department.id): statuses.get((department.id, month), NOT_STARTED) for department in departments
                },
            }
            for month in range(1, 13)
        ],
    }

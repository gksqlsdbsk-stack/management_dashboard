"""월 실적 입력(직원) 로직 [03 §5]. 뷰는 이 모듈을 호출하고 직렬화만 한다."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, status

from config.exceptions import ApiError
from organization.models import InputItem

from .models import MonthlyReport, ReportValue

NO_DEPARTMENT_MESSAGE = "소속 부서가 없습니다. 관리자에게 문의하세요."

# 값 검증: 숫자, 소수 4자리, 자릿수 20 [A-03, 02 §2.5]
_value_field = serializers.DecimalField(
    max_digits=20,
    decimal_places=4,
    error_messages={
        "invalid": "값이 숫자가 아닙니다.",
        "max_decimal_places": "소수는 4자리까지 입력할 수 있습니다.",
        "max_digits": "값이 허용 범위를 벗어났습니다.",
        "max_whole_digits": "값이 허용 범위를 벗어났습니다.",
    },
)
PROJECT_NAME_MAX_LENGTH = ReportValue._meta.get_field("project_name").max_length


# ---- 대상 확인 ----

def get_employee_department(user):
    """로그인한 직원의 소속 부서. 없거나 삭제된 부서면 403 [A-46]."""
    department = user.department
    if department is None or not department.is_active:
        raise ApiError(status.HTTP_403_FORBIDDEN, "forbidden", NO_DEPARTMENT_MESSAGE)
    return department


def validate_period(year, month):
    """연·월 검증. 현재(Asia/Seoul) 월 이하만 허용한다 [A-17]."""
    errors = {}
    if not 1 <= month <= 12:
        errors["month"] = ["월은 1~12 사이여야 합니다."]
    if year < 1:
        errors["year"] = ["연도가 올바르지 않습니다."]
    if not errors:
        today = timezone.localdate()
        if (year, month) > (today.year, today.month):
            errors["month"] = ["미래 월은 입력할 수 없습니다."]
    if errors:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.", errors)


def active_items(department):
    return list(InputItem.objects.filter(department=department, is_active=True))  # sort_order, id 순


def find_report(department, year, month):
    return MonthlyReport.objects.filter(department=department, year=year, month=month).first()


# ---- 진행률 ----

def calculate_progress(required_item_ids, filled_item_ids):
    """입력 완료된 필수 항목 수 ÷ 전체 필수 항목 수 × 100, 소수점 버림 [A-20].

    필수 항목이 없으면 100% [A-47]. 프런트의 실시간 진행률도 같은 규칙을 쓴다.
    """
    required = set(required_item_ids)
    filled = len(required & set(filled_item_ids))
    percent = 100 if not required else filled * 100 // len(required)
    return {"filled": filled, "required": len(required), "percent": percent}


# ---- 응답 본문 ----

def _number(value):
    """Decimal → JSON number. 정수면 정수로 낸다."""
    return int(value) if value == value.to_integral_value() else float(value)


def build_report_payload(department, year, month, report):
    """GET/PUT/submit 공통 응답 본문 [03 §5]. 활성 항목만 대상으로 한다."""
    items = active_items(department)
    values = []
    if report is not None:
        values = list(
            report.values.filter(item__in=items).order_by("item__sort_order", "item_id", "id")
        )
    progress = calculate_progress(
        [item.id for item in items if item.is_required],
        [v.item_id for v in values],
    )
    return {
        "department": {"id": department.id, "name": department.name, "input_guide": department.input_guide},
        "year": year,
        "month": month,
        "status": report.status if report else "NOT_STARTED",
        "submitted_at": timezone.localtime(report.submitted_at).isoformat() if report and report.submitted_at else None,
        "progress": progress,
        "items": [
            {
                "id": item.id, "name": item.name, "scope": item.scope, "unit": item.unit,
                "help_text": item.help_text, "is_required": item.is_required,
            }
            for item in items
        ],
        "values": [
            {"item_id": v.item_id, "project_name": v.project_name, "value": _number(v.value)} for v in values
        ],
    }


# ---- 임시 저장 ----

def parse_values(raw_values, items):
    """PUT 본문의 values를 검증해 [(item, project_name, Decimal)] 로 돌려준다. 오류는 모아서 400."""
    if not isinstance(raw_values, list):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.",
            {"values": ["values는 목록이어야 합니다."]},
        )

    items_by_id = {item.id: item for item in items}
    errors = []
    parsed = []
    seen = {}
    for position, entry in enumerate(raw_values, start=1):
        if not isinstance(entry, dict):
            errors.append(f"{position}번째 값: 형식이 올바르지 않습니다.")
            continue
        item_id = entry.get("item_id")
        item = items_by_id.get(item_id) if isinstance(item_id, int) and not isinstance(item_id, bool) else None
        if item is None:
            errors.append(f"{position}번째 값: 이 부서의 입력 항목이 아닙니다.")
            continue

        # 빈 값은 저장하지 않는다 [A-21]
        raw_value = entry.get("value")
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            continue
        label = f"'{item.name}'"
        try:
            value = _value_field.run_validation(raw_value)
        except serializers.ValidationError as error:
            errors.extend(f"{label}: {message}" for message in error.detail)
            continue

        project_name = entry.get("project_name")
        project_name = "" if project_name is None else project_name
        if not isinstance(project_name, str):
            errors.append(f"{label}: 프로젝트명 형식이 올바르지 않습니다.")
            continue
        project_name = project_name.strip()  # 앞뒤 공백 제거 [A-04]
        if item.scope == InputItem.Scope.MONTHLY and project_name:
            errors.append(f"{label}: 프로젝트명을 입력하지 않는 항목입니다.")
            continue
        if item.scope == InputItem.Scope.PROJECT and not project_name:
            errors.append(f"{label}: 프로젝트명이 필요합니다.")
            continue
        if len(project_name) > PROJECT_NAME_MAX_LENGTH:
            errors.append(f"{label}: 프로젝트명이 너무 깁니다.")
            continue
        key = (item.id, project_name)
        if key in seen:
            suffix = f" '{project_name}'" if project_name else ""
            errors.append(f"{label}{suffix}: 같은 항목이 중복되었습니다.")
            continue
        seen[key] = True
        parsed.append((item, project_name, value))

    if errors:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.", {"values": errors}
        )
    return parsed


def _locked_error():
    return ApiError(status.HTTP_409_CONFLICT, "report_locked", "제출된 보고서는 수정할 수 없습니다.")


def save_values(department, year, month, parsed, items):
    """값 전체 교체(임시 저장). 레코드가 없으면 DRAFT로 만든다 [A-21].

    비활성 항목의 과거 값은 건드리지 않는다 [A-06].
    """
    with transaction.atomic():
        report, _ = MonthlyReport.objects.select_for_update().get_or_create(
            department=department, year=year, month=month
        )
        if report.status == MonthlyReport.Status.SUBMITTED:
            raise _locked_error()
        report.values.filter(item__in=items).delete()
        ReportValue.objects.bulk_create(
            ReportValue(report=report, item=item, project_name=project_name, value=value)
            for item, project_name, value in parsed
        )
        report.save(update_fields=["updated_at"])
    return report


def check_not_locked(report):
    if report is not None and report.status == MonthlyReport.Status.SUBMITTED:
        raise _locked_error()


# ---- 제출 ----

def submit_report(department, year, month, user):
    """필수 항목이 모두 입력되었을 때만 제출한다. 재제출은 409 [A-18, A-20]."""
    items = active_items(department)
    try:
        with transaction.atomic():
            report = MonthlyReport.objects.select_for_update().filter(
                department=department, year=year, month=month
            ).first()
            if report is not None and report.status == MonthlyReport.Status.SUBMITTED:
                raise ApiError(
                    status.HTTP_409_CONFLICT, "duplicate_submission", "이미 제출된 보고서입니다."
                )

            filled = set()
            if report is not None:
                filled = set(report.values.filter(item__in=items).values_list("item_id", flat=True))
            missing = [item for item in items if item.is_required and item.id not in filled]
            if missing:
                raise ApiError(
                    status.HTTP_400_BAD_REQUEST, "incomplete_required", "필수 항목이 모두 입력되지 않았습니다.",
                    {"missing_items": [{"id": item.id, "name": item.name} for item in missing]},
                )

            if report is None:
                report = MonthlyReport(department=department, year=year, month=month)
            report.status = MonthlyReport.Status.SUBMITTED
            report.submitted_by = user
            report.submitted_at = timezone.now()
            report.save()
    except IntegrityError:
        # 같은 부서·월의 최초 생성이 동시에 일어난 경우 [A-18]
        raise ApiError(status.HTTP_409_CONFLICT, "duplicate_submission", "이미 제출된 보고서입니다.")
    return report

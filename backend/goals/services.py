"""연간 목표 조회·저장 [03 §7, A-49]."""

from django.db import transaction
from rest_framework import serializers, status

from config.exceptions import ApiError
from config.numbers import MAX_YEAR, to_number

from .keys import GOAL_METRICS
from .models import AnnualGoal


# 목표값: 0 이상의 숫자, 소수 4자리, 자릿수 20 [A-49, 02 §2.6]
_target_field = serializers.DecimalField(
    max_digits=20,
    decimal_places=4,
    min_value=0,
    error_messages={
        "invalid": "목표값이 숫자가 아닙니다.",
        "min_value": "목표값은 0 이상이어야 합니다.",
        "max_decimal_places": "소수는 4자리까지 입력할 수 있습니다.",
        "max_digits": "목표값이 허용 범위를 벗어났습니다.",
        "max_whole_digits": "목표값이 허용 범위를 벗어났습니다.",
    },
)


def validate_year(year):
    if not 1 <= year <= MAX_YEAR:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.",
            {"year": ["연도가 올바르지 않습니다."]},
        )


def build_goals_payload(year):
    """해당 연도의 목표 5개. 미설정은 `target_value: null`."""
    targets = {goal.metric_key: goal.target_value for goal in AnnualGoal.objects.filter(year=year)}
    return {
        "year": year,
        "goals": [
            {"metric_key": key, "label": label, "unit": unit, "target_value": to_number(targets.get(key))}
            for key, label, unit in GOAL_METRICS
        ],
    }


def parse_goals(raw_goals):
    """PUT 본문의 goals를 검증해 {metric_key: Decimal|None} 로 돌려준다. 오류는 모아서 400."""
    if not isinstance(raw_goals, list):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.",
            {"goals": ["goals는 목록이어야 합니다."]},
        )
    labels = {key: label for key, label, _unit in GOAL_METRICS}
    errors = []
    parsed = {}
    for position, entry in enumerate(raw_goals, start=1):
        key = entry.get("metric_key") if isinstance(entry, dict) else None
        if key not in labels:
            errors.append(f"{position}번째 목표: 알 수 없는 지표입니다.")
            continue
        label = labels[key]
        if key in parsed:
            errors.append(f"{label}: 같은 지표가 중복되었습니다.")
            continue
        raw_value = entry.get("target_value")
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            parsed[key] = None  # 목표 삭제
            continue
        try:
            parsed[key] = _target_field.run_validation(raw_value)
        except serializers.ValidationError as error:
            errors.extend(f"{label}: {message}" for message in error.detail)
    if errors:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "validation_error", "입력값이 올바르지 않습니다.", {"goals": errors}
        )
    return parsed


def save_goals(year, parsed):
    """`None`은 삭제, 값은 저장(upsert). 본문에 없는 지표는 그대로 둔다. 전체가 하나의 트랜잭션이다."""
    with transaction.atomic():
        for key, value in parsed.items():
            if value is None:
                AnnualGoal.objects.filter(year=year, metric_key=key).delete()
            else:
                AnnualGoal.objects.update_or_create(year=year, metric_key=key, defaults={"target_value": value})

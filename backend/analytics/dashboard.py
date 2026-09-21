"""대시보드·월별 리포트 응답 조립 [03 §8]. 계산은 `metrics.py`, 조회는 `queries.py`가 한다."""

from decimal import Decimal

from config.numbers import to_number
from goals.keys import GOAL_METRICS
from goals.models import AnnualGoal
from organization.models import Department
from reports.models import MonthlyReport

from . import metrics
from .queries import load_facts

TREND_SECTIONS = ("cost_profit", "trade", "production", "orders", "productivity")


def _plain(value):
    """Decimal → JSON number(반올림 없음). dict·list는 재귀 처리한다 [A-50]."""
    if isinstance(value, Decimal):
        return to_number(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _data_status(year, month):
    """기준 월 기준, 활성 부서 대상 미제출 경고 정보 [A-25, A-50]."""
    departments = list(Department.objects.filter(is_active=True))
    submitted_ids = set(
        MonthlyReport.objects.filter(
            year=year, month=month, status=MonthlyReport.Status.SUBMITTED, department__in=departments
        ).values_list("department_id", flat=True)
    )
    submitted = [d.name for d in departments if d.id in submitted_ids]
    missing = [d.name for d in departments if d.id not in submitted_ids]
    return {"submitted_departments": submitted, "missing_departments": missing, "has_warning": bool(missing)}


def _goals(year, cumulative):
    targets = {goal.metric_key: goal.target_value for goal in AnnualGoal.objects.filter(year=year)}
    return metrics.goal_rows(GOAL_METRICS, targets, cumulative)


def _header(year, month):
    return {
        "year": year,
        "month": month,
        "period": {"from_month": 1, "to_month": month},
        "data_status": _data_status(year, month),
    }


def build_dashboard(year, month, horizon):
    """누적 대시보드: 각 섹션 `cumulative` (+ 차트용 `trend`) [03 §8.2]."""
    facts = load_facts(year, month)
    months = list(range(1, month + 1))
    cumulative = metrics.compute_period(facts, months, month)
    trend = metrics.compute_trend(facts, month)

    body = _header(year, month)
    body["cost_profit"] = {"cumulative": cumulative["cost_profit"], "trend": trend["cost_profit"]}
    body["projects"] = {"cumulative": metrics.project_rows(facts, months)}
    body["trade"] = {"cumulative": cumulative["trade"], "trend": trend["trade"]}
    body["cash_forecast"] = metrics.cash_forecast(facts, year, month, horizon)
    body["bep"] = {"cumulative": cumulative["bep"]}
    for section in ("production", "orders", "productivity"):
        body[section] = {"cumulative": cumulative[section], "trend": trend[section]}
    body["goals"] = _goals(year, cumulative)
    return _plain(body)


def build_monthly_report(year, month, horizon):
    """월별 리포트: 각 섹션 `month`(당월) + `cumulative` [03 §8.2]."""
    facts = load_facts(year, month)
    months = list(range(1, month + 1))
    cumulative = metrics.compute_period(facts, months, month)
    current = metrics.compute_period(facts, [month], month)

    body = _header(year, month)
    body["cost_profit"] = {"month": current["cost_profit"], "cumulative": cumulative["cost_profit"]}
    body["projects"] = {
        "month": metrics.project_rows(facts, [month]),
        "cumulative": metrics.project_rows(facts, months),
    }
    body["trade"] = {"month": current["trade"], "cumulative": cumulative["trade"]}
    body["cash_forecast"] = metrics.cash_forecast(facts, year, month, horizon)
    for section in ("bep", "production", "orders", "productivity"):
        body[section] = {"month": current[section], "cumulative": cumulative[section]}
    body["goals"] = _goals(year, cumulative)
    return _plain(body)

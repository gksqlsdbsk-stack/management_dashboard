"""지표 계산 [05]. DB·HTTP에 의존하지 않는 순수 함수 모음이다 [NFR-04].

입력은 월별 집계 사실(`MonthFacts`)이고 출력은 `Decimal`/`None`/정수 월로 이루어진 dict다.
JSON 변환(반올림 없음)은 `dashboard.py`가 한다. 규칙은 `05-metrics.md`, 응답 필드는 `03-api.md` §8.3~8.4.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from organization.metric_keys import METRIC_KEYS

ZERO = Decimal(0)
HUNDRED = Decimal(100)

_AGGREGATION = {key: aggregation for key, _label, _unit, aggregation in METRIC_KEYS}
FLOW_KEYS = [key for key, aggregation in _AGGREGATION.items() if aggregation == "flow"]
POINT_KEYS = [key for key, aggregation in _AGGREGATION.items() if aggregation in ("stock", "rate")]
RATE_KEYS = {key for key, aggregation in _AGGREGATION.items() if aggregation == "rate"}

# 프로젝트별 표에 쓰는 연동 키 [05 §3.2]
PROJECT_KEYS = ("REVENUE", "MATERIAL_COST", "LABOR_COST", "EXPENSE_COST")

# 섹션별 블록 필드와 그 순서 [03 §8.3]
SECTION_FIELDS = {
    "cost_profit": [
        "revenue", "material_cost", "labor_cost", "expense_cost", "total_cost", "gross_profit",
        "sga_expense", "operating_profit", "gross_margin", "operating_margin",
    ],
    "trade": [
        "revenue", "purchase_amount", "collection_amount", "receivable_balance",
        "receivable_balance_as_of_month", "receivable_ratio",
    ],
    "bep": ["variable_cost", "fixed_cost", "contribution_margin_ratio", "bep_revenue", "bep_achievement_rate"],
    "production": ["production_qty", "production_capacity", "utilization_rate"],
    "orders": [
        "order_received", "order_backlog", "order_backlog_as_of_month", "pipeline_amount",
        "pipeline_amount_as_of_month", "pipeline_win_rate", "pipeline_win_rate_as_of_month", "weighted_pipeline",
    ],
    "productivity": [
        "headcount", "headcount_as_of_month", "revenue_per_head", "operating_profit_per_head", "production_per_head",
    ],
}

# `trend` 점에 담는 필드 (`month`는 항상 포함) [03 §8.3]
TREND_FIELDS = {
    "cost_profit": ["revenue", "operating_profit", "operating_margin"],
    "trade": ["revenue", "purchase_amount", "receivable_balance"],
    "production": ["production_qty", "utilization_rate"],
    "orders": ["order_backlog"],
    "productivity": ["revenue_per_head"],
}

# 목표 지표별 실적: (섹션, 필드) [05 §3.9]
GOAL_ACTUALS = {
    "REVENUE": ("cost_profit", "revenue"),
    "OPERATING_MARGIN": ("cost_profit", "operating_margin"),
    "UTILIZATION": ("production", "utilization_rate"),
    "PRODUCTION_QTY": ("production", "production_qty"),
    "ORDER_RECEIVED": ("orders", "order_received"),
}


@dataclass
class MonthFacts:
    """한 달의 `SUBMITTED` 보고서 집계."""

    month: int
    has_report: bool = False  # 그 달에 제출된 보고서가 하나라도 있는가
    sums: dict = field(default_factory=dict)  # 연동 키 → 그 달 값의 합계 (값이 없는 키는 없음)
    counts: dict = field(default_factory=dict)  # 연동 키 → 값 개수 (rate 평균용)
    projects: dict = field(default_factory=dict)  # 프로젝트명 → {연동 키: 합계}


def ratio(numerator, denominator, factor=HUNDRED):
    """분자 ÷ 분모 × factor. 분자·분모가 없거나 분모가 0이면 None [05 §1-5]."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator * factor


# ---- 집계 (flow / stock / rate) ----

def _flow(facts_by_month, months, key):
    return sum((facts_by_month[m].sums.get(key, ZERO) for m in months), ZERO)


def _month_value(facts, key):
    """그 달에 제출된 값만 본 stock/rate 값. rate는 평균, 값이 없으면 None."""
    if key not in facts.sums:
        return None
    if key in RATE_KEYS:
        return facts.sums[key] / facts.counts[key]
    return facts.sums[key]


def _carry_forward(facts_by_month, as_of_month, key):
    """기준 월 값, 없으면 이전 월 중 가장 최근에 값이 있는 월의 값. (값, 가져온 월) [05 §2]."""
    for month in range(as_of_month, 0, -1):
        value = _month_value(facts_by_month[month], key)
        if value is not None:
            return value, month
    return None, None


# ---- 섹션 계산 ----

def compute_sections(flow, point):
    """한 기간의 6개 섹션 블록을 계산한다.

    flow: {flow 키: Decimal}, point: {stock/rate 키: (값 또는 None, as_of 월 또는 None)}
    """
    revenue = flow["REVENUE"]
    material, labor, expense = flow["MATERIAL_COST"], flow["LABOR_COST"], flow["EXPENSE_COST"]
    sga = flow["SGA_EXPENSE"]
    total_cost = material + labor + expense
    gross_profit = revenue - total_cost
    operating_profit = gross_profit - sga

    receivable, receivable_as_of = point["RECEIVABLE_BALANCE"]
    backlog, backlog_as_of = point["ORDER_BACKLOG"]
    pipeline, pipeline_as_of = point["PIPELINE_AMOUNT"]
    win_rate, win_rate_as_of = point["PIPELINE_WIN_RATE"]
    headcount, headcount_as_of = point["HEADCOUNT"]

    variable_cost = material
    fixed_cost = labor + expense + sga
    contribution_margin_ratio = ratio(revenue - variable_cost, revenue)
    bep_revenue = None
    if contribution_margin_ratio is not None and contribution_margin_ratio > 0:
        bep_revenue = fixed_cost / (contribution_margin_ratio / HUNDRED)

    production_qty = flow["PRODUCTION_QTY"]

    return {
        "cost_profit": {
            "revenue": revenue, "material_cost": material, "labor_cost": labor, "expense_cost": expense,
            "total_cost": total_cost, "gross_profit": gross_profit, "sga_expense": sga,
            "operating_profit": operating_profit,
            "gross_margin": ratio(gross_profit, revenue), "operating_margin": ratio(operating_profit, revenue),
        },
        "trade": {
            "revenue": revenue, "purchase_amount": flow["PURCHASE_AMOUNT"],
            "collection_amount": flow["COLLECTION_AMOUNT"],
            "receivable_balance": receivable, "receivable_balance_as_of_month": receivable_as_of,
            "receivable_ratio": ratio(receivable, revenue),
        },
        "bep": {
            "variable_cost": variable_cost, "fixed_cost": fixed_cost,
            "contribution_margin_ratio": contribution_margin_ratio, "bep_revenue": bep_revenue,
            "bep_achievement_rate": ratio(revenue, bep_revenue),
        },
        "production": {
            "production_qty": production_qty, "production_capacity": flow["PRODUCTION_CAPACITY"],
            "utilization_rate": ratio(production_qty, flow["PRODUCTION_CAPACITY"]),
        },
        "orders": {
            "order_received": flow["ORDER_RECEIVED"],
            "order_backlog": backlog, "order_backlog_as_of_month": backlog_as_of,
            "pipeline_amount": pipeline, "pipeline_amount_as_of_month": pipeline_as_of,
            "pipeline_win_rate": win_rate, "pipeline_win_rate_as_of_month": win_rate_as_of,
            "weighted_pipeline": pipeline * win_rate / HUNDRED if pipeline is not None and win_rate is not None else None,
        },
        "productivity": {
            "headcount": headcount, "headcount_as_of_month": headcount_as_of,
            "revenue_per_head": ratio(revenue, headcount, 1),
            "operating_profit_per_head": ratio(operating_profit, headcount, 1),
            "production_per_head": ratio(production_qty, headcount, 1),
        },
    }


def null_sections():
    """데이터 없는 기간의 6개 섹션: 모든 값이 None [05 §1-9]."""
    return {section: {name: None for name in names} for section, names in SECTION_FIELDS.items()}


def compute_period(facts_by_month, months, as_of_month, carry_forward=True):
    """`months` 기간(누적 1~M, 당월 [M], trend의 한 달)의 섹션 블록.

    기간에 제출된 보고서가 하나도 없으면 전부 None이다. `carry_forward=False`는 stock을 이월하지 않고
    `as_of_month` 달에 제출된 값만 쓴다(trend) [05 §2].
    """
    if not any(facts_by_month[m].has_report for m in months):
        return null_sections()
    flow = {key: _flow(facts_by_month, months, key) for key in FLOW_KEYS}
    point = {}
    for key in POINT_KEYS:
        if carry_forward:
            point[key] = _carry_forward(facts_by_month, as_of_month, key)
        else:
            value = _month_value(facts_by_month[as_of_month], key)
            point[key] = (value, as_of_month if value is not None else None)
    return compute_sections(flow, point)


def compute_trend(facts_by_month, last_month):
    """1월~기준 월 매월 1개 점. 그 달을 '당월'로 계산하며 stock은 이월하지 않는다 [05 §2]."""
    trend = {section: [] for section in TREND_FIELDS}
    for month in range(1, last_month + 1):
        sections = compute_period(facts_by_month, [month], month, carry_forward=False)
        for section, names in TREND_FIELDS.items():
            trend[section].append({"month": month, **{name: sections[section][name] for name in names}})
    return trend


# ---- 프로젝트별 원가/이익률 [05 §3.2] ----

def project_rows(facts_by_month, months):
    """프로젝트명별 행. `revenue` 내림차순, 같으면 프로젝트명 오름차순. 제출 데이터가 없으면 빈 목록."""
    if not any(facts_by_month[m].has_report for m in months):
        return []
    totals = {}
    for month in months:
        for name, sums in facts_by_month[month].projects.items():
            row = totals.setdefault(name, {key: ZERO for key in PROJECT_KEYS})
            for key in PROJECT_KEYS:
                row[key] += sums.get(key, ZERO)
    rows = []
    for name, sums in totals.items():
        total_cost = sums["MATERIAL_COST"] + sums["LABOR_COST"] + sums["EXPENSE_COST"]
        gross_profit = sums["REVENUE"] - total_cost
        rows.append(
            {
                "project_name": name, "revenue": sums["REVENUE"], "material_cost": sums["MATERIAL_COST"],
                "labor_cost": sums["LABOR_COST"], "expense_cost": sums["EXPENSE_COST"], "total_cost": total_cost,
                "gross_profit": gross_profit, "gross_margin": ratio(gross_profit, sums["REVENUE"]),
            }
        )
    rows.sort(key=lambda row: (-row["revenue"], row["project_name"]))
    return rows


# ---- 자금 수지 예측 [05 §3.4] ----

def _forecast_month(year, month, offset):
    index = month + offset - 1
    return year + index // 12, index % 12 + 1


def cash_forecast(facts_by_month, year, month, horizon):
    """기준 월 `month`, 예측 개월 수 `horizon`의 자금 수지 예측과 실적선(`history`)."""
    base_cash, base_cash_as_of = _carry_forward(facts_by_month, month, "CASH_BALANCE")
    reference_months = [m for m in range(max(1, month - 2), month + 1) if facts_by_month[m].has_report]

    avg_inflow = avg_outflow = None
    if reference_months:
        count = len(reference_months)
        avg_inflow = sum((facts_by_month[m].sums.get("COLLECTION_AMOUNT", ZERO) for m in reference_months), ZERO) / count
        avg_outflow = sum(
            (
                sum((facts_by_month[m].sums.get(key, ZERO) for key in ("PURCHASE_AMOUNT", "LABOR_COST", "EXPENSE_COST", "SGA_EXPENSE")), ZERO)
                for m in reference_months
            ),
            ZERO,
        ) / count

    forecast = []
    projected = base_cash
    for offset in range(1, horizon + 1):
        row_year, row_month = _forecast_month(year, month, offset)
        row = {
            "year": row_year, "month": row_month, "inflow": None, "outflow": None,
            "net_cash_flow": None, "projected_cash": None, "shortfall": None,
        }
        if reference_months:
            net = avg_inflow - avg_outflow
            projected = projected + net if projected is not None else None
            row.update(
                inflow=avg_inflow, outflow=avg_outflow, net_cash_flow=net, projected_cash=projected,
                shortfall=projected < 0 if projected is not None else None,
            )
        forecast.append(row)

    return {
        "horizon": horizon,
        "base_month": month,
        "base_cash": base_cash,
        "base_cash_as_of_month": base_cash_as_of,
        "reference_months": reference_months,
        "avg_inflow": avg_inflow,
        "avg_outflow": avg_outflow,
        "history": [
            {"month": m, "cash_balance": facts_by_month[m].sums.get("CASH_BALANCE")} for m in range(1, month + 1)
        ],
        "forecast": forecast,
    }


# ---- 목표 대비 달성률 [05 §3.9] ----

def goal_rows(goal_metrics, targets, cumulative):
    """goal_metrics: [(key, label, unit)], targets: {key: Decimal}, cumulative: 누적 섹션 블록."""
    rows = []
    for key, label, unit in goal_metrics:
        section, name = GOAL_ACTUALS[key]
        actual = cumulative[section][name]
        target = targets.get(key)
        rate = ratio(actual, target) if target is not None and target > 0 else None
        rows.append(
            {
                "metric_key": key, "label": label, "unit": unit,
                "target": target, "actual": actual, "achievement_rate": rate,
            }
        )
    return rows

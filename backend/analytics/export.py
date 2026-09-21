"""대시보드·월별 리포트 CSV 생성 [05 §4, A-43, A-51].

응답(`dashboard.build_*`의 결과)을 세로형 `섹션,항목,구분,단위,값` 행으로 펼친다. DB에 접근하지 않는다.
값은 화면과 같은 규칙으로 반올림한다(API 자체는 반올림하지 않는다).
"""

import csv
import io
from decimal import ROUND_HALF_UP, Decimal, localcontext

from .metrics import TREND_FIELDS

HEADER = ["섹션", "항목", "구분", "단위", "값"]

# 표시 형식: int = 정수, one = 소수 1자리 (화면의 원·개·명 / % · 인당 생산량과 같다)
INT, ONE = "int", "one"

# 섹션별 항목 (한글 라벨, 응답 필드, 단위, 형식) [05 §4.1]
COST_PROFIT = [
    ("매출액", "revenue", "원", INT), ("재료비", "material_cost", "원", INT), ("노무비", "labor_cost", "원", INT),
    ("경비", "expense_cost", "원", INT), ("총원가", "total_cost", "원", INT), ("매출총이익", "gross_profit", "원", INT),
    ("판매관리비", "sga_expense", "원", INT), ("영업이익", "operating_profit", "원", INT),
    ("매출총이익률", "gross_margin", "%", ONE), ("영업이익률", "operating_margin", "%", ONE),
]
PROJECT = [
    ("매출액", "revenue", "원", INT), ("재료비", "material_cost", "원", INT), ("노무비", "labor_cost", "원", INT),
    ("경비", "expense_cost", "원", INT), ("총원가", "total_cost", "원", INT), ("매출총이익", "gross_profit", "원", INT),
    ("매출총이익률", "gross_margin", "%", ONE),
]
TRADE = [
    ("매출액", "revenue", "원", INT), ("매입액", "purchase_amount", "원", INT), ("수금액", "collection_amount", "원", INT),
    ("미수금 잔액", "receivable_balance", "원", INT), ("미수금 비율", "receivable_ratio", "%", ONE),
]
BEP = [
    ("변동비", "variable_cost", "원", INT), ("고정비", "fixed_cost", "원", INT),
    ("공헌이익률", "contribution_margin_ratio", "%", ONE), ("BEP 매출액", "bep_revenue", "원", INT),
    ("BEP 달성률", "bep_achievement_rate", "%", ONE),
]
PRODUCTION = [
    ("생산량", "production_qty", "개", INT), ("생산 능력", "production_capacity", "개", INT), ("가동률", "utilization_rate", "%", ONE),
]
ORDERS = [
    ("신규 수주액", "order_received", "원", INT), ("수주 잔고", "order_backlog", "원", INT),
    ("파이프라인 금액", "pipeline_amount", "원", INT), ("예상 수주 확률", "pipeline_win_rate", "%", ONE),
    ("가중 파이프라인", "weighted_pipeline", "원", INT),
]
PRODUCTIVITY = [
    ("인원수", "headcount", "명", INT), ("인당 매출액", "revenue_per_head", "원", INT),
    ("인당 영업이익", "operating_profit_per_head", "원", INT), ("인당 생산량", "production_per_head", "개/명", ONE),
]

# 섹션 순서 (응답 키, 섹션 한글명, 항목 목록) — `데이터 상태`·`프로젝트별`·`자금 수지 예측`·`목표 달성률`은 따로 만든다
BLOCK_SECTIONS = {
    "cost_profit": ("종합 원가/이익률", COST_PROFIT),
    "trade": ("매입·매출·미수금", TRADE),
    "bep": ("BEP", BEP),
    "production": ("생산·가동률", PRODUCTION),
    "orders": ("수주·파이프라인", ORDERS),
    "productivity": ("인당 생산성", PRODUCTIVITY),
}
SECTION_ORDER = [
    "data_status", "cost_profit", "projects", "trade", "cash_forecast", "bep", "production", "orders",
    "productivity", "goals",
]

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


# ---- 셀 형식 ----

def format_number(value, kind):
    """숫자 셀. 화면과 같은 규칙: 절반 올림(0에서 먼 쪽), 콤마·지수 없음, None은 빈 칸."""
    if value is None:
        return ""
    places = Decimal(1) if kind == INT else Decimal("0.1")
    with localcontext() as context:
        context.prec = 60
        rounded = Decimal(value).quantize(places, rounding=ROUND_HALF_UP)
    if rounded == 0:
        return "0" if kind == INT else "0.0"  # -0 방지
    return format(rounded, "f")


def safe_text(text):
    """텍스트 셀이 엑셀 수식으로 실행되지 않도록 `=`, `+`, `-`, `@`, 탭, CR로 시작하면 `'`를 붙인다 [A-51]."""
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


class _Rows:
    """행 목록. 텍스트 셀은 `safe_text`를 거치고 숫자 셀은 `format_number`를 거친다."""

    def __init__(self):
        self.rows = []

    def number(self, section, item, category, unit, value, kind):
        self.rows.append([safe_text(section), safe_text(item), safe_text(category), safe_text(unit), format_number(value, kind)])

    def text(self, section, item, category, unit, text):
        self.rows.append([safe_text(section), safe_text(item), safe_text(category), safe_text(unit), safe_text(text)])


def _period_label(period, block, field, base_month):
    """`누적` / `당월`. stock 값이 이전 월에서 이월되었으면 `(n월 기준)`을 붙인다 [05 §4.2]."""
    as_of = block.get(f"{field}_as_of_month")
    if block.get(field) is not None and as_of is not None and as_of != base_month:
        return f"{period}({as_of}월 기준)"
    return period


def _month_label(year, month):
    return f"{year}-{month:02d}"


# ---- 섹션별 행 ----

def _data_status(rows, data):
    status = data["data_status"]
    label = _month_label(data["year"], data["month"])
    rows.text("데이터 상태", "제출 부서", label, "", ", ".join(status["submitted_departments"]))
    rows.text("데이터 상태", "미제출 부서", label, "", ", ".join(status["missing_departments"]))


def _block_section(rows, data, key, periods):
    """지표 블록 섹션. periods: 대시보드는 ['cumulative'], 리포트는 ['month', 'cumulative']."""
    section, fields = BLOCK_SECTIONS[key]
    names = {"month": "당월", "cumulative": "누적"}
    for label, field, unit, kind in fields:
        for period in periods:
            block = data[key][period]
            rows.number(section, label, _period_label(names[period], block, field, data["month"]), unit, block[field], kind)
    # 대시보드: 누적 행 뒤에 trend 행 (월 오름차순, 한 달 안에서는 trend 항목 순서)
    if "trend" in data[key]:
        by_field = {field: (label, unit, kind) for label, field, unit, kind in fields}
        for point in data[key]["trend"]:
            for field in TREND_FIELDS[key]:
                label, unit, kind = by_field[field]
                rows.number(section, label, _month_label(data["year"], point["month"]), unit, point[field], kind)


def _projects(rows, data):
    section = data["projects"]
    if "month" in section:  # 리포트: 당월 프로젝트 행 전부, 다음에 누적 프로젝트 행 전부
        groups = [("month", " (당월)"), ("cumulative", " (누적)")]
    else:  # 대시보드
        groups = [("cumulative", "")]
    for period, suffix in groups:
        for project in section[period]:
            for label, field, unit, kind in PROJECT:
                rows.number("프로젝트별", label, f"{project['project_name']}{suffix}", unit, project[field], kind)


def _cash_forecast(rows, data):
    cash = data["cash_forecast"]
    name = "자금 수지 예측"
    base_label = "기준 월"
    if cash["base_cash"] is not None and cash["base_cash_as_of_month"] != cash["base_month"]:
        base_label = f"기준 월({cash['base_cash_as_of_month']}월 기준)"
    rows.number(name, "기준 현금 잔액", base_label, "원", cash["base_cash"], INT)
    rows.number(name, "참조 개월 수", "참조 기간", "개월", len(cash["reference_months"]), INT)
    rows.number(name, "월평균 유입", "참조 기간 평균", "원", cash["avg_inflow"], INT)
    rows.number(name, "월평균 유출", "참조 기간 평균", "원", cash["avg_outflow"], INT)
    for point in cash["history"]:
        rows.number(name, "현금 잔액(실적)", _month_label(data["year"], point["month"]), "원", point["cash_balance"], INT)
    for row in cash["forecast"]:
        label = _month_label(row["year"], row["month"])
        for item, field in (("예상 유입", "inflow"), ("예상 유출", "outflow"), ("순현금흐름", "net_cash_flow"), ("예상 잔액", "projected_cash")):
            rows.number(name, item, label, "원", row[field], INT)


def _goals(rows, data):
    for goal in data["goals"]:
        kind = ONE if goal["unit"] == "%" else INT
        rows.number("목표 달성률", goal["label"], "목표", goal["unit"], goal["target"], kind)
        rows.number("목표 달성률", goal["label"], "실적(누적)", goal["unit"], goal["actual"], kind)
        rows.number("목표 달성률", goal["label"], "달성률", "%", goal["achievement_rate"], ONE)


def build_rows(data, periods):
    rows = _Rows()
    for key in SECTION_ORDER:
        if key == "data_status":
            _data_status(rows, data)
        elif key == "projects":
            _projects(rows, data)
        elif key == "cash_forecast":
            _cash_forecast(rows, data)
        elif key == "goals":
            _goals(rows, data)
        else:
            _block_section(rows, data, key, periods)
    return rows.rows


def dashboard_rows(data):
    """누적 대시보드 응답 → CSV 행 (누적 행 + trend 행)."""
    return build_rows(data, ["cumulative"])


def monthly_report_rows(data):
    """월별 리포트 응답 → CSV 행 (지표마다 당월·누적 행)."""
    return build_rows(data, ["month", "cumulative"])


def render_csv(rows):
    """UTF-8 BOM, 쉼표, CRLF, RFC 4180 따옴표 처리 [A-51]."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def dashboard_csv(data):
    return render_csv(dashboard_rows(data))


def monthly_report_csv(data):
    return render_csv(monthly_report_rows(data))

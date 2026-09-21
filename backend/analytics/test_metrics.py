from decimal import Decimal

from django.test import SimpleTestCase

from goals.keys import GOAL_METRICS

from .metrics import (
    POINT_KEYS, SECTION_FIELDS, TREND_FIELDS, MonthFacts, cash_forecast, compute_period, compute_sections,
    compute_trend, goal_rows, null_sections, project_rows, ratio,
)


def facts(month, has_report=True, projects=None, **sums):
    """MonthFacts 생성 도우미. 값은 숫자, 개수는 1로 둔다."""
    return MonthFacts(
        month=month,
        has_report=has_report,
        sums={key: Decimal(str(value)) for key, value in sums.items()},
        counts={key: 1 for key in sums},
        projects={
            name: {key: Decimal(str(value)) for key, value in values.items()} for name, values in (projects or {}).items()
        },
    )


def by_month(last_month, *given):
    """1~last_month 모든 달의 MonthFacts. 주지 않은 달은 빈 값."""
    result = {m: MonthFacts(month=m) for m in range(1, last_month + 1)}
    result.update({f.month: f for f in given})
    return result


class SpecExampleTests(SimpleTestCase):
    """05 §5 검증용 예제: 1월 단독, 제출 완료 데이터."""

    def setUp(self):
        data = by_month(1, facts(
            1, REVENUE=1000, MATERIAL_COST=400, LABOR_COST=200, EXPENSE_COST=50, SGA_EXPENSE=150,
            PRODUCTION_QTY=80, PRODUCTION_CAPACITY=100, HEADCOUNT=10,
            projects={"A": {"REVENUE": 1000, "MATERIAL_COST": 400, "LABOR_COST": 200, "EXPENSE_COST": 50}},
        ))
        self.sections = compute_period(data, [1], 1)
        self.data = data

    def test_cost_profit(self):
        cp = self.sections["cost_profit"]
        self.assertEqual((cp["total_cost"], cp["gross_profit"], cp["operating_profit"]), (650, 350, 200))
        self.assertEqual((cp["gross_margin"], cp["operating_margin"]), (Decimal("35"), Decimal("20")))

    def test_utilization(self):
        self.assertEqual(self.sections["production"]["utilization_rate"], Decimal("80"))

    def test_project(self):
        (row,) = project_rows(self.data, [1])
        self.assertEqual((row["project_name"], row["gross_profit"], row["gross_margin"]), ("A", 350, Decimal("35")))

    def test_bep(self):
        bep = self.sections["bep"]
        self.assertEqual((bep["variable_cost"], bep["fixed_cost"], bep["contribution_margin_ratio"]), (400, 400, Decimal("60")))
        self.assertAlmostEqual(float(bep["bep_revenue"]), 666.67, places=2)
        self.assertAlmostEqual(float(bep["bep_achievement_rate"]), 150.0, places=6)

    def test_productivity(self):
        pr = self.sections["productivity"]
        self.assertEqual((pr["revenue_per_head"], pr["operating_profit_per_head"], pr["production_per_head"]), (100, 20, 8))


class StructureTests(SimpleTestCase):
    def test_sections_have_exactly_the_documented_fields_in_order(self):
        data = by_month(1, facts(1))
        sections = compute_period(data, [1], 1)
        self.assertEqual({s: list(v) for s, v in sections.items()}, SECTION_FIELDS)
        self.assertEqual({s: list(v) for s, v in null_sections().items()}, SECTION_FIELDS)

    def test_trend_fields_exist_in_sections(self):
        for section, names in TREND_FIELDS.items():
            self.assertTrue(set(names) <= set(SECTION_FIELDS[section]), section)

    def test_no_report_means_all_null(self):
        data = by_month(3, facts(2, has_report=False, REVENUE=999))  # 값이 있어도 보고서가 없으면 없는 것
        sections = compute_period(data, [1, 2, 3], 3)
        for block in sections.values():
            self.assertEqual(set(block.values()), {None})

    def test_missing_flow_keys_are_zero_when_a_report_exists(self):
        sections = compute_period(by_month(1, facts(1)), [1], 1)
        cp = sections["cost_profit"]
        self.assertEqual((cp["revenue"], cp["total_cost"], cp["operating_profit"]), (0, 0, 0))
        self.assertEqual((cp["gross_margin"], cp["operating_margin"]), (None, None))
        self.assertEqual(sections["trade"]["purchase_amount"], 0)
        self.assertIsNone(sections["trade"]["receivable_balance"])


class RatioTests(SimpleTestCase):
    def test_ratio(self):
        self.assertEqual(ratio(Decimal(1), Decimal(4)), Decimal(25))
        self.assertEqual(ratio(Decimal(6), Decimal(3), 1), Decimal(2))
        for args in ((None, Decimal(1)), (Decimal(1), None), (Decimal(1), Decimal(0)), (Decimal(0), Decimal(0))):
            self.assertIsNone(ratio(*args))
        self.assertEqual(ratio(Decimal(0), Decimal(5)), Decimal(0))  # 분자 0은 유효

    def test_no_intermediate_rounding(self):
        value = ratio(Decimal(1), Decimal(3))
        self.assertNotEqual(value, Decimal("33.3"))
        self.assertAlmostEqual(float(value), 33.3333333, places=5)


class BepEdgeTests(SimpleTestCase):
    def bep(self, **sums):
        return compute_period(by_month(1, facts(1, **sums)), [1], 1)["bep"]

    def test_zero_revenue(self):
        bep = self.bep(LABOR_COST=100)
        self.assertEqual((bep["contribution_margin_ratio"], bep["bep_revenue"], bep["bep_achievement_rate"]), (None, None, None))
        self.assertEqual(bep["fixed_cost"], 100)

    def test_non_positive_contribution_margin(self):
        for material in (1000, 1500):  # 공헌이익률 0, 음수
            bep = self.bep(REVENUE=1000, MATERIAL_COST=material, LABOR_COST=100)
            self.assertIsNone(bep["bep_revenue"])
            self.assertIsNone(bep["bep_achievement_rate"])
        self.assertEqual(self.bep(REVENUE=1000, MATERIAL_COST=1500)["contribution_margin_ratio"], Decimal(-50))

    def test_zero_fixed_cost(self):
        bep = self.bep(REVENUE=1000, MATERIAL_COST=400)
        self.assertEqual(bep["bep_revenue"], 0)
        self.assertIsNone(bep["bep_achievement_rate"])  # 0으로 나눌 수 없음

    def test_below_break_even(self):
        bep = self.bep(REVENUE=300, MATERIAL_COST=0, LABOR_COST=600)
        self.assertEqual(bep["bep_revenue"], 600)
        self.assertEqual(bep["bep_achievement_rate"], Decimal(50))


class StockCarryForwardTests(SimpleTestCase):
    def test_uses_base_month_value_when_present(self):
        data = by_month(3, facts(2, RECEIVABLE_BALANCE=100), facts(3, RECEIVABLE_BALANCE=300))
        trade = compute_period(data, [1, 2, 3], 3)["trade"]
        self.assertEqual((trade["receivable_balance"], trade["receivable_balance_as_of_month"]), (300, 3))

    def test_carries_forward_the_latest_earlier_month(self):
        data = by_month(4, facts(2, RECEIVABLE_BALANCE=100), facts(3, RECEIVABLE_BALANCE=200), facts(4))
        trade = compute_period(data, [1, 2, 3, 4], 4)["trade"]
        self.assertEqual((trade["receivable_balance"], trade["receivable_balance_as_of_month"]), (200, 3))

    def test_no_value_at_all(self):
        trade = compute_period(by_month(2, facts(1), facts(2)), [1, 2], 2)["trade"]
        self.assertEqual((trade["receivable_balance"], trade["receivable_balance_as_of_month"]), (None, None))

    def test_month_block_equals_cumulative_for_stock_when_month_has_a_report(self):
        data = by_month(3, facts(2, HEADCOUNT=7), facts(3))
        month = compute_period(data, [3], 3)["productivity"]
        cumulative = compute_period(data, [1, 2, 3], 3)["productivity"]
        self.assertEqual((month["headcount"], month["headcount_as_of_month"]), (7, 2))
        self.assertEqual((cumulative["headcount"], cumulative["headcount_as_of_month"]), (7, 2))

    def test_month_block_is_all_null_when_the_month_has_no_report(self):
        data = by_month(3, facts(2, HEADCOUNT=7, REVENUE=5))
        self.assertEqual(set(compute_period(data, [3], 3)["productivity"].values()), {None})
        self.assertEqual(compute_period(data, [1, 2, 3], 3)["productivity"]["headcount"], 7)

    def test_headcount_divides_cumulative_flows_by_base_month_headcount(self):
        data = by_month(2, facts(1, REVENUE=100, HEADCOUNT=5), facts(2, REVENUE=300, HEADCOUNT=10))
        pr = compute_period(data, [1, 2], 2)["productivity"]
        self.assertEqual((pr["headcount"], pr["revenue_per_head"]), (10, 40))

    def test_zero_or_missing_headcount(self):
        pr = compute_period(by_month(1, facts(1, REVENUE=100, HEADCOUNT=0)), [1], 1)["productivity"]
        self.assertEqual((pr["headcount"], pr["revenue_per_head"]), (0, None))
        pr = compute_period(by_month(1, facts(1, REVENUE=100)), [1], 1)["productivity"]
        self.assertEqual((pr["headcount"], pr["revenue_per_head"]), (None, None))


class RateTests(SimpleTestCase):
    def test_rate_is_averaged_and_weighted_pipeline(self):
        month = MonthFacts(
            month=1, has_report=True,
            sums={"PIPELINE_WIN_RATE": Decimal(100), "PIPELINE_AMOUNT": Decimal(1000)},
            counts={"PIPELINE_WIN_RATE": 2, "PIPELINE_AMOUNT": 1},
        )
        orders = compute_period({1: month}, [1], 1)["orders"]
        self.assertEqual(orders["pipeline_win_rate"], Decimal(50))
        self.assertEqual(orders["weighted_pipeline"], Decimal(500))

    def test_weighted_pipeline_needs_both(self):
        orders = compute_period(by_month(1, facts(1, PIPELINE_AMOUNT=1000)), [1], 1)["orders"]
        self.assertIsNone(orders["weighted_pipeline"])

    def test_as_of_months_are_tracked_per_key(self):
        data = by_month(3, facts(1, ORDER_BACKLOG=10), facts(2, PIPELINE_AMOUNT=20), facts(3))
        orders = compute_period(data, [1, 2, 3], 3)["orders"]
        self.assertEqual((orders["order_backlog_as_of_month"], orders["pipeline_amount_as_of_month"]), (1, 2))
        self.assertIsNone(orders["pipeline_win_rate_as_of_month"])

    def test_flows_are_summed_over_the_period(self):
        data = by_month(3, facts(1, ORDER_RECEIVED=1), facts(2, ORDER_RECEIVED=2), facts(3, ORDER_RECEIVED=4))
        self.assertEqual(compute_period(data, [1, 2, 3], 3)["orders"]["order_received"], 7)
        self.assertEqual(compute_period(data, [3], 3)["orders"]["order_received"], 4)

    def test_cumulative_utilization_is_not_an_average_of_monthly_rates(self):
        data = by_month(2, facts(1, PRODUCTION_QTY=10, PRODUCTION_CAPACITY=10), facts(2, PRODUCTION_QTY=0, PRODUCTION_CAPACITY=90))
        production = compute_period(data, [1, 2], 2)["production"]
        self.assertEqual(production["utilization_rate"], Decimal(10))  # (10+0)/(10+90), 월별 평균이면 50


class TrendTests(SimpleTestCase):
    def test_one_point_per_month_with_documented_fields(self):
        trend = compute_trend(by_month(4, facts(2, REVENUE=1)), 4)
        self.assertEqual({s: [p["month"] for p in points] for s, points in trend.items()}, {s: [1, 2, 3, 4] for s in TREND_FIELDS})
        for section, names in TREND_FIELDS.items():
            self.assertEqual(list(trend[section][0]), ["month", *names])

    def test_months_without_reports_are_null(self):
        trend = compute_trend(by_month(3, facts(2, REVENUE=100, SGA_EXPENSE=40)), 3)["cost_profit"]
        self.assertEqual(trend[0], {"month": 1, "revenue": None, "operating_profit": None, "operating_margin": None})
        self.assertEqual((trend[1]["revenue"], trend[1]["operating_profit"], trend[1]["operating_margin"]), (100, 60, Decimal(60)))
        self.assertIsNone(trend[2]["revenue"])

    def test_stock_is_not_carried_forward_in_trend(self):
        data = by_month(3, facts(1, RECEIVABLE_BALANCE=500, REVENUE=10), facts(2, REVENUE=20), facts(3, RECEIVABLE_BALANCE=700))
        trade = compute_trend(data, 3)["trade"]
        self.assertEqual([p["receivable_balance"] for p in trade], [500, None, 700])
        self.assertEqual([p["revenue"] for p in trade], [10, 20, 0])  # 보고서가 있으면 없는 flow는 0

    def test_ratios_use_that_months_values_only(self):
        data = by_month(2, facts(1, PRODUCTION_QTY=50, PRODUCTION_CAPACITY=100), facts(2, PRODUCTION_QTY=90, PRODUCTION_CAPACITY=100))
        production = compute_trend(data, 2)["production"]
        self.assertEqual([p["utilization_rate"] for p in production], [Decimal(50), Decimal(90)])

    def test_revenue_per_head_uses_own_month_headcount(self):
        data = by_month(2, facts(1, REVENUE=100, HEADCOUNT=10), facts(2, REVENUE=100))
        self.assertEqual([p["revenue_per_head"] for p in compute_trend(data, 2)["productivity"]], [10, None])


class ProjectRowTests(SimpleTestCase):
    def test_sorted_by_revenue_desc_then_name(self):
        data = by_month(1, facts(1, projects={
            "나": {"REVENUE": 100}, "가": {"REVENUE": 100}, "다": {"REVENUE": 500}, "라": {"REVENUE": 0, "MATERIAL_COST": 50},
        }))
        self.assertEqual([r["project_name"] for r in project_rows(data, [1])], ["다", "가", "나", "라"])

    def test_sums_across_months_and_zero_revenue_margin(self):
        data = by_month(2,
            facts(1, projects={"A": {"REVENUE": 100, "MATERIAL_COST": 30}, "B": {"MATERIAL_COST": 5}}),
            facts(2, projects={"A": {"REVENUE": 100, "LABOR_COST": 20, "EXPENSE_COST": 10}}))
        rows = {r["project_name"]: r for r in project_rows(data, [1, 2])}
        self.assertEqual((rows["A"]["revenue"], rows["A"]["total_cost"], rows["A"]["gross_profit"]), (200, 60, 140))
        self.assertEqual(rows["A"]["gross_margin"], Decimal(70))
        self.assertEqual((rows["B"]["revenue"], rows["B"]["gross_profit"], rows["B"]["gross_margin"]), (0, -5, None))

    def test_empty_without_reports(self):
        self.assertEqual(project_rows(by_month(2, facts(1, has_report=False, projects={"A": {"REVENUE": 1}})), [1, 2]), [])

    def test_month_only(self):
        data = by_month(2, facts(1, projects={"A": {"REVENUE": 1}}), facts(2, projects={"B": {"REVENUE": 2}}))
        self.assertEqual([r["project_name"] for r in project_rows(data, [2])], ["B"])


def cash_data(last_month, months, cash=None, **flows):
    """months 달에 매월 같은 flow 값을 넣는다. cash: {월: 잔액}"""
    cash = cash or {}
    given = []
    for m in months:
        values = dict(flows)
        if m in cash:
            values["CASH_BALANCE"] = cash[m]
        given.append(facts(m, **values))
    return by_month(last_month, *given)


MONTHLY = dict(COLLECTION_AMOUNT=100, PURCHASE_AMOUNT=100, LABOR_COST=30, EXPENSE_COST=10, SGA_EXPENSE=10)


class CashForecastTests(SimpleTestCase):
    def test_spec_example(self):
        data = cash_data(9, [7, 8, 9], cash={9: 120}, **MONTHLY)
        result = cash_forecast(data, 2026, 9, 3)
        self.assertEqual((result["horizon"], result["base_month"]), (3, 9))
        self.assertEqual((result["base_cash"], result["base_cash_as_of_month"]), (120, 9))
        self.assertEqual(result["reference_months"], [7, 8, 9])
        self.assertEqual((result["avg_inflow"], result["avg_outflow"]), (100, 150))
        self.assertEqual([(r["year"], r["month"]) for r in result["forecast"]], [(2026, 10), (2026, 11), (2026, 12)])
        self.assertEqual([r["net_cash_flow"] for r in result["forecast"]], [-50, -50, -50])
        self.assertEqual([r["projected_cash"] for r in result["forecast"]], [70, 20, -30])
        self.assertEqual([r["shortfall"] for r in result["forecast"]], [False, False, True])
        self.assertEqual({(r["inflow"], r["outflow"]) for r in result["forecast"]}, {(100, 150)})

    def test_year_rollover(self):
        result = cash_forecast(cash_data(11, [9, 10, 11], cash={11: 500}, **MONTHLY), 2026, 11, 4)
        self.assertEqual([(r["year"], r["month"]) for r in result["forecast"]], [(2026, 12), (2027, 1), (2027, 2), (2027, 3)])
        result = cash_forecast(cash_data(12, [10, 11, 12], **MONTHLY), 2026, 12, 3)
        self.assertEqual([(r["year"], r["month"]) for r in result["forecast"]], [(2027, 1), (2027, 2), (2027, 3)])

    def test_horizon_controls_row_count(self):
        data = cash_data(9, [7, 8, 9], cash={9: 0}, **MONTHLY)
        for horizon in (3, 4, 5, 6):
            result = cash_forecast(data, 2026, 9, horizon)
            self.assertEqual((result["horizon"], len(result["forecast"])), (horizon, horizon))
        self.assertEqual([r["projected_cash"] for r in cash_forecast(data, 2026, 9, 6)["forecast"]], [-50, -100, -150, -200, -250, -300])

    def test_reference_window_is_the_last_three_months_with_reports(self):
        result = cash_forecast(cash_data(9, [5, 7, 9], **MONTHLY), 2026, 9, 3)
        self.assertEqual(result["reference_months"], [7, 9])  # 5월은 창 밖, 8월은 제출 없음
        self.assertEqual((result["avg_inflow"], result["avg_outflow"]), (100, 150))

    def test_missing_keys_count_as_zero_in_the_average(self):
        data = by_month(3, facts(2, COLLECTION_AMOUNT=90), facts(3, COLLECTION_AMOUNT=30, SGA_EXPENSE=60))
        result = cash_forecast(data, 2026, 3, 3)
        self.assertEqual(result["reference_months"], [2, 3])
        self.assertEqual((result["avg_inflow"], result["avg_outflow"]), (60, 30))

    def test_january_and_february_use_the_same_year_only(self):
        self.assertEqual(cash_forecast(cash_data(1, [1], **MONTHLY), 2026, 1, 3)["reference_months"], [1])
        self.assertEqual(cash_forecast(cash_data(2, [1, 2], **MONTHLY), 2026, 2, 3)["reference_months"], [1, 2])

    def test_no_reference_months(self):
        data = cash_data(9, [6], cash={6: 300}, **MONTHLY)
        result = cash_forecast(data, 2026, 9, 3)
        self.assertEqual(result["reference_months"], [])
        self.assertEqual((result["avg_inflow"], result["avg_outflow"]), (None, None))
        self.assertEqual((result["base_cash"], result["base_cash_as_of_month"]), (300, 6))  # 기준 잔액은 그대로 보고
        self.assertEqual(len(result["forecast"]), 3)
        for row in result["forecast"]:
            self.assertEqual({row[k] for k in ("inflow", "outflow", "net_cash_flow", "projected_cash", "shortfall")}, {None})
        self.assertEqual([(r["year"], r["month"]) for r in result["forecast"]], [(2026, 10), (2026, 11), (2026, 12)])

    def test_no_cash_balance_data(self):
        result = cash_forecast(cash_data(9, [7, 8, 9], **MONTHLY), 2026, 9, 3)
        self.assertEqual((result["base_cash"], result["base_cash_as_of_month"]), (None, None))
        for row in result["forecast"]:
            self.assertEqual((row["inflow"], row["outflow"], row["net_cash_flow"]), (100, 150, -50))
            self.assertEqual((row["projected_cash"], row["shortfall"]), (None, None))

    def test_base_cash_carries_forward(self):
        data = cash_data(9, [7, 8, 9], cash={7: 400}, **MONTHLY)
        result = cash_forecast(data, 2026, 9, 3)
        self.assertEqual((result["base_cash"], result["base_cash_as_of_month"]), (400, 7))
        self.assertEqual(result["forecast"][0]["projected_cash"], 350)

    def test_history_has_each_months_own_balance_without_carry_forward(self):
        data = cash_data(4, [1, 2, 3, 4], cash={1: 10, 3: 30}, **MONTHLY)
        result = cash_forecast(data, 2026, 4, 3)
        self.assertEqual(result["history"], [
            {"month": 1, "cash_balance": 10}, {"month": 2, "cash_balance": None},
            {"month": 3, "cash_balance": 30}, {"month": 4, "cash_balance": None},
        ])

    def test_exact_zero_is_not_a_shortfall(self):
        data = cash_data(9, [7, 8, 9], cash={9: 100}, **MONTHLY)
        rows = cash_forecast(data, 2026, 9, 3)["forecast"]
        self.assertEqual([(r["projected_cash"], r["shortfall"]) for r in rows], [(50, False), (0, False), (-50, True)])


class GoalRowTests(SimpleTestCase):
    def cumulative(self, **sums):
        return compute_period(by_month(1, facts(1, **sums)), [1], 1)

    def rows(self, targets, cumulative):
        return {r["metric_key"]: r for r in goal_rows(GOAL_METRICS, targets, cumulative)}

    def test_all_five_metrics_in_order(self):
        rows = goal_rows(GOAL_METRICS, {}, null_sections())
        self.assertEqual([r["metric_key"] for r in rows], ["REVENUE", "OPERATING_MARGIN", "UTILIZATION", "PRODUCTION_QTY", "ORDER_RECEIVED"])
        self.assertEqual([(r["label"], r["unit"]) for r in rows][:2], [("매출액", "원"), ("영업이익률", "%")])

    def test_achievement(self):
        cumulative = self.cumulative(REVENUE=800, MATERIAL_COST=400, PRODUCTION_QTY=80, PRODUCTION_CAPACITY=100, ORDER_RECEIVED=30)
        rows = self.rows({
            "REVENUE": Decimal(1200), "OPERATING_MARGIN": Decimal(10), "UTILIZATION": Decimal(85),
            "PRODUCTION_QTY": Decimal(160), "ORDER_RECEIVED": Decimal(20),
        }, cumulative)
        self.assertAlmostEqual(float(rows["REVENUE"]["achievement_rate"]), 66.6667, places=3)
        self.assertEqual((rows["REVENUE"]["target"], rows["REVENUE"]["actual"]), (1200, 800))
        self.assertEqual(rows["OPERATING_MARGIN"]["actual"], Decimal(50))
        self.assertEqual(rows["OPERATING_MARGIN"]["achievement_rate"], Decimal(500))
        self.assertAlmostEqual(float(rows["UTILIZATION"]["achievement_rate"]), 94.1176, places=3)
        self.assertEqual(rows["PRODUCTION_QTY"]["achievement_rate"], Decimal(50))
        self.assertEqual(rows["ORDER_RECEIVED"]["achievement_rate"], Decimal(150))  # 100%를 넘어도 제한하지 않는다

    def test_unset_zero_target_or_missing_actual_is_null(self):
        cumulative = self.cumulative(REVENUE=800)
        rows = self.rows({"REVENUE": Decimal(0), "PRODUCTION_QTY": Decimal(10)}, cumulative)
        self.assertEqual((rows["REVENUE"]["target"], rows["REVENUE"]["achievement_rate"]), (0, None))  # 목표 0
        self.assertEqual((rows["UTILIZATION"]["target"], rows["UTILIZATION"]["achievement_rate"]), (None, None))  # 미설정
        self.assertEqual((rows["PRODUCTION_QTY"]["actual"], rows["PRODUCTION_QTY"]["achievement_rate"]), (Decimal(0), Decimal(0)))
        self.assertIsNone(self.rows({"UTILIZATION": Decimal(85)}, cumulative)["UTILIZATION"]["achievement_rate"])  # 실적 null

    def test_no_data_gives_null_actuals(self):
        rows = self.rows({"REVENUE": Decimal(100)}, null_sections())
        self.assertEqual((rows["REVENUE"]["actual"], rows["REVENUE"]["achievement_rate"]), (None, None))

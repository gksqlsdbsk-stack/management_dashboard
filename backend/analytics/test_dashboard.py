from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from goals.models import AnnualGoal
from organization.models import Department, InputItem
from reports.models import MonthlyReport, ReportValue

from .metrics import SECTION_FIELDS, TREND_FIELDS

TODAY = timezone.localdate()
YEAR, PAST = TODAY.year, TODAY.year - 1  # 과거 연도는 모든 월을 조회할 수 있다


class DashboardTestCase(TestCase):
    def setUp(self):
        self.dept = {d.name: d for d in Department.objects.all()}  # 초기 데이터 [A-01, A-02]
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.emp = User.objects.create_user(username="P001", password="password1", name="홍길동", department=self.dept["생산"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def submit(self, dept, month, values=(), year=PAST, status="SUBMITTED"):
        """values: [(항목명, 값) 또는 (항목명, 값, 프로젝트명)]"""
        report = MonthlyReport.objects.create(
            department=self.dept[dept], year=year, month=month, status=status,
            submitted_at=timezone.now() if status == "SUBMITTED" else None,
        )
        for entry in values:
            name, value, project = (*entry, "")[:3]
            item = InputItem.objects.get(department=self.dept[dept], name=name)
            ReportValue.objects.create(report=report, item=item, project_name=project, value=value)
        return report

    def dashboard(self, month, year=PAST, extra=""):
        return self.client.get(f"/api/dashboard/?year={year}&month={month}{extra}")

    def report(self, month, year=PAST, extra=""):
        return self.client.get(f"/api/monthly-report/?year={year}&month={month}{extra}")


def spec_example(test, month=1, year=PAST):
    """05 §5 검증용 예제 입력."""
    test.submit("영업", month, [("프로젝트별 매출액", 1000, "A"), ("월말 인원수", 4)], year)
    test.submit("생산", month, [
        ("프로젝트별 재료비", 400, "A"), ("프로젝트별 노무비", 200, "A"), ("프로젝트별 경비", 50, "A"),
        ("생산량", 80), ("생산 능력(월 최대 생산량)", 100), ("월말 인원수", 6),
    ], year)
    test.submit("경영지원", month, [("당월 판매관리비", 150)], year)


class SpecExampleApiTests(DashboardTestCase):
    def test_dashboard_matches_the_spec_example(self):
        spec_example(self)
        data = self.dashboard(1).data
        self.assertEqual(data["cost_profit"]["cumulative"], {
            "revenue": 1000, "material_cost": 400, "labor_cost": 200, "expense_cost": 50, "total_cost": 650,
            "gross_profit": 350, "sga_expense": 150, "operating_profit": 200, "gross_margin": 35, "operating_margin": 20,
        })
        self.assertEqual(data["production"]["cumulative"]["utilization_rate"], 80)
        self.assertEqual(data["projects"]["cumulative"], [{
            "project_name": "A", "revenue": 1000, "material_cost": 400, "labor_cost": 200, "expense_cost": 50,
            "total_cost": 650, "gross_profit": 350, "gross_margin": 35,
        }])
        bep = data["bep"]["cumulative"]
        self.assertEqual((bep["variable_cost"], bep["fixed_cost"], bep["contribution_margin_ratio"]), (400, 400, 60))
        self.assertAlmostEqual(bep["bep_revenue"], 666.67, places=2)
        self.assertAlmostEqual(bep["bep_achievement_rate"], 150, places=6)
        pr = data["productivity"]["cumulative"]
        self.assertEqual((pr["headcount"], pr["headcount_as_of_month"], pr["revenue_per_head"]), (10, 1, 100))
        self.assertEqual((pr["operating_profit_per_head"], pr["production_per_head"]), (20, 8))

    def test_monthly_report_month_equals_cumulative_in_january(self):
        spec_example(self)
        data = self.report(1).data
        for section in ("cost_profit", "trade", "bep", "production", "orders", "productivity"):
            self.assertEqual(data[section]["month"], data[section]["cumulative"], section)
        self.assertEqual(data["projects"]["month"], data["projects"]["cumulative"])

    def test_cumulative_versus_month_over_several_months(self):
        spec_example(self, month=1)
        self.submit("영업", 2, [("프로젝트별 매출액", 500, "A"), ("프로젝트별 매출액", 200, "B"), ("월말 인원수", 5)])
        self.submit("생산", 2, [("프로젝트별 재료비", 100, "A"), ("생산량", 20), ("생산 능력(월 최대 생산량)", 100), ("월말 인원수", 6)])
        data = self.report(2).data
        self.assertEqual(data["cost_profit"]["month"]["revenue"], 700)
        self.assertEqual(data["cost_profit"]["cumulative"]["revenue"], 1700)
        self.assertEqual(data["cost_profit"]["cumulative"]["material_cost"], 500)
        self.assertEqual(data["production"]["month"]["utilization_rate"], 20)
        self.assertEqual(data["production"]["cumulative"]["utilization_rate"], 50)  # (80+20)/(100+100)
        self.assertEqual([p["project_name"] for p in data["projects"]["cumulative"]], ["A", "B"])
        self.assertEqual([p["project_name"] for p in data["projects"]["month"]], ["A", "B"])
        self.assertEqual(data["projects"]["month"][0]["revenue"], 500)
        self.assertEqual(data["projects"]["cumulative"][0]["revenue"], 1500)
        self.assertEqual(data["productivity"]["month"]["headcount"], 11)
        self.assertEqual(data["productivity"]["cumulative"]["revenue_per_head"], 1700 / 11)


class ShapeTests(DashboardTestCase):
    def test_dashboard_shape(self):
        spec_example(self)
        data = self.dashboard(1).data
        self.assertEqual(list(data), [
            "year", "month", "period", "data_status", "cost_profit", "projects", "trade", "cash_forecast",
            "bep", "production", "orders", "productivity", "goals",
        ])
        self.assertEqual((data["year"], data["month"], data["period"]), (PAST, 1, {"from_month": 1, "to_month": 1}))
        for section in ("cost_profit", "trade", "production", "orders", "productivity"):
            self.assertEqual(set(data[section]), {"cumulative", "trend"}, section)
            self.assertEqual(list(data[section]["cumulative"]), SECTION_FIELDS[section], section)
            self.assertEqual(list(data[section]["trend"][0]), ["month", *TREND_FIELDS[section]], section)
        self.assertEqual(set(data["bep"]), {"cumulative"})
        self.assertEqual(list(data["bep"]["cumulative"]), SECTION_FIELDS["bep"])
        self.assertEqual(set(data["projects"]), {"cumulative"})

    def test_monthly_report_shape(self):
        spec_example(self)
        data = self.report(1).data
        self.assertEqual(list(data), list(self.dashboard(1).data))
        for section in ("cost_profit", "trade", "bep", "production", "orders", "productivity"):
            self.assertEqual(set(data[section]), {"month", "cumulative"}, section)
            self.assertEqual(list(data[section]["month"]), SECTION_FIELDS[section], section)
        self.assertEqual(set(data["projects"]), {"month", "cumulative"})

    def test_trend_has_one_point_per_month_up_to_the_base_month(self):
        spec_example(self, month=3)
        data = self.dashboard(5).data
        for section in TREND_FIELDS:
            self.assertEqual([p["month"] for p in data[section]["trend"]], [1, 2, 3, 4, 5], section)
        self.assertEqual(data["period"], {"from_month": 1, "to_month": 5})

    def test_values_are_unrounded_json_numbers(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 3, "A")])
        self.submit("생산", 1, [("프로젝트별 재료비", 2, "A")])
        margin = self.dashboard(1).data["cost_profit"]["cumulative"]["gross_margin"]
        self.assertIsInstance(margin, float)
        self.assertAlmostEqual(margin, 100 / 3, places=8)
        self.assertNotEqual(margin, 33.3)
        self.assertIsInstance(self.dashboard(1).data["cost_profit"]["cumulative"]["revenue"], int)


class StockAndNoDataTests(DashboardTestCase):
    """05 §5.2: 8월 영업 제출, 9월은 생산만 제출."""

    def setUp(self):
        super().setUp()
        self.submit("영업", 8, [("프로젝트별 매출액", 1000, "A"), ("미수금 잔액(월말)", 500)])
        self.submit("생산", 9, [("생산량", 10)])

    def test_cumulative_carries_forward_the_receivable_balance(self):
        trade = self.dashboard(9).data["trade"]["cumulative"]
        self.assertEqual((trade["revenue"], trade["receivable_balance"], trade["receivable_balance_as_of_month"]), (1000, 500, 8))
        self.assertEqual(trade["receivable_ratio"], 50)

    def test_monthly_report_month_block(self):
        data = self.report(9).data["trade"]
        month = data["month"]
        self.assertEqual((month["revenue"], month["purchase_amount"], month["collection_amount"]), (0, 0, 0))
        self.assertEqual((month["receivable_balance"], month["receivable_balance_as_of_month"]), (500, 8))
        self.assertIsNone(month["receivable_ratio"])  # 분모 0
        self.assertEqual(data["cumulative"]["revenue"], 1000)

    def test_trend_does_not_carry_forward_and_marks_empty_months(self):
        trend = self.dashboard(9).data["trade"]["trend"]
        self.assertEqual(len(trend), 9)
        for point in trend[:7]:  # 1~7월은 제출 없음
            self.assertEqual({k: v for k, v in point.items() if k != "month"}, {"revenue": None, "purchase_amount": None, "receivable_balance": None})
        self.assertEqual(trend[7], {"month": 8, "revenue": 1000, "purchase_amount": 0, "receivable_balance": 500})
        self.assertEqual(trend[8], {"month": 9, "revenue": 0, "purchase_amount": 0, "receivable_balance": None})

    def test_data_status_uses_the_base_month(self):
        status = self.dashboard(9).data["data_status"]
        self.assertEqual(status["submitted_departments"], ["생산"])
        self.assertEqual(status["missing_departments"], ["영업", "구매/자재", "경영지원"])
        self.assertTrue(status["has_warning"])
        earlier = self.dashboard(8).data["data_status"]
        self.assertEqual((earlier["submitted_departments"], earlier["has_warning"]), (["영업"], True))

    def test_month_without_any_report_is_all_null(self):
        data = self.report(6).data
        for section in ("cost_profit", "trade", "bep", "production", "orders", "productivity"):
            self.assertEqual(set(data[section]["month"].values()), {None}, section)
            self.assertEqual(set(data[section]["cumulative"].values()), {None}, section)  # 1~6월 전체가 비어 있다
        self.assertEqual(data["projects"], {"month": [], "cumulative": []})

    def test_dashboard_without_any_report_is_all_null_but_complete(self):
        data = self.dashboard(6).data
        self.assertEqual(set(data["cost_profit"]["cumulative"].values()), {None})
        self.assertEqual(data["projects"], {"cumulative": []})
        self.assertEqual(len(data["cost_profit"]["trend"]), 6)
        self.assertEqual(set(data["cost_profit"]["trend"][0].values()) - {1}, {None})
        self.assertEqual([g["actual"] for g in data["goals"]], [None] * 5)
        self.assertEqual(len(data["cash_forecast"]["forecast"]), 3)
        self.assertEqual(data["cash_forecast"]["reference_months"], [])


class CashForecastApiTests(DashboardTestCase):
    def fill(self, months, cash):
        for month in months:
            self.submit("영업", month, [("당월 수금액", 100)])
            self.submit("구매/자재", month, [("당월 매입액", 100)])
            self.submit("생산", month, [("프로젝트별 노무비", 30, "A"), ("프로젝트별 경비", 10, "A")])
            values = [("당월 판매관리비", 10)]
            if month in cash:
                values.append(("월말 현금 잔액", cash[month]))
            self.submit("경영지원", month, values)

    def test_spec_example(self):
        self.fill([7, 8, 9], {7: 200, 8: 150, 9: 120})
        forecast = self.dashboard(9).data["cash_forecast"]
        self.assertEqual((forecast["horizon"], forecast["base_month"], forecast["base_cash"], forecast["base_cash_as_of_month"]), (3, 9, 120, 9))
        self.assertEqual((forecast["reference_months"], forecast["avg_inflow"], forecast["avg_outflow"]), ([7, 8, 9], 100, 150))
        self.assertEqual(
            [(r["year"], r["month"], r["net_cash_flow"], r["projected_cash"], r["shortfall"]) for r in forecast["forecast"]],
            [(PAST, 10, -50, 70, False), (PAST, 11, -50, 20, False), (PAST, 12, -50, -30, True)],
        )
        self.assertEqual([h["cash_balance"] for h in forecast["history"]], [None] * 6 + [200, 150, 120])
        self.assertEqual([h["month"] for h in forecast["history"]], list(range(1, 10)))

    def test_same_in_dashboard_and_monthly_report(self):
        self.fill([7, 8, 9], {9: 120})
        self.assertEqual(self.dashboard(9).data["cash_forecast"], self.report(9).data["cash_forecast"])

    def test_year_rollover(self):
        self.fill([9, 10, 11], {11: 500})
        rows = self.dashboard(11, extra="&horizon=4").data["cash_forecast"]["forecast"]
        self.assertEqual([(r["year"], r["month"]) for r in rows], [(PAST, 12), (PAST + 1, 1), (PAST + 1, 2), (PAST + 1, 3)])

    def test_january_uses_only_january(self):
        self.fill([1], {1: 100})
        forecast = self.dashboard(1).data["cash_forecast"]
        self.assertEqual(forecast["reference_months"], [1])

    def test_no_reference_months_keeps_base_cash(self):
        self.fill([6], {6: 300})
        forecast = self.dashboard(9).data["cash_forecast"]
        self.assertEqual((forecast["reference_months"], forecast["avg_inflow"], forecast["avg_outflow"]), ([], None, None))
        self.assertEqual((forecast["base_cash"], forecast["base_cash_as_of_month"]), (300, 6))
        self.assertEqual({r["projected_cash"] for r in forecast["forecast"]}, {None})

    def test_no_cash_balance_gives_null_projection_only(self):
        self.fill([7, 8, 9], {})
        forecast = self.dashboard(9).data["cash_forecast"]
        self.assertIsNone(forecast["base_cash"])
        self.assertEqual((forecast["forecast"][0]["net_cash_flow"], forecast["forecast"][0]["projected_cash"]), (-50, None))

    def test_horizon_default_and_range(self):
        self.fill([7, 8, 9], {9: 0})
        self.assertEqual(len(self.dashboard(9).data["cash_forecast"]["forecast"]), 3)
        for horizon in (3, 4, 5, 6):
            forecast = self.dashboard(9, extra=f"&horizon={horizon}").data["cash_forecast"]
            self.assertEqual((forecast["horizon"], len(forecast["forecast"])), (horizon, horizon))


class GoalApiTests(DashboardTestCase):
    def test_achievement_uses_cumulative_actuals(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 300, "A")])
        self.submit("영업", 2, [("프로젝트별 매출액", 500, "A")])
        self.submit("생산", 2, [("프로젝트별 재료비", 400, "A"), ("생산량", 80), ("생산 능력(월 최대 생산량)", 100)])
        for key, value in {"REVENUE": 1200, "OPERATING_MARGIN": 10, "UTILIZATION": 85, "PRODUCTION_QTY": 0}.items():
            AnnualGoal.objects.create(year=PAST, metric_key=key, target_value=value)
        AnnualGoal.objects.create(year=PAST - 1, metric_key="ORDER_RECEIVED", target_value=5)  # 다른 해 목표는 무관
        goals = {g["metric_key"]: g for g in self.report(2).data["goals"]}
        self.assertEqual(list(goals), ["REVENUE", "OPERATING_MARGIN", "UTILIZATION", "PRODUCTION_QTY", "ORDER_RECEIVED"])
        self.assertEqual(goals["REVENUE"], {
            "metric_key": "REVENUE", "label": "매출액", "unit": "원", "target": 1200, "actual": 800,
            "achievement_rate": goals["REVENUE"]["achievement_rate"],
        })
        self.assertAlmostEqual(goals["REVENUE"]["achievement_rate"], 66.6667, places=3)
        self.assertEqual((goals["OPERATING_MARGIN"]["actual"], goals["OPERATING_MARGIN"]["achievement_rate"]), (50, 500))
        self.assertAlmostEqual(goals["UTILIZATION"]["achievement_rate"], 94.1176, places=3)
        self.assertEqual((goals["PRODUCTION_QTY"]["target"], goals["PRODUCTION_QTY"]["achievement_rate"]), (0, None))
        self.assertEqual((goals["ORDER_RECEIVED"]["target"], goals["ORDER_RECEIVED"]["achievement_rate"]), (None, None))
        self.assertEqual(goals["ORDER_RECEIVED"]["actual"], 0)
        self.assertEqual(self.dashboard(2).data["goals"], self.report(2).data["goals"])

    def test_report_goals_stay_cumulative_even_for_a_single_month(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 300, "A")])
        self.submit("영업", 2, [("프로젝트별 매출액", 500, "A")])
        AnnualGoal.objects.create(year=PAST, metric_key="REVENUE", target_value=1000)
        goal = self.report(2).data["goals"][0]
        self.assertEqual((goal["actual"], goal["achievement_rate"]), (800, 80))
        self.assertEqual(self.report(2).data["cost_profit"]["month"]["revenue"], 500)


class DataRuleTests(DashboardTestCase):
    def test_draft_reports_are_excluded(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A")], status="DRAFT")
        data = self.dashboard(1).data
        self.assertEqual(set(data["cost_profit"]["cumulative"].values()), {None})
        self.assertEqual(data["projects"]["cumulative"], [])
        self.assertEqual(data["data_status"]["submitted_departments"], [])
        self.submit("영업", 2, [("프로젝트별 매출액", 200, "A")])
        self.assertEqual(self.dashboard(2).data["cost_profit"]["cumulative"]["revenue"], 200)

    def test_reopened_report_leaves_the_totals(self):
        report = self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A")])
        self.assertEqual(self.dashboard(1).data["cost_profit"]["cumulative"]["revenue"], 1000)
        report.status = "DRAFT"
        report.save()
        self.assertIsNone(self.dashboard(1).data["cost_profit"]["cumulative"]["revenue"])

    def test_values_of_inactive_items_are_included(self):  # A-06
        self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A")])
        InputItem.objects.filter(name="프로젝트별 매출액").update(is_active=False)
        data = self.dashboard(1).data
        self.assertEqual(data["cost_profit"]["cumulative"]["revenue"], 1000)
        self.assertEqual(data["projects"]["cumulative"][0]["project_name"], "A")

    def test_deleted_departments_past_data_is_included_but_not_in_data_status(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A")])
        Department.objects.filter(name="영업").update(is_active=False)
        data = self.dashboard(1).data
        self.assertEqual(data["cost_profit"]["cumulative"]["revenue"], 1000)
        self.assertEqual(data["data_status"]["submitted_departments"], [])
        self.assertNotIn("영업", data["data_status"]["missing_departments"])

    def test_items_without_a_metric_key_are_ignored(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A"), ("당월 수금액", 700)])
        InputItem.objects.filter(name="당월 수금액").update(metric_key=None)
        self.assertEqual(self.dashboard(1).data["trade"]["cumulative"]["collection_amount"], 0)
        self.assertEqual(self.dashboard(1).data["trade"]["cumulative"]["revenue"], 1000)

    def test_monthly_scope_values_count_in_totals_but_not_in_project_rows(self):
        InputItem.objects.create(department=self.dept["영업"], name="공통 매출", scope="MONTHLY", metric_key="REVENUE")
        self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A"), ("공통 매출", 300)])
        data = self.dashboard(1).data
        self.assertEqual(data["cost_profit"]["cumulative"]["revenue"], 1300)
        self.assertEqual([(p["project_name"], p["revenue"]) for p in data["projects"]["cumulative"]], [("A", 1000)])

    def test_project_names_are_merged_across_departments(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 1000, "A프로젝트")])
        self.submit("생산", 1, [("프로젝트별 재료비", 300, "A프로젝트"), ("프로젝트별 노무비", 100, "A프로젝트"), ("프로젝트별 경비", 50, "공통")])
        rows = {p["project_name"]: p for p in self.dashboard(1).data["projects"]["cumulative"]}
        self.assertEqual((rows["A프로젝트"]["revenue"], rows["A프로젝트"]["total_cost"], rows["A프로젝트"]["gross_profit"]), (1000, 400, 600))
        self.assertEqual((rows["공통"]["revenue"], rows["공통"]["gross_margin"]), (0, None))
        self.assertEqual([p["project_name"] for p in self.dashboard(1).data["projects"]["cumulative"]], ["A프로젝트", "공통"])

    def test_values_of_the_same_key_are_summed_and_win_rate_is_averaged(self):
        InputItem.objects.create(department=self.dept["영업"], name="예상 확률 B", scope="MONTHLY", metric_key="PIPELINE_WIN_RATE")
        self.submit("영업", 1, [("영업 파이프라인 금액", 1000), ("파이프라인 예상 수주 확률", 40), ("예상 확률 B", 60), ("월말 인원수", 4)])
        self.submit("생산", 1, [("월말 인원수", 6)])
        self.submit("구매/자재", 1, [("월말 인원수", 2)])
        data = self.dashboard(1).data
        orders = data["orders"]["cumulative"]
        self.assertEqual((orders["pipeline_win_rate"], orders["weighted_pipeline"]), (50, 500))
        self.assertEqual(data["productivity"]["cumulative"]["headcount"], 12)

    def test_other_years_and_later_months_are_not_included(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 100, "A")])
        self.submit("영업", 5, [("프로젝트별 매출액", 900, "A")])  # 기준 월 이후
        self.submit("영업", 1, [("프로젝트별 매출액", 7000, "A")], year=PAST - 1)  # 다른 해
        self.assertEqual(self.dashboard(3).data["cost_profit"]["cumulative"]["revenue"], 100)
        self.assertEqual(self.dashboard(5).data["cost_profit"]["cumulative"]["revenue"], 1000)

    def test_orders_section_values(self):
        self.submit("영업", 1, [("당월 신규 수주액", 300), ("수주 잔고(월말)", 900), ("영업 파이프라인 금액", 2000), ("파이프라인 예상 수주 확률", 25)])
        self.submit("영업", 2, [("당월 신규 수주액", 100), ("수주 잔고(월말)", 950), ("영업 파이프라인 금액", 1000), ("파이프라인 예상 수주 확률", 50)])
        orders = self.dashboard(2).data["orders"]
        self.assertEqual(orders["cumulative"], {
            "order_received": 400, "order_backlog": 950, "order_backlog_as_of_month": 2, "pipeline_amount": 1000,
            "pipeline_amount_as_of_month": 2, "pipeline_win_rate": 50, "pipeline_win_rate_as_of_month": 2, "weighted_pipeline": 500,
        })
        self.assertEqual([p["order_backlog"] for p in orders["trend"]], [900, 950])


class ParamTests(DashboardTestCase):
    URLS = ("/api/dashboard/", "/api/monthly-report/")

    def test_year_and_month_are_required_integers(self):
        for base in self.URLS:
            for query in ("", f"?year={PAST}", "?month=1", f"?year=abc&month=1", f"?year={PAST}&month=x", f"?year=-1&month=1", f"?year={PAST}&month="):
                response = self.client.get(base + query)
                self.assertEqual(response.status_code, 400, base + query)
                self.assertEqual(response.data["code"], "validation_error")

    def test_month_range(self):
        for base in self.URLS:
            for month in (0, 13, 99):
                self.assertEqual(self.client.get(f"{base}?year={PAST}&month={month}").status_code, 400)
            self.assertEqual(self.client.get(f"{base}?year=0&month=1").status_code, 400)
            self.assertEqual(self.client.get(f"{base}?year=99999&month=1").status_code, 400)

    def test_future_month_is_rejected_but_current_month_is_allowed(self):
        next_year, next_month = (YEAR + 1, 1) if TODAY.month == 12 else (YEAR, TODAY.month + 1)
        for base in self.URLS:
            future = self.client.get(f"{base}?year={next_year}&month={next_month}")
            self.assertEqual(future.status_code, 400)
            self.assertIn("month", future.data["errors"])
            self.assertEqual(self.client.get(f"{base}?year={YEAR + 1}&month=1").status_code, 400)
            self.assertEqual(self.client.get(f"{base}?year={YEAR}&month={TODAY.month}").status_code, 200)

    def test_horizon_range(self):
        for base in self.URLS:
            for horizon in ("2", "7", "0", "abc", "-3", "", "3.5"):
                response = self.client.get(f"{base}?year={PAST}&month=1&horizon={horizon}")
                self.assertEqual(response.status_code, 400, horizon)
                self.assertEqual(response.data["code"], "validation_error")
            for horizon in ("3", "6"):
                self.assertEqual(self.client.get(f"{base}?year={PAST}&month=1&horizon={horizon}").status_code, 200)

    def test_permissions(self):
        for base in self.URLS:
            url = f"{base}?year={PAST}&month=1"
            self.assertEqual(APIClient().get(url).status_code, 401)
            self.client.force_authenticate(user=self.emp)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")
            self.client.force_authenticate(user=self.admin)

    def test_post_is_not_allowed(self):
        for base in self.URLS:
            self.assertEqual(self.client.post(f"{base}?year={PAST}&month=1").status_code, 405)


class DataStatusTests(DashboardTestCase):
    def test_all_submitted(self):
        for name in self.dept:
            self.submit(name, 1)
        status = self.dashboard(1).data["data_status"]
        self.assertEqual(status["submitted_departments"], ["영업", "생산", "구매/자재", "경영지원"])
        self.assertEqual((status["missing_departments"], status["has_warning"]), ([], False))

    def test_none_submitted(self):
        status = self.dashboard(1).data["data_status"]
        self.assertEqual(status["submitted_departments"], [])
        self.assertEqual(len(status["missing_departments"]), 4)
        self.assertTrue(status["has_warning"])

    def test_draft_counts_as_missing_and_report_has_same_status(self):
        self.submit("영업", 1)
        self.submit("생산", 1, status="DRAFT")
        status = self.report(1).data["data_status"]
        self.assertEqual(status["submitted_departments"], ["영업"])
        self.assertEqual(status["missing_departments"], ["생산", "구매/자재", "경영지원"])
        self.assertEqual(status, self.dashboard(1).data["data_status"])

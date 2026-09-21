from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from organization.models import Department

from .keys import GOAL_METRICS
from .models import AnnualGoal

KEYS = ["REVENUE", "OPERATING_MARGIN", "UTILIZATION", "PRODUCTION_QTY", "ORDER_RECEIVED"]


class GoalTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.emp = User.objects.create_user(
            username="P001", password="password1", name="홍길동", department=Department.objects.get(name="생산")
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def get(self, year=2026):
        return self.client.get(f"/api/goals/?year={year}")

    def put(self, goals, year=2026):
        return self.client.put(f"/api/goals/{year}/", {"goals": goals}, format="json")

    def targets(self, year=2026):
        return {g["metric_key"]: g["target_value"] for g in self.get(year).data["goals"]}


class GoalReadTests(GoalTestCase):
    def test_returns_five_metrics_in_fixed_order_with_null(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual([g["metric_key"] for g in response.data["goals"]], KEYS)
        self.assertEqual({g["target_value"] for g in response.data["goals"]}, {None})
        first = response.data["goals"][0]
        self.assertEqual(first, {"metric_key": "REVENUE", "label": "매출액", "unit": "원", "target_value": None})
        self.assertEqual([(g["label"], g["unit"]) for g in response.data["goals"]],
                         [("매출액", "원"), ("영업이익률", "%"), ("가동률", "%"), ("생산량", "개"), ("신규 수주액", "원")])
        self.assertEqual([k for k, _l, _u in GOAL_METRICS], KEYS)

    def test_year_is_required_and_validated(self):
        for url in ("/api/goals/", "/api/goals/?year=abc", "/api/goals/?year=0", "/api/goals/?year=99999", "/api/goals/?year=-1"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400, url)
            self.assertEqual(response.data["code"], "validation_error")

    def test_permissions(self):
        self.assertEqual(APIClient().get("/api/goals/?year=2026").status_code, 401)
        self.client.force_authenticate(user=self.emp)
        for response in (self.get(), self.put([])):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")


class GoalSaveTests(GoalTestCase):
    def test_save_and_read_back(self):
        response = self.put([
            {"metric_key": "REVENUE", "target_value": 1200000000},
            {"metric_key": "OPERATING_MARGIN", "target_value": 12.0},
            {"metric_key": "UTILIZATION", "target_value": "85.5"},
        ])
        self.assertEqual(response.status_code, 200)
        expected = {"REVENUE": 1200000000, "OPERATING_MARGIN": 12, "UTILIZATION": 85.5, "PRODUCTION_QTY": None, "ORDER_RECEIVED": None}
        self.assertEqual({g["metric_key"]: g["target_value"] for g in response.data["goals"]}, expected)
        self.assertEqual(self.targets(), expected)  # 응답 본문 = GET 본문
        self.assertEqual(response.data, self.get().data)

    def test_upsert_updates_existing_value(self):
        self.put([{"metric_key": "REVENUE", "target_value": 100}])
        self.put([{"metric_key": "REVENUE", "target_value": 200}])
        self.assertEqual(AnnualGoal.objects.filter(year=2026, metric_key="REVENUE").count(), 1)
        self.assertEqual(self.targets()["REVENUE"], 200)

    def test_null_deletes_goal(self):
        self.put([{"metric_key": "REVENUE", "target_value": 100}, {"metric_key": "UTILIZATION", "target_value": 80}])
        response = self.put([{"metric_key": "REVENUE", "target_value": None}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.targets()["REVENUE"], None)
        self.assertEqual(self.targets()["UTILIZATION"], 80)
        self.assertFalse(AnnualGoal.objects.filter(metric_key="REVENUE").exists())

    def test_blank_string_deletes_goal_and_deleting_missing_goal_is_ok(self):
        self.put([{"metric_key": "REVENUE", "target_value": 100}])
        self.assertEqual(self.put([{"metric_key": "REVENUE", "target_value": ""}, {"metric_key": "UTILIZATION", "target_value": None}]).status_code, 200)
        self.assertEqual(AnnualGoal.objects.count(), 0)

    def test_metrics_missing_from_body_are_unchanged(self):  # A-49
        self.put([{"metric_key": "REVENUE", "target_value": 100}, {"metric_key": "PRODUCTION_QTY", "target_value": 5}])
        self.put([{"metric_key": "UTILIZATION", "target_value": 90}])
        self.assertEqual(self.targets(), {"REVENUE": 100, "OPERATING_MARGIN": None, "UTILIZATION": 90, "PRODUCTION_QTY": 5, "ORDER_RECEIVED": None})
        self.put([])
        self.assertEqual(AnnualGoal.objects.count(), 3)

    def test_zero_is_a_valid_target(self):
        self.put([{"metric_key": "REVENUE", "target_value": 0}])
        self.assertEqual(self.targets()["REVENUE"], 0)
        self.assertTrue(AnnualGoal.objects.filter(metric_key="REVENUE").exists())

    def test_years_are_independent_and_future_year_allowed(self):
        self.put([{"metric_key": "REVENUE", "target_value": 100}], year=2026)
        self.put([{"metric_key": "REVENUE", "target_value": 300}], year=2030)
        self.assertEqual(self.targets(2026)["REVENUE"], 100)
        self.assertEqual(self.targets(2030)["REVENUE"], 300)
        self.assertEqual(self.targets(2027)["REVENUE"], None)

    def test_decimal_precision(self):
        self.put([{"metric_key": "OPERATING_MARGIN", "target_value": 12.3456}])
        self.assertEqual(self.targets()["OPERATING_MARGIN"], 12.3456)


class GoalValidationTests(GoalTestCase):
    def assert_rejected(self, goals, fragment):
        response = self.put(goals)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertTrue(any(fragment in m for m in response.data["errors"]["goals"]), response.data["errors"])
        self.assertEqual(AnnualGoal.objects.count(), 0)

    def test_unknown_metric(self):
        self.assert_rejected([{"metric_key": "NOPE", "target_value": 1}], "알 수 없는 지표")
        self.assert_rejected([{"target_value": 1}], "알 수 없는 지표")
        self.assert_rejected(["REVENUE"], "알 수 없는 지표")
        self.assert_rejected([{"metric_key": "MATERIAL_COST", "target_value": 1}], "알 수 없는 지표")  # 연동 키는 목표 지표가 아니다

    def test_duplicate_metric(self):
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": 1}, {"metric_key": "REVENUE", "target_value": 2}], "중복")

    def test_negative_and_non_numeric(self):
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": -1}], "0 이상")
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": "abc"}], "숫자가 아닙니다")
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": "1,000"}], "숫자가 아닙니다")
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": True}], "숫자가 아닙니다")

    def test_precision_and_range(self):
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": "1.23456"}], "4자리")
        self.assert_rejected([{"metric_key": "REVENUE", "target_value": "1" * 17}], "허용 범위")

    def test_body_shape(self):
        for body in ({}, {"goals": "x"}, {"goals": {"REVENUE": 1}}):
            response = self.client.put("/api/goals/2026/", body, format="json")
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(self.client.put("/api/goals/2026/", [], format="json").status_code, 400)

    def test_invalid_year(self):
        for year in (0, 99999):
            self.assertEqual(self.put([], year=year).status_code, 400)

    def test_one_bad_entry_saves_nothing(self):
        self.put([{"metric_key": "REVENUE", "target_value": 5}])
        response = self.put([{"metric_key": "UTILIZATION", "target_value": 80}, {"metric_key": "PRODUCTION_QTY", "target_value": "x"}])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.targets(), {"REVENUE": 5, "OPERATING_MARGIN": None, "UTILIZATION": None, "PRODUCTION_QTY": None, "ORDER_RECEIVED": None})

    def test_all_errors_are_reported_together(self):
        response = self.put([{"metric_key": "NOPE", "target_value": 1}, {"metric_key": "REVENUE", "target_value": -5}])
        self.assertEqual(len(response.data["errors"]["goals"]), 2)


class GoalConstraintTests(GoalTestCase):
    def test_unique_year_and_metric(self):
        AnnualGoal.objects.create(year=2026, metric_key="REVENUE", target_value=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AnnualGoal.objects.create(year=2026, metric_key="REVENUE", target_value=2)
        AnnualGoal.objects.create(year=2027, metric_key="REVENUE", target_value=2)
        AnnualGoal.objects.create(year=2026, metric_key="UTILIZATION", target_value=2)

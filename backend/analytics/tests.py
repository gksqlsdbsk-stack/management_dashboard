from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from organization.models import Department, InputItem
from reports.models import MonthlyReport, ReportValue

TODAY = timezone.localdate()
YEAR, MONTH = TODAY.year, TODAY.month
OTHER_MONTH = 1 if MONTH != 1 else 2


class StatusTestCase(TestCase):
    def setUp(self):
        self.dept = {d.name: d for d in Department.objects.filter(is_active=True)}  # 초기 데이터 [A-01]
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.kim = User.objects.create_user(username="S001", password="password1", name="김영업", department=self.dept["영업"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def make_report(self, department, status="DRAFT", month=MONTH, year=YEAR, filled=0, submitted_by=None):
        """`filled`: 앞에서부터 n개 필수 항목에 값을 채운다."""
        report = MonthlyReport.objects.create(
            department=self.dept[department], year=year, month=month, status=status,
            submitted_by=submitted_by, submitted_at=timezone.now() if status == "SUBMITTED" else None,
        )
        for item in self.dept[department].items.filter(is_active=True, is_required=True)[:filled]:
            ReportValue.objects.create(report=report, item=item, project_name="P" if item.scope == "PROJECT" else "", value=1)
        return report

    def status(self, year=YEAR, month=MONTH):
        return self.client.get(f"/api/status/?year={year}&month={month}")

    def matrix(self, year=YEAR):
        return self.client.get(f"/api/status/matrix/?year={year}")


class StatusSummaryTests(StatusTestCase):
    def test_nothing_started(self):
        response = self.status()
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual((data["year"], data["month"]), (YEAR, MONTH))
        self.assertEqual((data["total_departments"], data["submitted_count"], data["submitted_percent"]), (4, 0, 0))
        self.assertEqual([d["name"] for d in data["departments"]], ["영업", "생산", "구매/자재", "경영지원"])
        for row in data["departments"]:
            self.assertEqual(row["status"], "NOT_STARTED")
            self.assertEqual(row["progress_percent"], 0)
            self.assertIsNone(row["submitted_at"])
            self.assertIsNone(row["submitted_by_name"])
        self.assertEqual(data["unsubmitted"], ["영업", "생산", "구매/자재", "경영지원"])
        self.assertEqual(
            set(data["departments"][0]),
            {"department_id", "name", "status", "progress_percent", "submitted_at", "submitted_by_name"},
        )

    def test_mixed_statuses(self):
        self.make_report("영업", "SUBMITTED", submitted_by=self.kim)
        self.make_report("생산", "DRAFT", filled=3)  # 필수 6개 중 3개
        data = self.status().data
        rows = {r["name"]: r for r in data["departments"]}
        self.assertEqual(rows["영업"]["status"], "SUBMITTED")
        self.assertEqual(rows["영업"]["progress_percent"], 100)
        self.assertEqual(rows["영업"]["submitted_by_name"], "김영업")
        self.assertTrue(rows["영업"]["submitted_at"].endswith("+09:00"))
        self.assertEqual((rows["생산"]["status"], rows["생산"]["progress_percent"]), ("DRAFT", 50))
        self.assertIsNone(rows["생산"]["submitted_at"])
        self.assertEqual(rows["구매/자재"]["status"], "NOT_STARTED")
        self.assertEqual((data["submitted_count"], data["submitted_percent"]), (1, 25))
        self.assertEqual(data["unsubmitted"], ["생산", "구매/자재", "경영지원"])

    def test_all_submitted(self):
        for name in self.dept:
            self.make_report(name, "SUBMITTED")
        data = self.status().data
        self.assertEqual((data["submitted_count"], data["submitted_percent"]), (4, 100))
        self.assertEqual(data["unsubmitted"], [])

    def test_submitted_progress_stays_100_even_if_required_item_is_added_later(self):
        self.make_report("영업", "SUBMITTED")
        InputItem.objects.create(department=self.dept["영업"], name="새 필수 항목", scope="MONTHLY", is_required=True)
        row = next(r for r in self.status().data["departments"] if r["name"] == "영업")
        self.assertEqual(row["progress_percent"], 100)

    def test_draft_progress_uses_only_active_required_items(self):
        self.make_report("생산", "DRAFT", filled=2)  # 필수 6개 중 2개 → 33
        rows = {r["name"]: r for r in self.status().data["departments"]}
        self.assertEqual(rows["생산"]["progress_percent"], 33)
        for item in self.dept["생산"].items.filter(is_required=True)[2:]:
            item.is_required = False  # 선택 항목으로 바뀌면 분모에서 빠진다
            item.save()
        rows = {r["name"]: r for r in self.status().data["departments"]}
        self.assertEqual(rows["생산"]["progress_percent"], 100)

    def test_progress_ignores_values_of_inactive_items(self):
        self.make_report("생산", "DRAFT", filled=2)
        first = self.dept["생산"].items.filter(is_required=True).first()
        first.is_active = False
        first.save()  # 활성 필수 5개 중 1개 채움 → 20
        rows = {r["name"]: r for r in self.status().data["departments"]}
        self.assertEqual(rows["생산"]["progress_percent"], 20)

    def test_department_without_required_items_is_100_percent(self):  # A-47
        Department.objects.create(name="무필수")
        self.dept = {d.name: d for d in Department.objects.filter(is_active=True)}
        row = next(r for r in self.status().data["departments"] if r["name"] == "무필수")
        self.assertEqual((row["status"], row["progress_percent"]), ("NOT_STARTED", 100))

    def test_months_and_years_are_independent(self):
        self.make_report("영업", "SUBMITTED", month=OTHER_MONTH)
        self.make_report("생산", "SUBMITTED", year=YEAR - 1)
        self.assertEqual(self.status().data["submitted_count"], 0)
        self.assertEqual(self.status(month=OTHER_MONTH).data["submitted_count"], 1)
        self.assertEqual(self.status(year=YEAR - 1).data["submitted_count"], 1)

    def test_deleted_department_is_excluded(self):
        self.make_report("구매/자재", "SUBMITTED")
        Department.objects.filter(name="구매/자재").update(is_active=False)
        data = self.status().data
        self.assertEqual((data["total_departments"], data["submitted_count"], data["submitted_percent"]), (3, 0, 0))
        self.assertNotIn("구매/자재", [d["name"] for d in data["departments"]])
        self.assertNotIn("구매/자재", data["unsubmitted"])

    def test_percent_is_floored(self):
        Department.objects.filter(name="경영지원").update(is_active=False)  # 3개 부서
        self.make_report("영업", "SUBMITTED")
        self.assertEqual(self.status().data["submitted_percent"], 33)

    def test_no_departments(self):
        Department.objects.update(is_active=False)
        data = self.status().data
        self.assertEqual((data["total_departments"], data["submitted_percent"], data["departments"]), (0, 0, []))

    def test_deleted_submitter_gives_null_name(self):
        self.make_report("영업", "SUBMITTED", submitted_by=self.kim)
        self.kim.delete()  # submitted_by는 SET_NULL [A-15]
        row = next(r for r in self.status().data["departments"] if r["name"] == "영업")
        self.assertEqual(row["status"], "SUBMITTED")
        self.assertIsNone(row["submitted_by_name"])

    def test_future_month_is_allowed_and_empty(self):  # A-49
        response = self.status(year=YEAR + 1, month=1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({r["status"] for r in response.data["departments"]}, {"NOT_STARTED"})


class StatusValidationTests(StatusTestCase):
    def test_missing_or_bad_params(self):
        for url in (
            "/api/status/", f"/api/status/?year={YEAR}", f"/api/status/?month={MONTH}",
            f"/api/status/?year=abc&month={MONTH}", f"/api/status/?year={YEAR}&month=x",
            f"/api/status/?year={YEAR}&month=0", f"/api/status/?year={YEAR}&month=13",
            f"/api/status/?year=0&month={MONTH}", f"/api/status/?year=99999&month={MONTH}",
            f"/api/status/?year=-1&month={MONTH}",
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400, url)
            self.assertEqual(response.data["code"], "validation_error", url)

    def test_permissions(self):
        for url in (f"/api/status/?year={YEAR}&month={MONTH}", f"/api/status/matrix/?year={YEAR}"):
            self.assertEqual(APIClient().get(url).status_code, 401)
            self.client.force_authenticate(user=self.kim)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")
            self.client.force_authenticate(user=self.admin)


class StatusMatrixTests(StatusTestCase):
    def test_structure(self):
        data = self.matrix().data
        self.assertEqual(data["year"], YEAR)
        self.assertEqual([d["name"] for d in data["departments"]], ["영업", "생산", "구매/자재", "경영지원"])
        self.assertEqual(set(data["departments"][0]), {"id", "name"})
        self.assertEqual([m["month"] for m in data["months"]], list(range(1, 13)))
        ids = {str(d.id) for d in self.dept.values()}
        for month in data["months"]:
            self.assertEqual(set(month["statuses"]), ids)
            self.assertEqual(set(month["statuses"].values()), {"NOT_STARTED"})

    def test_statuses(self):
        self.make_report("영업", "SUBMITTED", month=3)
        self.make_report("생산", "DRAFT", month=3)
        self.make_report("영업", "DRAFT", month=5)
        data = self.matrix().data
        months = {m["month"]: m["statuses"] for m in data["months"]}
        sales, production = str(self.dept["영업"].id), str(self.dept["생산"].id)
        self.assertEqual((months[3][sales], months[3][production]), ("SUBMITTED", "DRAFT"))
        self.assertEqual(months[5][sales], "DRAFT")
        self.assertEqual(months[5][production], "NOT_STARTED")
        self.assertEqual(months[4][sales], "NOT_STARTED")

    def test_other_year_is_separate_and_deleted_department_excluded(self):
        self.make_report("영업", "SUBMITTED", month=3, year=YEAR - 1)
        self.make_report("생산", "SUBMITTED", month=3)
        Department.objects.filter(name="생산").update(is_active=False)
        data = self.matrix().data
        self.assertEqual(len(data["departments"]), 3)
        self.assertEqual(data["months"][2]["statuses"][str(self.dept["영업"].id)], "NOT_STARTED")
        self.assertNotIn(str(self.dept["생산"].id), data["months"][2]["statuses"])
        self.assertEqual(self.matrix(YEAR - 1).data["months"][2]["statuses"][str(self.dept["영업"].id)], "SUBMITTED")

    def test_year_validation(self):
        for url in ("/api/status/matrix/", "/api/status/matrix/?year=abc", "/api/status/matrix/?year=0"):
            self.assertEqual(self.client.get(url).status_code, 400, url)

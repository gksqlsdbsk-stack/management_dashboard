from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from organization.models import Department, InputItem

from .models import MonthlyReport, ReportValue
from .tests import PREV_MONTH, PREV_YEAR, TODAY

YEAR, MONTH = TODAY.year, TODAY.month


class AdminReportTestCase(TestCase):
    def setUp(self):
        self.production = Department.objects.get(name="생산")
        self.sales = Department.objects.get(name="영업")
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.emp = User.objects.create_user(username="P001", password="password1", name="홍길동", department=self.production)
        self.item = {i.name: i for i in InputItem.objects.filter(department=self.production)}
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)
        self.emp_client = APIClient()
        self.emp_client.force_authenticate(user=self.emp)

    def detail_url(self, department=None, year=YEAR, month=MONTH, suffix=""):
        return f"/api/departments/{(department or self.production).id}/report/{year}/{month}/{suffix}"

    def my_url(self, suffix=""):
        return f"/api/my-report/{YEAR}/{MONTH}/{suffix}"

    def fill_and_submit(self):
        values = [
            {"item_id": self.item["프로젝트별 재료비"].id, "project_name": "A프로젝트", "value": 1500000},
            {"item_id": self.item["프로젝트별 노무비"].id, "project_name": "A프로젝트", "value": 600000},
            {"item_id": self.item["프로젝트별 경비"].id, "project_name": "A프로젝트", "value": 100000},
            {"item_id": self.item["생산량"].id, "project_name": "", "value": 320},
            {"item_id": self.item["생산 능력(월 최대 생산량)"].id, "project_name": "", "value": 400},
            {"item_id": self.item["월말 인원수"].id, "project_name": "", "value": 12},
        ]
        self.emp_client.put(self.my_url(), {"values": values}, format="json")
        return self.emp_client.post(self.my_url("submit/"))


class DepartmentReportDetailTests(AdminReportTestCase):
    def test_not_started(self):
        response = self.admin_client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "NOT_STARTED")
        self.assertEqual(response.data["department"]["name"], "생산")
        self.assertEqual(response.data["values"], [])
        self.assertEqual(MonthlyReport.objects.count(), 0)  # 조회만으로 만들지 않는다

    def test_same_body_as_employee_get(self):
        self.fill_and_submit()
        admin_body = self.admin_client.get(self.detail_url()).data
        self.assertEqual(admin_body, self.emp_client.get(self.my_url()).data)
        self.assertEqual(admin_body["status"], "SUBMITTED")
        self.assertEqual(len(admin_body["values"]), 6)

    def test_draft_values_are_visible(self):
        self.emp_client.put(self.my_url(), {"values": [{"item_id": self.item["생산량"].id, "value": 7}]}, format="json")
        data = self.admin_client.get(self.detail_url()).data
        self.assertEqual((data["status"], data["progress"]["filled"]), ("DRAFT", 1))

    def test_shows_the_requested_department_not_the_admins(self):
        sales_data = self.admin_client.get(self.detail_url(self.sales)).data
        self.assertEqual(sales_data["department"]["name"], "영업")
        self.assertEqual(len(sales_data["items"]), 8)

    def test_other_month_is_independent(self):
        self.fill_and_submit()
        self.assertEqual(self.admin_client.get(self.detail_url(month=PREV_MONTH, year=PREV_YEAR)).data["status"], "NOT_STARTED")

    def test_future_month_is_allowed(self):
        response = self.admin_client.get(self.detail_url(year=YEAR + 1, month=1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "NOT_STARTED")

    def test_invalid_period(self):
        for year, month in ((YEAR, 0), (YEAR, 13), (0, 1), (99999, 1)):
            self.assertEqual(self.admin_client.get(self.detail_url(year=year, month=month)).status_code, 400)

    def test_unknown_or_deleted_department_is_404(self):
        response = self.admin_client.get("/api/departments/99999/report/2026/1/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "not_found")
        self.emp.delete()
        self.production.is_active = False
        self.production.save()
        self.assertEqual(self.admin_client.get(self.detail_url()).status_code, 404)

    def test_employee_and_anonymous_are_rejected(self):
        self.assertEqual(APIClient().get(self.detail_url()).status_code, 401)
        response = self.emp_client.get(self.detail_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "forbidden")

    def test_admin_cannot_write_values(self):  # A-22
        for method in (self.admin_client.put, self.admin_client.patch, self.admin_client.post, self.admin_client.delete):
            self.assertEqual(method(self.detail_url()).status_code, 405)
        self.assertEqual(self.admin_client.put(self.detail_url(), {"values": []}, format="json").status_code, 405)


class ReopenTests(AdminReportTestCase):
    def reopen(self, **kwargs):
        return self.admin_client.post(self.detail_url(suffix="reopen/", **kwargs))

    def test_reopen_submitted_report(self):
        self.fill_and_submit()
        response = self.reopen()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertIsNone(response.data["submitted_at"])
        self.assertEqual(len(response.data["values"]), 6)  # 값은 유지
        report = MonthlyReport.objects.get()
        self.assertEqual(report.status, "DRAFT")
        self.assertIsNone(report.submitted_by)
        self.assertIsNone(report.submitted_at)
        self.assertEqual(ReportValue.objects.count(), 6)

    def test_employee_can_edit_and_resubmit_after_reopen(self):
        self.fill_and_submit()
        self.assertEqual(self.emp_client.put(self.my_url(), {"values": []}, format="json").status_code, 409)
        self.reopen()
        edited = self.emp_client.put(
            self.my_url(), {"values": [{"item_id": self.item["생산량"].id, "project_name": "", "value": 999}]}, format="json"
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(self.emp_client.post(self.my_url("submit/")).status_code, 400)  # 값을 지웠으므로 필수 누락
        self.assertEqual(MonthlyReport.objects.count(), 1)

    def test_resubmit_after_reopen_succeeds_and_records_new_submitter(self):
        self.fill_and_submit()
        self.reopen()
        colleague = User.objects.create_user(username="P002", password="password1", name="이생산", department=self.production)
        self.emp_client.force_authenticate(user=colleague)
        response = self.emp_client.post(self.my_url("submit/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MonthlyReport.objects.get().submitted_by, colleague)

    def test_reopen_draft_is_409(self):
        self.emp_client.put(self.my_url(), {"values": []}, format="json")
        response = self.reopen()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_not_submitted")
        self.assertEqual(MonthlyReport.objects.get().status, "DRAFT")

    def test_reopen_not_started_is_409_and_creates_nothing(self):
        response = self.reopen()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_not_submitted")
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def test_reopen_twice_is_409(self):
        self.fill_and_submit()
        self.assertEqual(self.reopen().status_code, 200)
        self.assertEqual(self.reopen().status_code, 409)

    def test_reopen_affects_only_that_department_and_month(self):
        self.fill_and_submit()
        MonthlyReport.objects.create(department=self.sales, year=YEAR, month=MONTH, status="SUBMITTED", submitted_at=timezone.now())
        MonthlyReport.objects.create(department=self.production, year=PREV_YEAR, month=PREV_MONTH, status="SUBMITTED", submitted_at=timezone.now())
        self.reopen()
        self.assertEqual(MonthlyReport.objects.get(department=self.sales).status, "SUBMITTED")
        self.assertEqual(MonthlyReport.objects.get(department=self.production, month=PREV_MONTH, year=PREV_YEAR).status, "SUBMITTED")

    def test_reopen_is_reflected_in_status_summary(self):
        self.fill_and_submit()
        self.reopen()
        data = self.admin_client.get(f"/api/status/?year={YEAR}&month={MONTH}").data
        row = next(r for r in data["departments"] if r["name"] == "생산")
        self.assertEqual((row["status"], row["progress_percent"]), ("DRAFT", 100))
        self.assertEqual(data["submitted_count"], 0)

    def test_permissions_and_targets(self):
        self.fill_and_submit()
        url = self.detail_url(suffix="reopen/")
        self.assertEqual(APIClient().post(url).status_code, 401)
        response = self.emp_client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(MonthlyReport.objects.get().status, "SUBMITTED")
        self.assertEqual(self.admin_client.post("/api/departments/99999/report/2026/1/reopen/").status_code, 404)
        self.assertEqual(self.admin_client.get(url).status_code, 405)

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from organization.models import Department, InputItem

from .models import MonthlyReport, ReportValue
from .services import NO_DEPARTMENT_MESSAGE, calculate_progress

TODAY = timezone.localdate()
YEAR, MONTH = TODAY.year, TODAY.month
NEXT_YEAR, NEXT_MONTH = (YEAR + 1, 1) if MONTH == 12 else (YEAR, MONTH + 1)
PREV_YEAR, PREV_MONTH = (YEAR - 1, 12) if MONTH == 1 else (YEAR, MONTH - 1)


class CalculateProgressTests(SimpleTestCase):
    def test_nothing_filled(self):
        self.assertEqual(calculate_progress([1, 2, 3, 4], []), {"filled": 0, "required": 4, "percent": 0})

    def test_all_filled(self):
        self.assertEqual(calculate_progress([1, 2], [1, 2]), {"filled": 2, "required": 2, "percent": 100})

    def test_percent_is_floored(self):
        self.assertEqual(calculate_progress([1, 2, 3], [1])["percent"], 33)
        self.assertEqual(calculate_progress([1, 2, 3], [1, 2])["percent"], 66)

    def test_only_required_items_are_counted(self):
        self.assertEqual(calculate_progress([1, 2], [1, 99]), {"filled": 1, "required": 2, "percent": 50})

    def test_duplicate_filled_ids_count_once(self):
        self.assertEqual(calculate_progress([1, 2], [1, 1, 1])["filled"], 1)

    def test_no_required_items_is_complete(self):  # A-47
        self.assertEqual(calculate_progress([], []), {"filled": 0, "required": 0, "percent": 100})


class ReportTestCase(TestCase):
    def setUp(self):
        self.production = Department.objects.get(name="생산")  # 초기 데이터 [A-01, A-02]
        self.sales = Department.objects.get(name="영업")
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.emp = User.objects.create_user(username="P001", password="password1", name="홍길동", department=self.production)
        self.emp2 = User.objects.create_user(username="P002", password="password1", name="이생산", department=self.production)
        self.sales_emp = User.objects.create_user(username="S001", password="password1", name="김영업", department=self.sales)
        self.item = {i.name: i for i in InputItem.objects.filter(department=self.production)}
        self.client = APIClient()
        self.as_user(self.emp)

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def url(self, year=YEAR, month=MONTH, suffix=""):
        return f"/api/my-report/{year}/{month}/{suffix}"

    def entry(self, name, value, project_name=""):
        return {"item_id": self.item[name].id, "project_name": project_name, "value": value}

    def full_values(self):
        return [
            self.entry("프로젝트별 재료비", 1500000, "A프로젝트"),
            self.entry("프로젝트별 재료비", 820000, "B프로젝트"),
            self.entry("프로젝트별 노무비", 600000, "A프로젝트"),
            self.entry("프로젝트별 경비", 100000, "A프로젝트"),
            self.entry("생산량", 320),
            self.entry("생산 능력(월 최대 생산량)", 400),
            self.entry("월말 인원수", 12),
        ]

    def put(self, values, **kwargs):
        return self.client.put(self.url(**kwargs), {"values": values}, format="json")

    def submit_full(self):
        self.put(self.full_values())
        return self.client.post(self.url(suffix="submit/"))


class AccessTests(ReportTestCase):
    def test_unauthenticated_is_401(self):
        response = APIClient().get(self.url())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "not_authenticated")

    def test_admin_gets_403_on_every_endpoint(self):
        self.as_user(self.admin)
        for response in (
            self.client.get(self.url()),
            self.put([]),
            self.client.post(self.url(suffix="submit/")),
        ):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")

    def test_employee_without_department_gets_403_with_message(self):  # A-46
        loner = User.objects.create_user(username="P900", password="password1", name="무소속")
        self.as_user(loner)
        for response in (self.client.get(self.url()), self.put([]), self.client.post(self.url(suffix="submit/"))):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")
            self.assertEqual(response.data["detail"], NO_DEPARTMENT_MESSAGE)

    def test_employee_of_deleted_department_gets_403(self):
        self.production.is_active = False
        self.production.save()
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(MonthlyReport.objects.count(), 0)


class PeriodValidationTests(ReportTestCase):
    def test_current_month_is_allowed(self):
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_past_month_is_allowed(self):
        self.assertEqual(self.client.get(self.url(PREV_YEAR, PREV_MONTH)).status_code, 200)

    def test_future_month_is_rejected_for_every_endpoint(self):
        url = self.url(NEXT_YEAR, NEXT_MONTH)
        for response in (
            self.client.get(url),
            self.client.put(url, {"values": []}, format="json"),
            self.client.post(url + "submit/"),
        ):
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["code"], "validation_error")
            self.assertIn("month", response.data["errors"])
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def test_future_year_is_rejected(self):
        self.assertEqual(self.client.get(self.url(YEAR + 1, 1)).status_code, 400)

    def test_invalid_month_or_year(self):
        self.assertEqual(self.client.get(self.url(YEAR, 0)).status_code, 400)
        self.assertEqual(self.client.get(self.url(YEAR, 13)).status_code, 400)
        self.assertEqual(self.client.get(self.url(0, 1)).status_code, 400)


class GetReportTests(ReportTestCase):
    def test_not_started_form(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["status"], "NOT_STARTED")
        self.assertIsNone(data["submitted_at"])
        self.assertEqual((data["year"], data["month"]), (YEAR, MONTH))
        self.assertEqual(data["department"]["name"], "생산")
        self.assertTrue(data["department"]["input_guide"])
        self.assertEqual(data["progress"], {"filled": 0, "required": 6, "percent": 0})
        self.assertEqual(data["values"], [])
        self.assertEqual([i["name"] for i in data["items"]][:2], ["프로젝트별 재료비", "프로젝트별 노무비"])
        self.assertEqual(
            set(data["items"][0]), {"id", "name", "scope", "unit", "help_text", "is_required"}
        )
        self.assertEqual(MonthlyReport.objects.count(), 0)  # 조회만으로 레코드를 만들지 않는다

    def test_items_only_include_active_ones(self):
        self.item["생산량"].is_active = False
        self.item["생산량"].save()
        data = self.client.get(self.url()).data
        self.assertNotIn("생산량", [i["name"] for i in data["items"]])
        self.assertEqual(data["progress"]["required"], 5)

    def test_employee_sees_only_own_department(self):
        self.as_user(self.sales_emp)
        data = self.client.get(self.url()).data
        self.assertEqual(data["department"]["name"], "영업")
        self.assertEqual(len(data["items"]), 8)


class SaveDraftTests(ReportTestCase):
    def test_put_creates_draft_and_returns_form(self):
        response = self.put(self.full_values())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertEqual(response.data["progress"], {"filled": 6, "required": 6, "percent": 100})
        report = MonthlyReport.objects.get()
        self.assertEqual((report.department, report.year, report.month, report.status), (self.production, YEAR, MONTH, "DRAFT"))
        self.assertEqual(report.values.count(), 7)

    def test_saved_values_are_returned_by_get(self):
        self.put(self.full_values())
        data = self.client.get(self.url()).data
        self.assertEqual(data["status"], "DRAFT")
        self.assertIn(
            {"item_id": self.item["프로젝트별 재료비"].id, "project_name": "A프로젝트", "value": 1500000}, data["values"]
        )
        self.assertIn({"item_id": self.item["생산량"].id, "project_name": "", "value": 320}, data["values"])

    def test_values_are_numbers_with_decimals(self):
        self.put([self.entry("생산량", 12.5), self.entry("월말 인원수", "3.1234")])
        by_item = {v["item_id"]: v["value"] for v in self.client.get(self.url()).data["values"]}
        self.assertEqual(by_item[self.item["생산량"].id], 12.5)
        self.assertEqual(by_item[self.item["월말 인원수"].id], 3.1234)

    def test_put_replaces_all_values(self):
        self.put(self.full_values())
        response = self.put([self.entry("생산량", 999)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["progress"]["filled"], 1)
        self.assertEqual(ReportValue.objects.count(), 1)
        self.assertEqual(ReportValue.objects.get().value, 999)
        self.assertEqual(MonthlyReport.objects.count(), 1)

    def test_put_empty_list_clears_values_but_keeps_draft(self):
        self.put(self.full_values())
        self.assertEqual(self.put([]).status_code, 200)
        self.assertEqual(ReportValue.objects.count(), 0)
        self.assertEqual(MonthlyReport.objects.get().status, "DRAFT")

    def test_empty_values_are_not_saved(self):
        response = self.put([
            self.entry("생산량", None),
            {"item_id": self.item["생산 능력(월 최대 생산량)"].id},  # value 생략
            self.entry("월말 인원수", ""),
            self.entry("프로젝트별 재료비", None, "A프로젝트"),  # 이름만 있고 값 없음
            self.entry("프로젝트별 경비", None, ""),  # 빈 프로젝트 행
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReportValue.objects.count(), 0)
        self.assertEqual(response.data["progress"]["filled"], 0)

    def test_zero_is_a_valid_filled_value(self):  # A-05
        response = self.put([self.entry("생산량", 0)])
        self.assertEqual(response.data["progress"]["filled"], 1)
        self.assertEqual(ReportValue.objects.get().value, 0)

    def test_project_item_needs_only_one_row_to_count(self):  # A-05
        response = self.put([self.entry("프로젝트별 재료비", 100, "A프로젝트"), self.entry("프로젝트별 재료비", 50, "B프로젝트")])
        self.assertEqual(response.data["progress"]["filled"], 1)

    def test_progress_ignores_optional_items(self):
        self.item["생산량"].is_required = False
        self.item["생산량"].save()
        response = self.put([self.entry("생산량", 5)])
        self.assertEqual(response.data["progress"], {"filled": 0, "required": 5, "percent": 0})

    def test_project_name_is_trimmed(self):
        self.put([self.entry("프로젝트별 재료비", 100, "  A프로젝트 ")])
        self.assertEqual(ReportValue.objects.get().project_name, "A프로젝트")

    def test_values_of_inactive_items_are_kept(self):  # A-06
        self.put(self.full_values())
        capacity = self.item["생산 능력(월 최대 생산량)"]
        capacity.is_active = False
        capacity.save()
        response = self.put([self.entry("생산량", 1)])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReportValue.objects.filter(item=capacity).exists())
        self.assertNotIn(capacity.id, [v["item_id"] for v in response.data["values"]])

    def test_colleague_continues_the_same_report(self):  # A-11
        self.put([self.entry("생산량", 10)])
        self.as_user(self.emp2)
        self.assertEqual(self.client.get(self.url()).data["progress"]["filled"], 1)
        self.put([self.entry("생산량", 10), self.entry("월말 인원수", 4)])
        self.assertEqual(MonthlyReport.objects.count(), 1)
        self.assertEqual(ReportValue.objects.count(), 2)

    def test_departments_are_isolated(self):
        self.put([self.entry("생산량", 10)])
        self.as_user(self.sales_emp)
        self.assertEqual(self.client.get(self.url()).data["status"], "NOT_STARTED")

    def test_months_are_independent(self):
        self.put([self.entry("생산량", 10)])
        self.assertEqual(self.client.get(self.url(PREV_YEAR, PREV_MONTH)).data["status"], "NOT_STARTED")


class SaveValidationTests(ReportTestCase):
    def assert_rejected(self, values, expected_fragment=None):
        response = self.put(values)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["code"], "validation_error")
        messages = response.data["errors"]["values"]
        if expected_fragment:
            self.assertTrue(any(expected_fragment in m for m in messages), messages)
        self.assertEqual(MonthlyReport.objects.count(), 0)  # 실패하면 레코드도 만들지 않는다
        return messages

    def test_monthly_item_rejects_project_name(self):
        self.assert_rejected([self.entry("생산량", 1, "A프로젝트")], "프로젝트명을 입력하지 않는")

    def test_project_item_requires_project_name(self):
        self.assert_rejected([self.entry("프로젝트별 재료비", 1, "")], "프로젝트명이 필요")
        self.assert_rejected([self.entry("프로젝트별 재료비", 1, "   ")], "프로젝트명이 필요")

    def test_project_name_too_long(self):
        self.assert_rejected([self.entry("프로젝트별 재료비", 1, "가" * 101)], "너무 깁니다")

    def test_duplicate_item_and_project(self):
        self.assert_rejected(
            [self.entry("프로젝트별 재료비", 1, "A프로젝트"), self.entry("프로젝트별 재료비", 2, " A프로젝트")], "중복"
        )
        self.assert_rejected([self.entry("생산량", 1), self.entry("생산량", 2)], "중복")

    def test_duplicate_check_ignores_empty_rows(self):
        response = self.put([self.entry("생산량", 1), self.entry("생산량", None)])
        self.assertEqual(response.status_code, 200)

    def test_item_of_another_department(self):
        foreign = InputItem.objects.filter(department=self.sales).first()
        self.assert_rejected([{"item_id": foreign.id, "project_name": "", "value": 1}], "입력 항목이 아닙니다")

    def test_inactive_or_unknown_item(self):
        self.item["생산량"].is_active = False
        self.item["생산량"].save()
        self.assert_rejected([self.entry("생산량", 1)], "입력 항목이 아닙니다")
        self.assert_rejected([{"item_id": 999999, "project_name": "", "value": 1}], "입력 항목이 아닙니다")
        self.assert_rejected([{"value": 1}], "입력 항목이 아닙니다")
        self.assert_rejected([{"item_id": "7", "value": 1}], "입력 항목이 아닙니다")

    def test_value_must_be_a_number(self):
        self.assert_rejected([self.entry("생산량", "abc")], "숫자가 아닙니다")
        self.assert_rejected([self.entry("생산량", "1,000")], "숫자가 아닙니다")
        self.assert_rejected([self.entry("생산량", True)], "숫자가 아닙니다")

    def test_too_many_decimal_places(self):
        self.assert_rejected([self.entry("생산량", "1.23456")], "소수는 4자리")

    def test_value_out_of_range(self):
        self.assert_rejected([self.entry("생산량", "1" * 17)], "허용 범위")

    def test_malformed_body(self):
        for body in ({}, {"values": "x"}, {"values": {"a": 1}}, {"values": [1, "a"]}):
            response = self.client.put(self.url(), body, format="json")
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(self.client.put(self.url(), [], format="json").status_code, 400)

    def test_all_errors_are_reported_together(self):
        messages = self.assert_rejected([self.entry("생산량", "x"), self.entry("월말 인원수", 1, "P")])
        self.assertEqual(len(messages), 2)

    def test_invalid_put_keeps_previous_values(self):
        self.put([self.entry("생산량", 7)])
        self.assertEqual(self.put([self.entry("생산량", "x")]).status_code, 400)
        self.assertEqual(ReportValue.objects.get().value, 7)


class SubmitTests(ReportTestCase):
    def test_submit_success(self):
        response = self.submit_full()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUBMITTED")
        self.assertTrue(response.data["submitted_at"].endswith("+09:00"))
        report = MonthlyReport.objects.get()
        self.assertEqual(report.status, "SUBMITTED")
        self.assertEqual(report.submitted_by, self.emp)
        self.assertIsNotNone(report.submitted_at)
        self.assertEqual(self.client.get(self.url()).data["status"], "SUBMITTED")

    def test_submit_requires_all_required_items(self):
        self.put([self.entry("생산량", 1)])
        response = self.client.post(self.url(suffix="submit/"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "incomplete_required")
        missing = {m["name"] for m in response.data["errors"]["missing_items"]}
        self.assertEqual(missing, {"프로젝트별 재료비", "프로젝트별 노무비", "프로젝트별 경비", "생산 능력(월 최대 생산량)", "월말 인원수"})
        self.assertEqual(set(response.data["errors"]["missing_items"][0]), {"id", "name"})
        self.assertEqual(MonthlyReport.objects.get().status, "DRAFT")

    def test_optional_items_may_be_empty(self):
        self.item["생산량"].is_required = False
        self.item["생산량"].save()
        values = [v for v in self.full_values() if v["item_id"] != self.item["생산량"].id]
        self.put(values)
        self.assertEqual(self.client.post(self.url(suffix="submit/")).status_code, 200)

    def test_submit_without_any_record_is_rejected_and_creates_nothing(self):
        response = self.client.post(self.url(suffix="submit/"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data["errors"]["missing_items"]), 6)
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def test_submit_ignores_values_of_inactive_items(self):
        self.put(self.full_values())
        self.item["생산량"].is_active = False
        self.item["생산량"].save()
        self.assertEqual(self.client.post(self.url(suffix="submit/")).status_code, 200)

    def test_inactive_required_item_does_not_block_submission(self):
        self.put([v for v in self.full_values() if v["item_id"] != self.item["월말 인원수"].id])
        self.item["월말 인원수"].is_active = False
        self.item["월말 인원수"].save()
        self.assertEqual(self.client.post(self.url(suffix="submit/")).status_code, 200)

    def test_resubmit_is_409_duplicate_submission(self):
        self.submit_full()
        response = self.client.post(self.url(suffix="submit/"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "duplicate_submission")

    def test_colleague_cannot_resubmit(self):
        self.submit_full()
        self.as_user(self.emp2)
        response = self.client.post(self.url(suffix="submit/"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "duplicate_submission")
        self.assertEqual(MonthlyReport.objects.get().submitted_by, self.emp)

    def test_put_after_submit_is_locked(self):
        self.submit_full()
        response = self.put([self.entry("생산량", 1)])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_locked")
        self.assertEqual(ReportValue.objects.count(), 7)

    def test_lock_is_checked_before_body_validation(self):
        self.submit_full()
        response = self.put([self.entry("생산량", "x")])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_locked")

    def test_submit_with_no_required_items_is_allowed(self):  # A-47
        department = Department.objects.create(name="무필수")
        InputItem.objects.create(department=department, name="메모성 수치", scope="MONTHLY", is_required=False)
        user = User.objects.create_user(username="N001", password="password1", name="무필수", department=department)
        self.as_user(user)
        self.assertEqual(self.client.get(self.url()).data["progress"], {"filled": 0, "required": 0, "percent": 100})
        response = self.client.post(self.url(suffix="submit/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MonthlyReport.objects.get(department=department).status, "SUBMITTED")

    def test_other_department_and_month_are_unaffected(self):
        self.submit_full()
        self.assertEqual(self.client.get(self.url(PREV_YEAR, PREV_MONTH)).data["status"], "NOT_STARTED")
        self.assertEqual(self.put([self.entry("생산량", 1)], year=PREV_YEAR, month=PREV_MONTH).status_code, 200)
        self.as_user(self.sales_emp)
        self.assertEqual(self.client.get(self.url()).data["status"], "NOT_STARTED")


class ConstraintTests(ReportTestCase):
    def test_one_report_per_department_month(self):
        MonthlyReport.objects.create(department=self.production, year=YEAR, month=MONTH)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MonthlyReport.objects.create(department=self.production, year=YEAR, month=MONTH)
        MonthlyReport.objects.create(department=self.sales, year=YEAR, month=MONTH)  # 다른 부서는 가능

    def test_month_range_check(self):
        for month in (0, 13):
            with self.assertRaises(IntegrityError), transaction.atomic():
                MonthlyReport.objects.create(department=self.production, year=YEAR, month=month)

    def test_one_value_per_report_item_project(self):
        report = MonthlyReport.objects.create(department=self.production, year=YEAR, month=MONTH)
        item = self.item["프로젝트별 재료비"]
        ReportValue.objects.create(report=report, item=item, project_name="A", value=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ReportValue.objects.create(report=report, item=item, project_name="A", value=2)
        ReportValue.objects.create(report=report, item=item, project_name="B", value=2)


class ItemScopeGuardTests(ReportTestCase):
    """값이 있는 입력 항목의 범위 변경 방지 [A-04]."""

    def setUp(self):
        super().setUp()
        self.as_user(self.admin)

    def patch_item(self, name, data):
        return self.client.patch(f"/api/items/{self.item[name].id}/", data, format="json")

    def store_value(self, name, project_name=""):
        report, _ = MonthlyReport.objects.get_or_create(department=self.production, year=YEAR, month=MONTH)
        ReportValue.objects.create(report=report, item=self.item[name], project_name=project_name, value=1)

    def test_scope_change_is_rejected_when_values_exist(self):
        self.store_value("생산량")
        response = self.patch_item("생산량", {"scope": "PROJECT"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("scope", response.data["errors"])
        self.item["생산량"].refresh_from_db()
        self.assertEqual(self.item["생산량"].scope, "MONTHLY")

    def test_scope_change_is_allowed_without_values(self):
        self.assertEqual(self.patch_item("생산량", {"scope": "PROJECT"}).status_code, 200)
        self.item["생산량"].refresh_from_db()
        self.assertEqual(self.item["생산량"].scope, "PROJECT")

    def test_other_fields_and_same_scope_are_allowed_with_values(self):
        self.store_value("프로젝트별 재료비", "A")
        response = self.patch_item("프로젝트별 재료비", {"scope": "PROJECT", "unit": "천원", "name": "재료비(수정)"})
        self.assertEqual(response.status_code, 200)

    def test_values_in_other_items_do_not_block(self):
        self.store_value("생산량")
        self.assertEqual(self.patch_item("월말 인원수", {"scope": "PROJECT"}).status_code, 200)

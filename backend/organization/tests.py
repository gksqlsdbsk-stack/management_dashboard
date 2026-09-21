from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User

from .metric_keys import METRIC_KEYS
from .models import Department, InputItem


class OrganizationTestCase(TestCase):
    def setUp(self):
        self.production = Department.objects.get(name="생산")  # 초기 데이터 [A-01]
        self.sales = Department.objects.get(name="영업")
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.employee = User.objects.create_user(
            username="P001", password="password1", name="홍길동", department=self.production
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def item_payload(self, **overrides):
        payload = {
            "name": "기타 비용", "scope": "MONTHLY", "unit": "원", "metric_key": None,
            "help_text": "안내", "is_required": False, "sort_order": 9,
        }
        payload.update(overrides)
        return payload


class SeedDataTests(OrganizationTestCase):
    def test_departments(self):
        names = list(Department.objects.filter(is_active=True).values_list("name", flat=True))
        self.assertEqual(names, ["영업", "생산", "구매/자재", "경영지원"])

    def test_item_counts_per_department(self):
        counts = {d.name: d.items.count() for d in Department.objects.all()}
        self.assertEqual(counts, {"영업": 8, "생산": 6, "구매/자재": 2, "경영지원": 3})
        self.assertEqual(InputItem.objects.count(), 19)

    def test_items_are_required_and_have_guides(self):
        for item in InputItem.objects.all():
            self.assertTrue(item.is_required, item.name)
            self.assertTrue(item.help_text, item.name)
            self.assertIsNotNone(item.metric_key, item.name)
        for department in Department.objects.all():
            self.assertTrue(department.input_guide, department.name)

    def test_scope_and_metric_key_mapping(self):
        production = {i.name: (i.scope, i.unit, i.metric_key) for i in self.production.items.all()}
        self.assertEqual(production["프로젝트별 재료비"], ("PROJECT", "원", "MATERIAL_COST"))
        self.assertEqual(production["생산량"], ("MONTHLY", "개", "PRODUCTION_QTY"))
        sales = {i.name: (i.scope, i.unit, i.metric_key) for i in self.sales.items.all()}
        self.assertEqual(sales["프로젝트별 매출액"], ("PROJECT", "원", "REVENUE"))
        self.assertEqual(sales["파이프라인 예상 수주 확률"], ("MONTHLY", "%", "PIPELINE_WIN_RATE"))

    def test_every_department_has_headcount(self):
        self.assertEqual(InputItem.objects.filter(metric_key="HEADCOUNT").count(), 4)


class ConstraintTests(OrganizationTestCase):
    def test_active_department_name_unique_but_inactive_reusable(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Department.objects.create(name="생산")
        Department.objects.create(name="폐지부서", is_active=False)
        Department.objects.create(name="폐지부서")  # 비활성 이름은 재사용 가능

    def test_active_item_name_unique_per_department(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            InputItem.objects.create(department=self.production, name="생산량", scope="MONTHLY")
        InputItem.objects.create(department=self.sales, name="생산량", scope="MONTHLY")  # 다른 부서는 가능


class MetricKeyApiTests(OrganizationTestCase):
    def test_lists_sixteen_keys(self):
        response = self.client.get("/api/metric-keys/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 16)
        self.assertEqual(len(METRIC_KEYS), 16)
        by_key = {k["key"]: k for k in response.data}
        self.assertEqual(by_key["REVENUE"], {"key": "REVENUE", "label": "매출액", "unit": "원", "aggregation": "flow"})
        self.assertEqual(by_key["CASH_BALANCE"]["aggregation"], "stock")
        self.assertEqual(by_key["PIPELINE_WIN_RATE"]["aggregation"], "rate")

    def test_admin_only(self):
        self.as_user(self.employee)
        self.assertEqual(self.client.get("/api/metric-keys/").status_code, 403)
        self.assertEqual(APIClient().get("/api/metric-keys/").status_code, 401)


class DepartmentApiTests(OrganizationTestCase):
    def test_admin_lists_all_active_departments(self):
        Department.objects.create(name="폐지부서", is_active=False)
        response = self.client.get("/api/departments/")
        self.assertEqual([d["name"] for d in response.data], ["영업", "생산", "구매/자재", "경영지원"])
        self.assertEqual(set(response.data[0]), {"id", "name", "input_guide", "sort_order"})

    def test_employee_sees_only_own_department(self):
        self.as_user(self.employee)
        response = self.client.get("/api/departments/")
        self.assertEqual([d["name"] for d in response.data], ["생산"])

    def test_employee_without_department_sees_nothing(self):
        loner = User.objects.create_user(username="P900", password="password1", name="무소속")
        self.as_user(loner)
        self.assertEqual(self.client.get("/api/departments/").data, [])

    def test_unauthenticated_is_401(self):
        self.assertEqual(APIClient().get("/api/departments/").status_code, 401)

    def test_employee_cannot_write(self):
        self.as_user(self.employee)
        url = f"/api/departments/{self.production.id}/"
        self.assertEqual(self.client.post("/api/departments/", {"name": "신규"}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(url, {"name": "변경"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(self.client.get(f"{url}items/").status_code, 403)
        self.assertEqual(self.client.post(f"{url}items/", self.item_payload(), format="json").status_code, 403)

    def test_create(self):
        response = self.client.post(
            "/api/departments/", {"name": "품질", "input_guide": "안내", "sort_order": 5}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "품질")
        self.assertTrue(Department.objects.get(name="품질").is_active)

    def test_create_rejects_duplicate_active_name_and_blank(self):
        duplicate = self.client.post("/api/departments/", {"name": "생산"}, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.data["code"], "validation_error")
        self.assertIn("name", duplicate.data["errors"])
        self.assertEqual(self.client.post("/api/departments/", {"name": ""}, format="json").status_code, 400)

    def test_patch(self):
        response = self.client.patch(
            f"/api/departments/{self.sales.id}/", {"name": "영업1팀", "input_guide": "새 안내", "sort_order": 7}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.sales.refresh_from_db()
        self.assertEqual((self.sales.name, self.sales.input_guide, self.sales.sort_order), ("영업1팀", "새 안내", 7))

    def test_patch_same_name_allowed_but_other_active_name_rejected(self):
        url = f"/api/departments/{self.sales.id}/"
        self.assertEqual(self.client.patch(url, {"name": "영업"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"name": "생산"}, format="json").status_code, 400)

    def test_delete_is_logical_and_name_can_be_reused(self):
        self.employee.delete()  # 소속 사용자 없음
        response = self.client.delete(f"/api/departments/{self.production.id}/")
        self.assertEqual(response.status_code, 204)
        self.production.refresh_from_db()
        self.assertFalse(self.production.is_active)
        self.assertEqual(self.production.items.count(), 6)  # 과거 데이터 유지
        self.assertNotIn("생산", [d["name"] for d in self.client.get("/api/departments/").data])
        created = self.client.post("/api/departments/", {"name": "생산"}, format="json")  # 이름 재사용
        self.assertEqual(created.status_code, 201)

    def test_delete_blocked_when_active_user_belongs(self):
        response = self.client.delete(f"/api/departments/{self.production.id}/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "department_in_use")
        self.production.refresh_from_db()
        self.assertTrue(self.production.is_active)

    def test_delete_allowed_when_only_inactive_users_belong(self):
        self.employee.is_active = False
        self.employee.save()
        self.assertEqual(self.client.delete(f"/api/departments/{self.production.id}/").status_code, 204)

    def test_inactive_department_is_not_found(self):
        self.employee.delete()
        self.client.delete(f"/api/departments/{self.production.id}/")
        url = f"/api/departments/{self.production.id}/"
        self.assertEqual(self.client.patch(url, {"name": "x"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(self.client.get(f"{url}items/").status_code, 404)
        self.assertEqual(self.client.post(f"{url}items/", self.item_payload(), format="json").status_code, 404)


class InputItemApiTests(OrganizationTestCase):
    def test_list_returns_active_items_in_order(self):
        InputItem.objects.filter(department=self.production, name="생산량").update(is_active=False)
        response = self.client.get(f"/api/departments/{self.production.id}/items/")
        self.assertEqual(response.status_code, 200)
        names = [i["name"] for i in response.data]
        self.assertEqual(names[0], "프로젝트별 재료비")
        self.assertNotIn("생산량", names)
        self.assertEqual(
            set(response.data[0]),
            {"id", "department", "name", "scope", "unit", "metric_key", "help_text", "is_required", "sort_order"},
        )
        self.assertEqual(response.data[0]["department"], self.production.id)

    def test_create(self):
        response = self.client.post(
            f"/api/departments/{self.production.id}/items/",
            self.item_payload(metric_key="EXPENSE_COST"),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        item = InputItem.objects.get(pk=response.data["id"])
        self.assertEqual((item.department, item.name, item.metric_key, item.is_required), (self.production, "기타 비용", "EXPENSE_COST", False))

    def test_create_without_metric_key(self):
        response = self.client.post(
            f"/api/departments/{self.production.id}/items/", self.item_payload(metric_key=""), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["metric_key"])

    def test_create_validation(self):
        url = f"/api/departments/{self.production.id}/items/"
        bad_key = self.client.post(url, self.item_payload(metric_key="NOPE"), format="json")
        self.assertEqual(bad_key.status_code, 400)
        self.assertIn("metric_key", bad_key.data["errors"])
        bad_scope = self.client.post(url, self.item_payload(scope="DAILY"), format="json")
        self.assertIn("scope", bad_scope.data["errors"])
        no_name = self.client.post(url, self.item_payload(name=""), format="json")
        self.assertIn("name", no_name.data["errors"])

    def test_create_rejects_duplicate_active_name_in_same_department(self):
        response = self.client.post(
            f"/api/departments/{self.production.id}/items/", self.item_payload(name="생산량"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data["errors"])
        other = self.client.post(
            f"/api/departments/{self.sales.id}/items/", self.item_payload(name="생산량"), format="json"
        )
        self.assertEqual(other.status_code, 201)

    def test_patch(self):
        item = self.production.items.get(name="생산량")
        response = self.client.patch(
            f"/api/items/{item.id}/",
            {"name": "총 생산량", "unit": "EA", "is_required": False, "metric_key": None, "sort_order": 3, "scope": "PROJECT"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(
            (item.name, item.unit, item.is_required, item.metric_key, item.sort_order, item.scope),
            ("총 생산량", "EA", False, None, 3, "PROJECT"),
        )

    def test_patch_cannot_move_department_and_rejects_duplicate_name(self):
        item = self.production.items.get(name="생산량")
        self.client.patch(f"/api/items/{item.id}/", {"department": self.sales.id}, format="json")
        item.refresh_from_db()
        self.assertEqual(item.department, self.production)
        duplicate = self.client.patch(f"/api/items/{item.id}/", {"name": "프로젝트별 재료비"}, format="json")
        self.assertEqual(duplicate.status_code, 400)
        same = self.client.patch(f"/api/items/{item.id}/", {"name": "생산량"}, format="json")
        self.assertEqual(same.status_code, 200)

    def test_delete_is_logical_and_name_can_be_reused(self):
        item = self.production.items.get(name="생산량")
        self.assertEqual(self.client.delete(f"/api/items/{item.id}/").status_code, 204)
        item.refresh_from_db()
        self.assertFalse(item.is_active)
        names = [i["name"] for i in self.client.get(f"/api/departments/{self.production.id}/items/").data]
        self.assertNotIn("생산량", names)
        created = self.client.post(
            f"/api/departments/{self.production.id}/items/", self.item_payload(name="생산량"), format="json"
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.patch(f"/api/items/{item.id}/", {"name": "x"}, format="json").status_code, 404)

    def test_employee_cannot_modify_items(self):
        item = self.production.items.first()
        self.as_user(self.employee)
        self.assertEqual(self.client.patch(f"/api/items/{item.id}/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/items/{item.id}/").status_code, 403)

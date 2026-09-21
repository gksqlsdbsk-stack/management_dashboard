from django.test import TestCase
from rest_framework.test import APIClient

from organization.models import Department

from .models import User


class UserApiTestCase(TestCase):
    def setUp(self):
        self.production = Department.objects.get(name="생산")  # 초기 데이터 [A-01]
        self.sales = Department.objects.get(name="영업")
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.employee = User.objects.create_user(
            username="P001", password="password1", name="홍길동", department=self.production
        )
        self.client = APIClient()
        self.as_user(self.admin)

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def create_payload(self, **overrides):
        payload = {
            "name": "김영업", "employee_no": "S001", "role": "EMPLOYEE",
            "department_id": self.sales.id, "password": "password1",
        }
        payload.update(overrides)
        return payload


class UserPermissionTests(UserApiTestCase):
    def test_unauthenticated_is_401(self):
        response = APIClient().get("/api/users/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "not_authenticated")

    def test_employee_gets_403_on_every_endpoint(self):
        self.as_user(self.employee)
        detail = f"/api/users/{self.employee.id}/"
        responses = [
            self.client.get("/api/users/"),
            self.client.post("/api/users/", self.create_payload(), format="json"),
            self.client.get(detail),
            self.client.patch(detail, {"name": "변경"}, format="json"),
            self.client.delete(detail),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")


class UserCrudTests(UserApiTestCase):
    def test_list_and_department_filter(self):
        response = self.client.get("/api/users/")
        self.assertEqual([u["employee_no"] for u in response.data], ["A001", "P001"])
        self.assertNotIn("password", response.data[0])

        filtered = self.client.get(f"/api/users/?department={self.production.id}")
        self.assertEqual([u["employee_no"] for u in filtered.data], ["P001"])
        self.assertEqual(self.client.get("/api/users/?department=abc").status_code, 400)

    def test_create_employee(self):
        response = self.client.post("/api/users/", self.create_payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["department"], {"id": self.sales.id, "name": "영업"})
        self.assertTrue(response.data["is_active"])
        user = User.objects.get(username="S001")
        self.assertNotEqual(user.password, "password1")  # 해시로 저장
        self.assertTrue(user.check_password("password1"))

    def test_created_user_can_log_in(self):
        self.client.post("/api/users/", self.create_payload(), format="json")
        response = APIClient().post(
            "/api/auth/login/", {"name": "김영업", "employee_no": "S001", "password": "password1"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_create_admin_without_department(self):
        payload = self.create_payload(role="ADMIN", employee_no="A002")
        del payload["department_id"]
        response = self.client.post("/api/users/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["department"])

    def test_create_employee_requires_department(self):
        payload = self.create_payload()
        del payload["department_id"]
        response = self.client.post("/api/users/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("department_id", response.data["errors"])

    def test_create_rejects_inactive_department(self):
        self.sales.is_active = False
        self.sales.save()
        response = self.client.post("/api/users/", self.create_payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("department_id", response.data["errors"])

    def test_create_validates_password(self):
        short = self.client.post("/api/users/", self.create_payload(password="short"), format="json")
        self.assertEqual(short.status_code, 400)
        self.assertIn("password", short.data["errors"])
        payload = self.create_payload()
        del payload["password"]
        missing = self.client.post("/api/users/", payload, format="json")
        self.assertEqual(missing.status_code, 400)
        self.assertIn("password", missing.data["errors"])

    def test_create_rejects_duplicate_employee_no(self):
        response = self.client.post("/api/users/", self.create_payload(employee_no="P001"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("employee_no", response.data["errors"])

    def test_create_rejects_unknown_role(self):
        response = self.client.post("/api/users/", self.create_payload(role="BOSS"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data["errors"])

    def test_retrieve(self):
        response = self.client.get(f"/api/users/{self.employee.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "홍길동")
        missing = self.client.get("/api/users/99999/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.data["code"], "not_found")

    def test_patch_updates_fields_and_keeps_password(self):
        response = self.client.patch(
            f"/api/users/{self.employee.id}/",
            {"name": "홍길순", "employee_no": "P002", "department_id": self.sales.id, "is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(
            (self.employee.name, self.employee.username, self.employee.department, self.employee.is_active),
            ("홍길순", "P002", self.sales, False),
        )
        self.assertTrue(self.employee.check_password("password1"))

    def test_patch_same_employee_no_is_allowed(self):
        response = self.client.patch(f"/api/users/{self.employee.id}/", {"employee_no": "P001"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_patch_password_reset(self):
        response = self.client.patch(f"/api/users/{self.employee.id}/", {"password": "newpassword9"}, format="json")
        self.assertEqual(response.status_code, 200)
        login = APIClient().post(
            "/api/auth/login/", {"name": "홍길동", "employee_no": "P001", "password": "newpassword9"}, format="json"
        )
        self.assertEqual(login.status_code, 200)
        old = APIClient().post(
            "/api/auth/login/", {"name": "홍길동", "employee_no": "P001", "password": "password1"}, format="json"
        )
        self.assertEqual(old.status_code, 400)

    def test_patch_short_password_rejected(self):
        response = self.client.patch(f"/api/users/{self.employee.id}/", {"password": "short"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_patch_role_to_employee_requires_department(self):
        response = self.client.patch(f"/api/users/{self.admin.id}/", {"role": "EMPLOYEE"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("department_id", response.data["errors"])

    def test_patch_cannot_clear_employee_department(self):
        response = self.client.patch(f"/api/users/{self.employee.id}/", {"department_id": None}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_put_not_allowed(self):
        response = self.client.put(f"/api/users/{self.employee.id}/", self.create_payload(), format="json")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["code"], "method_not_allowed")


class UserDeleteTests(UserApiTestCase):
    def test_delete_employee(self):
        response = self.client.delete(f"/api/users/{self.employee.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.employee.pk).exists())

    def test_cannot_delete_self(self):
        response = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "cannot_delete_user")
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_can_delete_other_admin_but_not_the_last_one(self):
        other = User.objects.create_user(username="A002", password="password1", name="부대표", role=User.Role.ADMIN)
        self.assertEqual(self.client.delete(f"/api/users/{other.id}/").status_code, 204)
        last = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(last.status_code, 409)
        self.assertEqual(last.data["code"], "cannot_delete_user")
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 1)

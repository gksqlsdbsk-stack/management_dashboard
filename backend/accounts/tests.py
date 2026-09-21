from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from organization.models import Department

from .models import User
from .services import (
    DEFAULT_ADMIN_EMPLOYEE_NO,
    DEFAULT_ADMIN_NAME,
    DEFAULT_ADMIN_PASSWORD,
    ensure_default_admin,
)
from .views import LOGIN_FAILED_MESSAGE


class DefaultAdminTests(TestCase):
    def test_creates_default_admin_when_no_admin(self):
        user = ensure_default_admin()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertEqual(user.name, DEFAULT_ADMIN_NAME)
        self.assertEqual(user.username, DEFAULT_ADMIN_EMPLOYEE_NO)
        self.assertTrue(user.check_password(DEFAULT_ADMIN_PASSWORD))

    def test_idempotent(self):
        ensure_default_admin()
        self.assertIsNone(ensure_default_admin())
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 1)

    def test_skipped_when_another_admin_exists(self):
        User.objects.create_user(username="A001", password="pw", name="대표", role=User.Role.ADMIN)
        self.assertIsNone(ensure_default_admin())
        self.assertFalse(User.objects.filter(username=DEFAULT_ADMIN_EMPLOYEE_NO).exists())

    def test_skipped_when_username_taken_by_employee(self):
        User.objects.create_user(username=DEFAULT_ADMIN_EMPLOYEE_NO, password="pw", name="직원")
        with self.assertLogs("accounts.services", level="WARNING"):
            self.assertIsNone(ensure_default_admin())
        self.assertFalse(User.objects.filter(role=User.Role.ADMIN).exists())


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(name="생산")
        self.employee = User.objects.create_user(
            username="P001", password="password1", name="홍길동", department=self.department
        )
        self.admin = ensure_default_admin()

    def login(self, name="홍길동", employee_no="P001", password="password1"):
        return self.client.post(
            "/api/auth/login/", {"name": name, "employee_no": employee_no, "password": password}, format="json"
        )

    def test_login_success_employee(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["employee_no"], "P001")
        self.assertEqual(response.data["user"]["role"], "EMPLOYEE")
        self.assertEqual(response.data["user"]["department"], {"id": self.department.id, "name": "생산"})
        self.assertTrue(Token.objects.filter(key=response.data["token"], user=self.employee).exists())

    def test_login_success_default_admin(self):
        response = self.login("ADMIN", "ADMIN", "admin1234!")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "ADMIN")
        self.assertIsNone(response.data["user"]["department"])

    def test_login_failures_share_same_message(self):
        cases = [
            self.login(name="다른이름"),
            self.login(employee_no="X999"),
            self.login(password="wrong-password"),
        ]
        for response in cases:
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["code"], "login_failed")
            self.assertEqual(response.data["detail"], LOGIN_FAILED_MESSAGE)

    def test_login_inactive_user_fails(self):
        self.employee.is_active = False
        self.employee.save()
        response = self.login()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "login_failed")

    def test_login_missing_field_is_validation_error(self):
        response = self.client.post("/api/auth/login/", {"name": "홍길동"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("employee_no", response.data["errors"])

    def test_login_ignores_invalid_token_header(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid")
        self.assertEqual(self.login().status_code, 200)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "not_authenticated")

    def test_me_with_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "not_authenticated")

    def test_me_returns_current_user(self):
        token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "홍길동")

    def test_logout_deletes_token(self):
        token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertFalse(Token.objects.filter(key=token).exists())
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

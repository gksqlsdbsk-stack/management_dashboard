import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User

from .env import allowed_hosts, cors_origins, database_from_url, env_bool, env_list

BACKEND_DIR = Path(__file__).resolve().parent.parent


class EnvBoolTests(SimpleTestCase):
    def test_values(self):
        for raw in ("true", "True", "TRUE", "1", "yes", "on", " true "):
            self.assertTrue(env_bool({"X": raw}, "X", False), raw)
        for raw in ("false", "False", "0", "no", "off", ""):
            self.assertFalse(env_bool({"X": raw}, "X", True), raw)

    def test_default_when_missing(self):
        self.assertTrue(env_bool({}, "X", True))
        self.assertFalse(env_bool({}, "X", False))

    def test_invalid_value_fails_loudly(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "DEBUG"):
            env_bool({"DEBUG": "maybe"}, "DEBUG", True)


class EnvListTests(SimpleTestCase):
    def test_splits_and_trims(self):
        self.assertEqual(env_list({"X": " a.com , b.com,, "}, "X"), ["a.com", "b.com"])
        self.assertEqual(env_list({}, "X"), [])
        self.assertEqual(env_list({"X": ""}, "X"), [])

    def test_allowed_hosts_adds_render_hostname_once(self):
        self.assertEqual(allowed_hosts({}), [])
        self.assertEqual(allowed_hosts({"ALLOWED_HOSTS": "a.com"}), ["a.com"])
        self.assertEqual(allowed_hosts({"RENDER_EXTERNAL_HOSTNAME": "app.onrender.com"}), ["app.onrender.com"])
        self.assertEqual(
            allowed_hosts({"ALLOWED_HOSTS": "a.com,app.onrender.com", "RENDER_EXTERNAL_HOSTNAME": "app.onrender.com"}),
            ["a.com", "app.onrender.com"],
        )


class CorsOriginsTests(SimpleTestCase):
    def test_valid_origins_are_normalized(self):
        env = {"CORS_ALLOWED_ORIGINS": "https://app.onrender.com/, http://localhost:5173"}
        self.assertEqual(cors_origins(env), ["https://app.onrender.com", "http://localhost:5173"])
        self.assertEqual(cors_origins({}), [])

    def test_invalid_origins_fail_loudly(self):
        for bad in ("app.onrender.com", "ftp://app.com", "https://app.com/path", "https://", "*", "https://a.com?x=1"):
            with self.assertRaises(ImproperlyConfigured, msg=bad):
                cors_origins({"CORS_ALLOWED_ORIGINS": bad})


class DatabaseUrlTests(SimpleTestCase):
    def test_render_style_url(self):
        db = database_from_url("postgresql://dashboard_user:s3cret@dpg-abc123-a:5432/dashboard_db")
        self.assertEqual(db, {
            "ENGINE": "django.db.backends.postgresql", "NAME": "dashboard_db", "USER": "dashboard_user",
            "PASSWORD": "s3cret", "HOST": "dpg-abc123-a", "PORT": "5432",
        })

    def test_external_url_and_default_port_and_sslmode(self):
        db = database_from_url("postgres://u:p@dpg-abc123-a.oregon-postgres.render.com/dbname?sslmode=require")
        self.assertEqual((db["HOST"], db["PORT"], db["NAME"]), ("dpg-abc123-a.oregon-postgres.render.com", "5432", "dbname"))
        self.assertEqual(db["OPTIONS"], {"sslmode": "require"})
        self.assertNotIn("OPTIONS", database_from_url("postgresql://u:p@h/db"))

    def test_percent_encoded_credentials(self):
        db = database_from_url("postgresql://us%40er:p%40ss%2Fw%3Ard%23@host:6543/my%20db")
        self.assertEqual((db["USER"], db["PASSWORD"], db["PORT"], db["NAME"]), ("us@er", "p@ss/w:rd#", "6543", "my db"))

    def test_invalid_urls(self):
        for bad in ("mysql://u:p@h/db", "postgresql://u:p@h", "postgresql://u:p@h/", "postgresql:///db", "not a url", ""):
            with self.assertRaises(ImproperlyConfigured, msg=bad):
                database_from_url(bad)


SETTING_KEYS = ["DEBUG", "SECRET_KEY", "ALLOWED_HOSTS", "DATABASES", "CORS_ALLOWED_ORIGINS", "CORS_EXPOSE_HEADERS", "SECURE_PROXY_SSL_HEADER"]
MANAGED_ENV = ["DEBUG", "SECRET_KEY", "ALLOWED_HOSTS", "DATABASE_URL", "CORS_ALLOWED_ORIGINS", "RENDER_EXTERNAL_HOSTNAME",
               "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DEFAULT_ADMIN_PASSWORD"]


def load_settings(**overrides):
    """새 프로세스에서 settings 를 읽는다(환경변수 조합별 동작 확인용). 실패하면 (None, 오류 메시지)."""
    env = {k: v for k, v in os.environ.items() if k not in MANAGED_ENV}
    env.update(overrides, DJANGO_SETTINGS_MODULE="config.settings")
    code = (
        "import json; from django.conf import settings; "
        f"print(json.dumps({{k: getattr(settings, k, None) for k in {SETTING_KEYS!r}}}, default=list))"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return None, result.stderr
    return json.loads(result.stdout), ""


class SettingsEnvironmentTests(SimpleTestCase):
    def test_local_defaults_need_no_environment(self):
        s, error = load_settings()
        self.assertIsNotNone(s, error)
        self.assertTrue(s["DEBUG"])
        self.assertTrue(s["SECRET_KEY"].startswith("django-insecure-"))
        self.assertEqual(s["ALLOWED_HOSTS"], [])
        self.assertEqual(s["CORS_ALLOWED_ORIGINS"], [])
        self.assertIsNone(s["SECURE_PROXY_SSL_HEADER"])
        self.assertEqual(s["DATABASES"]["default"]["NAME"], "management_dashboard")
        self.assertEqual(s["DATABASES"]["default"]["HOST"], "localhost")

    def test_db_variables_still_work(self):
        s, _ = load_settings(DB_NAME="other", DB_HOST="db.local", DB_PORT="6000", DB_USER="me", DB_PASSWORD="pw")
        db = s["DATABASES"]["default"]
        self.assertEqual((db["NAME"], db["HOST"], db["PORT"], db["USER"], db["PASSWORD"]), ("other", "db.local", "6000", "me", "pw"))

    def test_database_url_takes_precedence(self):
        s, error = load_settings(DATABASE_URL="postgresql://u:p@dpg-x:5432/prod", DB_NAME="ignored")
        self.assertIsNotNone(s, error)
        db = s["DATABASES"]["default"]
        self.assertEqual((db["NAME"], db["HOST"], db["USER"], db["PASSWORD"]), ("prod", "dpg-x", "u", "p"))

    def test_production_requires_secret_key(self):
        s, error = load_settings(DEBUG="false", ALLOWED_HOSTS="a.com")
        self.assertIsNone(s)
        self.assertIn("SECRET_KEY", error)
        self.assertIn("ImproperlyConfigured", error)

    def test_production_requires_allowed_hosts(self):
        s, error = load_settings(DEBUG="false", SECRET_KEY="x" * 50)
        self.assertIsNone(s)
        self.assertIn("ALLOWED_HOSTS", error)

    def test_render_hostname_satisfies_allowed_hosts(self):
        s, error = load_settings(DEBUG="false", SECRET_KEY="k" * 50, RENDER_EXTERNAL_HOSTNAME="api.onrender.com")
        self.assertIsNotNone(s, error)
        self.assertFalse(s["DEBUG"])
        self.assertEqual(s["SECRET_KEY"], "k" * 50)
        self.assertEqual(s["ALLOWED_HOSTS"], ["api.onrender.com"])
        self.assertEqual(s["SECURE_PROXY_SSL_HEADER"], ["HTTP_X_FORWARDED_PROTO", "https"])

    def test_cors_origins_and_exposed_headers(self):
        s, error = load_settings(CORS_ALLOWED_ORIGINS="https://web.onrender.com/,http://localhost:5173")
        self.assertIsNotNone(s, error)
        self.assertEqual(s["CORS_ALLOWED_ORIGINS"], ["https://web.onrender.com", "http://localhost:5173"])
        self.assertEqual(s["CORS_EXPOSE_HEADERS"], ["Content-Disposition"])

    def test_invalid_values_stop_startup(self):
        for overrides, fragment in (
            ({"DEBUG": "maybe"}, "DEBUG"),
            ({"CORS_ALLOWED_ORIGINS": "web.onrender.com"}, "CORS_ALLOWED_ORIGINS"),
            ({"DATABASE_URL": "mysql://u:p@h/db"}, "DATABASE_URL"),
        ):
            s, error = load_settings(**overrides)
            self.assertIsNone(s, overrides)
            self.assertIn(fragment, error)


PROD_ORIGIN = "https://web.onrender.com"


@override_settings(CORS_ALLOWED_ORIGINS=[PROD_ORIGIN])
class CorsBehaviourTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.client = APIClient()

    def preflight(self, origin, method="PUT", headers="authorization,content-type"):
        return self.client.options(
            "/api/goals/2026/", HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD=method,
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=headers,
        )

    def test_preflight_from_the_frontend_origin_is_allowed(self):
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            response = self.preflight(PROD_ORIGIN, method)
            self.assertEqual(response.status_code, 200, method)
            self.assertEqual(response["Access-Control-Allow-Origin"], PROD_ORIGIN)
            self.assertIn(method, response["Access-Control-Allow-Methods"])
            self.assertIn("authorization", response["Access-Control-Allow-Headers"])
            self.assertIn("content-type", response["Access-Control-Allow-Headers"])

    def test_preflight_from_another_origin_gets_no_cors_headers(self):
        response = self.preflight("https://evil.example.com")
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_actual_request_carries_the_allow_origin_header(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/auth/me/", HTTP_ORIGIN=PROD_ORIGIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], PROD_ORIGIN)
        self.assertNotIn("Access-Control-Allow-Credentials", response)  # 토큰 헤더 인증이라 쿠키 자격 증명은 필요 없다

    def test_error_responses_also_carry_cors_headers(self):
        response = self.client.get("/api/auth/me/", HTTP_ORIGIN=PROD_ORIGIN)  # 미인증 401
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Access-Control-Allow-Origin"], PROD_ORIGIN)

    def test_login_from_the_frontend_origin(self):
        response = self.client.post(
            "/api/auth/login/", {"name": "대표", "employee_no": "A001", "password": "password1"}, format="json", HTTP_ORIGIN=PROD_ORIGIN,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], PROD_ORIGIN)

    def test_csv_filename_header_is_exposed_to_the_frontend(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/dashboard/export/?year=2020&month=1", HTTP_ORIGIN=PROD_ORIGIN)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Content-Disposition", response["Access-Control-Expose-Headers"])
        self.assertIn("attachment", response["Content-Disposition"])

    def test_same_origin_requests_have_no_cors_headers(self):
        self.client.force_authenticate(user=self.admin)
        self.assertNotIn("Access-Control-Allow-Origin", self.client.get("/api/auth/me/"))


class NoCorsByDefaultTests(TestCase):
    """개발(Vite 프록시)에서는 CORS 오리진을 설정하지 않으므로 어떤 오리진에도 CORS 헤더가 붙지 않는다."""

    def test_no_origin_is_allowed_without_configuration(self):
        response = APIClient().options(
            "/api/auth/login/", HTTP_ORIGIN=PROD_ORIGIN, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertNotIn("Access-Control-Allow-Origin", response)


class DefaultAdminPasswordTests(TestCase):
    def test_environment_variable_sets_the_initial_password(self):
        from accounts.services import ensure_default_admin

        with mock.patch.dict(os.environ, {"DEFAULT_ADMIN_PASSWORD": "Str0ng-Prod-Pass!"}):
            admin = ensure_default_admin()
        self.assertTrue(admin.check_password("Str0ng-Prod-Pass!"))
        self.assertFalse(admin.check_password("admin1234!"))

    def test_falls_back_to_the_documented_default(self):
        from accounts.services import ensure_default_admin

        for value in (None, ""):
            User.objects.all().delete()
            env = {} if value is None else {"DEFAULT_ADMIN_PASSWORD": value}
            with mock.patch.dict(os.environ, env):
                if value is None:
                    os.environ.pop("DEFAULT_ADMIN_PASSWORD", None)
                admin = ensure_default_admin()
            self.assertTrue(admin.check_password("admin1234!"))

    def test_existing_admin_is_not_touched(self):
        from accounts.services import ensure_default_admin

        existing = User.objects.create_user(username="A001", password="keep-me-123", name="대표", role=User.Role.ADMIN)
        with mock.patch.dict(os.environ, {"DEFAULT_ADMIN_PASSWORD": "another-pass-1"}):
            self.assertIsNone(ensure_default_admin())
        existing.refresh_from_db()
        self.assertTrue(existing.check_password("keep-me-123"))
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 1)

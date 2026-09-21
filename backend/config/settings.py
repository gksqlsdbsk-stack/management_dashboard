"""Django 설정. 로컬 개발은 환경변수 없이 동작하고, 운영(Render)은 환경변수로 바꾼다 [A-40, A-52].

환경변수: DEBUG, SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL(또는 DB_*), CORS_ALLOWED_ORIGINS,
DEFAULT_ADMIN_PASSWORD(accounts). 자세한 내용은 README의 “Render 배포”.
"""

import getpass
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .env import allowed_hosts, cors_origins, database_from_url, env_bool

BASE_DIR = Path(__file__).resolve().parent.parent

# 기본값 true = 로컬 개발. 운영은 반드시 DEBUG=false [A-52]
DEBUG = env_bool(os.environ, "DEBUG", default=True)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DEBUG=false에서는 SECRET_KEY 환경변수가 필요합니다.")
    SECRET_KEY = "django-insecure-f@h+*7&-=p#k&_-bk=-5hfqej5i0%fcxx!emkdu$mv(!!k@c$s"  # 로컬 개발용

ALLOWED_HOSTS = allowed_hosts(os.environ)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DEBUG=false에서는 ALLOWED_HOSTS 환경변수가 필요합니다.")

# Django admin 사이트는 사용하지 않는다 [02 §2.1]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "organization",
    "reports",
    "goals",
    "analytics",
]

# 토큰 인증만 쓰므로 세션·CSRF 미들웨어는 두지 않는다 [A-12]. CorsMiddleware는 응답을 만들 수 있는 미들웨어보다 앞에 둔다
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": database_from_url(os.environ["DATABASE_URL"])}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "management_dashboard"),
            "USER": os.environ.get("DB_USER", getpass.getuser()),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

AUTH_USER_MODEL = "accounts.User"

# 비밀번호 검증은 서버 시리얼라이저에서 8자 이상만 확인한다 [A-14]
AUTH_PASSWORD_VALIDATORS = []

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}

# 운영: 프런트(Static Site)는 다른 오리진이라 CORS를 허용한다. 개발은 Vite 프록시를 쓰므로 비어 있다 [A-39, A-52].
# 인증은 Authorization 헤더(토큰)라 쿠키 자격 증명은 허용하지 않는다. 프런트가 CSV 파일명을 읽도록 헤더를 노출한다.
CORS_ALLOWED_ORIGINS = cors_origins(os.environ)
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

# Render 같은 프록시 뒤에서 HTTPS 요청임을 알 수 있게 한다. TLS 종료와 리다이렉트는 프록시가 한다 [A-52]
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# DEBUG=false에서는 Django 기본 설정이 예외를 콘솔에 남기지 않으므로 Render 로그에 보이도록 콘솔 로깅을 둔다
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

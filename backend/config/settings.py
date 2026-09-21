"""Django 설정. DB 접속 정보는 환경변수로 받는다 [A-40]."""

import getpass
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# PoC 개발용 키. 배포는 범위 밖이다.
SECRET_KEY = "django-insecure-f@h+*7&-=p#k&_-bk=-5hfqej5i0%fcxx!emkdu$mv(!!k@c$s"

DEBUG = True

ALLOWED_HOSTS = []

# Django admin 사이트는 사용하지 않는다 [02 §2.1]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "organization",
    "reports",
    "goals",
    "analytics",
]

# 토큰 인증만 쓰므로 세션·CSRF 미들웨어는 두지 않는다 [A-12]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

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

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

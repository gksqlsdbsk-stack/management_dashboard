import sys
import warnings

from django.apps import AppConfig
from django.db import DatabaseError

# DB 스키마를 만들거나 바꾸는 명령·테스트 중에는 기본 관리자를 만들지 않는다.
SKIP_COMMANDS = {"migrate", "makemigrations", "test"}


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        if len(sys.argv) > 1 and sys.argv[1] in SKIP_COMMANDS:
            return
        from .services import ensure_default_admin

        try:
            # 명세가 앱 시작 시 생성을 요구하므로 ready()에서 DB에 접근한다 [A-13]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                ensure_default_admin()
        except DatabaseError:
            # DB·마이그레이션 미준비 시 건너뛴다
            pass

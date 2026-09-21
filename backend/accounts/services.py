import logging

from .models import User

logger = logging.getLogger(__name__)

# 기본 관리자 [A-13]
DEFAULT_ADMIN_NAME = "ADMIN"
DEFAULT_ADMIN_EMPLOYEE_NO = "ADMIN"
DEFAULT_ADMIN_PASSWORD = "admin1234!"


def ensure_default_admin():
    """관리자가 1명도 없으면 기본 관리자를 만든다. 여러 번 호출해도 중복 생성되지 않는다."""
    if User.objects.filter(role=User.Role.ADMIN).exists():
        return None
    if User.objects.filter(username=DEFAULT_ADMIN_EMPLOYEE_NO).exists():
        logger.warning("사번 '%s' 사용자가 이미 있어 기본 관리자를 만들지 않았습니다.", DEFAULT_ADMIN_EMPLOYEE_NO)
        return None
    return User.objects.create_user(
        username=DEFAULT_ADMIN_EMPLOYEE_NO,
        password=DEFAULT_ADMIN_PASSWORD,
        name=DEFAULT_ADMIN_NAME,
        role=User.Role.ADMIN,
    )

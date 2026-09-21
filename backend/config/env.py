"""환경변수 읽기 도우미 [A-52]. settings.py에서 쓰고 단위 테스트한다.

`environ`(보통 os.environ)을 인자로 받아 전역 상태 없이 테스트할 수 있다.
"""

from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def env_bool(environ, name, default):
    """`true/false`(대소문자 무관), `1/0`, `yes/no`, `on/off`. 값이 없으면 default."""
    raw = environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ImproperlyConfigured(f"{name} 값은 true 또는 false여야 합니다. (현재: {raw!r})")


def env_list(environ, name):
    """쉼표로 구분한 값 목록. 앞뒤 공백과 빈 항목은 버린다."""
    return [item.strip() for item in environ.get(name, "").split(",") if item.strip()]


def allowed_hosts(environ):
    """`ALLOWED_HOSTS` + Render가 주는 `RENDER_EXTERNAL_HOSTNAME`(중복 없이)."""
    hosts = env_list(environ, "ALLOWED_HOSTS")
    render_host = environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_host and render_host not in hosts:
        hosts.append(render_host)
    return hosts


def cors_origins(environ):
    """`CORS_ALLOWED_ORIGINS`. 오리진은 `https://호스트[:포트]` 형태이며 끝의 `/`는 제거한다."""
    origins = []
    for origin in env_list(environ, "CORS_ALLOWED_ORIGINS"):
        origin = origin.rstrip("/")
        parsed = urlparse(origin)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path or parsed.query:
            raise ImproperlyConfigured(
                f"CORS_ALLOWED_ORIGINS의 '{origin}'은(는) 올바른 오리진이 아닙니다. 예: https://example.onrender.com"
            )
        origins.append(origin)
    return origins


def database_from_url(url):
    """`postgresql://사용자:비밀번호@호스트:포트/DB이름[?sslmode=…]` → Django DATABASES 항목."""
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured("DATABASE_URL은 postgres:// 또는 postgresql:// 로 시작해야 합니다.")
    name = parsed.path.lstrip("/")
    if not name or not parsed.hostname:
        raise ImproperlyConfigured("DATABASE_URL에 호스트와 DB 이름이 있어야 합니다.")
    database = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(name),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(parsed.port or 5432),
    }
    sslmode = parse_qs(parsed.query).get("sslmode")
    if sslmode:
        database["OPTIONS"] = {"sslmode": sslmode[0]}
    return database

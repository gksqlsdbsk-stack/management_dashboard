from decimal import Decimal

MAX_YEAR = 32767  # 연도를 담는 PositiveSmallIntegerField 상한


def to_number(value):
    """Decimal → JSON number. 정수면 정수로, 아니면 소수로 낸다. None은 그대로."""
    if value is None:
        return None
    value = Decimal(value)
    return int(value) if value == value.to_integral_value() else float(value)

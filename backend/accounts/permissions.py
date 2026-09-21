from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    """관리자(ADMIN)만 허용한다 [03 §1.2]."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)


class IsEmployee(BasePermission):
    """직원(EMPLOYEE)만 허용한다 [03 §1.2]."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.EMPLOYEE)

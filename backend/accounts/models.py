from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """사번은 username에 저장한다 [A-10]. first_name/last_name/email 등은 사용하지 않는다."""

    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "직원"
        ADMIN = "ADMIN", "관리자"

    name = models.CharField(max_length=50)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.ForeignKey(
        "organization.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    def __str__(self):
        return f"{self.name}({self.username})"

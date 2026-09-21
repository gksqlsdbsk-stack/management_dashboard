from django.db import models
from django.db.models import Q

from .metric_keys import METRIC_KEY_CHOICES


class Department(models.Model):
    name = models.CharField(max_length=50)
    input_guide = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(is_active=True),
                name="unique_active_department_name",
            ),
        ]

    def __str__(self):
        return self.name


class InputItem(models.Model):
    class Scope(models.TextChoices):
        MONTHLY = "MONTHLY", "월 합계형"
        PROJECT = "PROJECT", "프로젝트별형"

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=100)
    scope = models.CharField(max_length=10, choices=Scope.choices)
    unit = models.CharField(max_length=20, blank=True)
    metric_key = models.CharField(max_length=30, choices=METRIC_KEY_CHOICES, null=True, blank=True)
    help_text = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                condition=Q(is_active=True),
                name="unique_active_item_name_per_department",
            ),
        ]

    def __str__(self):
        return f"{self.department.name} - {self.name}"

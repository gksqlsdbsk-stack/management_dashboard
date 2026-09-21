from django.conf import settings
from django.db import models
from django.db.models import Q


class MonthlyReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "작성 중"
        SUBMITTED = "SUBMITTED", "제출 완료"

    department = models.ForeignKey("organization.Department", on_delete=models.PROTECT, related_name="reports")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # 같은 부서·같은 월은 1건만 [A-18]
            models.UniqueConstraint(fields=["department", "year", "month"], name="unique_report_per_department_month"),
            models.CheckConstraint(condition=Q(month__gte=1, month__lte=12), name="report_month_between_1_and_12"),
        ]

    def __str__(self):
        return f"{self.department.name} {self.year}-{self.month:02d} ({self.status})"


class ReportValue(models.Model):
    report = models.ForeignKey(MonthlyReport, on_delete=models.CASCADE, related_name="values")
    item = models.ForeignKey("organization.InputItem", on_delete=models.PROTECT, related_name="report_values")
    # PROJECT 범위 항목만 값을 가진다. MONTHLY는 빈 문자열 [A-04]
    project_name = models.CharField(max_length=100, default="", blank=True)
    value = models.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["report", "item", "project_name"], name="unique_value_per_report_item_project"),
        ]

    def __str__(self):
        return f"{self.item.name} {self.project_name} {self.value}".replace("  ", " ")

from django.db import models

from .keys import GOAL_METRIC_CHOICES


class AnnualGoal(models.Model):
    """연도별·지표별 목표값. 금액=원, 비율=%, 수량=개 [A-35]. 다른 테이블과 FK 없음."""

    year = models.PositiveSmallIntegerField()
    metric_key = models.CharField(max_length=30, choices=GOAL_METRIC_CHOICES)
    target_value = models.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["year", "metric_key"], name="unique_goal_per_year_metric"),
        ]

    def __str__(self):
        return f"{self.year} {self.metric_key} {self.target_value}"

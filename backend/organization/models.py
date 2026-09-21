from django.db import models
from django.db.models import Q


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

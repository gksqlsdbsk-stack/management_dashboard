from rest_framework import serializers

from .models import Department, InputItem


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "input_guide", "sort_order"]

    def validate_name(self, value):
        # 활성 부서 사이에서만 이름 중복을 막는다 [A-06]
        duplicates = Department.objects.filter(name=value, is_active=True)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("같은 이름의 부서가 이미 있습니다.")
        return value


class InputItemSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = InputItem
        fields = [
            "id", "department", "name", "scope", "unit", "metric_key",
            "help_text", "is_required", "sort_order",
        ]

    def validate_name(self, value):
        department = self.context.get("department") or self.instance.department
        duplicates = InputItem.objects.filter(department=department, name=value, is_active=True)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("같은 부서에 같은 이름의 입력 항목이 이미 있습니다.")
        return value

    def validate_metric_key(self, value):
        return value or None

    def validate_scope(self, value):
        # 이미 값이 입력된 항목은 범위를 바꾸면 기존 데이터 해석이 깨진다 [A-04]
        if self.instance and value != self.instance.scope and self.instance.report_values.exists():
            raise serializers.ValidationError("이미 입력된 값이 있는 항목은 범위를 바꿀 수 없습니다.")
        return value

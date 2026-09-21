from rest_framework import serializers

from .models import User


class LoginSerializer(serializers.Serializer):
    name = serializers.CharField()
    employee_no = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class CurrentUserSerializer(serializers.ModelSerializer):
    employee_no = serializers.CharField(source="username")
    department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "employee_no", "role", "department"]

    def get_department(self, user):
        if user.department is None:
            return None
        return {"id": user.department.id, "name": user.department.name}

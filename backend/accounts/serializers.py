from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from organization.models import Department

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


class UserSerializer(serializers.ModelSerializer):
    """사용자 관리(관리자)용. 읽기는 `department`, 쓰기는 `department_id`를 쓴다 [03 §3]."""

    employee_no = serializers.CharField(
        source="username",
        max_length=150,
        validators=[UniqueValidator(queryset=User.objects.all(), message="이미 사용 중인 사번입니다.")],
    )
    department = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
        error_messages={"does_not_exist": "존재하지 않는 부서입니다.", "incorrect_type": "부서 값이 올바르지 않습니다."},
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8,
        trim_whitespace=False,
        error_messages={"min_length": "비밀번호는 8자 이상이어야 합니다.", "blank": "비밀번호를 입력해 주세요."},
    )

    class Meta:
        model = User
        fields = ["id", "name", "employee_no", "role", "department", "department_id", "is_active", "password"]

    def get_department(self, user):
        if user.department is None:
            return None
        return {"id": user.department.id, "name": user.department.name}

    def validate(self, attrs):
        role = attrs.get("role", self.instance.role if self.instance else User.Role.EMPLOYEE)
        department = attrs["department"] if "department" in attrs else (
            self.instance.department if self.instance else None
        )
        if role == User.Role.EMPLOYEE and department is None:
            raise serializers.ValidationError({"department_id": ["직원은 소속 부서가 필요합니다."]})
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": ["비밀번호를 입력해 주세요."]})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:  # 비밀번호 재설정 [A-14]
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance

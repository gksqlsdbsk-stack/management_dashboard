from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from config.exceptions import ApiError

from .metric_keys import METRIC_KEYS
from .models import Department, InputItem
from .serializers import DepartmentSerializer, InputItemSerializer


class DepartmentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DepartmentSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        # 목록만 로그인한 누구나, 나머지는 관리자 [03 §4]
        if self.action == "list":
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        queryset = Department.objects.filter(is_active=True)
        user = self.request.user
        if self.action == "list" and user.role != get_user_model().Role.ADMIN:
            queryset = queryset.filter(pk=user.department_id)  # 직원은 본인 부서만
        return queryset

    def perform_destroy(self, instance):
        User = get_user_model()
        if User.objects.filter(department=instance, is_active=True).exists():
            raise ApiError(
                status.HTTP_409_CONFLICT,
                "department_in_use",
                "소속 사용자가 있는 부서는 삭제할 수 없습니다. 먼저 다른 부서로 재배정하세요.",
            )
        # 논리 삭제: 과거 제출 데이터는 유지된다 [A-06]
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["get", "post"], url_path="items")
    def items(self, request, pk=None):
        department = self.get_object()
        if request.method == "GET":
            queryset = department.items.filter(is_active=True)
            return Response(InputItemSerializer(queryset, many=True).data)

        serializer = InputItemSerializer(data=request.data, context={"department": department})
        serializer.is_valid(raise_exception=True)
        serializer.save(department=department)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InputItemViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = InputItemSerializer
    queryset = InputItem.objects.filter(is_active=True).select_related("department")
    http_method_names = ["patch", "delete", "head", "options"]

    def perform_destroy(self, instance):
        # 논리 삭제 [A-06]
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class MetricKeyListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(
            [
                {"key": key, "label": label, "unit": unit, "aggregation": aggregation}
                for key, label, unit, aggregation in METRIC_KEYS
            ]
        )

from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import ApiError

from .models import User
from .permissions import IsAdmin
from .serializers import CurrentUserSerializer, LoginSerializer, UserSerializer

LOGIN_FAILED_MESSAGE = "성명, 사번 또는 비밀번호가 올바르지 않습니다."


class LoginView(APIView):
    # 잘못된 토큰 헤더가 로그인을 막지 않도록 인증을 끈다
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(
            username=data["employee_no"], name=data["name"], is_active=True
        ).select_related("department").first()
        # 어느 값이 틀렸는지 알려주지 않는다 [A-10]
        if user is None or not user.check_password(data["password"]):
            raise ApiError(status.HTTP_400_BAD_REQUEST, "login_failed", LOGIN_FAILED_MESSAGE)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": CurrentUserSerializer(user).data})


class LogoutView(APIView):
    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


class UserViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdmin]
    serializer_class = UserSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = User.objects.select_related("department").order_by("id")
        department = self.request.query_params.get("department")
        if self.action == "list" and department:
            if not department.isdigit():
                raise ApiError(status.HTTP_400_BAD_REQUEST, "validation_error", "부서 값이 올바르지 않습니다.")
            queryset = queryset.filter(department_id=department)
        return queryset

    def perform_destroy(self, instance):
        # 자기 자신과 마지막 관리자는 삭제할 수 없다 [A-15]
        if instance.pk == self.request.user.pk:
            raise ApiError(status.HTTP_409_CONFLICT, "cannot_delete_user", "본인 계정은 삭제할 수 없습니다.")
        if instance.role == User.Role.ADMIN and User.objects.filter(role=User.Role.ADMIN).count() <= 1:
            raise ApiError(status.HTTP_409_CONFLICT, "cannot_delete_user", "마지막 관리자는 삭제할 수 없습니다.")
        instance.delete()

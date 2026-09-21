"""오류 응답을 {code, detail, errors} 형식으로 통일한다 [03 §1.1]."""

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ApiError(exceptions.APIException):
    """명세의 `code`를 가진 오류. 예: ApiError(409, "report_locked", "제출된 보고서입니다.")"""

    def __init__(self, status_code, code, detail, errors=None):
        self.status_code = status_code
        self.code = code
        self.errors = errors
        super().__init__(detail=detail, code=code)


def _body(code, detail, errors=None):
    body = {"code": code, "detail": str(detail)}
    if errors is not None:
        body["errors"] = errors
    return body


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ApiError):
        return Response(_body(exc.code, exc.detail, exc.errors), status=exc.status_code)
    if isinstance(exc, exceptions.ValidationError):
        errors = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
        return Response(
            _body("validation_error", "입력값이 올바르지 않습니다.", errors),
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return Response(_body("not_authenticated", "인증이 필요합니다."), status=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, exceptions.PermissionDenied):
        return Response(_body("forbidden", "권한이 없습니다."), status=status.HTTP_403_FORBIDDEN)
    if isinstance(exc, exceptions.NotFound):
        return Response(_body("not_found", "대상을 찾을 수 없습니다."), status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, exceptions.ParseError):
        return Response(_body("validation_error", "요청 형식이 올바르지 않습니다."), status=status.HTTP_400_BAD_REQUEST)

    return Response(_body(exc.default_code, exc.detail), status=response.status_code)

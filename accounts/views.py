from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User, VerificationCode
from accounts.serializers import (
    UserRegisterSerializer,
    VerifyEmailSerializer,
    CustomTokenObtainPairSerializer,
    UserPublicSerializer,
    GoogleLoginSerializer,
)
from accounts.permissions import IsAdmin
from accounts.utils.code_generator import generate_verification_code
from accounts.utils.send_email import send_verification_email


# ===============================
# Helper: Generate JWT + user payload
# ===============================
def get_jwt_user_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": UserPublicSerializer(user).data,
    }


# ===============================
# User ViewSet
# ===============================
class UserViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
    - POST /api/accounts/users/           → Register
    - GET  /api/accounts/users/           → List users (admin)
    - GET  /api/accounts/users/profile/   → Logged-in profile
    - POST /api/accounts/users/verify_email/ → Activate account
    """

    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        if self.action == "list":
            return [IsAdmin()]
        return super().get_permissions()

    # List users (admin only)
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().only(
            "id", "full_name", "email", "role", "created_at"
        )
        serializer = UserPublicSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Logged-in user profile
    @action(detail=False, methods=["get"])
    def profile(self, request):
        serializer = UserPublicSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Register user → unified JWT response
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(get_jwt_user_response(user), status=status.HTTP_201_CREATED)

    # Email verification
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def verify_email(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        verification = serializer.validated_data["verification"]

        user.is_active = True
        user.save()

        verification.is_used = True
        verification.save()

        return Response(
            {"message": "Account activated successfully"},
            status=status.HTTP_200_OK,
        )


# ===============================
# JWT Login View
# ===============================
class LoginViewSet(TokenObtainPairView):
    """
    POST /api/accounts/login/
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


# ===============================
# Google Login View
# ===============================
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user_instance"]  # GoogleLoginSerializer returns user
        return Response(get_jwt_user_response(user), status=status.HTTP_200_OK)

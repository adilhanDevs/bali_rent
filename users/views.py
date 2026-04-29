from rest_framework import viewsets, permissions, generics, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User, UserProfile
from .serializers import (
    UserSerializer, UserProfileSerializer, UserRegistrationSerializer, 
    ProfileSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer
)
from bali_rent.permissions import IsOwnerOrAdmin
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

# Admin ViewSets
from audit.mixins import AuditMixin

class UserViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related('profile').order_by('-id')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            from django.forms.models import model_to_dict
            before_dict = model_to_dict(request.user)
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            self._log_audit(instance, 'update', before_dict=before_dict, after_dict=model_to_dict(instance))
            return Response(serializer.data)

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

from rest_framework import throttling


class LoginView(TokenObtainPairView):
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = 'login'

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = 'register'

class LogoutView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # In a real app, send email here. For Phase 1, we just return success.
        return Response({"detail": "Password reset email has been sent."}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # In a real app, verify token/uid and change password here.
        return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)

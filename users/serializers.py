from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from .models import User, UserProfile, UserDevice, SocialAccount
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from bookings.serializers import BookingSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

PROFILE_LANGUAGE_CHOICES = {'en', 'ru', 'zh', 'id', 'de', 'fr'}
PROFILE_CURRENCY_CHOICES = {'USD', 'RUB', 'EUR', 'CNY', 'AUD'}
ADMIN_PERMISSION_CHOICES = {
    'overview',
    'bookings',
    'fleet',
    'calendar',
    'crm',
    'analytics',
    'support',
    'news',
    'addons',
    'categories',
    'locations',
    'site',
    'promocodes',
    'team',
}


def default_admin_permissions_for_role(role):
    normalized_role = (role or 'client').strip().lower()
    if normalized_role == 'admin':
        return sorted(ADMIN_PERMISSION_CHOICES)
    if normalized_role == 'manager':
        return [
            'overview',
            'bookings',
            'fleet',
            'calendar',
            'crm',
            'analytics',
            'support',
            'news',
            'addons',
            'categories',
            'locations',
            'site',
            'promocodes',
        ]
    if normalized_role == 'staff':
        return ['overview', 'bookings', 'calendar', 'support']
    return []

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('country', 'preferred_language', 'preferred_currency', 'avatar', 'marketing_accepted')

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'role', 'admin_permissions', 'is_active', 'is_staff', 'is_superuser', 'profile', 'created_at')
        read_only_fields = ('role', 'admin_permissions', 'is_active', 'is_staff', 'is_superuser', 'created_at')

class AdminUserSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, validators=[validate_password])

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('password',)
        read_only_fields = ('created_at',)

    def validate_email(self, value):
        normalized = value.strip().lower()
        queryset = User.objects.filter(email=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_phone(self, value):
        if not value:
            return value
        queryset = User.objects.filter(phone=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_admin_permissions(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Admin permissions must be a list.")

        normalized = []
        for permission in value:
            code = str(permission or '').strip().lower()
            if not code:
                continue
            if code not in ADMIN_PERMISSION_CHOICES:
                raise serializers.ValidationError(f"Unsupported admin permission: {code}")
            if code not in normalized:
                normalized.append(code)
        return normalized

    def _apply_role_flags(self, instance, role):
        normalized_role = (role or instance.role or 'client').strip().lower()
        instance.role = normalized_role
        instance.is_staff = normalized_role in {'admin', 'manager', 'staff'}
        instance.is_superuser = normalized_role == 'admin'

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        email = validated_data.get('email', '').strip().lower()
        admin_permissions = validated_data.pop('admin_permissions', None)
        validated_data['email'] = email
        validated_data['username'] = validated_data.get('username') or email

        user = User(**validated_data)
        self._apply_role_flags(user, validated_data.get('role'))
        user.admin_permissions = admin_permissions if admin_permissions is not None else default_admin_permissions_for_role(user.role)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        UserProfile.objects.get_or_create(user=user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        admin_permissions = validated_data.pop('admin_permissions', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        self._apply_role_flags(instance, validated_data.get('role'))
        if admin_permissions is not None:
            instance.admin_permissions = admin_permissions
        elif not instance.admin_permissions and instance.is_staff:
            instance.admin_permissions = default_admin_permissions_for_role(instance.role)
        if password:
            instance.set_password(password)
        instance.save()
        UserProfile.objects.get_or_create(user=instance)
        return instance

class ProfileSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='profile.country', allow_blank=True)
    language = serializers.CharField(source='profile.preferred_language')
    currency = serializers.CharField(source='profile.preferred_currency')
    avatar = serializers.ImageField(source='profile.avatar', read_only=True)
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)
    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'phone', 'role', 'is_staff', 'is_superuser', 'country', 'language', 'currency', 'avatar', 'created_at', 'bookings')
        read_only_fields = ('id', 'email', 'role', 'is_staff', 'is_superuser', 'avatar', 'created_at')

    def validate_language(self, value):
        normalized = value.strip().lower()
        if normalized not in PROFILE_LANGUAGE_CHOICES:
            raise serializers.ValidationError('Unsupported language.')
        return normalized

    def validate_currency(self, value):
        normalized = value.strip().upper()
        if normalized not in PROFILE_CURRENCY_CHOICES:
            raise serializers.ValidationError('Unsupported currency.')
        return normalized

    def update(self, instance, validated_data):
        # User fields
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()

        # Profile fields (mapped via source='profile.xxx')
        profile_data = validated_data.get('profile', {})
        profile = instance.profile
        profile.country = profile_data.get('country', profile.country)
        profile.preferred_language = profile_data.get('preferred_language', profile.preferred_language)
        profile.preferred_currency = profile_data.get('preferred_currency', profile.preferred_currency)
        profile.save()

        return instance

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    language = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'phone', 'language')

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_phone(self, value):
        if value and User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        language = validated_data.pop('language', '').strip().lower()
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            phone=validated_data.get('phone', '')
        )
        # Create profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if language:
            profile.preferred_language = language
            profile.save(update_fields=['preferred_language'])
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    default_error_messages = {
        'no_active_account': 'Unable to sign in with these credentials.',
    }

    def validate(self, attrs):
        email = str(attrs.get(self.username_field, '')).strip().lower()
        password = attrs.get('password') or ''

        if not email:
            raise serializers.ValidationError({'email': ['Enter your email address.']})
        if not password:
            raise serializers.ValidationError({'password': ['Enter your password.']})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed({'email': ['No account was found with this email address.']}) from exc

        if not user.is_active:
            raise AuthenticationFailed({'email': ['This account is inactive.']})
        if not user.check_password(password):
            raise AuthenticationFailed({'password': ['Incorrect password. Please try again.']})

        data = super().validate({self.username_field: email, 'password': password})
        data['user'] = UserSerializer(user).data
        return data

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        normalized = value.strip().lower()
        try:
            user = User.objects.get(email=normalized)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("No account was found with this email address.") from exc

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        self.user = user
        return normalized

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    token = serializers.CharField()
    uid = serializers.CharField()

    def validate(self, attrs):
        uid = attrs.get('uid', '')
        token = attrs.get('token', '')

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as exc:
            raise serializers.ValidationError({'uid': ['Password reset link is invalid or has expired.']}) from exc

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({'token': ['Password reset link is invalid or has expired.']})

        self.user = user
        return attrs

    def save(self, **kwargs):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save(update_fields=['password'])
        return self.user

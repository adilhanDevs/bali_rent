from rest_framework import serializers
from .models import User, UserProfile, UserDevice, SocialAccount
from django.contrib.auth.password_validation import validate_password
from bookings.serializers import BookingSerializer

PROFILE_LANGUAGE_CHOICES = {'en', 'ru', 'zh', 'id', 'de', 'fr'}
PROFILE_CURRENCY_CHOICES = {'USD', 'RUB', 'EUR', 'CNY', 'AUD'}

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('country', 'preferred_language', 'preferred_currency', 'avatar', 'marketing_accepted')

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'role', 'is_active', 'is_staff', 'is_superuser', 'profile', 'created_at')
        read_only_fields = ('role', 'is_active', 'is_staff', 'is_superuser', 'created_at')

class AdminUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = ('created_at',)

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
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

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

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    token = serializers.CharField()
    uid = serializers.CharField()

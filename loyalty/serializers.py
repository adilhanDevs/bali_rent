from rest_framework import serializers

from users.models import User

from .models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
    ReferralCode,
)


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'role')
        read_only_fields = fields


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = ('id', 'name', 'is_active')


class LoyaltyTierSerializer(serializers.ModelSerializer):
    program = LoyaltyProgramSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(source='program', queryset=LoyaltyProgram.objects.all(), write_only=True)

    class Meta:
        model = LoyaltyTier
        fields = ('id', 'program', 'program_id', 'name', 'min_points', 'discount_percent')
        read_only_fields = ('id', 'program')

    def validate_min_points(self, value):
        if value < 0:
            raise serializers.ValidationError('Minimum points must be greater than or equal to 0.')
        return value

    def validate_discount_percent(self, value):
        if value < 0:
            raise serializers.ValidationError('Discount percent must be greater than or equal to 0.')
        return value


class LoyaltyTierNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyTier
        fields = ('id', 'name', 'min_points', 'discount_percent')
        read_only_fields = fields


class CustomerLoyaltyAccountSerializer(serializers.ModelSerializer):
    customer = UserSummarySerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(source='customer', queryset=User.objects.all(), write_only=True)
    program = LoyaltyProgramSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(source='program', queryset=LoyaltyProgram.objects.all(), write_only=True)
    tier = LoyaltyTierNestedSerializer(read_only=True)
    tier_id = serializers.PrimaryKeyRelatedField(
        source='tier',
        queryset=LoyaltyTier.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CustomerLoyaltyAccount
        fields = (
            'id',
            'customer',
            'customer_id',
            'program',
            'program_id',
            'points',
            'tier',
            'tier_id',
        )
        read_only_fields = ('id', 'customer', 'program', 'tier')

    def validate_points(self, value):
        if value < 0:
            raise serializers.ValidationError('Points must be greater than or equal to 0.')
        return value

    def validate(self, attrs):
        program = attrs.get('program') or getattr(self.instance, 'program', None)
        tier = attrs.get('tier') if 'tier' in attrs else getattr(self.instance, 'tier', None)
        if tier and program and tier.program_id != program.id:
            raise serializers.ValidationError({'tier_id': 'Tier must belong to the selected loyalty program.'})
        return attrs


class CustomerLoyaltyAccountNestedSerializer(serializers.ModelSerializer):
    customer = UserSummarySerializer(read_only=True)
    tier = LoyaltyTierNestedSerializer(read_only=True)
    program = LoyaltyProgramSerializer(read_only=True)

    class Meta:
        model = CustomerLoyaltyAccount
        fields = ('id', 'customer', 'program', 'points', 'tier')
        read_only_fields = fields


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    account = CustomerLoyaltyAccountNestedSerializer(read_only=True)
    account_id = serializers.PrimaryKeyRelatedField(source='account', queryset=CustomerLoyaltyAccount.objects.all(), write_only=True)

    class Meta:
        model = LoyaltyTransaction
        fields = ('id', 'account', 'account_id', 'points', 'type', 'created_at')
        read_only_fields = ('id', 'account')

    def validate_points(self, value):
        if value < 0:
            raise serializers.ValidationError('Points must be greater than or equal to 0.')
        return value

    def validate(self, attrs):
        account = attrs.get('account') or getattr(self.instance, 'account', None)
        tx_type = attrs.get('type') or getattr(self.instance, 'type', None)
        points = attrs.get('points')
        if points is None and self.instance is not None:
            points = self.instance.points

        if account and tx_type == LoyaltyTransaction.TYPE_SPEND and points is not None:
            current_balance = account.points
            if self.instance:
                current_balance -= self.instance.signed_points()
            projected_balance = current_balance - points
            if projected_balance < 0:
                raise serializers.ValidationError({'points': 'Spend transaction cannot make account points negative.'})
        return attrs


class ReferralCodeSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.all(), write_only=True)

    class Meta:
        model = ReferralCode
        fields = ('id', 'user', 'user_id', 'code', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')

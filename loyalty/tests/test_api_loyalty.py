from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.contrib.auth import get_user_model

from loyalty.models import (
    CustomerLoyaltyAccount,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTransaction,
    ReferralCode,
)


User = get_user_model()


class LoyaltyApiTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_counter = 0

        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            full_name='Admin User',
            phone='+10000000001',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123',
            full_name='Manager User',
            phone='+10000000002',
            role='manager',
            is_staff=True,
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            full_name='Staff User',
            phone='+10000000003',
            role='staff',
            is_staff=True,
        )

        self.customer_1 = self._create_customer('alice@example.com', 'Alice Customer', '+11111111111')
        self.customer_2 = self._create_customer('bob@example.com', 'Bob Customer', '+12222222222')
        self.customer_3 = self._create_customer('charlie@example.com', 'Charlie Customer', '+13333333333')

        self.program = LoyaltyProgram.objects.create(name='Main Program', is_active=True)
        self.second_program = LoyaltyProgram.objects.create(name='Seasonal Program', is_active=False)
        self.silver_tier = LoyaltyTier.objects.create(
            program=self.program,
            name='Silver',
            min_points=0,
            discount_percent='5.00',
        )
        self.gold_tier = LoyaltyTier.objects.create(
            program=self.program,
            name='Gold',
            min_points=100,
            discount_percent='10.00',
        )
        self.vip_tier = LoyaltyTier.objects.create(
            program=self.program,
            name='VIP',
            min_points=200,
            discount_percent='15.00',
        )
        self.account = CustomerLoyaltyAccount.objects.create(
            customer=self.customer_1,
            program=self.program,
            points=20,
        )
        self.transaction = LoyaltyTransaction.objects.create(
            account=self.account,
            points=10,
            type=LoyaltyTransaction.TYPE_EARN,
        )
        self.account.refresh_from_db()
        self.referral_code = ReferralCode.objects.create(user=self.customer_1, code='REF-ALICE')

    def _create_customer(self, email, full_name, phone):
        self.user_counter += 1
        return User.objects.create_user(
            username=email,
            email=email,
            password='customerpass123',
            full_name=full_name,
            phone=phone,
            role='client',
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)


class LoyaltyProgramTierApiTests(LoyaltyApiTestCase):
    def test_admin_can_crud_programs_and_tiers(self):
        self.authenticate(self.admin_user)

        program_list = self.client.get('/api/v1/admin/loyalty/programs/')
        self.assertEqual(program_list.status_code, status.HTTP_200_OK)

        program_create = self.client.post(
            '/api/v1/admin/loyalty/programs/',
            {'name': 'VIP Program', 'is_active': True},
            format='json',
        )
        self.assertEqual(program_create.status_code, status.HTTP_201_CREATED)
        program_id = program_create.data['id']

        program_detail = self.client.get(f'/api/v1/admin/loyalty/programs/{program_id}/')
        self.assertEqual(program_detail.status_code, status.HTTP_200_OK)

        program_patch = self.client.patch(
            f'/api/v1/admin/loyalty/programs/{program_id}/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(program_patch.status_code, status.HTTP_200_OK)
        self.assertFalse(program_patch.data['is_active'])

        tier_list = self.client.get('/api/v1/admin/loyalty/tiers/')
        self.assertEqual(tier_list.status_code, status.HTTP_200_OK)

        tier_create = self.client.post(
            '/api/v1/admin/loyalty/tiers/',
            {
                'program_id': program_id,
                'name': 'VIP Tier',
                'min_points': 300,
                'discount_percent': '20.00',
            },
            format='json',
        )
        self.assertEqual(tier_create.status_code, status.HTTP_201_CREATED)
        tier_id = tier_create.data['id']

        tier_detail = self.client.get(f'/api/v1/admin/loyalty/tiers/{tier_id}/')
        self.assertEqual(tier_detail.status_code, status.HTTP_200_OK)

        tier_patch = self.client.patch(
            f'/api/v1/admin/loyalty/tiers/{tier_id}/',
            {'discount_percent': '25.00'},
            format='json',
        )
        self.assertEqual(tier_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(tier_patch.data['discount_percent'], '25.00')

        tier_delete = self.client.delete(f'/api/v1/admin/loyalty/tiers/{tier_id}/')
        self.assertEqual(tier_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LoyaltyTier.objects.filter(pk=tier_id).exists())

        program_delete = self.client.delete(f'/api/v1/admin/loyalty/programs/{program_id}/')
        self.assertEqual(program_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LoyaltyProgram.objects.filter(pk=program_id).exists())

    def test_manager_can_crud_programs_and_tiers(self):
        self.authenticate(self.manager_user)

        create_program = self.client.post(
            '/api/v1/admin/loyalty/programs/',
            {'name': 'Manager Program', 'is_active': True},
            format='json',
        )
        self.assertEqual(create_program.status_code, status.HTTP_201_CREATED)
        program_id = create_program.data['id']

        create_tier = self.client.post(
            '/api/v1/admin/loyalty/tiers/',
            {
                'program_id': program_id,
                'name': 'Manager Gold',
                'min_points': 150,
                'discount_percent': '12.50',
            },
            format='json',
        )
        self.assertEqual(create_tier.status_code, status.HTTP_201_CREATED)
        tier_id = create_tier.data['id']

        self.assertEqual(self.client.get(f'/api/v1/admin/loyalty/programs/{program_id}/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f'/api/v1/admin/loyalty/tiers/{tier_id}/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/loyalty/programs/{program_id}/', {'is_active': False}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/loyalty/tiers/{tier_id}/', {'min_points': 175}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(f'/api/v1/admin/loyalty/tiers/{tier_id}/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.delete(f'/api/v1/admin/loyalty/programs/{program_id}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_is_read_only_for_programs_and_tiers(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get('/api/v1/admin/loyalty/programs/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/v1/admin/loyalty/tiers/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post('/api/v1/admin/loyalty/programs/', {'name': 'Blocked', 'is_active': True}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/loyalty/programs/{self.program.pk}/', {'is_active': False}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/admin/loyalty/tiers/{self.silver_tier.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_program_and_tier_validation_errors(self):
        self.authenticate(self.admin_user)

        invalid_program = self.client.post('/api/v1/admin/loyalty/programs/', {'name': '', 'is_active': True}, format='json')
        self.assertEqual(invalid_program.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', invalid_program.data)

        invalid_tier = self.client.post(
            '/api/v1/admin/loyalty/tiers/',
            {
                'program_id': self.program.pk,
                'name': '',
                'min_points': -10,
                'discount_percent': '-5.00',
            },
            format='json',
        )
        self.assertEqual(invalid_tier.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', invalid_tier.data)
        self.assertIn('min_points', invalid_tier.data)
        self.assertIn('discount_percent', invalid_tier.data)


class LoyaltyAccountApiTests(LoyaltyApiTestCase):
    def test_admin_can_crud_loyalty_accounts(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get('/api/v1/loyalty/accounts/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/loyalty/accounts/',
            {
                'customer_id': self.customer_2.pk,
                'program_id': self.program.pk,
                'points': 150,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        account_id = create_response.data['id']
        created_account = CustomerLoyaltyAccount.objects.get(pk=account_id)
        self.assertEqual(created_account.customer, self.customer_2)
        self.assertEqual(created_account.tier, self.gold_tier)

        detail_response = self.client.get(f'/api/v1/loyalty/accounts/{account_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/loyalty/accounts/{account_id}/',
            {'points': 220},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        created_account.refresh_from_db()
        self.assertEqual(created_account.points, 220)
        self.assertEqual(created_account.tier, self.vip_tier)

        delete_response = self.client.delete(f'/api/v1/loyalty/accounts/{account_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerLoyaltyAccount.objects.filter(pk=account_id).exists())

    def test_manager_can_crud_loyalty_accounts(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            '/api/v1/loyalty/accounts/',
            {
                'customer_id': self.customer_3.pk,
                'program_id': self.program.pk,
                'points': 50,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        account_id = create_response.data['id']

        self.assertEqual(self.client.get(f'/api/v1/loyalty/accounts/{account_id}/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f'/api/v1/loyalty/accounts/{account_id}/', {'points': 110}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(f'/api/v1/loyalty/accounts/{account_id}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_is_read_only_for_accounts(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get('/api/v1/loyalty/accounts/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f'/api/v1/loyalty/accounts/{self.account.pk}/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(
                '/api/v1/loyalty/accounts/',
                {'customer_id': self.customer_2.pk, 'program_id': self.program.pk, 'points': 10},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/loyalty/accounts/{self.account.pk}/', {'points': 30}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/loyalty/accounts/{self.account.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_account_validation_and_pagination(self):
        self.authenticate(self.admin_user)

        invalid_response = self.client.post(
            '/api/v1/loyalty/accounts/',
            {'customer_id': self.customer_2.pk, 'program_id': self.program.pk, 'points': -1},
            format='json',
        )
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', invalid_response.data)

        CustomerLoyaltyAccount.objects.create(customer=self.customer_2, program=self.second_program, points=5)
        CustomerLoyaltyAccount.objects.create(customer=self.customer_3, program=self.program, points=250)

        page_one = self.client.get('/api/v1/loyalty/accounts/', {'page_size': 2})
        self.assertEqual(page_one.status_code, status.HTTP_200_OK)
        self.assertEqual(page_one.data['count'], 3)
        self.assertEqual(len(page_one.data['results']), 2)
        self.assertIsNotNone(page_one.data['next'])
        self.assertIsNone(page_one.data['previous'])

        page_two = self.client.get('/api/v1/loyalty/accounts/', {'page_size': 2, 'page': 2})
        self.assertEqual(page_two.status_code, status.HTTP_200_OK)
        self.assertEqual(len(page_two.data['results']), 1)
        self.assertIsNone(page_two.data['next'])
        self.assertIsNotNone(page_two.data['previous'])


class LoyaltyTransactionApiTests(LoyaltyApiTestCase):
    def test_admin_can_crud_transactions_and_tier_updates_on_earn(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get('/api/v1/loyalty/transactions/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/loyalty/transactions/',
            {
                'account_id': self.account.pk,
                'points': 80,
                'type': 'earn',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        transaction_id = create_response.data['id']
        self.account.refresh_from_db()
        self.assertEqual(self.account.points, 110)
        self.assertEqual(self.account.tier, self.gold_tier)

        detail_response = self.client.get(f'/api/v1/loyalty/transactions/{transaction_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/loyalty/transactions/{transaction_id}/',
            {'points': 190},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertEqual(self.account.points, 220)
        self.assertEqual(self.account.tier, self.vip_tier)

        delete_response = self.client.delete(f'/api/v1/loyalty/transactions/{transaction_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.account.refresh_from_db()
        self.assertEqual(self.account.points, 30)
        self.assertEqual(self.account.tier, self.silver_tier)

    def test_manager_can_crud_transactions(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            '/api/v1/loyalty/transactions/',
            {
                'account_id': self.account.pk,
                'points': 5,
                'type': 'earn',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        transaction_id = create_response.data['id']

        self.assertEqual(self.client.get(f'/api/v1/loyalty/transactions/{transaction_id}/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f'/api/v1/loyalty/transactions/{transaction_id}/', {'points': 6}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(f'/api/v1/loyalty/transactions/{transaction_id}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_is_read_only_for_transactions(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get('/api/v1/loyalty/transactions/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(f'/api/v1/loyalty/transactions/{self.transaction.pk}/').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                '/api/v1/loyalty/transactions/',
                {'account_id': self.account.pk, 'points': 5, 'type': 'earn'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/loyalty/transactions/{self.transaction.pk}/', {'points': 7}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/loyalty/transactions/{self.transaction.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_spend_cannot_make_balance_negative(self):
        self.authenticate(self.admin_user)

        response = self.client.post(
            '/api/v1/loyalty/transactions/',
            {
                'account_id': self.account.pk,
                'points': 1000,
                'type': 'spend',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)

    def test_transaction_validation_errors(self):
        self.authenticate(self.admin_user)

        invalid_response = self.client.post(
            '/api/v1/loyalty/transactions/',
            {
                'account_id': self.account.pk,
                'points': -5,
                'type': 'earn',
            },
            format='json',
        )
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', invalid_response.data)


class ReferralCodeApiTests(LoyaltyApiTestCase):
    def test_admin_can_crud_referral_codes(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get('/api/v1/loyalty/referral-codes/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/loyalty/referral-codes/',
            {'user_id': self.customer_2.pk, 'code': 'REF-BOB'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        referral_id = create_response.data['id']

        detail_response = self.client.get(f'/api/v1/loyalty/referral-codes/{referral_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/loyalty/referral-codes/{referral_id}/',
            {'code': 'REF-BOB-UPD'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['code'], 'REF-BOB-UPD')

        delete_response = self.client.delete(f'/api/v1/loyalty/referral-codes/{referral_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ReferralCode.objects.filter(pk=referral_id).exists())

    def test_manager_can_crud_referral_codes(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            '/api/v1/loyalty/referral-codes/',
            {'user_id': self.customer_3.pk, 'code': 'REF-CHARLIE'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        referral_id = create_response.data['id']

        self.assertEqual(self.client.get(f'/api/v1/loyalty/referral-codes/{referral_id}/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f'/api/v1/loyalty/referral-codes/{referral_id}/', {'code': 'REF-CHARLIE-UPD'}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(f'/api/v1/loyalty/referral-codes/{referral_id}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_is_read_only_for_referral_codes(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get('/api/v1/loyalty/referral-codes/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(f'/api/v1/loyalty/referral-codes/{self.referral_code.pk}/').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                '/api/v1/loyalty/referral-codes/',
                {'user_id': self.customer_2.pk, 'code': 'BLOCKED'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/loyalty/referral-codes/{self.referral_code.pk}/', {'code': 'BLOCKED-UPD'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/loyalty/referral-codes/{self.referral_code.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_referral_code_validation_errors(self):
        self.authenticate(self.admin_user)

        invalid_response = self.client.post(
            '/api/v1/loyalty/referral-codes/',
            {'user_id': '', 'code': ''},
            format='json',
        )
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', invalid_response.data)
        self.assertIn('code', invalid_response.data)

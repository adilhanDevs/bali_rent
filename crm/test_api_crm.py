from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.contrib.auth import get_user_model

from crm.models import CustomerInteraction, CustomerNote, CustomerProfile, CustomerSegment


User = get_user_model()


class CRMApiBaseTestCase(APITestCase):
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

        self.segment_vip = CustomerSegment.objects.create(code='vip', name='VIP', discount_percent='10.00')
        self.segment_regular = CustomerSegment.objects.create(code='regular', name='Regular', discount_percent='5.00')

        self.customer_user_1 = self._create_customer_user(
            email='alice@example.com',
            full_name='Alice Customer',
            phone='+11111111111',
        )
        self.customer_user_2 = self._create_customer_user(
            email='bob@example.com',
            full_name='Bob Customer',
            phone='+12222222222',
        )
        self.customer_user_3 = self._create_customer_user(
            email='charlie@example.com',
            full_name='Charlie Customer',
            phone='+13333333333',
        )
        self.customer_user_4 = self._create_customer_user(
            email='diana@example.com',
            full_name='Diana Customer',
            phone='+14444444444',
        )

        self.customer_profile_1 = CustomerProfile.objects.create(user=self.customer_user_1, segment=self.segment_vip)
        self.customer_profile_2 = CustomerProfile.objects.create(user=self.customer_user_2, segment=self.segment_regular)
        self.customer_profile_3 = CustomerProfile.objects.create(user=self.customer_user_3, segment=self.segment_vip)
        self.customer_profile_4 = CustomerProfile.objects.create(user=self.customer_user_4, segment=None)

        self.customer_note = CustomerNote.objects.create(
            customer=self.customer_profile_1,
            author=self.admin_user,
            text='Initial customer note',
        )
        self.customer_interaction = CustomerInteraction.objects.create(
            customer=self.customer_profile_1,
            interaction_type='call',
            description='Initial customer call',
            created_by=self.manager_user,
        )

    def _create_customer_user(self, email=None, full_name=None, phone=None):
        self.user_counter += 1
        index = self.user_counter
        return User.objects.create_user(
            username=email or f'customer{index}@example.com',
            email=email or f'customer{index}@example.com',
            password='customerpass123',
            full_name=full_name or f'Customer {index}',
            phone=phone or f'+19999999{index:03d}',
            role='client',
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def segment_list_url(self):
        return '/api/v1/admin/crm/customer-segments/'

    def segment_detail_url(self, pk):
        return f'/api/v1/admin/crm/customer-segments/{pk}/'

    def profile_list_url(self):
        return '/api/v1/admin/crm/customer-profiles/'

    def profile_detail_url(self, pk):
        return f'/api/v1/admin/crm/customer-profiles/{pk}/'

    def note_list_url(self):
        return '/api/v1/admin/crm/customer-notes/'

    def note_detail_url(self, pk):
        return f'/api/v1/admin/crm/customer-notes/{pk}/'

    def interaction_list_url(self):
        return '/api/v1/admin/crm/customer-interactions/'

    def interaction_detail_url(self, pk):
        return f'/api/v1/admin/crm/customer-interactions/{pk}/'


class CustomerSegmentApiTests(CRMApiBaseTestCase):
    def test_admin_can_crud_customer_segment(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get(self.segment_list_url())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            self.segment_list_url(),
            {'code': 'gold', 'name': 'Gold', 'discount_percent': '15.00'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        segment_id = create_response.data['id']

        detail_response = self.client.get(self.segment_detail_url(segment_id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['code'], 'gold')

        patch_response = self.client.patch(
            self.segment_detail_url(segment_id),
            {'name': 'Gold Plus', 'discount_percent': '17.50'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['name'], 'Gold Plus')

        delete_response = self.client.delete(self.segment_detail_url(segment_id))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerSegment.objects.filter(pk=segment_id).exists())

    def test_manager_can_crud_customer_segment(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            self.segment_list_url(),
            {'code': 'silver', 'name': 'Silver', 'discount_percent': '7.50'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        segment_id = create_response.data['id']

        self.assertEqual(self.client.get(self.segment_detail_url(segment_id)).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(self.segment_detail_url(segment_id), {'name': 'Silver Plus'}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(self.segment_detail_url(segment_id)).status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_has_read_only_access_to_customer_segments(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get(self.segment_list_url()).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(self.segment_detail_url(self.segment_vip.pk)).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(self.segment_list_url(), {'code': 'blocked', 'name': 'Blocked'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(self.segment_detail_url(self.segment_vip.pk), {'name': 'Blocked'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.segment_detail_url(self.segment_vip.pk)).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_segment_validation_errors(self):
        self.authenticate(self.admin_user)

        empty_fields_response = self.client.post(
            self.segment_list_url(),
            {'code': '', 'name': '', 'discount_percent': '10.00'},
            format='json',
        )
        self.assertEqual(empty_fields_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('code', empty_fields_response.data)
        self.assertIn('name', empty_fields_response.data)

        invalid_data_response = self.client.post(
            self.segment_list_url(),
            {'code': 'bad', 'name': 'Bad', 'discount_percent': 'not-a-number'},
            format='json',
        )
        self.assertEqual(invalid_data_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('discount_percent', invalid_data_response.data)


class CustomerProfileApiTests(CRMApiBaseTestCase):
    def test_admin_can_crud_customer_profile(self):
        self.authenticate(self.admin_user)
        create_user = self._create_customer_user(email='eve@example.com', full_name='Eve Customer', phone='+15555555555')

        list_response = self.client.get(self.profile_list_url())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            self.profile_list_url(),
            {'user_id': create_user.pk, 'segment_id': self.segment_regular.pk},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        profile_id = create_response.data['id']
        self.assertEqual(CustomerProfile.objects.get(pk=profile_id).user, create_user)

        detail_response = self.client.get(self.profile_detail_url(profile_id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['user']['email'], 'eve@example.com')

        patch_response = self.client.patch(
            self.profile_detail_url(profile_id),
            {'segment_id': self.segment_vip.pk},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(CustomerProfile.objects.get(pk=profile_id).segment, self.segment_vip)

        delete_response = self.client.delete(self.profile_detail_url(profile_id))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerProfile.objects.filter(pk=profile_id).exists())

    def test_manager_can_crud_customer_profile(self):
        self.authenticate(self.manager_user)
        create_user = self._create_customer_user(email='frank@example.com', full_name='Frank Customer', phone='+16666666666')

        create_response = self.client.post(
            self.profile_list_url(),
            {'user_id': create_user.pk, 'segment_id': self.segment_vip.pk},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        profile_id = create_response.data['id']

        self.assertEqual(self.client.get(self.profile_detail_url(profile_id)).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(self.profile_detail_url(profile_id), {'segment_id': self.segment_regular.pk}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(self.profile_detail_url(profile_id)).status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_has_read_only_access_to_customer_profiles(self):
        self.authenticate(self.staff_user)
        create_user = self._create_customer_user(email='readonly@example.com')

        self.assertEqual(self.client.get(self.profile_list_url()).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(self.profile_detail_url(self.customer_profile_1.pk)).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                self.profile_list_url(),
                {'user_id': create_user.pk, 'segment_id': self.segment_vip.pk},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(self.profile_detail_url(self.customer_profile_1.pk), {'segment_id': None}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.profile_detail_url(self.customer_profile_1.pk)).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_profile_validation_errors(self):
        self.authenticate(self.admin_user)

        empty_fields_response = self.client.post(self.profile_list_url(), {}, format='json')
        self.assertEqual(empty_fields_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', empty_fields_response.data)

        invalid_data_response = self.client.post(
            self.profile_list_url(),
            {'user_id': 'not-an-id', 'segment_id': self.segment_vip.pk},
            format='json',
        )
        self.assertEqual(invalid_data_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', invalid_data_response.data)

    def test_customer_profiles_search_by_name_and_email(self):
        self.authenticate(self.admin_user)

        name_response = self.client.get(self.profile_list_url(), {'search': 'Alice Customer'})
        self.assertEqual(name_response.status_code, status.HTTP_200_OK)
        self.assertEqual(name_response.data['count'], 1)
        self.assertEqual(name_response.data['results'][0]['user']['email'], 'alice@example.com')

        email_response = self.client.get(self.profile_list_url(), {'search': 'bob@example.com'})
        self.assertEqual(email_response.status_code, status.HTTP_200_OK)
        self.assertEqual(email_response.data['count'], 1)
        self.assertEqual(email_response.data['results'][0]['user']['email'], 'bob@example.com')

    def test_customer_profiles_filter_by_segment(self):
        self.authenticate(self.admin_user)

        response = self.client.get(self.profile_list_url(), {'segment': self.segment_vip.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        result_ids = {item['id'] for item in response.data['results']}
        self.assertIn(self.customer_profile_1.pk, result_ids)
        self.assertIn(self.customer_profile_3.pk, result_ids)
        self.assertNotIn(self.customer_profile_2.pk, result_ids)

    def test_customer_profiles_pagination(self):
        self.authenticate(self.admin_user)

        first_page = self.client.get(self.profile_list_url(), {'page_size': 2})
        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data['count'], 4)
        self.assertEqual(len(first_page.data['results']), 2)
        self.assertIsNotNone(first_page.data['next'])
        self.assertIsNone(first_page.data['previous'])

        second_page = self.client.get(self.profile_list_url(), {'page_size': 2, 'page': 2})
        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page.data['results']), 2)
        self.assertIsNone(second_page.data['next'])
        self.assertIsNotNone(second_page.data['previous'])


class CustomerNoteApiTests(CRMApiBaseTestCase):
    def test_admin_can_crud_customer_note(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get(self.note_list_url())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            self.note_list_url(),
            {
                'customer_id': self.customer_profile_2.pk,
                'author_id': self.manager_user.pk,
                'text': 'Follow up with customer tomorrow',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        note_id = create_response.data['id']
        created_note = CustomerNote.objects.get(pk=note_id)
        self.assertEqual(created_note.customer, self.customer_profile_2)
        self.assertEqual(created_note.author, self.manager_user)

        detail_response = self.client.get(self.note_detail_url(note_id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['author']['email'], 'manager@example.com')

        patch_response = self.client.patch(
            self.note_detail_url(note_id),
            {'text': 'Updated follow-up plan'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(CustomerNote.objects.get(pk=note_id).text, 'Updated follow-up plan')

        delete_response = self.client.delete(self.note_detail_url(note_id))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerNote.objects.filter(pk=note_id).exists())

    def test_manager_can_crud_customer_note(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            self.note_list_url(),
            {'customer_id': self.customer_profile_3.pk, 'text': 'Manager note'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        note_id = create_response.data['id']
        self.assertEqual(CustomerNote.objects.get(pk=note_id).author, self.manager_user)

        self.assertEqual(self.client.get(self.note_detail_url(note_id)).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(self.note_detail_url(note_id), {'text': 'Updated manager note'}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(self.note_detail_url(note_id)).status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_has_read_only_access_to_customer_notes(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get(self.note_list_url()).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.note_detail_url(self.customer_note.pk)).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(
                self.note_list_url(),
                {'customer_id': self.customer_profile_1.pk, 'text': 'Blocked note'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(self.note_detail_url(self.customer_note.pk), {'text': 'Blocked'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.note_detail_url(self.customer_note.pk)).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_note_validation_errors(self):
        self.authenticate(self.admin_user)

        empty_fields_response = self.client.post(
            self.note_list_url(),
            {'customer_id': '', 'text': ''},
            format='json',
        )
        self.assertEqual(empty_fields_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_id', empty_fields_response.data)
        self.assertIn('text', empty_fields_response.data)

        invalid_data_response = self.client.post(
            self.note_list_url(),
            {'customer_id': 999999, 'author_id': 'bad', 'text': 'Broken note'},
            format='json',
        )
        self.assertEqual(invalid_data_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_id', invalid_data_response.data)
        self.assertIn('author_id', invalid_data_response.data)


class CustomerInteractionApiTests(CRMApiBaseTestCase):
    def test_admin_can_crud_customer_interaction(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get(self.interaction_list_url())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            self.interaction_list_url(),
            {
                'customer_id': self.customer_profile_2.pk,
                'interaction_type': 'email',
                'description': 'Sent welcome email',
                'created_by_id': self.manager_user.pk,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        interaction_id = create_response.data['id']
        created_interaction = CustomerInteraction.objects.get(pk=interaction_id)
        self.assertEqual(created_interaction.customer, self.customer_profile_2)
        self.assertEqual(created_interaction.created_by, self.manager_user)

        detail_response = self.client.get(self.interaction_detail_url(interaction_id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['interaction_type'], 'email')

        patch_response = self.client.patch(
            self.interaction_detail_url(interaction_id),
            {'interaction_type': 'support', 'description': 'Escalated to support'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        updated_interaction = CustomerInteraction.objects.get(pk=interaction_id)
        self.assertEqual(updated_interaction.interaction_type, 'support')
        self.assertEqual(updated_interaction.description, 'Escalated to support')

        delete_response = self.client.delete(self.interaction_detail_url(interaction_id))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerInteraction.objects.filter(pk=interaction_id).exists())

    def test_manager_can_crud_customer_interaction(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            self.interaction_list_url(),
            {
                'customer_id': self.customer_profile_3.pk,
                'interaction_type': 'chat',
                'description': 'Manager started chat',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        interaction_id = create_response.data['id']
        self.assertEqual(CustomerInteraction.objects.get(pk=interaction_id).created_by, self.manager_user)

        self.assertEqual(self.client.get(self.interaction_detail_url(interaction_id)).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(
                self.interaction_detail_url(interaction_id),
                {'description': 'Manager updated chat log'},
                format='json',
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(self.interaction_detail_url(interaction_id)).status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_has_read_only_access_to_customer_interactions(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get(self.interaction_list_url()).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(self.interaction_detail_url(self.customer_interaction.pk)).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                self.interaction_list_url(),
                {
                    'customer_id': self.customer_profile_1.pk,
                    'interaction_type': 'email',
                    'description': 'Blocked interaction',
                },
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(
                self.interaction_detail_url(self.customer_interaction.pk),
                {'description': 'Blocked'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self.interaction_detail_url(self.customer_interaction.pk)).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_interaction_validation_errors(self):
        self.authenticate(self.admin_user)

        empty_fields_response = self.client.post(
            self.interaction_list_url(),
            {'customer_id': '', 'interaction_type': '', 'description': ''},
            format='json',
        )
        self.assertEqual(empty_fields_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_id', empty_fields_response.data)
        self.assertIn('description', empty_fields_response.data)

        invalid_data_response = self.client.post(
            self.interaction_list_url(),
            {
                'customer_id': 999999,
                'interaction_type': 'email',
                'description': 'Broken interaction',
                'created_by_id': 'bad',
            },
            format='json',
        )
        self.assertEqual(invalid_data_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_id', invalid_data_response.data)
        self.assertIn('created_by_id', invalid_data_response.data)

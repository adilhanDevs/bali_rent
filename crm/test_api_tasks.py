from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from crm.models import StaffTask, TaskChecklistItem, TaskComment


User = get_user_model()


class StaffTaskApiBaseTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

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
        self.client_user = User.objects.create_user(
            username='client',
            email='client@example.com',
            password='clientpass123',
            full_name='Client User',
            phone='+11111111111',
            role='client',
        )

        vehicle_type = VehicleType.objects.create(code='scooter', name='Scooter')
        vehicle_model = VehicleModel.objects.create(
            name='NMax',
            brand='Yamaha',
            type=vehicle_type,
            engine_cc=155,
            transmission='automatic',
            fuel_consumption=2.1,
            year=2024,
            trunk='medium',
            helmets_count=2,
            description='QA model',
            rental_terms='QA terms',
        )
        self.vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title='QA Vehicle',
            slug='qa-task-vehicle',
            sku='QA-TASK-001',
            color='black',
            base_price_usd='25.00',
            status='available',
        )
        self.booking = Booking.objects.create(
            public_number='BK-TASK-001',
            user=self.client_user,
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=3),
            payment_method='online_card',
            subtotal_usd='50.00',
            addons_total_usd='0.00',
            discount_usd='0.00',
            markup_usd='0.00',
            total_usd='50.00',
            total_display='$50.00',
            status='created',
        )
        self.task = StaffTask.objects.create(
            title='Prepare scooter',
            description='Prepare scooter for delivery',
            assigned_to=self.manager_user,
            related_booking=self.booking,
            due_at=timezone.now() + timedelta(days=2),
        )
        self.checklist_item = TaskChecklistItem.objects.create(
            task=self.task,
            title='Wash scooter',
            is_completed=False,
            sort_order=1,
        )
        self.comment = TaskComment.objects.create(
            task=self.task,
            author=self.admin_user,
            text='Initial task comment',
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)


class StaffTaskApiTests(StaffTaskApiBaseTestCase):
    def test_admin_can_crud_staff_tasks(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get('/api/v1/admin/tasks/staff-tasks/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/admin/tasks/staff-tasks/',
            {
                'title': 'Inspect vehicle',
                'description': 'Inspect vehicle before handoff',
                'assigned_to_id': self.staff_user.pk,
                'related_booking_id': self.booking.pk,
                'status': 'pending',
                'due_at': (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        task_id = create_response.data['id']

        detail_response = self.client.get(f'/api/v1/admin/tasks/staff-tasks/{task_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_to_in_progress = self.client.patch(
            f'/api/v1/admin/tasks/staff-tasks/{task_id}/',
            {'status': 'in_progress'},
            format='json',
        )
        self.assertEqual(patch_to_in_progress.status_code, status.HTTP_200_OK)

        patch_title = self.client.patch(
            f'/api/v1/admin/tasks/staff-tasks/{task_id}/',
            {'title': 'Inspect vehicle updated'},
            format='json',
        )
        self.assertEqual(patch_title.status_code, status.HTTP_200_OK)
        self.assertEqual(StaffTask.objects.get(pk=task_id).title, 'Inspect vehicle updated')

        delete_response = self.client.delete(f'/api/v1/admin/tasks/staff-tasks/{task_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StaffTask.objects.filter(pk=task_id).exists())

    def test_manager_can_crud_staff_tasks(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            '/api/v1/admin/tasks/staff-tasks/',
            {
                'title': 'Charge battery',
                'description': 'Charge battery fully',
                'assigned_to_id': self.staff_user.pk,
                'related_booking_id': self.booking.pk,
                'status': 'pending',
                'due_at': (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        task_id = create_response.data['id']

        self.assertEqual(self.client.get(f'/api/v1/admin/tasks/staff-tasks/{task_id}/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/tasks/staff-tasks/{task_id}/', {'status': 'in_progress'}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self.client.delete(f'/api/v1/admin/tasks/staff-tasks/{task_id}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_is_read_only_for_task_api(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get('/api/v1/admin/tasks/staff-tasks/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(
                '/api/v1/admin/tasks/staff-tasks/',
                {
                    'title': 'Blocked',
                    'description': 'Blocked',
                    'status': 'pending',
                    'due_at': (timezone.now() + timedelta(days=1)).isoformat(),
                },
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/', {'status': 'in_progress'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_task_validation_rejects_past_due_date_and_direct_completion(self):
        self.authenticate(self.admin_user)

        past_due_response = self.client.post(
            '/api/v1/admin/tasks/staff-tasks/',
            {
                'title': 'Past due task',
                'description': 'This should fail',
                'status': 'pending',
                'due_at': (timezone.now() - timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(past_due_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('due_at', past_due_response.data)

        direct_complete_response = self.client.post(
            '/api/v1/admin/tasks/staff-tasks/',
            {
                'title': 'Direct complete task',
                'description': 'This should fail',
                'status': 'completed',
                'due_at': (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(direct_complete_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', direct_complete_response.data)

    def test_task_workflow_requires_in_progress_before_completed(self):
        self.authenticate(self.admin_user)

        response = self.client.patch(
            f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

        progress_response = self.client.patch(
            f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/',
            {'status': 'in_progress'},
            format='json',
        )
        self.assertEqual(progress_response.status_code, status.HTTP_200_OK)

    def test_task_completion_requires_completed_checklist(self):
        self.authenticate(self.admin_user)

        self.assertEqual(
            self.client.patch(f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/', {'status': 'in_progress'}, format='json').status_code,
            status.HTTP_200_OK,
        )

        blocked_response = self.client.patch(
            f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(blocked_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', blocked_response.data)

        self.assertEqual(
            self.client.patch(
                f'/api/v1/admin/tasks/checklist-items/{self.checklist_item.pk}/',
                {'is_completed': True},
                format='json',
            ).status_code,
            status.HTTP_200_OK,
        )

        completed_response = self.client.patch(
            f'/api/v1/admin/tasks/staff-tasks/{self.task.pk}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(completed_response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'completed')

    def test_task_pagination(self):
        self.authenticate(self.admin_user)

        for index in range(3):
            StaffTask.objects.create(
                title=f'Paged task {index}',
                description='Paged task',
                assigned_to=self.manager_user,
                due_at=timezone.now() + timedelta(days=index + 2),
            )

        first_page = self.client.get('/api/v1/admin/tasks/staff-tasks/', {'page_size': 2})
        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data['count'], 4)
        self.assertEqual(len(first_page.data['results']), 2)
        self.assertIsNotNone(first_page.data['next'])
        self.assertIsNone(first_page.data['previous'])


class StaffTaskChecklistAndCommentApiTests(StaffTaskApiBaseTestCase):
    def test_admin_can_crud_checklist_items(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get('/api/v1/admin/tasks/checklist-items/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/admin/tasks/checklist-items/',
            {
                'task_id': self.task.pk,
                'title': 'Top up fuel',
                'is_completed': False,
                'sort_order': 2,
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        item_id = create_response.data['id']

        detail_response = self.client.get(f'/api/v1/admin/tasks/checklist-items/{item_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/admin/tasks/checklist-items/{item_id}/',
            {'is_completed': True},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(TaskChecklistItem.objects.get(pk=item_id).is_completed)

        delete_response = self.client.delete(f'/api/v1/admin/tasks/checklist-items/{item_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TaskChecklistItem.objects.filter(pk=item_id).exists())

    def test_admin_can_crud_task_comments(self):
        self.authenticate(self.admin_user)

        list_response = self.client.get('/api/v1/admin/tasks/comments/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/admin/tasks/comments/',
            {
                'task_id': self.task.pk,
                'text': 'Second task comment',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        created_comment = TaskComment.objects.get(pk=comment_id)
        self.assertEqual(created_comment.author, self.admin_user)

        detail_response = self.client.get(f'/api/v1/admin/tasks/comments/{comment_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/admin/tasks/comments/{comment_id}/',
            {'text': 'Updated task comment'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(TaskComment.objects.get(pk=comment_id).text, 'Updated task comment')

        delete_response = self.client.delete(f'/api/v1/admin/tasks/comments/{comment_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TaskComment.objects.filter(pk=comment_id).exists())

    def test_checklist_and_comment_validation(self):
        self.authenticate(self.admin_user)

        invalid_checklist = self.client.post(
            '/api/v1/admin/tasks/checklist-items/',
            {'task_id': self.task.pk, 'title': '', 'sort_order': 1},
            format='json',
        )
        self.assertEqual(invalid_checklist.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', invalid_checklist.data)

        invalid_comment = self.client.post(
            '/api/v1/admin/tasks/comments/',
            {'task_id': self.task.pk, 'text': ''},
            format='json',
        )
        self.assertEqual(invalid_comment.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('text', invalid_comment.data)

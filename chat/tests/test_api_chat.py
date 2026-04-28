from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from chat.models import ChatAttachment, ChatMessage, ChatParticipant, ChatThread, QuickReply


User = get_user_model()


class ChatApiBaseTestCase(APITestCase):
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
        self.other_client = User.objects.create_user(
            username='other-client',
            email='other@example.com',
            password='otherpass123',
            full_name='Other Client',
            phone='+12222222222',
            role='client',
        )

        self.thread = ChatThread.objects.create(
            title='Support Chat',
            status=ChatThread.STATUS_OPEN,
            created_by=self.client_user,
        )
        self.client_participant = ChatParticipant.objects.create(
            thread=self.thread,
            user=self.client_user,
            role=ChatParticipant.ROLE_CLIENT,
        )
        self.manager_participant = ChatParticipant.objects.create(
            thread=self.thread,
            user=self.manager_user,
            role=ChatParticipant.ROLE_MANAGER,
        )
        self.message = ChatMessage.objects.create(
            thread=self.thread,
            sender=self.client_user,
            text='Initial message',
        )
        self.attachment = ChatAttachment.objects.create(
            message=self.message,
            uploaded_by=self.client_user,
            file=SimpleUploadedFile('hello.txt', b'hello world', content_type='text/plain'),
        )
        self.quick_reply = QuickReply.objects.create(
            title='Greeting',
            text='Hello, how can I help you?',
            is_active=True,
            created_by=self.manager_user,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)


class PublicChatApiTests(ChatApiBaseTestCase):
    def test_participant_can_crud_threads(self):
        self.authenticate(self.client_user)

        list_response = self.client.get('/api/v1/chat/threads/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)

        create_response = self.client.post(
            '/api/v1/chat/threads/',
            {
                'title': 'New Chat Thread',
                'status': ChatThread.STATUS_OPEN,
                'participant_ids': [self.manager_user.pk],
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        thread_id = create_response.data['id']
        self.assertTrue(ChatParticipant.objects.filter(thread_id=thread_id, user=self.client_user).exists())
        self.assertTrue(ChatParticipant.objects.filter(thread_id=thread_id, user=self.manager_user).exists())

        detail_response = self.client.get(f'/api/v1/chat/threads/{thread_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/chat/threads/{thread_id}/',
            {'status': ChatThread.STATUS_CLOSED, 'title': 'Closed Chat Thread'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['status'], ChatThread.STATUS_CLOSED)

        delete_response = self.client.delete(f'/api/v1/chat/threads/{thread_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatThread.objects.filter(pk=thread_id).exists())

    def test_participant_can_crud_messages(self):
        self.authenticate(self.manager_user)

        list_response = self.client.get('/api/v1/chat/messages/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/chat/messages/',
            {
                'thread_id': self.thread.pk,
                'text': 'Manager reply',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        message_id = create_response.data['id']
        created_message = ChatMessage.objects.get(pk=message_id)
        self.assertEqual(created_message.sender, self.manager_user)

        detail_response = self.client.get(f'/api/v1/chat/messages/{message_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/chat/messages/{message_id}/',
            {'text': 'Updated manager reply'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ChatMessage.objects.get(pk=message_id).text, 'Updated manager reply')

        delete_response = self.client.delete(f'/api/v1/chat/messages/{message_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatMessage.objects.filter(pk=message_id).exists())

    def test_participant_can_crud_attachments(self):
        self.authenticate(self.manager_user)
        manager_message = ChatMessage.objects.create(thread=self.thread, sender=self.manager_user, text='Attachment message')

        list_response = self.client.get('/api/v1/chat/attachments/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/chat/attachments/',
            {
                'message_id': manager_message.pk,
                'file': SimpleUploadedFile('note.txt', b'note body', content_type='text/plain'),
            },
            format='multipart',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        attachment_id = create_response.data['id']
        created_attachment = ChatAttachment.objects.get(pk=attachment_id)
        self.assertEqual(created_attachment.uploaded_by, self.manager_user)

        detail_response = self.client.get(f'/api/v1/chat/attachments/{attachment_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            f'/api/v1/chat/attachments/{attachment_id}/',
            {'original_name': 'renamed-note.txt'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ChatAttachment.objects.get(pk=attachment_id).original_name, 'renamed-note.txt')

        delete_response = self.client.delete(f'/api/v1/chat/attachments/{attachment_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatAttachment.objects.filter(pk=attachment_id).exists())

    def test_quick_replies_are_read_only_for_clients(self):
        self.authenticate(self.client_user)

        list_response = self.client.get('/api/v1/chat/quick-replies/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 1)

        detail_response = self.client.get(f'/api/v1/chat/quick-replies/{self.quick_reply.pk}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        create_response = self.client.post(
            '/api/v1/chat/quick-replies/',
            {'title': 'Blocked', 'text': 'Blocked text', 'is_active': True},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_participants_can_view_chat_objects(self):
        self.authenticate(self.other_client)

        self.assertEqual(self.client.get('/api/v1/chat/threads/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/v1/chat/threads/').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/v1/chat/threads/{self.thread.pk}/').status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f'/api/v1/chat/messages/{self.message.pk}/').status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f'/api/v1/chat/attachments/{self.attachment.pk}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_thread_pagination_for_participant(self):
        self.authenticate(self.client_user)

        for index in range(3):
            thread = ChatThread.objects.create(title=f'Paged Thread {index}', created_by=self.client_user)
            ChatParticipant.objects.create(thread=thread, user=self.client_user, role=ChatParticipant.ROLE_CLIENT)
            ChatParticipant.objects.create(thread=thread, user=self.manager_user, role=ChatParticipant.ROLE_MANAGER)

        first_page = self.client.get('/api/v1/chat/threads/', {'page_size': 2})
        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data['count'], 4)
        self.assertEqual(len(first_page.data['results']), 2)
        self.assertIsNotNone(first_page.data['next'])
        self.assertIsNone(first_page.data['previous'])

        second_page = self.client.get('/api/v1/chat/threads/', {'page_size': 2, 'page': 2})
        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page.data['results']), 2)
        self.assertIsNone(second_page.data['next'])
        self.assertIsNotNone(second_page.data['previous'])


class AdminChatApiTests(ChatApiBaseTestCase):
    def test_admin_can_crud_admin_chat_resources(self):
        self.authenticate(self.admin_user)

        thread_list = self.client.get('/api/v1/admin/chat/threads/')
        self.assertEqual(thread_list.status_code, status.HTTP_200_OK)

        participant_create = self.client.post(
            '/api/v1/admin/chat/participants/',
            {
                'thread_id': self.thread.pk,
                'user_id': self.staff_user.pk,
                'role': ChatParticipant.ROLE_STAFF,
            },
            format='json',
        )
        self.assertEqual(participant_create.status_code, status.HTTP_201_CREATED)
        participant_id = participant_create.data['id']

        quick_reply_create = self.client.post(
            '/api/v1/admin/chat/quick-replies/',
            {'title': 'Escalation', 'text': 'I am escalating this issue.', 'is_active': True},
            format='json',
        )
        self.assertEqual(quick_reply_create.status_code, status.HTTP_201_CREATED)
        quick_reply_id = quick_reply_create.data['id']

        quick_reply_detail = self.client.get(f'/api/v1/admin/chat/quick-replies/{quick_reply_id}/')
        self.assertEqual(quick_reply_detail.status_code, status.HTTP_200_OK)

        quick_reply_patch = self.client.patch(
            f'/api/v1/admin/chat/quick-replies/{quick_reply_id}/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(quick_reply_patch.status_code, status.HTTP_200_OK)
        self.assertFalse(quick_reply_patch.data['is_active'])

        participant_delete = self.client.delete(f'/api/v1/admin/chat/participants/{participant_id}/')
        self.assertEqual(participant_delete.status_code, status.HTTP_204_NO_CONTENT)

        quick_reply_delete = self.client.delete(f'/api/v1/admin/chat/quick-replies/{quick_reply_id}/')
        self.assertEqual(quick_reply_delete.status_code, status.HTTP_204_NO_CONTENT)

    def test_manager_has_full_admin_chat_access(self):
        self.authenticate(self.manager_user)

        create_response = self.client.post(
            '/api/v1/admin/chat/quick-replies/',
            {'title': 'Manager Reply', 'text': 'Manager quick reply', 'is_active': True},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        quick_reply_id = create_response.data['id']

        self.assertEqual(self.client.get('/api/v1/admin/chat/threads/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/chat/quick-replies/{quick_reply_id}/', {'title': 'Updated Manager Reply'}, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/admin/chat/quick-replies/{quick_reply_id}/').status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_staff_is_read_only_on_admin_chat_api(self):
        self.authenticate(self.staff_user)

        self.assertEqual(self.client.get('/api/v1/admin/chat/threads/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/v1/admin/chat/participants/').status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(
                '/api/v1/admin/chat/quick-replies/',
                {'title': 'Blocked', 'text': 'Blocked', 'is_active': True},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(f'/api/v1/admin/chat/threads/{self.thread.pk}/', {'status': ChatThread.STATUS_CLOSED}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/admin/chat/participants/{self.client_participant.pk}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_chat_validation_errors(self):
        self.authenticate(self.admin_user)

        invalid_thread = self.client.post(
            '/api/v1/chat/threads/',
            {'title': 'Broken Thread', 'participant_ids': []},
            format='json',
        )
        self.assertEqual(invalid_thread.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participant_ids', invalid_thread.data)

        invalid_message = self.client.post(
            '/api/v1/chat/messages/',
            {'thread_id': self.thread.pk, 'text': ''},
            format='json',
        )
        self.assertEqual(invalid_message.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('text', invalid_message.data)

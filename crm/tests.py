from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from crm.models import StaffTask
from users.models import User


class StaffTaskSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            role="admin",
        )
        cls.staff_users = [
            User.objects.create_user(
                username=f"staff{i}",
                email=f"staff{i}@example.com",
                password="staffpass123",
                role="staff",
                is_staff=True,
                full_name=f"Staff User {i}",
            )
            for i in range(1, 4)
        ]

        vehicle_type = VehicleType.objects.create(code="scooter", name="Scooter")
        vehicle_model = VehicleModel.objects.create(
            name="NMax",
            brand="Yamaha",
            type=vehicle_type,
            engine_cc=155,
            transmission="automatic",
            fuel_consumption=2.1,
            year=2024,
            trunk="medium",
            helmets_count=2,
            description="QA vehicle model",
            rental_terms="Standard rental terms",
        )
        cls.vehicle = Vehicle.objects.create(
            model=vehicle_model,
            title="QA Scooter",
            slug="qa-scooter",
            sku="QA-SCOOTER-001",
            color="black",
            base_price_usd="25.00",
            status="available",
        )

        now = timezone.now()
        cls.bookings = [
            Booking.objects.create(
                public_number=f"BK-000{i}",
                user=cls.staff_users[i - 1],
                vehicle=cls.vehicle,
                start_at=now + timedelta(days=i),
                end_at=now + timedelta(days=i + 2),
                payment_method="online_card",
                subtotal_usd="50.00",
                addons_total_usd="0.00",
                discount_usd="0.00",
                markup_usd="0.00",
                total_usd="50.00",
                total_display="$50.00",
                status="created",
            )
            for i in range(1, 3)
        ]

        cls.seed_tasks = []
        seed_specs = [
            ("Pending follow-up", cls.staff_users[0], cls.bookings[0], now + timedelta(days=1)),
            ("Pending invoice review", cls.staff_users[1], cls.bookings[1], now + timedelta(days=2)),
            ("In progress delivery prep", cls.staff_users[0], cls.bookings[0], now + timedelta(days=3)),
            ("In progress documents", cls.staff_users[2], cls.bookings[1], now + timedelta(days=4)),
            ("Completed handoff", cls.staff_users[2], None, now + timedelta(days=5)),
        ]
        for title, assigned_to, booking, due_at in seed_specs:
            cls.seed_tasks.append(
                StaffTask.objects.create(
                    title=title,
                    description=f"{title} description",
                    assigned_to=assigned_to,
                    related_booking=booking,
                    due_at=due_at,
                )
            )
        cls.seed_tasks[2].status = "in_progress"
        cls.seed_tasks[2].save()
        cls.seed_tasks[3].status = "in_progress"
        cls.seed_tasks[3].save()
        cls.seed_tasks[4].status = "in_progress"
        cls.seed_tasks[4].save()
        cls.seed_tasks[4].status = "completed"
        cls.seed_tasks[4].save()

    def _admin_task_payload(self, **overrides):
        payload = {
            "title": "Admin created QA task",
            "description": "Created from the Django admin smoke test",
            "assigned_to": str(self.staff_users[0].pk),
            "related_booking": str(self.bookings[0].pk),
            "status": "pending",
            "due_at_0": "",
            "due_at_1": "",
            "_save": "Save",
            "checklist_items-TOTAL_FORMS": "0",
            "checklist_items-INITIAL_FORMS": "0",
            "checklist_items-MIN_NUM_FORMS": "0",
            "checklist_items-MAX_NUM_FORMS": "1000",
            "comments-TOTAL_FORMS": "0",
            "comments-INITIAL_FORMS": "0",
            "comments-MIN_NUM_FORMS": "0",
            "comments-MAX_NUM_FORMS": "1000",
        }
        payload.update(overrides)
        return payload

    def test_seed_data_matches_requested_shape(self):
        self.assertEqual(User.objects.filter(role="staff").count(), 3)
        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(StaffTask.objects.count(), 5)
        self.assertEqual(StaffTask.objects.filter(status="pending").count(), 2)
        self.assertEqual(StaffTask.objects.filter(status="in_progress").count(), 2)
        self.assertEqual(StaffTask.objects.filter(status="completed").count(), 1)

    def test_title_is_required(self):
        task = StaffTask(
            title="",
            description="Has no title",
            assigned_to=self.staff_users[0],
            status="pending",
        )
        with self.assertRaises(ValidationError) as exc:
            task.full_clean()
        self.assertIn("title", exc.exception.message_dict)

    def test_description_is_currently_required(self):
        task = StaffTask(
            title="Missing description",
            description="",
            assigned_to=self.staff_users[0],
            status="pending",
        )
        with self.assertRaises(ValidationError) as exc:
            task.full_clean()
        self.assertIn("description", exc.exception.message_dict)

    def test_task_can_be_created_without_assigned_user(self):
        task = StaffTask.objects.create(
            title="Unassigned task",
            description="Edge case without assignee",
            assigned_to=None,
            related_booking=self.bookings[0],
            status="pending",
        )
        self.assertIsNone(task.assigned_to)

    def test_invalid_assigned_user_is_rejected_by_validation(self):
        with self.assertRaises(ValidationError) as exc:
            StaffTask.objects.create(
                title="Bad assignee",
                description="Uses a missing user id",
                assigned_to_id=999999,
                status="pending",
            )
        self.assertIn("assigned_to", exc.exception.message_dict)

    def test_invalid_booking_is_rejected_by_validation(self):
        with self.assertRaises(ValidationError) as exc:
            StaffTask.objects.create(
                title="Bad booking",
                description="Uses a missing booking id",
                assigned_to=self.staff_users[0],
                related_booking_id=999999,
                status="pending",
            )
        self.assertIn("related_booking", exc.exception.message_dict)

    def test_past_due_date_is_rejected(self):
        task = StaffTask(
            title="Past due task",
            description="Due date validation should reject this",
            assigned_to=self.staff_users[0],
            due_at=timezone.now() - timedelta(days=1),
            status="pending",
        )
        with self.assertRaises(ValidationError) as exc:
            task.full_clean()
        self.assertIn("due_at", exc.exception.message_dict)

    def test_relationships_work_for_assigned_user_and_booking(self):
        task = self.seed_tasks[0]
        self.assertEqual(task.assigned_to, self.staff_users[0])
        self.assertEqual(task.related_booking, self.bookings[0])
        self.assertIn(task, self.staff_users[0].assigned_tasks.all())
        self.assertIn(task, self.bookings[0].staff_tasks.all())

    def test_admin_can_add_edit_and_delete_task(self):
        self.client.force_login(self.admin_user)

        add_response = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._admin_task_payload(),
            follow=False,
        )
        self.assertEqual(add_response.status_code, 302)

        task = StaffTask.objects.get(title="Admin created QA task")
        self.assertEqual(task.assigned_to, self.staff_users[0])
        self.assertEqual(task.related_booking, self.bookings[0])

        edit_response = self.client.post(
            reverse("admin:crm_stafftask_change", args=[task.pk]),
            data=self._admin_task_payload(
                title="Admin edited QA task",
                description="Edited from the Django admin smoke test",
                assigned_to=str(self.staff_users[1].pk),
                related_booking=str(self.bookings[1].pk),
                status="in_progress",
            ),
            follow=False,
        )
        self.assertEqual(edit_response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.title, "Admin edited QA task")
        self.assertEqual(task.status, "in_progress")
        self.assertEqual(task.assigned_to, self.staff_users[1])
        self.assertEqual(task.related_booking, self.bookings[1])

        delete_response = self.client.post(
            reverse("admin:crm_stafftask_delete", args=[task.pk]),
            data={"post": "yes"},
            follow=False,
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(StaffTask.objects.filter(pk=task.pk).exists())

    def test_admin_changelist_has_status_filter_and_title_search(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("admin:crm_stafftask_changelist"))
        self.assertEqual(response.status_code, 200)

        model_admin = admin.site._registry[StaffTask]
        self.assertEqual(model_admin.list_filter, ('status',))
        self.assertEqual(model_admin.search_fields, ('title',))

    def test_admin_rejects_empty_title(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._admin_task_payload(title=""),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")

    def test_admin_rejects_blank_description(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._admin_task_payload(description=""),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")

    def test_staff_task_api_endpoints_are_exposed(self):
        api_client = APIClient()
        api_client.force_authenticate(user=self.admin_user)
        task = self.seed_tasks[0]

        list_response = api_client.get("/api/v1/admin/tasks/staff-tasks/")
        self.assertEqual(list_response.status_code, 200)

        create_response = api_client.post(
            "/api/v1/admin/tasks/staff-tasks/",
            {
                "title": "API created task",
                "description": "Created via API",
                "assigned_to_id": self.staff_users[0].pk,
                "related_booking_id": self.bookings[0].pk,
                "status": "pending",
                "due_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        patch_response = api_client.patch(
            f"/api/v1/admin/tasks/staff-tasks/{task.pk}/",
            {"status": "in_progress"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)

        delete_response = api_client.delete(f"/api/v1/admin/tasks/staff-tasks/{task.pk}/")
        self.assertEqual(delete_response.status_code, 204)

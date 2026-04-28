from datetime import timedelta

from django.contrib import admin
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from catalog.models import Vehicle, VehicleModel, VehicleType
from crm.models import StaffTask
from users.models import User


class AdminSmokeBase(TestCase):
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
        cls.vehicle_type = VehicleType.objects.create(code="scooter", name="Scooter")
        cls.vehicle_model = VehicleModel.objects.create(
            name="NMax",
            brand="Yamaha",
            type=cls.vehicle_type,
            engine_cc=155,
            transmission="automatic",
            fuel_consumption=2.1,
            year=2024,
            trunk="medium",
            helmets_count=2,
            description="Base model",
            rental_terms="Base terms",
        )
        cls.vehicle = Vehicle.objects.create(
            model=cls.vehicle_model,
            title="Base Vehicle",
            slug="base-vehicle",
            sku="BASE-001",
            color="black",
            base_price_usd="25.00",
            status="available",
        )
        now = timezone.now()
        cls.booking = Booking.objects.create(
            public_number="BK-BASE-001",
            user=cls.staff_users[0],
            vehicle=cls.vehicle,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=3),
            payment_method="online_card",
            subtotal_usd="50.00",
            addons_total_usd="0.00",
            discount_usd="0.00",
            markup_usd="0.00",
            total_usd="50.00",
            total_display="$50.00",
            status="created",
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def _empty_inline(self, prefix):
        return {
            f"{prefix}-TOTAL_FORMS": "0",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

    def _assert_admin_field_error(self, response, field_name):
        self.assertEqual(response.status_code, 200)
        self.assertIn("adminform", response.context)
        self.assertIn(field_name, response.context["adminform"].form.errors)

    def _assert_not_in_changelist_result(self, response, obj):
        self.assertEqual(response.status_code, 200)
        self.assertIn("cl", response.context)
        self.assertFalse(any(item.pk == obj.pk for item in response.context["cl"].result_list))

    def _booking_payload(self, **overrides):
        now = timezone.now()
        payload = {
            "public_number": "BK-ADMIN-001",
            "user": str(self.staff_users[1].pk),
            "vehicle": str(self.vehicle.pk),
            "start_at_0": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
            "start_at_1": "10:00:00",
            "end_at_0": (now + timedelta(days=4)).strftime("%Y-%m-%d"),
            "end_at_1": "11:00:00",
            "delivery_address": "",
            "delivery_time_0": "",
            "delivery_time_1": "",
            "delivery_price_usd": "0.00",
            "payment_method": "online_card",
            "payment_status": "pending",
            "currency": "USD",
            "subtotal_usd": "75.00",
            "addons_total_usd": "0.00",
            "discount_usd": "0.00",
            "markup_usd": "0.00",
            "total_usd": "75.00",
            "total_display": "$75.00",
            "status": "created",
            "expires_at_0": "",
            "expires_at_1": "",
            "_save": "Save",
        }
        payload.update(self._empty_inline("addons"))
        payload.update(self._empty_inline("status_history"))
        payload.update(overrides)
        return payload

    def _staff_task_payload(self, **overrides):
        now = timezone.now()
        payload = {
            "title": "Admin task",
            "description": "Created through admin",
            "assigned_to": str(self.staff_users[0].pk),
            "related_booking": str(self.booking.pk),
            "status": "pending",
            "due_at_0": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
            "due_at_1": "09:00:00",
            "_save": "Save",
        }
        payload.update(self._empty_inline("checklist_items"))
        payload.update(self._empty_inline("comments"))
        payload.update(overrides)
        return payload

    def _vehicle_payload(self, **overrides):
        payload = {
            "model": str(self.vehicle_model.pk),
            "title": "Admin Vehicle",
            "slug": "admin-vehicle",
            "sku": "ADMIN-VEH-001",
            "color": "white",
            "base_price_usd": "30.00",
            "status": "available",
            "mileage": "100",
            "rating_avg": "4.5",
            "reviews_count": "7",
            "is_featured": "on",
            "_save": "Save",
        }
        payload.update(self._empty_inline("images"))
        payload.update(self._empty_inline("translations"))
        payload.update(overrides)
        return payload


class CatalogAdminSmokeTests(AdminSmokeBase):
    def test_vehicle_type_admin_crud_and_validation(self):
        list_response = self.client.get(reverse("admin:catalog_vehicletype_changelist"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Scooter")

        add_response = self.client.post(
            reverse("admin:catalog_vehicletype_add"),
            data={"code": "bike", "name": "Bike", "_save": "Save"},
        )
        self.assertEqual(add_response.status_code, 302)
        vehicle_type = VehicleType.objects.get(code="bike")

        edit_response = self.client.post(
            reverse("admin:catalog_vehicletype_change", args=[vehicle_type.pk]),
            data={"code": "bike-upd", "name": "Bike Updated", "_save": "Save"},
        )
        self.assertEqual(edit_response.status_code, 302)
        vehicle_type.refresh_from_db()
        self.assertEqual(vehicle_type.code, "bike-upd")
        self.assertEqual(vehicle_type.name, "Bike Updated")

        invalid_required = self.client.post(
            reverse("admin:catalog_vehicletype_add"),
            data={"code": "", "name": "Broken", "_save": "Save"},
        )
        self._assert_admin_field_error(invalid_required, "code")

        duplicate_response = self.client.post(
            reverse("admin:catalog_vehicletype_add"),
            data={"code": self.vehicle_type.code, "name": "Duplicate", "_save": "Save"},
        )
        self._assert_admin_field_error(duplicate_response, "code")

        delete_response = self.client.post(
            reverse("admin:catalog_vehicletype_delete", args=[vehicle_type.pk]),
            data={"post": "yes"},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(VehicleType.objects.filter(pk=vehicle_type.pk).exists())
        post_delete_list = self.client.get(reverse("admin:catalog_vehicletype_changelist"))
        self._assert_not_in_changelist_result(post_delete_list, vehicle_type)

        model_admin = admin.site._registry[VehicleType]
        self.assertEqual(model_admin.search_fields, ())
        self.assertEqual(model_admin.list_filter, ())

    def test_vehicle_model_admin_crud_and_validation(self):
        list_response = self.client.get(reverse("admin:catalog_vehiclemodel_changelist"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Yamaha NMax")

        add_response = self.client.post(
            reverse("admin:catalog_vehiclemodel_add"),
            data={
                "name": "PCX",
                "brand": "Honda",
                "type": str(self.vehicle_type.pk),
                "engine_cc": "160",
                "transmission": "automatic",
                "fuel_consumption": "2.0",
                "year": "2025",
                "trunk": "large",
                "helmets_count": "2",
                "description": "PCX model",
                "rental_terms": "PCX terms",
                "_save": "Save",
            },
        )
        self.assertEqual(add_response.status_code, 302)
        vehicle_model = VehicleModel.objects.get(name="PCX")

        edit_response = self.client.post(
            reverse("admin:catalog_vehiclemodel_change", args=[vehicle_model.pk]),
            data={
                "name": "PCX Updated",
                "brand": "Honda",
                "type": str(self.vehicle_type.pk),
                "engine_cc": "165",
                "transmission": "automatic",
                "fuel_consumption": "2.2",
                "year": "2026",
                "trunk": "x-large",
                "helmets_count": "3",
                "description": "Updated PCX model",
                "rental_terms": "Updated terms",
                "_save": "Save",
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        vehicle_model.refresh_from_db()
        self.assertEqual(vehicle_model.name, "PCX Updated")
        self.assertEqual(vehicle_model.engine_cc, 165)
        change_page = self.client.get(reverse("admin:catalog_vehiclemodel_change", args=[vehicle_model.pk]))
        self.assertContains(change_page, "PCX Updated")

        invalid_required = self.client.post(
            reverse("admin:catalog_vehiclemodel_add"),
            data={
                "name": "",
                "brand": "Broken",
                "type": str(self.vehicle_type.pk),
                "engine_cc": "125",
                "transmission": "automatic",
                "fuel_consumption": "1.9",
                "year": "2024",
                "trunk": "small",
                "helmets_count": "1",
                "description": "Broken",
                "rental_terms": "Broken",
                "_save": "Save",
            },
        )
        self._assert_admin_field_error(invalid_required, "name")

        invalid_fk = self.client.post(
            reverse("admin:catalog_vehiclemodel_add"),
            data={
                "name": "Bad FK",
                "brand": "Honda",
                "type": "999999",
                "engine_cc": "160",
                "transmission": "automatic",
                "fuel_consumption": "2.0",
                "year": "2025",
                "trunk": "large",
                "helmets_count": "2",
                "description": "Bad FK",
                "rental_terms": "Bad FK",
                "_save": "Save",
            },
        )
        self._assert_admin_field_error(invalid_fk, "type")

        duplicate_allowed = self.client.post(
            reverse("admin:catalog_vehiclemodel_add"),
            data={
                "name": self.vehicle_model.name,
                "brand": self.vehicle_model.brand,
                "type": str(self.vehicle_type.pk),
                "engine_cc": str(self.vehicle_model.engine_cc),
                "transmission": self.vehicle_model.transmission,
                "fuel_consumption": str(self.vehicle_model.fuel_consumption),
                "year": str(self.vehicle_model.year),
                "trunk": self.vehicle_model.trunk,
                "helmets_count": str(self.vehicle_model.helmets_count),
                "description": self.vehicle_model.description,
                "rental_terms": self.vehicle_model.rental_terms,
                "_save": "Save",
            },
        )
        self.assertEqual(duplicate_allowed.status_code, 302)

        delete_response = self.client.post(
            reverse("admin:catalog_vehiclemodel_delete", args=[vehicle_model.pk]),
            data={"post": "yes"},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(VehicleModel.objects.filter(pk=vehicle_model.pk).exists())
        post_delete_list = self.client.get(reverse("admin:catalog_vehiclemodel_changelist"))
        self._assert_not_in_changelist_result(post_delete_list, vehicle_model)

        model_admin = admin.site._registry[VehicleModel]
        self.assertEqual(model_admin.search_fields, ())
        self.assertEqual(model_admin.list_filter, ())

    def test_vehicle_admin_crud_validation_filter_and_search(self):
        list_response = self.client.get(reverse("admin:catalog_vehicle_changelist"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Base Vehicle")

        add_response = self.client.post(
            reverse("admin:catalog_vehicle_add"),
            data=self._vehicle_payload(),
        )
        self.assertEqual(add_response.status_code, 302)
        vehicle = Vehicle.objects.get(sku="ADMIN-VEH-001")

        edit_response = self.client.post(
            reverse("admin:catalog_vehicle_change", args=[vehicle.pk]),
            data=self._vehicle_payload(
                title="Admin Vehicle Updated",
                slug="admin-vehicle-updated",
                sku="ADMIN-VEH-001-UPD",
                status="maintenance",
                is_featured="",
            ),
        )
        self.assertEqual(edit_response.status_code, 302)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.title, "Admin Vehicle Updated")
        self.assertEqual(vehicle.status, "maintenance")
        self.assertFalse(vehicle.is_featured)
        change_page = self.client.get(reverse("admin:catalog_vehicle_change", args=[vehicle.pk]))
        self.assertContains(change_page, "Admin Vehicle Updated")
        self.assertContains(change_page, "ADMIN-VEH-001-UPD")

        invalid_required = self.client.post(
            reverse("admin:catalog_vehicle_add"),
            data=self._vehicle_payload(title="", slug="blank-title-vehicle", sku="ADMIN-VEH-002"),
        )
        self._assert_admin_field_error(invalid_required, "title")

        invalid_number = self.client.post(
            reverse("admin:catalog_vehicle_add"),
            data=self._vehicle_payload(
                slug="bad-price-vehicle",
                sku="ADMIN-VEH-005",
                base_price_usd="abc",
            ),
        )
        self._assert_admin_field_error(invalid_number, "base_price_usd")

        duplicate_response = self.client.post(
            reverse("admin:catalog_vehicle_add"),
            data=self._vehicle_payload(slug=self.vehicle.slug, sku="ADMIN-VEH-003"),
        )
        self._assert_admin_field_error(duplicate_response, "slug")

        invalid_fk = self.client.post(
            reverse("admin:catalog_vehicle_add"),
            data=self._vehicle_payload(model="999999", slug="bad-fk-vehicle", sku="ADMIN-VEH-004"),
        )
        self._assert_admin_field_error(invalid_fk, "model")

        searchable_vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title="Searchable QA Vehicle",
            slug="searchable-qa-vehicle",
            sku="SEARCH-001",
            color="red",
            base_price_usd="31.00",
            status="available",
        )
        other_vehicle = Vehicle.objects.create(
            model=self.vehicle_model,
            title="Non Matching Vehicle",
            slug="non-matching-vehicle",
            sku="SEARCH-002",
            color="blue",
            base_price_usd="29.00",
            status="inactive",
        )

        filter_response = self.client.get(
            reverse("admin:catalog_vehicle_changelist"),
            data={"status__exact": "available"},
        )
        self.assertContains(filter_response, searchable_vehicle.title)
        self.assertNotContains(filter_response, other_vehicle.title)

        search_response = self.client.get(
            reverse("admin:catalog_vehicle_changelist"),
            data={"q": "Searchable QA Vehicle"},
        )
        self.assertContains(search_response, searchable_vehicle.title)
        self.assertNotContains(search_response, other_vehicle.title)

        delete_response = self.client.post(
            reverse("admin:catalog_vehicle_delete", args=[vehicle.pk]),
            data={"post": "yes"},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())
        post_delete_list = self.client.get(reverse("admin:catalog_vehicle_changelist"))
        self._assert_not_in_changelist_result(post_delete_list, vehicle)


class BookingAdminSmokeTests(AdminSmokeBase):
    def test_booking_admin_crud_validation_filter_and_search(self):
        list_response = self.client.get(reverse("admin:bookings_booking_changelist"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.booking.public_number)

        add_response = self.client.post(
            reverse("admin:bookings_booking_add"),
            data=self._booking_payload(),
        )
        self.assertEqual(add_response.status_code, 302)
        booking = Booking.objects.get(public_number="BK-ADMIN-001")

        edit_response = self.client.post(
            reverse("admin:bookings_booking_change", args=[booking.pk]),
            data=self._booking_payload(
                public_number="BK-ADMIN-001-UPD",
                status="confirmed",
                payment_status="paid",
                total_usd="99.00",
                total_display="$99.00",
            ),
        )
        self.assertEqual(edit_response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.public_number, "BK-ADMIN-001-UPD")
        self.assertEqual(booking.status, "confirmed")
        self.assertEqual(str(booking.total_usd), "99.00")
        change_page = self.client.get(reverse("admin:bookings_booking_change", args=[booking.pk]))
        self.assertContains(change_page, "BK-ADMIN-001-UPD")
        self.assertContains(change_page, "99.00")

        invalid_required = self.client.post(
            reverse("admin:bookings_booking_add"),
            data=self._booking_payload(public_number=""),
        )
        self._assert_admin_field_error(invalid_required, "public_number")

        invalid_number = self.client.post(
            reverse("admin:bookings_booking_add"),
            data=self._booking_payload(public_number="BK-BAD-NUM", total_usd="abc"),
        )
        self._assert_admin_field_error(invalid_number, "total_usd")

        duplicate_response = self.client.post(
            reverse("admin:bookings_booking_add"),
            data=self._booking_payload(public_number=self.booking.public_number),
        )
        self._assert_admin_field_error(duplicate_response, "public_number")

        invalid_fk_user = self.client.post(
            reverse("admin:bookings_booking_add"),
            data=self._booking_payload(public_number="BK-BAD-USER", user="999999"),
        )
        self._assert_admin_field_error(invalid_fk_user, "user")

        invalid_fk_vehicle = self.client.post(
            reverse("admin:bookings_booking_add"),
            data=self._booking_payload(public_number="BK-BAD-VEH", vehicle="999999"),
        )
        self._assert_admin_field_error(invalid_fk_vehicle, "vehicle")

        searchable_booking = Booking.objects.create(
            public_number="BK-SEARCH-001",
            user=self.staff_users[1],
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=6),
            end_at=timezone.now() + timedelta(days=8),
            payment_method="cash_on_delivery",
            subtotal_usd="88.00",
            addons_total_usd="0.00",
            discount_usd="0.00",
            markup_usd="0.00",
            total_usd="88.00",
            total_display="$88.00",
            status="confirmed",
        )
        other_booking = Booking.objects.create(
            public_number="BK-SEARCH-002",
            user=self.staff_users[2],
            vehicle=self.vehicle,
            start_at=timezone.now() + timedelta(days=7),
            end_at=timezone.now() + timedelta(days=9),
            payment_method="online_card",
            subtotal_usd="77.00",
            addons_total_usd="0.00",
            discount_usd="0.00",
            markup_usd="0.00",
            total_usd="77.00",
            total_display="$77.00",
            status="cancelled",
        )

        filter_response = self.client.get(
            reverse("admin:bookings_booking_changelist"),
            data={"status__exact": "confirmed"},
        )
        self.assertContains(filter_response, searchable_booking.public_number)
        self.assertNotContains(filter_response, other_booking.public_number)

        search_response = self.client.get(
            reverse("admin:bookings_booking_changelist"),
            data={"q": "BK-SEARCH-001"},
        )
        self.assertContains(search_response, searchable_booking.public_number)
        self.assertNotContains(search_response, other_booking.public_number)

        delete_response = self.client.post(
            reverse("admin:bookings_booking_delete", args=[booking.pk]),
            data={"post": "yes"},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Booking.objects.filter(pk=booking.pk).exists())
        post_delete_list = self.client.get(reverse("admin:bookings_booking_changelist"))
        self._assert_not_in_changelist_result(post_delete_list, booking)


class StaffTaskAdminSmokeTests(AdminSmokeBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        now = timezone.now()
        cls.pending_task = StaffTask.objects.create(
            title="Pending admin task",
            description="Pending state",
            assigned_to=cls.staff_users[0],
            related_booking=cls.booking,
            due_at=now + timedelta(days=1),
        )
        cls.in_progress_task = StaffTask.objects.create(
            title="In progress admin task",
            description="In progress state",
            assigned_to=cls.staff_users[1],
            related_booking=cls.booking,
            due_at=now + timedelta(days=2),
        )
        cls.in_progress_task.status = "in_progress"
        cls.in_progress_task.save()
        cls.completed_task = StaffTask.objects.create(
            title="Completed admin task",
            description="Completed state",
            assigned_to=cls.staff_users[2],
            related_booking=cls.booking,
            due_at=now + timedelta(days=3),
        )
        cls.completed_task.status = "in_progress"
        cls.completed_task.save()
        cls.completed_task.status = "completed"
        cls.completed_task.save()

    def test_staff_task_admin_crud_relationships_and_edge_cases(self):
        list_response = self.client.get(reverse("admin:crm_stafftask_changelist"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.pending_task.title)
        self.assertContains(list_response, self.in_progress_task.title)
        self.assertContains(list_response, self.completed_task.title)

        add_response = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(),
        )
        self.assertEqual(add_response.status_code, 302)
        task = StaffTask.objects.get(title="Admin task")

        edit_response = self.client.post(
            reverse("admin:crm_stafftask_change", args=[task.pk]),
            data=self._staff_task_payload(
                title="Admin task updated",
                assigned_to=str(self.staff_users[1].pk),
                status="in_progress",
            ),
        )
        self.assertEqual(edit_response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.title, "Admin task updated")
        self.assertEqual(task.assigned_to, self.staff_users[1])
        self.assertEqual(task.status, "in_progress")
        change_page = self.client.get(reverse("admin:crm_stafftask_change", args=[task.pk]))
        self.assertContains(change_page, "Admin task updated")

        unassigned_response = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(
                title="Unassigned admin task",
                assigned_to="",
                status="pending",
            ),
        )
        self.assertEqual(unassigned_response.status_code, 302)
        unassigned_task = StaffTask.objects.get(title="Unassigned admin task")
        self.assertIsNone(unassigned_task.assigned_to)

        past_due_response = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(
                title="Past due admin task",
                due_at_0=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                due_at_1="08:00:00",
            ),
        )
        self._assert_admin_field_error(past_due_response, "due_at")

        invalid_required = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(title=""),
        )
        self._assert_admin_field_error(invalid_required, "title")

        invalid_date = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(
                title="Bad date task",
                due_at_0="not-a-date",
                due_at_1="09:00:00",
            ),
        )
        self._assert_admin_field_error(invalid_date, "due_at")

        invalid_fk_user = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(title="Bad user task", assigned_to="999999"),
        )
        self._assert_admin_field_error(invalid_fk_user, "assigned_to")

        invalid_fk_booking = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(title="Bad booking task", related_booking="999999"),
        )
        self._assert_admin_field_error(invalid_fk_booking, "related_booking")

        duplicate_allowed = self.client.post(
            reverse("admin:crm_stafftask_add"),
            data=self._staff_task_payload(title=self.pending_task.title),
        )
        self.assertEqual(duplicate_allowed.status_code, 302)

        self.assertIn(self.pending_task, self.staff_users[0].assigned_tasks.all())
        self.assertIn(self.pending_task, self.booking.staff_tasks.all())

        delete_response = self.client.post(
            reverse("admin:crm_stafftask_delete", args=[task.pk]),
            data={"post": "yes"},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(StaffTask.objects.filter(pk=task.pk).exists())
        post_delete_list = self.client.get(reverse("admin:crm_stafftask_changelist"))
        self._assert_not_in_changelist_result(post_delete_list, task)

        model_admin = admin.site._registry[StaffTask]
        self.assertEqual(model_admin.list_filter, ('status',))
        self.assertEqual(model_admin.search_fields, ('title',))

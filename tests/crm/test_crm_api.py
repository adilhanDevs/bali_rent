from datetime import timedelta

import pytest
from django.utils import timezone

from crm.models import (
    CustomerInteraction,
    CustomerNote,
    CustomerProfile,
    CustomerSegment,
    StaffTask,
    TaskChecklistItem,
    TaskComment,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def vip_segment():
    return CustomerSegment.objects.create(code="vip", name="VIP", discount_percent="10.00")


@pytest.fixture
def regular_segment():
    return CustomerSegment.objects.create(code="regular", name="Regular", discount_percent="5.00")


@pytest.fixture
def customer_profile(user, vip_segment):
    return CustomerProfile.objects.create(user=user, segment=vip_segment)


@pytest.fixture
def second_customer_profile(regular_segment):
    from django.contrib.auth import get_user_model

    other_user = get_user_model().objects.create_user(
        username="crm-customer",
        email="crm-customer@example.com",
        password="testpass123",
        full_name="CRM Customer",
        phone="+996555000111",
        role="client",
    )
    return CustomerProfile.objects.create(user=other_user, segment=regular_segment)


def test_admin_customer_segments_crud(admin_client):
    list_response = admin_client.get("/api/v1/admin/crm/customer-segments/")
    assert list_response.status_code == 200

    create_response = admin_client.post(
        "/api/v1/admin/crm/customer-segments/",
        {"code": "gold", "name": "Gold", "discount_percent": "15.50"},
        format="json",
    )
    assert create_response.status_code == 201
    segment_id = create_response.data["id"]

    detail_response = admin_client.get(f"/api/v1/admin/crm/customer-segments/{segment_id}/")
    assert detail_response.status_code == 200
    assert detail_response.data["code"] == "gold"

    patch_response = admin_client.patch(
        f"/api/v1/admin/crm/customer-segments/{segment_id}/",
        {"name": "Gold Plus"},
        format="json",
    )
    assert patch_response.status_code == 200
    assert patch_response.data["name"] == "Gold Plus"

    delete_response = admin_client.delete(f"/api/v1/admin/crm/customer-segments/{segment_id}/")
    assert delete_response.status_code == 204

    missing_response = admin_client.get(f"/api/v1/admin/crm/customer-segments/{segment_id}/")
    assert missing_response.status_code == 404


def test_customer_profiles_filter_search_pagination_and_permissions(
    admin_client,
    staff_client,
    auth_client,
    customer_profile,
    second_customer_profile,
    vip_segment,
    regular_segment,
):
    third_user_email = "crm-third@example.com"
    from django.contrib.auth import get_user_model

    third_user = get_user_model().objects.create_user(
        username=third_user_email,
        email=third_user_email,
        password="testpass123",
        full_name="Segment Search",
        phone="+996555000222",
        role="client",
    )
    CustomerProfile.objects.create(user=third_user, segment=vip_segment)

    page_response = admin_client.get("/api/v1/admin/crm/customer-profiles/?page_size=1")
    assert page_response.status_code == 200
    assert page_response.data["count"] >= 3
    assert len(page_response.data["results"]) == 1
    assert page_response.data["next"]

    search_response = admin_client.get("/api/v1/admin/crm/customer-profiles/?search=Segment Search")
    assert search_response.status_code == 200
    assert search_response.data["count"] == 1

    filter_response = admin_client.get(f"/api/v1/admin/crm/customer-profiles/?segment={regular_segment.id}")
    assert filter_response.status_code == 200
    assert filter_response.data["count"] == 1
    assert filter_response.data["results"][0]["id"] == second_customer_profile.id

    staff_list = staff_client.get("/api/v1/admin/crm/customer-profiles/")
    assert staff_list.status_code == 200

    staff_create = staff_client.post(
        "/api/v1/admin/crm/customer-profiles/",
        {"user_id": customer_profile.user_id, "segment_id": vip_segment.id},
        format="json",
    )
    assert staff_create.status_code == 403

    client_forbidden = auth_client.get("/api/v1/admin/crm/customer-profiles/")
    assert client_forbidden.status_code == 403


def test_customer_note_and_interaction_crud_and_validation(
    admin_client,
    manager_user,
    customer_profile,
):
    note_response = admin_client.post(
        "/api/v1/admin/crm/customer-notes/",
        {"customer_id": customer_profile.id, "text": "First note"},
        format="json",
    )
    assert note_response.status_code == 201
    note_id = note_response.data["id"]
    assert note_response.data["author"]["id"] != 0

    invalid_note = admin_client.post(
        "/api/v1/admin/crm/customer-notes/",
        {"customer_id": 999999, "text": "Broken"},
        format="json",
    )
    assert invalid_note.status_code == 400
    assert "customer_id" in invalid_note.data

    interaction_response = admin_client.post(
        "/api/v1/admin/crm/customer-interactions/",
        {
            "customer_id": customer_profile.id,
            "interaction_type": "chat",
            "description": "Reached out in messenger",
            "created_by_id": manager_user.id,
        },
        format="json",
    )
    assert interaction_response.status_code == 201
    interaction_id = interaction_response.data["id"]

    patch_response = admin_client.patch(
        f"/api/v1/admin/crm/customer-interactions/{interaction_id}/",
        {"description": "Updated chat summary"},
        format="json",
    )
    assert patch_response.status_code == 200

    delete_response = admin_client.delete(f"/api/v1/admin/crm/customer-notes/{note_id}/")
    assert delete_response.status_code == 204

    assert CustomerNote.objects.filter(pk=note_id).exists() is False
    assert CustomerInteraction.objects.filter(pk=interaction_id).exists() is True


def test_tasks_workflow_checklist_comments_and_validation(
    admin_client,
    manager_user,
    booking,
):
    due_at = (timezone.now() + timedelta(days=2)).isoformat()
    create_task = admin_client.post(
        "/api/v1/admin/tasks/staff-tasks/",
        {
            "title": "Prepare booking",
            "description": "Check scooter before delivery",
            "assigned_to_id": manager_user.id,
            "related_booking_id": booking.id,
            "due_at": due_at,
        },
        format="json",
    )
    assert create_task.status_code == 201
    task_id = create_task.data["id"]

    detail_response = admin_client.get(f"/api/v1/admin/tasks/staff-tasks/{task_id}/")
    assert detail_response.status_code == 200

    move_in_progress = admin_client.patch(
        f"/api/v1/admin/tasks/staff-tasks/{task_id}/",
        {"status": "in_progress"},
        format="json",
    )
    assert move_in_progress.status_code == 200

    checklist_response = admin_client.post(
        "/api/v1/admin/tasks/checklist-items/",
        {"task_id": task_id, "title": "Battery check", "sort_order": 1},
        format="json",
    )
    assert checklist_response.status_code == 201
    checklist_id = checklist_response.data["id"]

    blocked_complete = admin_client.patch(
        f"/api/v1/admin/tasks/staff-tasks/{task_id}/",
        {"status": "completed"},
        format="json",
    )
    assert blocked_complete.status_code == 400
    assert "status" in blocked_complete.data

    complete_item = admin_client.patch(
        f"/api/v1/admin/tasks/checklist-items/{checklist_id}/",
        {"is_completed": True},
        format="json",
    )
    assert complete_item.status_code == 200

    comment_response = admin_client.post(
        "/api/v1/admin/tasks/comments/",
        {"task_id": task_id, "text": "Checklist finished"},
        format="json",
    )
    assert comment_response.status_code == 201
    comment_id = comment_response.data["id"]

    finish_task = admin_client.patch(
        f"/api/v1/admin/tasks/staff-tasks/{task_id}/",
        {"status": "completed"},
        format="json",
    )
    assert finish_task.status_code == 200
    assert finish_task.data["status"] == "completed"

    delete_comment = admin_client.delete(f"/api/v1/admin/tasks/comments/{comment_id}/")
    assert delete_comment.status_code == 204

    missing_comment = admin_client.get("/api/v1/admin/tasks/comments/999999/")
    assert missing_comment.status_code == 404


def test_tasks_permissions_and_validation_errors(
    admin_client,
    staff_client,
    auth_client,
):
    invalid_task = admin_client.post(
        "/api/v1/admin/tasks/staff-tasks/",
        {
            "title": "Bad task",
            "description": "Past date",
            "status": "completed",
            "due_at": (timezone.now() - timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert invalid_task.status_code == 400
    assert "due_at" in invalid_task.data or "status" in invalid_task.data

    invalid_checklist = admin_client.post(
        "/api/v1/admin/tasks/checklist-items/",
        {"task_id": 999999, "title": "Ghost"},
        format="json",
    )
    assert invalid_checklist.status_code == 400
    assert "task_id" in invalid_checklist.data

    staff_read = staff_client.get("/api/v1/admin/tasks/staff-tasks/")
    assert staff_read.status_code == 200

    staff_write = staff_client.post(
        "/api/v1/admin/tasks/staff-tasks/",
        {"title": "Forbidden", "description": "Should fail"},
        format="json",
    )
    assert staff_write.status_code == 403

    client_forbidden = auth_client.get("/api/v1/admin/tasks/staff-tasks/")
    assert client_forbidden.status_code == 403


def test_crm_404_deleted_duplicate_and_long_field_cases(
    admin_client,
    customer_profile,
    vip_segment,
):
    missing_segment = admin_client.get("/api/v1/admin/crm/customer-segments/999999/")
    assert missing_segment.status_code == 404

    create_segment = admin_client.post(
        "/api/v1/admin/crm/customer-segments/",
        {"code": "dup-code", "name": "Duplicate", "discount_percent": "1.00"},
        format="json",
    )
    assert create_segment.status_code == 201
    segment_id = create_segment.data["id"]

    duplicate_segment = admin_client.post(
        "/api/v1/admin/crm/customer-segments/",
        {"code": "dup-code", "name": "Duplicate 2", "discount_percent": "2.00"},
        format="json",
    )
    assert duplicate_segment.status_code == 400
    assert "code" in duplicate_segment.data

    long_task_title = admin_client.post(
        "/api/v1/admin/tasks/staff-tasks/",
        {"title": "x" * 256, "description": "Too long"},
        format="json",
    )
    assert long_task_title.status_code == 400
    assert "title" in long_task_title.data

    delete_response = admin_client.delete(f"/api/v1/admin/crm/customer-segments/{segment_id}/")
    assert delete_response.status_code == 204

    deleted_segment = admin_client.get(f"/api/v1/admin/crm/customer-segments/{segment_id}/")
    assert deleted_segment.status_code == 404

    duplicate_profile = admin_client.post(
        "/api/v1/admin/crm/customer-profiles/",
        {"user_id": customer_profile.user_id, "segment_id": vip_segment.id},
        format="json",
    )
    assert duplicate_profile.status_code == 400
    assert "user_id" in duplicate_profile.data


def test_crm_empty_payloads_partial_updates_and_invalid_foreign_keys(
    admin_client,
    customer_profile,
    regular_segment,
):
    empty_note = admin_client.post("/api/v1/admin/crm/customer-notes/", {}, format="json")
    assert empty_note.status_code == 400
    assert "customer_id" in empty_note.data

    partial_profile_patch = admin_client.patch(
        f"/api/v1/admin/crm/customer-profiles/{customer_profile.id}/",
        {"segment_id": regular_segment.id},
        format="json",
    )
    assert partial_profile_patch.status_code == 200
    assert partial_profile_patch.data["segment"]["id"] == regular_segment.id

    bad_interaction = admin_client.post(
        "/api/v1/admin/crm/customer-interactions/",
        {"customer_id": 999999, "interaction_type": "call", "description": "Missing customer"},
        format="json",
    )
    assert bad_interaction.status_code == 400
    assert "customer_id" in bad_interaction.data

    bad_comment = admin_client.post(
        "/api/v1/admin/tasks/comments/",
        {"task_id": 999999, "text": "Ghost task"},
        format="json",
    )
    assert bad_comment.status_code == 400
    assert "task_id" in bad_comment.data


def test_crm_profile_duplicate_update_serializer_path(
    admin_client,
    customer_profile,
    second_customer_profile,
):
    duplicate_user_patch = admin_client.patch(
        f"/api/v1/admin/crm/customer-profiles/{second_customer_profile.id}/",
        {"user_id": customer_profile.user_id},
        format="json",
    )
    assert duplicate_user_patch.status_code == 400
    assert "user_id" in duplicate_user_patch.data


def test_crm_task_transition_serializer_paths(admin_client):
    invalid_new_task = admin_client.post(
        "/api/v1/admin/tasks/staff-tasks/",
        {
            "title": "Wrong start",
            "description": "Must fail",
            "status": "completed",
            "due_at": (timezone.now() + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert invalid_new_task.status_code == 400
    assert "status" in invalid_new_task.data

    task = StaffTask.objects.create(
        title="Cancelled",
        description="Cancelled flow",
        due_at=timezone.now() + timedelta(days=1),
    )
    task.status = "cancelled"
    task.save()
    invalid_transition = admin_client.patch(
        f"/api/v1/admin/tasks/staff-tasks/{task.id}/",
        {"status": "pending"},
        format="json",
    )
    assert invalid_transition.status_code == 400
    assert "status" in invalid_transition.data

    completed_task = StaffTask.objects.create(
        title="Completed base",
        description="Completed",
        due_at=timezone.now() + timedelta(days=1),
    )
    completed_task.status = "in_progress"
    completed_task.save()
    TaskChecklistItem.objects.create(task=completed_task, title="Must stay done", is_completed=True)
    completed_task.status = "completed"
    completed_task.save()
    invalid_item_create = admin_client.post(
        "/api/v1/admin/tasks/checklist-items/",
        {"task_id": completed_task.id, "title": "Late incomplete", "is_completed": False},
        format="json",
    )
    assert invalid_item_create.status_code == 400
    assert "is_completed" in invalid_item_create.data


@pytest.mark.django_db(transaction=True)
def test_task_status_rollback_when_completion_fails(admin_client):
    task = StaffTask.objects.create(
        title="Rollback Task",
        description="Should stay in progress",
        status="pending",
        due_at=timezone.now() + timedelta(days=1),
    )
    task.status = "in_progress"
    task.save()
    TaskChecklistItem.objects.create(task=task, title="Incomplete", is_completed=False)

    response = admin_client.patch(
        f"/api/v1/admin/tasks/staff-tasks/{task.id}/",
        {"status": "completed"},
        format="json",
    )
    assert response.status_code == 400

    task.refresh_from_db()
    assert task.status == "in_progress"
    assert task.checklist_items.filter(is_completed=False).count() == 1


def test_crm_list_endpoints_are_query_efficient(
    admin_client,
    customer_profile,
    django_assert_num_queries,
):
    CustomerNote.objects.create(customer=customer_profile, author=customer_profile.user, text="One")
    CustomerInteraction.objects.create(customer=customer_profile, description="Ping", interaction_type="chat")

    with django_assert_num_queries(6, exact=False):
        response = admin_client.get("/api/v1/admin/crm/customer-profiles/")

    assert response.status_code == 200


def test_crm_model_branches_and_string_representations(customer_profile, admin_user):
    note = CustomerNote.objects.create(customer=customer_profile, author=admin_user, text="Readable note")
    interaction = CustomerInteraction.objects.create(
        customer=customer_profile,
        interaction_type="email",
        description="Readable interaction",
        created_by=admin_user,
    )
    task = StaffTask.objects.create(
        title="Cancelable task",
        description="Task text",
        due_at=timezone.now() + timedelta(days=1),
    )
    checklist = TaskChecklistItem.objects.create(task=task, title="Check me", is_completed=True)
    comment = TaskComment.objects.create(task=task, author=admin_user, text="Readable comment")

    assert str(customer_profile.segment) == "VIP"
    assert "Note for" in str(note)
    assert "Email for" in str(interaction)
    assert str(task) == "Cancelable task"
    assert str(checklist) == "Check me"
    assert "Comment on" in str(comment)

    task.status = "cancelled"
    task.save()
    task.status = "in_progress"
    with pytest.raises(Exception):
        task.save()

    task.status = "completed"
    task.pk = None
    with pytest.raises(Exception):
        task.save()


def test_crm_checklist_and_comment_update_paths(admin_client, admin_user):
    task = StaffTask.objects.create(
        title="Completed task",
        description="Done",
        due_at=timezone.now() + timedelta(days=1),
    )
    task.status = "in_progress"
    task.save()
    item = TaskChecklistItem.objects.create(task=task, title="Done item", is_completed=True)
    task.status = "completed"
    task.save()

    bad_item_patch = admin_client.patch(
        f"/api/v1/admin/tasks/checklist-items/{item.id}/",
        {"is_completed": False},
        format="json",
    )
    assert bad_item_patch.status_code == 400
    assert "is_completed" in bad_item_patch.data

    comment = TaskComment.objects.create(task=task, author=admin_user, text="Before update")
    patch_comment = admin_client.patch(
        f"/api/v1/admin/tasks/comments/{comment.id}/",
        {"text": "After update"},
        format="json",
    )
    assert patch_comment.status_code == 200

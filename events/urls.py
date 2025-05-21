from django.urls import path

from events.views.event_views import BatchEventCreateView, EventDetailView, EventListCreateView
from events.views.permission_views import EventPermissionDetailView, EventPermissionView
from events.views.version_views import EventChangeLogView, EventDiffView, EventVersionView

urlpatterns = [
    # Event Management
    path("events", EventListCreateView.as_view(), name="event-list-create"),
    path("events/<uuid:pk>", EventDetailView.as_view(), name="event-detail"),
    path("events/batch", BatchEventCreateView.as_view(), name="event-batch-create"),
    # Event Permissions
    path("events/<uuid:event_id>/permissions", EventPermissionView.as_view(), name="event-permissions"),
    path(
        "events/<uuid:event_id>/permissions/<uuid:user_id>",
        EventPermissionDetailView.as_view(),
        name="event-permission-detail",
    ),
    # Version History
    path("events/<uuid:event_id>/history/<int:version_id>", EventVersionView.as_view(), name="event-version"),
    path("events/<uuid:event_id>/changelog", EventChangeLogView.as_view(), name="event-changelog"),
    path("events/<uuid:event_id>/diff/<int:version1>/<int:version2>", EventDiffView.as_view(), name="event-diff"),
    # Collaboration
    path("events/<uuid:event_id>/share", EventPermissionView.as_view(), name="event-share"),
    path("events/<uuid:event_id>/rollback/<int:version_id>", EventVersionView.as_view(), name="event-rollback"),
]

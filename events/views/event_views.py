from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import api_response
from events.models.event import Event
from events.models.event_permission import EventPermission
from events.serializers.event_serializer import BatchEventCreateSerializer, EventSerializer
from events.utils.changelog_utils import create_changelog_entry, get_event_data


class EventPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class EventListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = EventPagination

    def get(self, request):
        # Get all events user has access to
        events = Event.objects.filter(Q(owner=request.user) | Q(permissions__user=request.user)).distinct()

        # Apply filters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            events = events.filter(start_date__gte=start_date)
        if end_date:
            events = events.filter(end_date__lte=end_date)

        # Apply pagination
        paginator = self.pagination_class()
        paginated_events = paginator.paginate_queryset(events, request)
        serializer = EventSerializer(paginated_events, many=True)

        return api_response(code=status.HTTP_200_OK, message="Events retrieved successfully", data=serializer.data)

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save(owner=request.user, created_by=request.user, updated_by=request.user)

            # Create owner permission
            EventPermission.objects.create(event=event, user=request.user, role="owner", granted_by=request.user)

            # Create changelog entry for creation
            create_changelog_entry(
                event=event,
                user=request.user,
                change_type="create",
                previous_data=None,
                new_data=get_event_data(event),
                old_version=None,
                new_version=event,
            )

            return api_response(
                code=status.HTTP_201_CREATED, message="Event created successfully", data=EventSerializer(event).data
            )
        return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)


class EventDetailView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_event(self, pk, user):
        # Get the root event (either the event itself or its parent version)
        event = get_object_or_404(Event, pk=pk)
        root_event = event.parent_version or event

        # Get the latest version of the event
        latest_version = (
            Event.objects.filter(Q(id=root_event.id) | Q(parent_version=root_event)).order_by("-version").first()
        )

        if not user.has_event_permission(latest_version, "view"):
            raise PermissionError("You don't have permission to access this event")
        return latest_version

    def get(self, request, pk):
        try:
            event = self.get_event(pk, request.user)
            serializer = EventSerializer(event)
            return api_response(code=status.HTTP_200_OK, message="Event retrieved successfully", data=serializer.data)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)

    def put(self, request, pk):
        try:
            event = self.get_event(pk, request.user)
            if not request.user.has_event_permission(event, "edit"):
                raise PermissionError("You don't have permission to edit this event")

            # Store previous data for changelog
            previous_data = get_event_data(event)

            serializer = EventSerializer(event, data=request.data, partial=True)
            if serializer.is_valid():
                # Create new version
                new_version = event.create_version(request.user)
                updated_event = serializer.save(updated_by=request.user, version=new_version.version)

                # Create changelog entry for update
                create_changelog_entry(
                    event=updated_event,
                    user=request.user,
                    change_type="update",
                    previous_data=previous_data,
                    new_data=get_event_data(updated_event),
                    old_version=event,
                    new_version=updated_event,
                )

                # Create changelog entries for each changed field
                for field, value in request.data.items():
                    if hasattr(event, field) and getattr(event, field) != value:
                        create_changelog_entry(
                            event=updated_event,
                            user=request.user,
                            change_type="field_update",
                            previous_data={field: getattr(event, field)},
                            new_data={field: value},
                            old_version=event,
                            new_version=updated_event,
                        )

                return api_response(
                    code=status.HTTP_200_OK,
                    message="Event updated successfully",
                    data=EventSerializer(updated_event).data,
                )
            return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)

    def delete(self, request, pk):
        try:
            event = self.get_event(pk, request.user)
            if not request.user.has_event_permission(event, "delete"):
                raise PermissionError("You don't have permission to delete this event")

            # Create changelog entry before deletion
            create_changelog_entry(
                event=event,
                user=request.user,
                change_type="delete",
                previous_data=get_event_data(event),
                new_data=None,
                old_version=event,
                new_version=None,
            )

            event.delete()
            return api_response(code=status.HTTP_204_NO_CONTENT, message="Event deleted successfully", data=None)
        except PermissionError as e:
            return api_response(code=status.HTTP_403_FORBIDDEN, message=str(e), data=None)


class BatchEventCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = BatchEventCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            events = serializer.save()
            # Create permissions and changelog entries for all events
            for event in events:
                EventPermission.objects.create(event=event, user=request.user, role="owner", granted_by=request.user)

                # Create changelog entry for each event
                create_changelog_entry(
                    event=event,
                    user=request.user,
                    change_type="create",
                    previous_data=None,
                    new_data=get_event_data(event),
                    old_version=None,
                    new_version=event,
                )

            return api_response(
                code=status.HTTP_201_CREATED,
                message="Events created successfully",
                data=EventSerializer(events, many=True).data,
            )
        return api_response(code=status.HTTP_400_BAD_REQUEST, message="Invalid data", data=serializer.errors)

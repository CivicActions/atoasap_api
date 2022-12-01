from django.db.models import QuerySet
from django_filters import rest_framework as filters
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from components.filters import ComponentFilter, ComponentPermissionsFilter
from components.models import Component
from components.permissions import ComponentPermissions
from components.serializers import (
    ComponentControlSerializer,
    ComponentListSerializer,
    ComponentSerializer,
)


class ComponentListView(generics.ListCreateAPIView):
    """Use for read-write endpoints to represent a collection of model instances.
    Provides get and post method handlers.
    """

    queryset = Component.objects.all()
    serializer_class = ComponentListSerializer
    permission_classes = [
        ComponentPermissions,
    ]
    filter_backends = [
        ComponentPermissionsFilter,
    ]

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        # Need to apply the order_by after the union in ComponentPermissionsFilter
        return super().filter_queryset(queryset).order_by("pk")


class ComponentDetailView(generics.RetrieveAPIView):
    """
    Use for read or update endpoints to represent a single model instance.
    Provides get, put, and patch method handlers.
    """

    queryset = Component.objects.all()
    permission_classes = [
        ComponentPermissions,
    ]
    serializer_class = ComponentSerializer


class ComponentListSearchView(generics.ListAPIView):
    serializer_class = ComponentListSerializer
    filterset_class = ComponentFilter
    filter_backends = [
        filters.DjangoFilterBackend,
    ]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return Component.objects.exclude(status=Component.Status.SYSTEM).order_by("pk")


class ComponentTypeListView(generics.ListAPIView):
    queryset = Component.objects.values_list("type")
    permission_classes = [
        ComponentPermissions,
    ]
    filter_backends = [
        ComponentPermissionsFilter,
    ]

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset = self.filter_queryset(self.get_queryset())

        return Response(queryset, status=status.HTTP_200_OK)


class ComponentImplementedRequirementView(generics.UpdateAPIView):
    queryset = Component.objects.all()
    permission_classes = [
        ComponentPermissions,
    ]
    serializer_class = ComponentControlSerializer

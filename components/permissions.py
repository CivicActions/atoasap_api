from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView

from components.models import Component
from ratoapi.permissions import StrictDjangoObjectPermissions


class ComponentPermissions(StrictDjangoObjectPermissions):
    def has_object_permission(
        self, request: Request, view: APIView, obj: Component
    ) -> bool:
        if obj.status == Component.Status.PUBLIC and request.method in SAFE_METHODS:
            return True

        return super().has_object_permission(request, view, obj)

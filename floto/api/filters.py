import logging

from django.db.models import Q
from rest_framework import filters

LOG = logging.getLogger(__name__)


class HasReadAccessFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        Filters a queryset to objects are either:
        - public
        - owned by the current user
        """
        return queryset.filter(
            Q(created_by=request.user) | Q(is_public=True)
        )
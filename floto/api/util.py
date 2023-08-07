from django.db.models import Q

def filter_by_created_by_or_public(queryset, request):
    return queryset.filter(Q(created_by=request.user) | Q(is_public=True))

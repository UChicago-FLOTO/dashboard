from .api.serializers import ProjectSerializer
from django.conf import settings


def global_values(request):
    selected_project = None
    if request.user.is_authenticated:
        if not request.session.get('selected_project'):
            try:
                request.session['selected_project'] = ProjectSerializer(
                    request.user.projects.first()
                ).data
            except Exception as e:
                # User has no projects
                pass
        selected_project = request.session.get('selected_project')
    return {
        "selected_project": selected_project,
        "swift_data_public_url": settings.FLOTO_SWIFT_DATA_PUBLIC_URL,
    }
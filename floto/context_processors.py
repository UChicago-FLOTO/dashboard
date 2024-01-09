from .api.serializers import ProjectSerializer


def global_values(request):
    selected_project = None
    projects = []
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
    }
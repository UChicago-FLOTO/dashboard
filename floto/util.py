from .api.serializers import ProjectSerializer


def set_active_project(request, project_uuid):
    project = request.user.projects.get(pk=project_uuid)
    if project:
        request.session["selected_project"] = ProjectSerializer(project).data

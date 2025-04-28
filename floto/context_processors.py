from .api.serializers import ProjectSerializer
import logging

LOG = logging.getLogger(__name__)


def global_values(request):
    selected_project = {}
    projects = []
    if request.user.is_authenticated:
        projects = list(request.user.projects.all())
        if not request.session.get("selected_project"):
            try:
                request.session["selected_project"] = ProjectSerializer(
                    projects[0]
                ).data
            except Exception:
                # User has no projects
                pass
        selected_project = request.session.get("selected_project", {})
    return {
        "selected_project": selected_project,
        "projects": [
            {
                "uuid": p.uuid,
                "name": p.name,
                "selected": str(p.uuid) == selected_project.get("uuid"),
            }
            for p in projects
        ],
    }

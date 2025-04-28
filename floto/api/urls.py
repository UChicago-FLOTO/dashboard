from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register("devices", views.DeviceViewSet, basename="device")
router.register("collections", views.CollectionViewSet, basename="collection")
router.register("services", views.ServiceViewSet, basename="service")
router.register("applications", views.ApplicationViewSet, basename="application")
router.register("jobs", views.JobViewSet, basename="job")
router.register("timeslots", views.TimeslotViewSet, basename="timeslot")
router.register("projects", views.ProjectViewSet, basename="project")
router.register(
    "peripheral_schema", views.PeripheralSchemaViewSet, basename="peripheral_schema"
)
router.register("peripheral", views.PeripheralViewSet, basename="peripheral")
router.register("resources", views.ClaimableResourceViewSet, basename="resource")
router.register("datasets", views.DatasetViewSet, basename="dataset")
urlpatterns = router.urls

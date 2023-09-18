from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register("devices", views.DeviceViewSet, basename="device")
router.register("fleets", views.FleetViewSet, basename="fleet")
router.register("collections", views.CollectionViewSet, basename="collection")
router.register("envs", views.EnvViewSet, basename="env")
router.register("services", views.ServiceViewSet, basename="service")
router.register(
    "applications", views.ApplicationViewSet, basename="application")
router.register("jobs", views.JobViewSet, basename="job")
urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("devices", views.DeviceViewSet, basename="device")
router.register("fleets", views.FleetViewSet, basename="fleet")
router.register("collections", views.CollectionViewSet, basename="collection")
urlpatterns = router.urls

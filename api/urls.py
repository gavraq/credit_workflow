from rest_framework.routers import DefaultRouter
from .views import CreditRequestViewSet, DocumentViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'credit-requests', CreditRequestViewSet)
router.register(r'documents', DocumentViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = router.urls

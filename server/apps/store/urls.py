from .views import ShoppingCartViewSet
from rest_framework_nested import routers

router = routers.SimpleRouter()
router.register('carts', ShoppingCartViewSet, 'cart')

urlpatterns = router.urls


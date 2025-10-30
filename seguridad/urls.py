from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, RefreshView, MeViewSet

router = DefaultRouter()
router.register(r'me', MeViewSet, basename='me')

urlpatterns = [
    path('auth/login',  LoginView.as_view(),   name='token_obtain_pair'),  # POST
    path('auth/refresh', RefreshView.as_view(), name='token_refresh'),     # POST
    path('', include(router.urls)),
]



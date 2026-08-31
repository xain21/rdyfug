from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MemberListViewSet

router = DefaultRouter()
# router.register("members", MemberListViewSet, "members-api")

urlpatterns = [
    path('', include(router.urls)), 
    path('members/<int:id>/', MemberListViewSet.as_view({"get": "list"})), 
]

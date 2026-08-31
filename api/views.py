from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin

from .serializers import MemberModelSerialzier
from Dashboard.models import Member, BODMember

class MemberListViewSet(ListModelMixin, GenericViewSet):
    serializer_class = MemberModelSerialzier

    def get_queryset(self):
        bodMember = BODMember.objects.filter(id=self.kwargs["id"]).first()
        if bodMember:
            department = self.request.query_params.get("department")
            if department:
                return bodMember.members.filter(department_name=department)
            return bodMember.members.all()
        return Member.objects.none()
    

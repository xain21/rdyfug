from rest_framework import serializers
from Dashboard.models import Member, Designation, Department


class DesignationModelSerialzier(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Designation
class DepartmentModelSerialzier(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Department

        
class MemberModelSerialzier(serializers.ModelSerializer):
    designation_name = DesignationModelSerialzier(read_only=True)
    department_name = DepartmentModelSerialzier(read_only=True)
    class Meta:
        fields = [
            "id",
            "email",
            "address",
            "phone",
            "image",
            "name",
            "designation_name",
            "department_name",
        ]
        model = Member
    
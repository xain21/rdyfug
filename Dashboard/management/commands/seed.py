from django.core.management.base import BaseCommand
from Dashboard.models import Designation, Department

class Command(BaseCommand):
    help = 'Seed the database with initial data'

    def handle(self, *args, **kwargs):
        designations = ['IT Officer', 'Director', 'Independent Director', 'Chairman']
        for designation in designations:
            Designation.objects.get_or_create(Designation_name=designation)

        departments = ['Audit', 'HR', 'Finance', 'Agm', 'procurement']
        for department in departments:
            Department.objects.get_or_create(Department_name=department)

        self.stdout.write(self.style.SUCCESS('Successfully seeded the database'))
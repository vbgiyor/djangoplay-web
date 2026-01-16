from rest_framework import serializers

from users.models.employee import Employee


class BaseEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "id",
            "employee_code",
            "username",
            "email",
            "first_name",
            "last_name",
            "department",
            "role",
            "team",
            "phone_number",
            "job_title",
            "address",
            "manager",
            "hire_date",
            "employment_status",
            "employee_type",
            "date_of_birth",
            "gender",
            "marital_status",
            "is_active",
        )
        read_only_fields = ("id", "employee_code")

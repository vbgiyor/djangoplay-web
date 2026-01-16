from users.serializers.base import BaseEmployeeSerializer


class EmployeeWriteSerializerV1(BaseEmployeeSerializer):
    class Meta(BaseEmployeeSerializer.Meta):
        fields = (
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

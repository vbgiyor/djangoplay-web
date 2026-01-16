from industries.serializers.base import BaseIndustrySerializer


class IndustryWriteSerializerV1(BaseIndustrySerializer):

    """
    Write-only Industry serializer (v1).
    Explicit field control.
    """

    class Meta(BaseIndustrySerializer.Meta):
        fields = (
            "code",
            "description",
            "level",
            "sector",
            "parent",
        )

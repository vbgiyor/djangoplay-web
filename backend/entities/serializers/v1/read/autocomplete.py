from rest_framework import serializers


class EntityAutocompleteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    value = serializers.CharField()

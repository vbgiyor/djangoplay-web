class SerializerByActionMixin:

    """
    Cleanly resolves read/write serializers per action.
    """

    read_serializer_class = None
    write_serializer_class = None

    def get_serializer_class(self):
        assert self.read_serializer_class is not None, (
            f"{self.__class__.__name__} must define read_serializer_class"
        )
        assert self.write_serializer_class is not None, (
            f"{self.__class__.__name__} must define write_serializer_class"
        )

        if self.action in ("list", "retrieve"):
            return self.read_serializer_class

        return self.write_serializer_class

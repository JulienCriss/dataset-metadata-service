from copy import copy

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Max
from rest_framework import serializers
from rest_framework.settings import api_settings

from metadata_catalog.models import DataElement, Dataset


class CurrentDatasetDefault:
    """The dataset comes from the URL, never from the request body."""

    requires_context = True

    def __call__(self, serializer_field):
        return serializer_field.context["dataset"]


class DataElementSerializer(serializers.ModelSerializer):
    # Hidden rather than omitted: DRF silently skips the (dataset, key)
    # uniqueness check if `dataset` is not a field on the serializer.
    dataset = serializers.HiddenField(default=CurrentDatasetDefault())
    type_signature = serializers.CharField(read_only=True)
    ordinal_position = serializers.IntegerField(required=False, min_value=1)

    class Meta:
        model = DataElement
        fields = [
            "id",
            "dataset",
            "key",
            "name",
            "description",
            "data_type",
            "type_signature",
            "max_length",
            "precision",
            "scale",
            "is_nullable",
            "is_pii",
            "pii_category",
            "retention_days",
            "ordinal_position",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type_signature", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate against the model, so the rules are defined in one place."""

        if self.instance is None and attrs.get("ordinal_position") is None:
            attrs["ordinal_position"] = self.next_ordinal_position(attrs["dataset"])

        # The element as it would look after this request, without saving it.
        element = copy(self.instance) if self.instance else DataElement()
        for field, value in attrs.items():
            setattr(element, field, value)

        try:
            element.full_clean(validate_unique=False)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(self.as_drf_errors(exc)) from exc

        return attrs

    @staticmethod
    def as_drf_errors(exc: DjangoValidationError) -> dict:
        """Model errors, with __all__ renamed to DRF's non_field_errors."""
        errors = exc.message_dict
        if NON_FIELD_ERRORS in errors:
            errors[api_settings.NON_FIELD_ERRORS_KEY] = errors.pop(NON_FIELD_ERRORS)
        return errors

    @staticmethod
    def next_ordinal_position(dataset: Dataset) -> int:
        """Append after the dataset's current last element."""
        highest = DataElement.objects.filter(dataset=dataset).aggregate(
            highest=Max("ordinal_position")
        )["highest"]
        return (highest or 0) + 1


class DatasetListSerializer(serializers.ModelSerializer):
    data_element_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dataset
        fields = [
            "id",
            "key",
            "name",
            "description",
            "owner",
            "data_element_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "data_element_count", "created_at", "updated_at"]


class DatasetDetailSerializer(DatasetListSerializer):
    """Adds the dataset's elements. Needs prefetch_related in the view."""

    data_elements = DataElementSerializer(many=True, read_only=True)

    class Meta(DatasetListSerializer.Meta):
        fields = [*DatasetListSerializer.Meta.fields, "data_elements"]
        read_only_fields = [*DatasetListSerializer.Meta.read_only_fields, "data_elements"]

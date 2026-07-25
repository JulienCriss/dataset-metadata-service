from rest_framework import serializers

from metadata_catalog.models import DataElement, Dataset


class DataElementSerializer(serializers.ModelSerializer):
    type_signature = serializers.CharField(read_only=True)

    class Meta:
        model = DataElement
        fields = [
            "id",
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
        read_only_fields = [
            "id",
            "type_signature",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        data_type = attrs.get(
            "data_type",
            getattr(instance, "data_type", None),
        )
        max_length = attrs.get(
            "max_length",
            getattr(instance, "max_length", None),
        )
        precision = attrs.get(
            "precision",
            getattr(instance, "precision", None),
        )
        scale = attrs.get(
            "scale",
            getattr(instance, "scale", None),
        )
        is_pii = attrs.get(
            "is_pii",
            getattr(instance, "is_pii", False),
        )
        pii_category = attrs.get(
            "pii_category",
            getattr(instance, "pii_category", None),
        )

        errors = {}

        if data_type == DataElement.DataType.STRING:
            if max_length is None:
                errors["max_length"] = "max_length is required for STRING data elements."

            if precision is not None:
                errors["precision"] = (
                    "precision is only supported for DECIMAL data elements."
                )

            if scale is not None:
                errors["scale"] = "scale is only supported for DECIMAL data elements."

        elif data_type == DataElement.DataType.DECIMAL:
            if precision is None:
                errors["precision"] = "precision is required for DECIMAL data elements."

            if scale is None:
                errors["scale"] = "scale is required for DECIMAL data elements."

            if precision is not None and scale is not None and scale > precision:
                errors["scale"] = "scale cannot be greater than precision."

            if max_length is not None:
                errors["max_length"] = (
                    "max_length is only supported for STRING data elements."
                )

        else:
            if max_length is not None:
                errors["max_length"] = (
                    "max_length is only supported for STRING data elements."
                )

            if precision is not None:
                errors["precision"] = (
                    "precision is only supported for DECIMAL data elements."
                )

            if scale is not None:
                errors["scale"] = "scale is only supported for DECIMAL data elements."

        if is_pii and not pii_category:
            errors["pii_category"] = "pii_category is required when is_pii is true."

        if not is_pii and pii_category:
            errors["pii_category"] = "pii_category must be empty when is_pii is false."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class DatasetSerializer(serializers.ModelSerializer):
    data_element_count = serializers.IntegerField(
        read_only=True,
    )

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
        read_only_fields = [
            "id",
            "data_element_count",
            "created_at",
            "updated_at",
        ]


class DatasetDetailSerializer(serializers.ModelSerializer):
    data_elements = DataElementSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Dataset
        fields = [
            "id",
            "key",
            "name",
            "description",
            "owner",
            "created_at",
            "updated_at",
            "data_elements",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "data_elements",
        ]

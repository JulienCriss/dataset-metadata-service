import uuid

from django.db import models
from django.db.models import F, Q

from metadata_catalog.models.dataset import Dataset
from metadata_catalog.utils.validators import KEY_MAX_LENGTH, key_validator


class DataType(models.TextChoices):
    """
    Closed vocabulary of logical types a data element may have.

    The catalog records what a field *means*,
    not how a particular database happens to store it.
    """

    STRING = "STRING", "String"
    INTEGER = "INTEGER", "Integer"
    DECIMAL = "DECIMAL", "Decimal"
    BOOLEAN = "BOOLEAN", "Boolean"
    DATE = "DATE", "Date"
    DATETIME = "DATETIME", "Date and time"
    UUID = "UUID", "UUID"


class PiiCategory(models.TextChoices):
    """Classification applied to elements that hold personal data."""

    IDENTITY = "IDENTITY", "Identity"  # name, BSN, passport no.
    CONTACT = "CONTACT", "Contact"  # email, phone, address
    FINANCIAL = "FINANCIAL", "Financial"  # IBAN, balance, salary
    LOCATION = "LOCATION", "Location"  # geo, IP
    SENSITIVE = "SENSITIVE", "Sensitive"  # GDPR Art. 9 special category
    OTHER = "OTHER", "Other"  # escape hatch


class DataElement(models.Model):
    """A single piece of information within a dataset."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="data_elements",
        help_text="A data element has no meaning outside its dataset.",
    )

    key = models.CharField(
        max_length=KEY_MAX_LENGTH,
        validators=[key_validator],
        help_text="Machine-readable identifier, unique within the dataset.",
    )

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name, e.g. 'Email address'.",
    )

    description = models.TextField(
        blank=True,
        help_text="What this element represents in business terms.",
    )

    data_type = models.CharField(
        max_length=20,
        choices=DataType.choices,
        help_text="Logical type, drawn from a closed vocabulary.",
    )

    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum character length. Applies to STRING only.",
    )

    precision = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total number of significant digits. Applies to DECIMAL only.",
    )

    scale = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Digits after the decimal point. Applies to DECIMAL only.",
    )

    is_nullable = models.BooleanField(
        default=True,
        help_text="Whether this element may be absent for a given record.",
    )

    is_pii = models.BooleanField(
        default=False,
        help_text="Whether this element holds personally identifiable information.",
    )

    # DJ001 is suppressed deliberately: NULL is a meaningful third state here
    # ("not applicable"), distinct from every valid category. An empty string
    # would claim the element has a category that happens to be blank.
    pii_category = models.CharField(  # noqa: DJ001
        max_length=20,
        choices=PiiCategory.choices,
        null=True,
        blank=True,
        help_text=(
            "Kind of personal data held. NULL means 'not applicable' and is "
            "only valid when is_pii is false."
        ),
    )

    retention_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "How long this element may be retained. NULL means no policy has "
            "been defined yet, which is not the same as 'keep forever'."
        ),
    )

    ordinal_position = models.PositiveIntegerField(
        help_text="Advisory display order within the dataset, starting at 1.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Declared order first, then key as a deterministic tie-breaker so that
        # pagination is stable even if two elements share an ordinal.
        ordering = ["ordinal_position", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "key"],
                name="unique_data_element_key_per_dataset",
                violation_error_code="duplicate_element_key",
                violation_error_message=(
                    "A data element with this key already exists in this dataset."
                ),
            ),
            # Validate the vocabulary at the database level.
            models.CheckConstraint(
                condition=Q(data_type__in=DataType.values),
                name="data_element_data_type_valid",
                violation_error_code="invalid_data_type",
                violation_error_message="Unknown data type.",
            ),
            models.CheckConstraint(
                condition=(
                    Q(pii_category__isnull=True)
                    | Q(pii_category__in=PiiCategory.values)
                ),
                name="data_element_pii_category_valid",
                violation_error_code="invalid_pii_category",
                violation_error_message="Unknown PII category.",
            ),
            # PII classification is a biconditional: an element is either
            # flagged and categorized, or neither.
            models.CheckConstraint(
                condition=(
                    Q(is_pii=True, pii_category__isnull=False)
                    | Q(is_pii=False, pii_category__isnull=True)
                ),
                name="data_element_pii_category_matches_is_pii",
                violation_error_code="pii_category_inconsistent",
                violation_error_message=(
                    "pii_category is required when is_pii is true, and must be "
                    "empty when it is false."
                ),
            ),
            # A type parameter is only meaningful for the type that defines it,
            # so each is required for its own type and forbidden for all others.
            models.CheckConstraint(
                condition=(
                    Q(data_type=DataType.STRING, max_length__gte=1)
                    | (~Q(data_type=DataType.STRING) & Q(max_length__isnull=True))
                ),
                name="data_element_max_length_only_for_string",
                violation_error_code="invalid_max_length",
                violation_error_message=(
                    "max_length is required for STRING (minimum 1) and must be "
                    "empty for every other data type."
                ),
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        data_type=DataType.DECIMAL,
                        precision__gte=1,
                        scale__isnull=False,
                    )
                    | (
                        ~Q(data_type=DataType.DECIMAL)
                        & Q(precision__isnull=True, scale__isnull=True)
                    )
                ),
                name="data_element_precision_scale_only_for_decimal",
                violation_error_code="invalid_precision_scale",
                violation_error_message=(
                    "precision (minimum 1) and scale are both required for "
                    "DECIMAL and must be empty for every other data type."
                ),
            ),
            models.CheckConstraint(
                condition=Q(scale__isnull=True) | Q(scale__lte=F("precision")),
                name="data_element_scale_within_precision",
                violation_error_code="scale_exceeds_precision",
                violation_error_message="scale cannot exceed precision.",
            ),
            models.CheckConstraint(
                condition=Q(retention_days__isnull=True) | Q(retention_days__gte=1),
                name="data_element_retention_days_positive",
                violation_error_code="invalid_retention_days",
                violation_error_message=(
                    "retention_days must be at least 1 day when set."
                ),
            ),
            models.CheckConstraint(
                condition=Q(ordinal_position__gte=1),
                name="data_element_ordinal_position_positive",
                violation_error_code="invalid_ordinal_position",
                violation_error_message="ordinal_position starts at 1.",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.dataset.key}.{self.key}"

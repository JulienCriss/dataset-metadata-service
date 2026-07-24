import uuid

from django.db import models

from metadata_catalog.utils.validators import KEY_MAX_LENGTH, key_validator


class Dataset(models.Model):
    """A business entity whose structure is described by its data elements."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    key = models.CharField(
        max_length=KEY_MAX_LENGTH,
        unique=True,
        validators=[key_validator],
        help_text="Machine-readable identifier, unique across the catalog.",
    )

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name, e.g. 'Customer'.",
    )

    description = models.TextField(
        blank=True,
        help_text="What this dataset represents in business terms.",
    )

    owner = models.CharField(
        max_length=255,
        help_text="Business or data domain responsible for this dataset.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name

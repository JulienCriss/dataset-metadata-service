"""
Datasets and data elements both expose a machine-readable ``key``. The rules for
those keys live here so that the two models cannot drift apart.
"""

from django.core.validators import RegexValidator

KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
KEY_MAX_LENGTH = 100

key_validator = RegexValidator(
    regex=KEY_PATTERN,
    code="invalid_key",
    message=(
        "Key must start with a lowercase letter and contain only "
        "lowercase letters, numbers, and underscores."
    ),
)

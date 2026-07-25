"""Tests that the rules survive without the API in front of them.

The serializer validates by delegating to the model, so these tests prove the
rules are enforced by the database itself rather than by request handling: a
management command, a data migration or a raw ORM call cannot get around them.
"""

import pytest
from django.db import IntegrityError, transaction

from metadata_catalog.models import DataElement, DataType, PiiCategory

pytestmark = pytest.mark.django_db


def test_database_rejects_a_duplicate_key_when_the_api_is_bypassed(customer, email):
    """The unique key rule is a database constraint, not a serializer check."""
    # Arrange
    duplicate = DataElement(
        dataset=customer,
        key=email.key,
        name="Duplicate",
        data_type=DataType.DATE,
        ordinal_position=2,
    )

    # Act / Assert
    with pytest.raises(IntegrityError), transaction.atomic():
        duplicate.save()


def test_database_rejects_a_pii_element_without_a_category(customer):
    """The PII classification rule is enforced below the application layer."""
    # Arrange
    unclassified = DataElement(
        dataset=customer,
        key="bsn",
        name="Citizen number",
        data_type=DataType.DATE,
        is_pii=True,
        pii_category=None,
        ordinal_position=1,
    )

    # Act / Assert
    with pytest.raises(IntegrityError), transaction.atomic():
        unclassified.save()


def test_the_same_key_is_accepted_in_a_different_dataset(customer, order, email):
    """The constraint is on (dataset, key), so it does not span datasets."""
    # Arrange
    twin = DataElement(
        dataset=order,
        key=email.key,
        name="Email address",
        data_type=DataType.STRING,
        max_length=320,
        is_pii=True,
        pii_category=PiiCategory.CONTACT,
        ordinal_position=1,
    )

    # Act
    twin.save()

    # Assert
    assert DataElement.objects.filter(key="email").count() == 2


def test_deleting_a_dataset_cascades_to_its_data_elements(customer, email):
    """A data element has no meaning outside its dataset, so it goes with it."""
    # Arrange
    assert DataElement.objects.count() == 1

    # Act
    customer.delete()

    # Assert
    assert DataElement.objects.count() == 0


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"data_type": DataType.STRING, "max_length": 320}, "STRING(320)"),
        ({"data_type": DataType.DECIMAL, "precision": 18, "scale": 2}, "DECIMAL(18,2)"),
        ({"data_type": DataType.DATE}, "DATE"),
    ],
)
def test_type_signature_renders_the_type_parameters(customer, fields, expected):
    """The signature is derived from the type and its parameters, not stored."""
    # Arrange
    element = DataElement(
        dataset=customer,
        key="value",
        name="Value",
        ordinal_position=1,
        **fields,
    )

    # Act
    signature = element.type_signature

    # Assert
    assert signature == expected

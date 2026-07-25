import pytest

from metadata_catalog.models import DataElement, DataType, PiiCategory
from metadata_catalog.tests.helpers import (
    element_payload,
    element_url,
    elements_url,
)

pytestmark = pytest.mark.django_db


def test_add_data_element_to_dataset_returns_201(api_client, customer):
    """A valid POST attaches the element to the dataset named in the URL."""
    # Arrange
    payload = element_payload(
        key="email",
        name="Email address",
        data_type=DataType.STRING,
        max_length=320,
    )

    # Act
    response = api_client.post(elements_url(customer), payload)

    # Assert
    assert response.status_code == 201
    assert response.data["type_signature"] == "STRING(320)"
    assert DataElement.objects.get(key="email").dataset == customer


def test_ordinal_position_is_assigned_when_omitted(api_client, customer, email):
    """Clients may omit the ordinal; the element is appended to the end."""
    # Arrange
    # `email` already occupies ordinal position 1.

    # Act
    response = api_client.post(elements_url(customer), element_payload())

    # Assert
    assert response.status_code == 201
    assert response.data["ordinal_position"] == 2


def test_list_data_elements_uses_declared_order_not_alphabetical(
    api_client, customer, email
):
    """Elements are returned in declared order, so ordinals are meaningful."""
    # Arrange
    # `email` is at ordinal 1; `account_balance` sorts first alphabetically but
    # is declared second.
    api_client.post(
        elements_url(customer),
        element_payload(key="account_balance", name="Balance", data_type=DataType.DATE),
    )

    # Act
    response = api_client.get(elements_url(customer))

    # Assert
    assert [element["key"] for element in response.data["results"]] == [
        "email",
        "account_balance",
    ]


def test_duplicate_key_in_the_same_dataset_is_rejected(api_client, customer, email):
    """A data element key must be unique within its dataset."""
    # Arrange
    payload = element_payload(key=email.key, name="Duplicate")

    # Act
    response = api_client.post(elements_url(customer), payload)

    # Assert
    assert response.status_code == 400
    assert DataElement.objects.filter(dataset=customer, key="email").count() == 1


def test_the_same_key_in_a_different_dataset_is_allowed(
    api_client, customer, order, email
):
    """Uniqueness is scoped to the dataset, not global to the catalog."""
    # Arrange
    payload = element_payload(key=email.key, name="Email address")

    # Act
    response = api_client.post(elements_url(order), payload)

    # Assert
    assert response.status_code == 201
    assert DataElement.objects.filter(key="email").count() == 2


def test_pii_element_without_a_category_is_rejected(api_client, customer):
    """Personal data must be classified: is_pii and pii_category go together."""
    # Arrange
    payload = element_payload(key="bsn", name="Citizen number", is_pii=True)

    # Act
    response = api_client.post(elements_url(customer), payload)

    # Assert
    assert response.status_code == 400
    assert not DataElement.objects.exists()


def test_string_element_without_max_length_is_rejected(api_client, customer):
    """A type parameter is required by the type that defines it."""
    # Arrange
    payload = element_payload(key="surname", data_type=DataType.STRING)

    # Act
    response = api_client.post(elements_url(customer), payload)

    # Assert
    assert response.status_code == 400
    assert not DataElement.objects.exists()


def test_max_length_is_rejected_for_a_non_string_element(api_client, customer):
    """A type parameter is forbidden for every type that does not define it."""
    # Arrange
    payload = element_payload(key="opened_on", data_type=DataType.DATE, max_length=10)

    # Act
    response = api_client.post(elements_url(customer), payload)

    # Assert
    assert response.status_code == 400
    assert not DataElement.objects.exists()


def test_patch_validates_the_element_that_would_result(api_client, email):
    """A partial update is checked against the merged element, not the patch.

    Changing the type to DATE leaves the element carrying a max_length that
    only STRING may have, so the patch is rejected even though DATE alone is
    a valid type.
    """
    # Arrange
    url = element_url(email)

    # Act
    rejected = api_client.patch(url, {"data_type": DataType.DATE})
    accepted = api_client.patch(url, {"data_type": DataType.DATE, "max_length": None})

    # Assert
    assert rejected.status_code == 400
    assert accepted.status_code == 200
    assert accepted.data["type_signature"] == "DATE"


def test_element_of_another_dataset_is_not_reachable(api_client, customer, order):
    """Elements are addressed through their owning dataset only."""
    # Arrange
    foreign = DataElement.objects.create(
        dataset=order,
        key="placed_on",
        name="Placed on",
        data_type=DataType.DATE,
        ordinal_position=1,
    )

    # Act
    response = api_client.get(element_url(foreign, dataset=customer))

    # Assert
    assert response.status_code == 404


def test_delete_removes_the_data_element(api_client, customer, email):
    """Deleting an element removes it from its dataset."""
    # Arrange
    url = element_url(email)

    # Act
    response = api_client.delete(url)

    # Assert
    assert response.status_code == 204
    assert not DataElement.objects.filter(pk=email.pk).exists()


def test_updating_pii_flag_requires_clearing_the_category(api_client, email):
    """The PII flag and its category are a pair, in both directions."""
    # Arrange
    url = element_url(email)

    # Act
    rejected = api_client.patch(url, {"is_pii": False})
    accepted = api_client.patch(url, {"is_pii": False, "pii_category": None})

    # Assert
    assert rejected.status_code == 400
    assert accepted.status_code == 200
    email.refresh_from_db()
    assert email.is_pii is False
    assert email.pii_category is None


def test_elements_are_listed_only_for_their_own_dataset(
    api_client, customer, order, email
):
    """Listing one dataset's elements never leaks another dataset's."""
    # Arrange
    DataElement.objects.create(
        dataset=order,
        key="placed_on",
        name="Placed on",
        data_type=DataType.DATE,
        is_pii=True,
        pii_category=PiiCategory.IDENTITY,
        ordinal_position=1,
    )

    # Act
    response = api_client.get(elements_url(customer))

    # Assert
    assert [element["key"] for element in response.data["results"]] == ["email"]

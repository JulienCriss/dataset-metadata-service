import pytest

from metadata_catalog.models import DataElement, Dataset, DataType, PiiCategory
from metadata_catalog.tests.helpers import datasets_url, elements_url

pytestmark = pytest.mark.django_db


@pytest.fixture
def balance(customer: Dataset) -> DataElement:
    """A non-PII decimal element, to contrast with the PII string `email`."""
    return DataElement.objects.create(
        dataset=customer,
        key="account_balance",
        name="Account balance",
        description="Current balance in euros.",
        data_type=DataType.DECIMAL,
        precision=18,
        scale=2,
        ordinal_position=2,
    )


class TestFilterDataElements:
    """GET /datasets/{id}/elements/?..."""

    def test_filter_by_is_pii(self, api_client, customer, email, balance):
        """Returns only the elements holding personal data."""
        # Arrange
        # `customer` has one PII element (email) and one non-PII (balance).

        # Act
        response = api_client.get(elements_url(customer), {"is_pii": "true"})

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["email"]

    def test_filter_by_data_type(self, api_client, customer, email, balance):
        """Returns only the elements of the requested logical type."""
        # Arrange
        # `email` is STRING, `balance` is DECIMAL.

        # Act
        response = api_client.get(elements_url(customer), {"data_type": "DECIMAL"})

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["account_balance"]

    def test_filter_by_pii_category(self, api_client, customer, email, balance):
        """Returns only the elements with the requested classification."""
        # Arrange
        # Only `email` is classified, as CONTACT.

        # Act
        response = api_client.get(
            elements_url(customer),
            {"pii_category": PiiCategory.CONTACT},
        )

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["email"]

    def test_search_matches_the_description_too(self, api_client, customer, balance):
        """Search spans key, name and description, not just the key."""
        # Arrange
        # Only `balance` mentions euros, and only in its description.

        # Act
        response = api_client.get(elements_url(customer), {"search": "euros"})

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["account_balance"]

    def test_an_unknown_data_type_is_rejected(self, api_client, customer, email):
        """Filtering by a value outside the vocabulary is a client error."""
        # Arrange
        # BANANA is not a member of DataType.

        # Act
        response = api_client.get(elements_url(customer), {"data_type": "BANANA"})

        # Assert
        assert response.status_code == 400
        assert "data_type" in response.data

    def test_filters_do_not_escape_the_dataset(self, api_client, customer, order, email):
        """A filter narrows within one dataset; it never widens across them."""
        # Arrange
        DataElement.objects.create(
            dataset=order,
            key="customer_email",
            name="Customer email",
            data_type=DataType.STRING,
            max_length=320,
            is_pii=True,
            pii_category=PiiCategory.CONTACT,
            ordinal_position=1,
        )

        # Act
        response = api_client.get(elements_url(customer), {"is_pii": "true"})

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["email"]


class TestFilterDatasets:
    """GET /datasets/?..."""

    def test_filter_by_owner(self, api_client, customer, order):
        """Returns only the datasets owned by the given domain."""
        # Arrange
        # `customer` is owned by retail-data-domain, `order` by lending-domain.

        # Act
        response = api_client.get(datasets_url(), {"owner": "lending-domain"})

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["order"]

    def test_search_by_name(self, api_client, customer, order):
        """Search matches a substring of the dataset name."""
        # Arrange
        # Only the `customer` dataset is named "Customer".

        # Act
        response = api_client.get(datasets_url(), {"search": "custom"})

        # Assert
        assert [item["key"] for item in response.data["results"]] == ["customer"]

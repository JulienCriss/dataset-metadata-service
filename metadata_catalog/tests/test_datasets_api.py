import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from metadata_catalog.models import Dataset
from metadata_catalog.tests.helpers import dataset_url, datasets_url

pytestmark = pytest.mark.django_db


def test_create_dataset_returns_201_and_persists(api_client):
    """A valid POST creates the dataset and echoes it back."""
    # Arrange
    payload = {
        "key": "customer",
        "name": "Customer",
        "owner": "retail-data-domain",
        "description": "Master data for retail banking customers.",
    }

    # Act
    response = api_client.post(datasets_url(), payload)

    # Assert
    assert response.status_code == 201
    assert response.data["key"] == "customer"
    assert response.data["data_element_count"] == 0
    assert Dataset.objects.filter(key="customer").exists()


def test_create_dataset_rejects_an_invalid_key(api_client):
    """Keys are lower_snake_case identifiers, so 'Customer' is refused."""
    # Arrange
    payload = {"key": "Customer", "name": "Customer", "owner": "retail-data-domain"}

    # Act
    response = api_client.post(datasets_url(), payload)

    # Assert
    assert response.status_code == 400
    assert "key" in response.data
    assert not Dataset.objects.exists()


def test_create_dataset_rejects_a_duplicate_key(api_client, customer):
    """Dataset keys identify a dataset across the whole catalog."""
    # Arrange
    payload = {"key": customer.key, "name": "Another customer", "owner": "somebody"}

    # Act
    response = api_client.post(datasets_url(), payload)

    # Assert
    assert response.status_code == 400
    assert "key" in response.data
    assert Dataset.objects.filter(key="customer").count() == 1


def test_list_datasets_includes_the_number_of_data_elements(api_client, customer, email):
    """The list is shallow: it reports how many elements a dataset has."""
    # Arrange
    # `customer` owns exactly one element, `email`.

    # Act
    response = api_client.get(datasets_url())

    # Assert
    assert response.status_code == 200
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["data_element_count"] == 1
    assert "data_elements" not in response.data["results"][0]


def test_retrieve_dataset_includes_its_data_elements(api_client, customer, email):
    """The detail view embeds the dataset's elements, unlike the list view."""
    # Arrange
    # `customer` owns exactly one element, `email`.

    # Act
    response = api_client.get(dataset_url(customer))

    # Assert
    assert response.status_code == 200
    assert response.data["key"] == "customer"
    assert [element["key"] for element in response.data["data_elements"]] == ["email"]
    assert response.data["data_elements"][0]["type_signature"] == "STRING(320)"


def test_listing_datasets_does_not_run_more_queries_as_datasets_are_added(api_client):
    """The list endpoint must not issue one query per dataset (no N+1)."""
    # Arrange
    Dataset.objects.create(key="customer", name="Customer", owner="retail")

    with CaptureQueriesContext(connection) as one_dataset:
        api_client.get(datasets_url())

    for index in range(5):
        Dataset.objects.create(key=f"dataset_{index}", name="D", owner="retail")

    # Act
    with CaptureQueriesContext(connection) as six_datasets:
        api_client.get(datasets_url())

    # Assert
    assert len(six_datasets) == len(one_dataset)

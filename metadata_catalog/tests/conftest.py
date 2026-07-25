import pytest
from rest_framework.test import APIClient

from metadata_catalog.models import DataElement, Dataset, DataType, PiiCategory


@pytest.fixture
def api_client() -> APIClient:
    """An unauthenticated client; the service has no authentication."""
    return APIClient()


@pytest.fixture
def customer(db) -> Dataset:
    """A dataset with no data elements yet."""
    return Dataset.objects.create(
        key="customer",
        name="Customer",
        owner="retail-data-domain",
        description="Master data for retail banking customers.",
    )


@pytest.fixture
def order(db) -> Dataset:
    """A second dataset, used to prove that rules are scoped per dataset."""
    return Dataset.objects.create(
        key="order",
        name="Order",
        owner="lending-domain",
    )


@pytest.fixture
def email(customer: Dataset) -> DataElement:
    """A PII string element belonging to the ``customer`` dataset."""
    return DataElement.objects.create(
        dataset=customer,
        key="email",
        name="Email address",
        data_type=DataType.STRING,
        max_length=320,
        is_pii=True,
        pii_category=PiiCategory.CONTACT,
        retention_days=2555,
        ordinal_position=1,
    )

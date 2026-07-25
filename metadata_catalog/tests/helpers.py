"""URL builders and payload factories shared by the tests."""

from django.urls import reverse

from metadata_catalog.models import DataElement, Dataset, DataType


def datasets_url() -> str:
    """Collection of datasets."""
    return reverse("metadata_catalog:dataset-list")


def dataset_url(dataset: Dataset) -> str:
    """A single dataset, with its data elements."""
    return reverse(
        "metadata_catalog:dataset-detail",
        kwargs={"dataset_id": dataset.pk},
    )


def elements_url(dataset: Dataset) -> str:
    """Collection of data elements belonging to a dataset."""
    return reverse(
        "metadata_catalog:data-element-list",
        kwargs={"dataset_id": dataset.pk},
    )


def element_url(element: DataElement, dataset: Dataset | None = None) -> str:
    """A single data element.

    ``dataset`` defaults to the element's own dataset, and can be overridden to
    build a deliberately mismatched URL.
    """
    return reverse(
        "metadata_catalog:data-element-detail",
        kwargs={
            "dataset_id": (dataset or element.dataset).pk,
            "element_id": element.pk,
        },
    )


def element_payload(**overrides) -> dict:
    """A valid request body for a data element, overridable per test."""
    return {
        "key": "date_of_birth",
        "name": "Date of birth",
        "data_type": DataType.DATE,
        **overrides,
    }

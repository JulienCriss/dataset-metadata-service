from functools import cached_property

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics

from .models import DataElement, Dataset
from .serializers import (
    DataElementSerializer,
    DatasetDetailSerializer,
    DatasetListSerializer,
)


class DatasetListCreateView(generics.ListCreateAPIView):
    """List the datasets in the catalog, or register a new one."""

    serializer_class = DatasetListSerializer

    def get_queryset(self):
        return Dataset.objects.annotate(
            data_element_count=Count("data_elements")
        ).order_by("key")

    def perform_create(self, serializer):
        dataset = serializer.save()
        dataset.data_element_count = 0


class DatasetDetailView(generics.RetrieveAPIView):
    """Retrieve a dataset together with its data elements."""

    serializer_class = DatasetDetailSerializer
    lookup_url_kwarg = "dataset_id"

    def get_queryset(self):
        return (
            Dataset.objects.annotate(data_element_count=Count("data_elements"))
            .prefetch_related("data_elements")
            .order_by("key")
        )


class DatasetScopedElementMixin:
    """Restricts data elements to the dataset named in the URL."""

    serializer_class = DataElementSerializer
    queryset = DataElement.objects.none()

    @cached_property
    def dataset(self) -> Dataset:
        """The dataset named in the URL, resolved once per request."""
        return get_object_or_404(Dataset, pk=self.kwargs["dataset_id"])

    def get_queryset(self):
        return DataElement.objects.filter(dataset=self.dataset)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dataset"] = self.dataset
        return context


class DataElementListCreateView(DatasetScopedElementMixin, generics.ListCreateAPIView):
    """List the data elements of a dataset, or add one to it."""


class DataElementDetailView(
    DatasetScopedElementMixin, generics.RetrieveUpdateDestroyAPIView
):
    """Retrieve, update or delete a single data element."""

    lookup_url_kwarg = "element_id"

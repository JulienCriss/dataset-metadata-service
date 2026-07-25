from django.db.models import Q
from django_filters import rest_framework as filters

from .models import DataElement, Dataset, DataType, PiiCategory


class KeywordSearchMixin:
    """Adds a `search` term matching any of SEARCH_FIELDS, case-insensitively."""

    SEARCH_FIELDS = ("key", "name", "description")

    def filter_search(self, queryset, name, value):
        query = Q()
        for field in self.SEARCH_FIELDS:
            query |= Q(**{f"{field}__icontains": value})
        return queryset.filter(query)


class DatasetFilterSet(KeywordSearchMixin, filters.FilterSet):
    """Query parameters accepted by the dataset list endpoint."""

    owner = filters.CharFilter(
        lookup_expr="iexact",
        help_text="Exact owning domain, case-insensitive.",
    )
    search = filters.CharFilter(
        method="filter_search",
        help_text="Substring of the key, name or description.",
    )

    class Meta:
        model = Dataset
        fields = ["owner", "search"]


class DataElementFilterSet(KeywordSearchMixin, filters.FilterSet):
    """Query parameters accepted by the data element list endpoint."""

    is_pii = filters.BooleanFilter(
        help_text="Only elements that do, or do not, hold personal data.",
    )
    data_type = filters.ChoiceFilter(
        choices=DataType.choices,
        help_text="Exact logical type.",
    )
    pii_category = filters.ChoiceFilter(
        choices=PiiCategory.choices,
        help_text="Exact PII classification.",
    )
    search = filters.CharFilter(
        method="filter_search",
        help_text="Substring of the key, name or description.",
    )

    class Meta:
        model = DataElement
        fields = ["is_pii", "data_type", "pii_category", "search"]

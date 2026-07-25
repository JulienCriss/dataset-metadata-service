from django.urls import path

from . import views

app_name = "metadata_catalog"

urlpatterns = [
    path(
        "datasets/",
        views.DatasetListCreateView.as_view(),
        name="dataset-list",
    ),
    path(
        "datasets/<uuid:dataset_id>/",
        views.DatasetDetailView.as_view(),
        name="dataset-detail",
    ),
    # Elements are nested under their dataset: the URL states the ownership
    # that the model expresses with a cascading foreign key.
    path(
        "datasets/<uuid:dataset_id>/elements/",
        views.DataElementListCreateView.as_view(),
        name="data-element-list",
    ),
]

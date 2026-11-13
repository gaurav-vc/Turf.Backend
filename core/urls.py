from django.urls import path
from .views import GlobalSearchView
from .apm_views import (
    APMMetricsView,
    APMProbeView,
    APMSubsystemHealthView,
    APMClearBufferView,
    APMExportTracesCSVView,
    APMDatabaseInspectorView,
    APMAPICatalogView,
    APMAsyncPipelineView
)

urlpatterns = [
    path('search/', GlobalSearchView.as_view(), name='global_search'),
    # APM & Telemetry Endpoints (Zero Storage)
    path('apm/metrics/', APMMetricsView.as_view(), name='apm_metrics'),
    path('apm/probe/', APMProbeView.as_view(), name='apm_probe'),
    path('apm/subsystems/', APMSubsystemHealthView.as_view(), name='apm_subsystems'),
    path('apm/clear/', APMClearBufferView.as_view(), name='apm_clear'),
    path('apm/export-csv/', APMExportTracesCSVView.as_view(), name='apm_export_csv'),
    path('apm/db-inspector/', APMDatabaseInspectorView.as_view(), name='apm_db_inspector'),
    path('apm/api-catalog/', APMAPICatalogView.as_view(), name='apm_api_catalog'),
    path('apm/async-pipeline/', APMAsyncPipelineView.as_view(), name='apm_async_pipeline'),
]

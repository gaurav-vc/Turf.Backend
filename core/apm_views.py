import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .apm_engine import (
    apm_buffer, 
    run_subsystem_health_check, 
    execute_synthetic_probe,
    get_db_schema_inspection,
    get_api_catalog,
    get_async_pipeline_status
)

class APMMetricsView(APIView):
    """
    Returns live APM metrics, health score, P50/P95/P99 latencies, failure rates,
    and recent transient traces from in-memory ring buffer (zero database storage).
    """
    permission_classes = [permissions.AllowAny]  # Admin layout provides UI auth guard; can query metrics freely

    def get(self, request):
        metrics = apm_buffer.get_metrics()
        return Response(metrics, status=status.HTTP_200_OK)


class APMProbeView(APIView):
    """
    Executes a synthetic probe on a given endpoint URL or page name.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        endpoint = request.data.get('endpoint', '').strip()
        method = request.data.get('method', 'GET').upper()

        if not endpoint:
            return Response(
                {"error": "Endpoint URL or route path is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        probe_result = execute_synthetic_probe(target_path=endpoint, method=method)
        return Response(probe_result, status=status.HTTP_200_OK)


class APMSubsystemHealthView(APIView):
    """
    Runs multi-subsystem diagnostic (DB, Cache, Auth, Storage).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        result = run_subsystem_health_check()
        return Response(result, status=status.HTTP_200_OK)


class APMClearBufferView(APIView):
    """
    Instantly purges all in-memory traces (Zero-storage reset).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        apm_buffer.clear()
        return Response({"message": "In-memory APM traces buffer cleared successfully"}, status=status.HTTP_200_OK)


class APMExportTracesCSVView(APIView):
    """
    Streams out the current in-memory transient traces as CSV.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="apm_telemetry_traces.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Timestamp', 'Method', 'Path', 'Status_Code', 'Latency_ms', 'Is_Anomaly', 'Is_Probe', 'Client_IP'])

        with apm_buffer.lock:
            traces = list(apm_buffer.traces)

        for t in reversed(traces):
            writer.writerow([
                t.get('id', ''),
                t.get('timestamp', ''),
                t.get('method', ''),
                t.get('path', ''),
                t.get('status_code', ''),
                t.get('latency_ms', ''),
                'YES' if t.get('is_anomaly') else 'NO',
                'YES' if t.get('is_probe') else 'NO',
                t.get('client_ip', '')
            ])

        return response


class APMDatabaseInspectorView(APIView):
    """
    Returns real database tables, models, row counts, and column schemas.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = get_db_schema_inspection()
        return Response(data, status=status.HTTP_200_OK)


class APMAPICatalogView(APIView):
    """
    Returns all registered Django endpoints dynamically with category breakdowns.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = get_api_catalog()
        return Response(data, status=status.HTTP_200_OK)


class APMAsyncPipelineView(APIView):
    """
    Returns active worker concurrency threads, task queue health, and processing counts.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = get_async_pipeline_status()
        return Response(data, status=status.HTTP_200_OK)



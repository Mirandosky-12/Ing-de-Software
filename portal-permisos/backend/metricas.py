"""
metricas.py — Instrumentación para Prometheus, que es la fuente de datos de Grafana.

Grafana no lee la aplicación directamente: Prometheus raspa (scrape) el endpoint
/metrics cada 15 segundos y guarda las series de tiempo; Grafana consulta a
Prometheus. Este módulo sólo define QUÉ se mide.

Se mide lo que el municipio necesita responder en una auditoría:
  · cuántas solicitudes entran, por permiso y por corregimiento
  · cuánto tarda de verdad un trámite (no cuánto dice el reglamento)
  · cuántos documentos se rechazaron y por qué
  · si el antivirus está vivo y con firmas frescas
"""

from __future__ import annotations

import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram, Info

# ---------------------------------------------------------------- solicitudes

solicitudes_creadas = Counter(
    "mupa_solicitudes_creadas_total",
    "Solicitudes de permiso creadas.",
    ["permiso", "corregimiento", "municipio"],
)

solicitudes_por_estado = Gauge(
    "mupa_solicitudes_por_estado",
    "Expedientes abiertos actualmente en cada estado.",
    ["estado", "municipio"],
)

duracion_tramite = Histogram(
    "mupa_tramite_dias",
    "Días hábiles entre la recepción y la resolución de un expediente.",
    ["permiso", "municipio"],
    buckets=(1, 3, 5, 8, 12, 15, 20, 30, 45, 60, 90),
)

# ---------------------------------------------------------------- documentos

documentos_verificados = Counter(
    "mupa_documentos_verificados_total",
    "Documentos que pasaron por la cadena de verificación.",
    ["resultado", "municipio"],   # limpio | infectado | formato_invalido | ...
)

amenazas_detectadas = Counter(
    "mupa_amenazas_detectadas_total",
    "Amenazas encontradas por ClamAV, desglosadas por firma.",
    ["firma", "municipio"],
)

duracion_escaneo = Histogram(
    "mupa_escaneo_segundos",
    "Tiempo que tarda ClamAV en analizar un documento.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

# ---------------------------------------------------------------- plataforma

antivirus_arriba = Gauge(
    "mupa_antivirus_arriba",
    "1 si clamd responde PONG, 0 si no.",
)

info_antivirus = Info(
    "mupa_antivirus",
    "Versión del motor y de la base de firmas de ClamAV.",
)

peticiones_http = Counter(
    "mupa_http_peticiones_total",
    "Peticiones HTTP atendidas.",
    ["metodo", "ruta", "codigo"],
)

latencia_http = Histogram(
    "mupa_http_segundos",
    "Latencia de las peticiones HTTP.",
    ["metodo", "ruta"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


@contextmanager
def cronometrar(histograma, **etiquetas):
    """with cronometrar(duracion_escaneo): ..."""
    inicio = time.perf_counter()
    try:
        yield
    finally:
        h = histograma.labels(**etiquetas) if etiquetas else histograma
        h.observe(time.perf_counter() - inicio)

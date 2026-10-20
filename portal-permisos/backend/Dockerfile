# Imagen de la API: Alpine y sólo lo necesario para correr (~105 MB).
#   docker build -t mupa-api:local .
#   docker images mupa-api:local

# ---------- etapa 1: instala las dependencias en un entorno aislado
FROM python:3.13-alpine AS dependencias
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt .
# --only-binary: si a una librería le falta paquete para Alpine, el build
# falla aquí en lugar de intentar compilarla sin compilador.
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-compile --only-binary=:all: -r requirements.txt \
 && rm -rf /opt/venv/lib/python3.13/site-packages/pip* /opt/venv/bin/pip*

# ---------- etapa 2: la imagen final, sin pip ni cachés
FROM python:3.13-alpine
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALMACEN_DIR=/datos/expedientes
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip* /usr/local/bin/pip* \
           /usr/local/lib/python3.13/ensurepip /usr/local/lib/python3.13/idlelib \
 && adduser -D -H -u 10001 api \
 && mkdir -p /datos/expedientes && chown api /datos/expedientes
COPY --from=dependencias /opt/venv /opt/venv
WORKDIR /app
COPY main.py antivirus.py metricas.py bd.py tablas.py seguridad.py repositorio.py \
     catalogo.py almacen.py migrar.py constancia.py ./
USER api
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:8000/salud >/dev/null || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Imagen del portal: nginx sin privilegios sirviendo index.html.
#   docker build -t mupa-portal:local .
#   docker run --rm -p 5173:8080 mupa-portal:local      → http://localhost:5173
#
# La variante "unprivileged" corre como el usuario nginx (uid 101) y escucha
# en el 8080, así el contenedor no necesita root ni capacidades especiales.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -qO- http://127.0.0.1:8080/salud >/dev/null || exit 1

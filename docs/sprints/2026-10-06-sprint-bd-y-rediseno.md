# Sprint — Base de datos segura y rediseño del portal

**Proyecto:** Ventanilla Única Municipal — Caso 3: Permisos Municipales
**Rama:** `prueba-local` (integra `base-de-datos` y `rediseno-portal`)
**Fecha de cierre:** 6 de octubre de 2026
**Planes de origen:** [base de datos](../superpowers/plans/2026-09-29-base-de-datos.md) · [rediseño del portal](../superpowers/plans/2026-09-29-rediseno-portal.md)

## Objetivo del sprint

Que los datos del sistema sean persistentes y estén protegidos, y que el
portal se vea oficial y se use sin explicaciones, en escritorio y en celular.

## Resultado

| Indicador | Antes | Después |
|---|---|---|
| Almacenamiento de la API | Listas en memoria (se pierde al reiniciar) | SQLite en desarrollo, PostgreSQL 17 en Docker |
| Pruebas del backend | 13 | 79 + 18 contra PostgreSQL real |
| Pruebas del portal (Playwright) | 40 (27 fallaban) | 132, todas en verde |
| Accesibilidad | Sin revisión automática | axe (WCAG 2.1 AA) en todas las secciones y ambos temas |
| Imagen de la API | No existía | 101 MB, sin pip, usuario no root, sólo lectura |

Puntos comprometidos: **55** · Puntos completados: **55** (estimación en Fibonacci).

---

## Backlog del sprint

### Épica 1 — Base de datos segura

| ID | Historia | Pts | Estado |
|---|---|---|---|
| BD-1 | Como equipo, quiero un entorno Python 3.13 con dependencias fijas, para que todos corramos lo mismo. | 2 | Hecho |
| BD-2 | Como ciudadano, quiero que mi contraseña y mi sesión no se puedan robar de una copia de la base. | 3 | Hecho |
| BD-3 | Como municipio, quiero un esquema de 8 tablas con restricciones, para que los datos inválidos no entren aunque la API falle. | 5 | Hecho |
| BD-4 | Como auditor, quiero una bitácora encadenada que delate cualquier alteración. | 3 | Hecho |
| BD-5 | Como ciudadano, quiero que mis PDF verificados queden guardados con su huella SHA-256. | 2 | Hecho |
| BD-6 | Como desarrollador, quiero un único módulo de acceso a datos (`repositorio.py`). | 5 | Hecho |
| BD-7 | Como ciudadano, quiero que mi cuenta, expedientes y citas sigan ahí después de un reinicio. | 8 | Hecho |
| BD-8 | Como municipio, quiero PostgreSQL con roles de mínimo privilegio, secretos y red interna. | 5 | Hecho |
| BD-9 | Como operador, quiero levantar todo el sistema con un comando y una imagen liviana de la API. | 3 | Hecho |

**Criterios de aceptación verificados:**
- La API (rol `mupa_app`) no puede borrar tablas, ni modificar o vaciar la bitácora y el historial.
- Ni el dueño de la base puede reescribir la auditoría (triggers de sólo anexado).
- La cédula se guarda cifrada (`gAAAA…`) y la contraseña con PBKDF2 de 600 000 iteraciones.
- Diez escrituras simultáneas no bifurcan la cadena de la bitácora.
- Dos registros simultáneos con el mismo correo dan 409, no 500.
- La base no tiene puerto publicado; la alerta `BaseDeDatosCaida` se dispara al detenerla.
- Respaldo y restauración probados: la bitácora sigue íntegra.

### Épica 2 — Rediseño del portal

| ID | Historia | Pts | Estado |
|---|---|---|---|
| UX-1 | Como equipo, quiero el documento HTML completo y la suite de pruebas en verde. | 2 | Hecho |
| UX-2 | Como ciudadano, quiero que el portal se vea oficial: franja del municipio, íconos y controles cómodos de tocar (44 px). | 3 | Hecho |
| UX-3 | Como ciudadano en el celular, quiero una barra de navegación inferior y que el portal recuerde mi tema. | 3 | Hecho |
| UX-4 | Como ciudadano, quiero que un error me lleve al campo exacto que debo corregir. | 3 | Hecho |
| UX-5 | Como ciudadano, quiero buscar mi trámite por nombre, ver mi avance y poder corregir el resumen. | 3 | Hecho |
| UX-6 | Como ciudadano, quiero ver qué requiere mi atención, el detalle de cada expediente y qué sigue. | 3 | Hecho |
| UX-7 | Como ciudadano, quiero elegir la fecha de mi cita con un toque y entender los horarios. | 2 | Hecho |

**Criterios de aceptación verificados:**
- axe no encuentra violaciones de WCAG 2.1 AA en ninguna sección, en tema claro ni oscuro.
- A 320 px de ancho ninguna sección obliga a desplazarse de lado (WCAG 1.4.10).
- El tema cambia aunque el navegador bloquee el almacenamiento.
- La búsqueda de trámites exige todas las palabras, en cualquier orden y sin importar tildes.
- «Hoy» se calcula en hora de Panamá, también después de las 7 p. m.

---

## Defectos encontrados y corregidos durante el sprint

| Defecto | Causa | Corrección |
|---|---|---|
| Un PDF válido con nombre de más de 255 caracteres se rechazaba como «no es un PDF válido». | El recorte del nombre quitaba `.pdf` antes de validar. | Se valida con el nombre original; se guarda recortado conservando la extensión. |
| La búsqueda con varias palabras no funcionaba. | Al copiar el código se perdió la barra de `/\s+/`. | Restaurada, con una prueba que lo cubre. |
| La prueba VUM-22 (EICAR) fallaba con ClamAV real. | ClamAV sólo reconoce EICAR al inicio de un archivo; venía detrás de `%PDF`. Nunca se vio porque sin ClamAV la prueba se omitía. | EICAR va dentro de un stream del PDF. |
| Métricas y alertas duplicadas en Prometheus. | Docker Desktop expone el contenedor también en `host.docker.internal:8000`. | Prometheus lee sólo `api:8000`. |
| Los comandos de respaldo del README fallaban. | La base sólo acepta al usuario de sistema `postgres` en el socket local. | Se usa `docker compose exec -u postgres`. |

## Definición de terminado

- Las pruebas nuevas fallan antes del cambio y pasan después.
- La suite completa queda en verde: backend, PostgreSQL y Playwright.
- Ningún secreto, base local ni dependencia instalada entra a git.
- Cada cambio queda en un commit con mensaje descriptivo.

---

## Revisión (demo)

1. Entrar al portal con `demo@mupa.gob.pa` / `demo1234`.
2. Probar el celular: en DevTools, vista de dispositivo → barra inferior.
3. Solicitar un permiso: buscar «nocturno», avanzar el asistente, dejar un campo vacío y ver el error en el campo exacto.
4. En «Mis solicitudes», abrir el detalle de un expediente en subsanación y agendar la cita desde ahí.
5. En la API (http://localhost:8000/docs), crear una cuenta, reiniciar el contenedor y volver a entrar.
6. En Grafana (http://localhost:3001), mostrar el tablero; detener la base y ver la alerta en Prometheus (http://localhost:9090/alerts).

## Retrospectiva

**Qué funcionó**
- Escribir primero la prueba y verla fallar descubrió dos defectos que el plan traía escritos.
- Correr las pruebas con ClamAV y PostgreSQL reales sacó a la luz fallos que con simulaciones nunca aparecían.

**Qué mejorar**
- Copiar código con scripts puede perder caracteres de escape: verificar con `grep` después de aplicar.
- Las pruebas de integración (ClamAV, PostgreSQL) deben correr en CI, no sólo en local.

---

## Pendiente para el siguiente sprint

| Pendiente | Por qué importa |
|---|---|
| Conectar `index.html` a la API | Hoy el portal usa datos simulados; la API ya está lista. |
| Flujo de aprobación: roles `revisor` y `director`, bandeja del funcionario | El panel de control aún no existe. |
| Revisión manual: NVDA, iPhone/Safari, zoom al 200 % | Las pruebas automáticas no lo cubren. |
| Días hábiles con feriados; corregimiento contra lista cerrada | Validaciones de la Fase 1 sin terminar. |
| Migraciones con Alembic | `create_all` no altera tablas existentes. |
| CI (`calidad.yml`) con `webServer` de Playwright | El README lo menciona, pero no existe. |
| Cambiar `admin/admin` de Grafana y planear la rotación de la clave de cifrado | Operación segura. |

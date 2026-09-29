# Casos de prueba para Qase — Proyecto VUM

Súbelos a Qase antes de correr las pruebas automatizadas. Cada `ID` de aquí
corresponde al `qase.id(N)` que lleva la prueba en `tests/portal.spec.js`; si
Qase te asigna otros números, ajusta el `qase.id()` y no al revés.

**Cómo cargarlos rápido:** Qase → *Test cases* → *Import* → pega la tabla del
final como CSV, o créalos a mano en las cuatro suites de abajo.

---

## Suite 1 · Autenticación

### VUM-1 · Inicio de sesión con credenciales válidas
**Severidad:** crítica · **Prioridad:** alta · **Tipo:** funcional
**Precondición:** existe la cuenta `demo@mupa.gob.pa`.

| # | Acción | Resultado esperado |
|---|--------|--------------------|
| 1 | Abrir el portal | Se muestra la pestaña «Iniciar sesión» |
| 2 | Escribir correo y contraseña válidos | Los campos aceptan el texto |
| 3 | Pulsar «Iniciar sesión» | Entra al panel y saluda por el nombre del usuario |

### VUM-2 · Inicio de sesión con contraseña incorrecta
**Severidad:** crítica · **Prioridad:** alta · **Tipo:** seguridad
Resultado esperado: mensaje «El correo o la contraseña no coinciden» y **el
usuario no entra**. El mensaje no revela si el correo existe o no.

### VUM-3 · Registro rechaza a un menor de edad
**Severidad:** mayor · **Prioridad:** alta
Con edad `16`, el formulario muestra «Debes tener al menos 18 años para
tramitar un permiso» y no crea la cuenta.

### VUM-4 · Registro exige que las contraseñas coincidan
**Severidad:** mayor · **Prioridad:** media

### VUM-5 · Campos obligatorios del registro
**Severidad:** mayor · **Prioridad:** alta · *(manual)*
Verificar uno por uno que faltan bloquean el envío: nombre, apellido, edad,
lugar donde colabora, correo, contraseña y la casilla de la Ley 81 de 2019.

---

## Suite 2 · Solicitud de permiso

### VUM-10 · El catálogo carga los trámites de la MUPA
**Severidad:** crítica · **Prioridad:** alta
Las 8 categorías muestran los 35 trámites del catálogo oficial.

### VUM-11 · Al elegir un permiso se listan sus requisitos
**Severidad:** mayor · **Prioridad:** alta
Para «Permiso Nocturno Categoría A» aparecen los 8 documentos y el plazo de
25 días hábiles.

### VUM-12 · Se rechaza una fecha con menos de 15 días de antelación
**Severidad:** mayor · **Prioridad:** alta · **Tipo:** regla de negocio

### VUM-13 · El aforo debe caber en el rango del permiso
**Severidad:** mayor · **Prioridad:** alta · **Tipo:** regla de negocio
Aforo 1,200 sobre «Espectáculo Público — menos de 500 personas» debe fallar y
sugerir cambiar de permiso.

### VUM-14 · El motivo exige un mínimo de detalle
**Severidad:** menor · **Prioridad:** media

### VUM-15 · Se puede volver atrás sin perder lo escrito
**Severidad:** menor · **Prioridad:** media · *(manual)*

### VUM-16 · El envío genera un número de expediente único
**Severidad:** crítica · **Prioridad:** alta
Formato `EXP-AAAA-NNNNNN`. Aparece en «Mis solicitudes» con estado «Recibido».

---

## Suite 3 · Seguridad documental (ClamAV)

> Esta suite es la que sustenta la respuesta a la pregunta del Caso 3.
> Córrela en cada despliegue: si falla, el portal no sale a producción.

### VUM-20 · Un PDF válido supera las cinco verificaciones
**Severidad:** crítica · **Prioridad:** alta
Formato, tamaño, antivirus, huella SHA-256 y sellado quedan en verde; el botón
«Continuar» se habilita.

### VUM-21 · Un archivo que no es PDF se rechaza aunque tenga extensión .pdf
**Severidad:** crítica · **Prioridad:** alta · **Tipo:** seguridad
Un `.txt` renombrado a `.pdf` falla en la verificación 1, porque se leen los
bytes mágicos `%PDF-` y no sólo la extensión ni el MIME que manda el navegador.

### VUM-22 · ClamAV detiene el archivo de prueba EICAR
**Severidad:** crítica · **Prioridad:** alta · **Tipo:** seguridad
Con la cadena EICAR el escaneo devuelve «Rechazado», el archivo no se adjunta y
el contador `mupa_amenazas_detectadas_total` sube en Grafana.

### VUM-23 · La huella SHA-256 se muestra y viaja al resumen
**Severidad:** mayor · **Prioridad:** alta
La huella del paso 3 es idéntica a la del paso 4 y a la del comprobante.

### VUM-24 · Un PDF de más de 10 MB se rechaza
**Severidad:** mayor · **Prioridad:** media

### VUM-25 · Si ClamAV está caído, no se acepta el documento
**Severidad:** crítica · **Prioridad:** alta · **Tipo:** seguridad · *(manual)*
Detener el contenedor `mupa-clamav` y subir un PDF: la API responde **503** con
«El servicio de verificación no está disponible». *Nunca* debe aceptarlo sin
escanear. En Grafana, `mupa_antivirus_arriba` cae a 0 y dispara la alerta
`AntivirusCaido`.

---

## Suite 4 · Citas, contacto y accesibilidad

### VUM-30 · No se puede reservar sin elegir horario
### VUM-31 · Una cita confirmada aparece en la lista con su número de turno
### VUM-32 · Se rechaza una cita en fin de semana
### VUM-33 · Dos personas no pueden tomar el mismo turno *(manual, requiere backend)*
### VUM-40 · El formulario de contacto devuelve un número de seguimiento
### VUM-41 · Un mensaje demasiado corto se rechaza
### VUM-50 · El portal es usable a 400 px sin desplazamiento horizontal
### VUM-51 · Se puede navegar el formulario de acceso sólo con el teclado
### VUM-52 · El contraste cumple WCAG AA en tema claro y oscuro *(manual)*

---

## Tabla para importar en Qase (CSV)

```csv
id,title,suite,severity,priority,type,is_flaky,automation
1,Inicio de sesión con credenciales válidas,Autenticación,critical,high,functional,0,automated
2,Inicio de sesión con contraseña incorrecta,Autenticación,critical,high,security,0,automated
3,Registro rechaza a un menor de edad,Autenticación,major,high,functional,0,automated
4,Registro exige que las contraseñas coincidan,Autenticación,major,medium,functional,0,automated
5,Campos obligatorios del registro,Autenticación,major,high,functional,0,manual
10,El catálogo carga los trámites de la MUPA,Solicitud de permiso,critical,high,functional,0,automated
11,Al elegir un permiso se listan sus requisitos,Solicitud de permiso,major,high,functional,0,automated
12,Se rechaza una fecha con menos de 15 días de antelación,Solicitud de permiso,major,high,functional,0,automated
13,El aforo debe caber en el rango del permiso,Solicitud de permiso,major,high,functional,0,automated
14,El motivo exige un mínimo de detalle,Solicitud de permiso,minor,medium,functional,0,automated
15,Se puede volver atrás sin perder lo escrito,Solicitud de permiso,minor,medium,usability,0,manual
16,El envío genera un número de expediente único,Solicitud de permiso,critical,high,functional,0,manual
20,Un PDF válido supera las cinco verificaciones,Seguridad documental,critical,high,security,0,automated
21,Un archivo que no es PDF se rechaza aunque tenga extensión .pdf,Seguridad documental,critical,high,security,0,automated
22,ClamAV detiene el archivo de prueba EICAR,Seguridad documental,critical,high,security,0,automated
23,La huella SHA-256 se muestra y viaja al resumen,Seguridad documental,major,high,security,0,automated
24,Un PDF de más de 10 MB se rechaza,Seguridad documental,major,medium,functional,0,manual
25,Si ClamAV está caído no se acepta el documento,Seguridad documental,critical,high,security,0,manual
30,No se puede reservar sin elegir horario,Citas,minor,medium,functional,0,automated
31,Una cita confirmada aparece en la lista,Citas,major,high,functional,0,automated
32,Se rechaza una cita en fin de semana,Citas,minor,medium,functional,0,automated
33,Dos personas no pueden tomar el mismo turno,Citas,major,high,functional,0,manual
40,El formulario de contacto devuelve un número de seguimiento,Contacto,minor,medium,functional,0,automated
41,Un mensaje demasiado corto se rechaza,Contacto,minor,low,functional,0,automated
50,El portal es usable a 400 px sin desplazamiento horizontal,Accesibilidad,major,medium,usability,0,automated
51,Se puede navegar el formulario de acceso sólo con el teclado,Accesibilidad,major,medium,accessibility,0,automated
52,El contraste cumple WCAG AA en tema claro y oscuro,Accesibilidad,major,medium,accessibility,0,manual
```

# Rediseño del portal: tema institucional y experiencia intuitiva — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el portal se vea y se sienta oficial, se use sin explicaciones y funcione igual de bien en el celular, partiendo del diseño y los colores actuales.

**Architecture:** Todo sigue en `portal-permisos/index.html`: un solo archivo, sin framework ni build. Los cambios se hacen sobre el CSS, el HTML y el JavaScript que ya existen, sin reescribirlos. Cada tarea deja la suite de Playwright en verde y agrega su propio archivo de pruebas; axe vigila WCAG 2.1 AA en los dos temas.

**Tech Stack:** HTML, CSS y JavaScript sin dependencias · Playwright 1.49.1 · `@axe-core/playwright` 4.10.1 (nueva, sólo desarrollo).

**Spec:** [portal-permisos/README.md](../../../portal-permisos/README.md) y lo acordado en la conversación:
- tomar el diseño y los colores actuales como base;
- que la identidad se sienta oficial, la interacción moderna y todo sea defendible ante la rúbrica;
- alcance: tema y UX de las pantallas existentes, más el detalle del expediente y el buscador de trámites.

## Estado de la validación

Las 7 tareas se aplicaron en orden sobre una copia limpia del repositorio, con Chromium de Playwright, en escritorio (`chromium`) y celular (`movil`, Pixel 7).
- Después de cada tarea la suite completa pasó, y la final (130 pruebas) pasó en corridas repetidas sin pruebas inestables.
- Las pruebas nuevas de cada tarea se corrieron también contra el portal **anterior** a la tarea, para confirmar que fallan. Los conteos de «Expected» de cada paso son los que se midieron.
- Safari/iOS y los lectores de pantalla **no** se probaron: tienen un paso de revisión manual en la Tarea 7.

## Global Constraints

- **Un solo `index.html`**, sin framework, build ni dependencias en el navegador. Las fuentes siguen siendo Archivo, IBM Plex Sans e IBM Plex Mono.
- **La paleta no cambia de valor** (`--brand #0b4f8a`, `--accent #b8701c`, `--ok`, `--warn`, `--crit` y sus pares oscuros); sólo se agregan tokens nuevos. Ya cumple AA, y axe lo confirma en cada corrida.
- **Nombres que las pruebas usan y no pueden cambiar:**
  - botones «Iniciar sesión», «Continuar», «Solicitar permiso», «Citas», «Contacto», «Confirmar cita», «Enviar mensaje» y «Crear cuenta y entrar», y la pestaña «Crear cuenta»;
  - los IDs `#f-*`, `#c-*`, `#ct-*`, `#su-*`, `#li-*`, `#scan-pill`, `#s1-next`, `#s3-next`, `#file-in`, `#sum` y `#citas-list`.
- **Ningún botón nuevo puede contener esos textos.** Playwright busca el nombre por subcadena: un botón «Ver citas» rompería las pruebas que buscan «Citas». Por la misma razón, el menú móvil es el mismo `<nav>` reubicado, no una copia.
- **Un mensaje de error no se repite en dos lugares** (las búsquedas por texto son estrictas): la pista del campo y el error deben decir cosas distintas.
- **Nada enfocable antes de las pestañas del login:** la prueba VUM-51 espera llegar al formulario con 3 Tab.
- **Los cambios de cada tarea se aplican en el orden en que aparecen:** cada «reemplaza» busca un texto que existe *en ese momento*, y algunos se apoyan en el cambio anterior. Cada texto a buscar aparece una sola vez, salvo los marcados «todas las apariciones».
- **`index.html` usa finales de línea CRLF.** La herramienta Edit los respeta; si editas con otro medio, no los conviertas.
- **Estilo del código actual:** comentarios en español y tuteo en los textos.
- **Servidor para las pruebas:** `npx serve -l 5173 .` desde `portal-permisos`, en otra terminal (`playwright.config.js` no lo levanta solo).
- Cada commit termina con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Lectores de pantalla reales.** axe revisa la estructura, pero no escucha lo que NVDA anuncia al mostrar un error, al mover el foco o al abrir el diálogo. Queda como revisión manual en la Tarea 7.
2. **Safari e iOS.** Las pruebas sólo usan Chromium. `<dialog>`, `100dvh` y `env(safe-area-inset-bottom)` bajo la barra de inicio del iPhone son lo más probable que falle. Revisión manual en la Tarea 7.
3. **Navegadores que bloquean `localStorage`** (modo privado). El tema debe cambiar igual, aunque no se recuerde. Lo prueba `El tema cambia aunque el navegador bloquee el almacenamiento` (Tarea 3).
4. **Pantallas de 320 px** (WCAG 1.4.10). Ninguna sección debe obligar a desplazarse de lado. Lo prueba `A 320 px ninguna sección obliga a desplazarse de lado` (Tarea 7).
5. **Zoom al 200 % en escritorio** (WCAG 1.4.4). Revisión manual en la Tarea 7.

---
### Task 1: Base sana: documento completo, `hidden` que sí oculta y pruebas en verde

**Files:**
- Modify: `portal-permisos/calidad/tests/portal.spec.js`
- Modify: `portal-permisos/index.html`

**Por qué:**

Hoy la suite de Playwright falla en 27 de 40 pruebas, y casi todo es por errores reales del portal:

| Error | Qué ve el usuario |
|---|---|
| Falta `<!doctype>`, `<meta charset>` y `<meta name="viewport">` | Acentos rotos («PanamÃ¡») según cómo se abra el archivo; en el celular se ve la versión de escritorio reducida |
| `.shell`, `.notice` y los estilos en línea de los pasos anulan el atributo `hidden` | El panel completo aparece **debajo del login** sin haber entrado; los pasos del asistente se **apilan**; hay recuadros rojos de error **vacíos** desde el inicio |
| La cuadrícula móvil usa `1fr` | El menú estira la página más allá de la pantalla (desplazamiento lateral) |
| Los botones del menú móvil tienen `width:100%` en una fila | Se enciman: al tocar «Contacto» se abre «Mis solicitudes» |
| Si el PDF cambia mientras se lee, la promesa falla sin capturarse | La pantalla queda en «Verificando» para siempre |

El resto son pruebas ambiguas:
- `getByLabel("Edad")` también coincide con «grav**edad**».
- El registro escribía en el correo del formulario de **Contacto**.
- Dos pruebas en paralelo reescribían el mismo PDF.
- Varios mensajes aparecían repetidos en una pista y en el error.

- [ ] **Step 1: Preparar el entorno y ver la línea base**

En una terminal, desde `portal-permisos`:

```powershell
npx serve -l 5173 .
```

En otra terminal, desde `portal-permisos/calidad`:

```powershell
npm install
npx playwright install chromium
npx playwright test
```

Expected: `27 failed`, `13 passed` (en los dos proyectos, `chromium` y `movil`).

- [ ] **Step 2: Corregir las pruebas ambiguas**

**1. «Edad» también coincidía con «gravedad».** En `portal-permisos/calidad/tests/portal.spec.js` (todas las apariciones), reemplaza:

```js
await page.getByLabel("Edad").fill(
```

por:

```js
await page.getByLabel(/^Edad/).fill(
```

**2. Sin ^ también coincidía con la Renovación.** En `portal-permisos/calidad/tests/portal.spec.js`, reemplaza:

```js
name: /Permiso Nocturno Categoría A$/
```

por:

```js
name: /^Permiso Nocturno Categoría A$/
```

**3. El correo del registro, no el de Contacto.** En `portal-permisos/calidad/tests/portal.spec.js` (todas las apariciones), reemplaza:

```js
await page.getByLabel(/Correo electrónico/).last().fill(
```

por:

```js
await page.locator("#pane-signup").getByLabel(/Correo electrónico/).fill(
```

**4. La contraseña del registro, no la del login.** En `portal-permisos/calidad/tests/portal.spec.js` (todas las apariciones), reemplaza:

```js
await page.getByLabel("Contraseña", { exact: false }).first().fill(
```

por:

```js
await page.locator("#pane-signup").getByLabel("Contraseña", { exact: false }).first().fill(
```

**5. Cada prueba escribe su propio archivo.** En `portal-permisos/calidad/tests/portal.spec.js`, reemplaza:

```js
  fs.mkdirSync(TMP, { recursive: true });
  const ruta = path.join(TMP, nombre);
```

por:

```js
  // Una carpeta por llamada: las pruebas corren en paralelo y compartir el
  // archivo hacía que una lo reescribiera mientras la otra lo leía.
  fs.mkdirSync(TMP, { recursive: true });
  const ruta = path.join(fs.mkdtempSync(path.join(TMP, "f-")), nombre);
```

- [ ] **Step 3: Corregir el portal**

**1. Documento completo: charset, viewport, idioma.** En `portal-permisos/index.html`, reemplaza:

```html
<title>Ventanilla Única Municipal</title>
```

por:

```html
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="Portal oficial para solicitar permisos ante la Dirección de Permisos y Cumplimiento del Municipio de Panamá.">
<title>Ventanilla Única Municipal</title>
```

**2. Cierra head y abre body.** En `portal-permisos/index.html`, reemplaza:

```html
</style>

<!-- =================== ACCESO =================== -->
```

por:

```html
</style>
</head>
<body>

<!-- =================== ACCESO =================== -->
```

**3. Cierra body y html.** En `portal-permisos/index.html`, reemplaza:

```html
mostrarPanel("login");
</script>
```

por:

```html
mostrarPanel("login");
</script>
</body>
</html>
```

**4. Hidden gana siempre.** En `portal-permisos/index.html`, reemplaza:

```html
*{box-sizing:border-box}
body{
```

por:

```html
*{box-sizing:border-box}
/* `hidden` debe ganar siempre. Antes .shell, .notice y los estilos en línea de
   los pasos ponían su propio display y dejaban visible lo que debía ocultarse:
   el panel aparecía bajo el login y los pasos del asistente se apilaban. */
[hidden]{display:none !important}
html{height:100%}
body{
  margin:0;min-height:100%;
```

**5. La pista no repite el mensaje de error.** En `portal-permisos/index.html`, reemplaza:

```html
<span class="hint">Mínimo 15 días hábiles de antelación.</span>
```

por:

```html
<span class="hint">Mínimo 15 días hábiles a partir de hoy.</span>
```

**6. La pista de citas no repite el mensaje de error.** En `portal-permisos/index.html`, reemplaza:

```html
<span class="hint">Atención de lunes a viernes.</span>
```

por:

```html
<span class="hint">Atención en días hábiles (L–V).</span>
```

**7. El aviso no compite con la etiqueta Confirmada.** En `portal-permisos/index.html`, reemplaza:

```html
toast(`Cita ${turno} confirmada`);
```

por:

```html
toast(`Cita ${turno} reservada`);
```

**8. Nombre accesible del trámite = sólo su nombre.** En `portal-permisos/index.html`, reemplaza:

```html
    `<button type="button" class="opt" data-perm="${esc(p.id)}" aria-pressed="false">
       <span class="radio"></span>
       <span><span class="on">${esc(p.n)}</span><span class="od">${p.req.length} documentos requeridos</span></span>
       <span class="days">${p.d} días háb.</span>
     </button>`).join("");
```

por:

```html
    `<button type="button" class="opt" data-perm="${esc(p.id)}" aria-pressed="false"
             aria-label="${esc(p.n)}" aria-describedby="od-${i} dd-${i}">
       <span class="radio"></span>
       <span><span class="on">${esc(p.n)}</span><span class="od" id="od-${i}">${p.req.length} documentos requeridos</span></span>
       <span class="days" id="dd-${i}">${p.d} días háb.</span>
     </button>`).join("");
```

**9. Índice para los ids de descripción.** En `portal-permisos/index.html`, reemplaza:

```html
  $("#perms").innerHTML = CATALOGO[state.sel.cat].items.map(p =>
```

por:

```html
  $("#perms").innerHTML = CATALOGO[state.sel.cat].items.map((p, i) =>
```

**10. Los requisitos del paso 3 se pintan al llegar.** En `portal-permisos/index.html`, reemplaza:

```html
  $("#req-wrap").innerHTML = html; $("#req-wrap").hidden = false;
  $("#req-wrap-3").innerHTML = html;
```

por:

```html
  $("#req-wrap").innerHTML = html; $("#req-wrap").hidden = false;
```

**11. Pinta requisitos al entrar al paso 3.** En `portal-permisos/index.html`, reemplaza:

```html
  state.sel.datos = d;
  paso(3);
```

por:

```html
  state.sel.datos = d;
  $("#req-wrap-3").innerHTML = requisitosHTML(state.sel.perm);
  paso(3);
```

**12. Fila corta, mensaje completo en el aviso.** En `portal-permisos/index.html`, reemplaza:

```html
  const fallar = (c, msg) => {
    marcar(c, "bad", msg);
```

por:

```html
  const fallar = (c, msg, corto) => {
    marcar(c, "bad", corto);
```

**13. Corto: formato.** En `portal-permisos/index.html`, reemplaza:

```html
return fallar("fmt", "El archivo no es un PDF válido. Sube un documento con extensión .pdf.");
```

por:

```html
return fallar("fmt", "El archivo no es un PDF válido. Sube un documento con extensión .pdf.", "No es un PDF");
```

**14. Corto: tamaño.** En `portal-permisos/index.html`, reemplaza:

```html
Comprime el PDF e inténtalo de nuevo.`);
```

por:

```html
Comprime el PDF e inténtalo de nuevo.`, "Supera 10 MB");
```

**15. Corto: vacío.** En `portal-permisos/index.html`, reemplaza:

```html
return fallar("size", "El archivo está vacío.");
```

por:

```html
return fallar("size", "El archivo está vacío.", "Vacío");
```

**16. Corto: antivirus.** En `portal-permisos/index.html`, reemplaza:

```html
El documento fue puesto en cuarentena y no se adjuntó al expediente.");
```

por:

```html
El documento fue puesto en cuarentena y no se adjuntó al expediente.", "Bloqueado");
```

**17. La columna no crece con el menú.** En `portal-permisos/index.html`, reemplaza:

```html
@media (max-width:900px){.shell{grid-template-columns:1fr}}
```

por:

```html
@media (max-width:900px){.shell{grid-template-columns:minmax(0,1fr)}}
```

**18. En móvil los botones del menú no se enciman.** En `portal-permisos/index.html`, reemplaza:

```html
  nav.menu{flex-direction:row;overflow-x:auto;gap:4px;scrollbar-width:none}
```

por:

```html
  nav.menu{flex-direction:row;overflow-x:auto;gap:4px;scrollbar-width:none}
  nav.menu button{width:auto;flex:none}
```

**19. Una lectura fallida no deja la verificación colgada.** En `portal-permisos/index.html`, reemplaza:

```html
async function verificar(file){
  showErr($("#s3-err"), null);
```

por:

```html
async function verificar(file){
  try { await verificarPasos(file); }
  catch {
    // El archivo cambió o desapareció del disco mientras se leía (carpeta
    // sincronizada, memoria USB retirada…): se rechaza en vez de quedar en «Verificando».
    const c = $('.chk[data-s="run"]')?.dataset.c || "fmt";
    marcar(c, "bad", "No se pudo leer");
    $("#scan-pill").className = "pill crit"; $("#scan-pill").textContent = "Rechazado";
    showErr($("#s3-err"), "No pudimos leer el archivo. Vuelve a seleccionarlo.");
    fileIn.value = "";
  }
}

async function verificarPasos(file){
  showErr($("#s3-err"), null);
```

- [ ] **Step 4: Verificar**

Run: `npx playwright test`
Expected: `40 passed`. Córrelo dos veces: no debe haber pruebas inestables.

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "fix(portal): documento completo, hidden que oculta y suite de Playwright en verde" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Sistema visual: tokens, franja oficial, íconos y controles de 44 px

**Files:**
- Create: `portal-permisos/calidad/tests/accesibilidad.spec.js`
- Create: `portal-permisos/calidad/tests/ayuda.js`
- Modify: `portal-permisos/calidad/package.json`
- Modify: `portal-permisos/index.html`

**Por qué:**

La paleta actual **ya cumple el contraste WCAG 2.1 AA** en los dos temas (axe no encuentra violaciones), así que los colores no cambian: esta tarea los consolida y completa.
- **Franja «Portal oficial del Municipio de Panamá»** con la raya en el ámbar de acento, que hoy casi no se usa. Es la señal de confianza que tienen los portales de gobierno.
- **Letra base de 16 px:** en el celular evita el zoom automático al escribir.
- **Campos y botones de 44 px** de alto, del tamaño cómodo para el dedo.
- **Foco visible de 3 px** con halo.
- **Íconos SVG** en lugar de los emojis ⚠ y ✓, que cada sistema dibuja distinto.
- **`role="alert"`** en los errores, para que los lectores de pantalla los anuncien.
- Se respeta **«reducir movimiento»** del sistema operativo.

axe entra como dependencia de desarrollo para vigilar WCAG en cada corrida.

- [ ] **Step 1: Escribir las pruebas**

**1. Axe para revisar WCAG automáticamente.** En `portal-permisos/calidad/package.json`, reemplaza:

```json
    "@playwright/test": "1.49.1",
```

por:

```json
    "@axe-core/playwright": "4.10.1",
    "@playwright/test": "1.49.1",
```

**2. Crea `portal-permisos/calidad/tests/ayuda.js`**

```js
// @ts-check
/**
 * Utilidades compartidas por las pruebas de interfaz (navegación, formularios,
 * asistente, expedientes y accesibilidad). portal.spec.js conserva las suyas.
 */
const { expect } = require("@playwright/test");
const { AxeBuilder } = require("@axe-core/playwright");

const CUENTA = { email: "demo@mupa.gob.pa", pass: "demo1234" };

async function entrar(page) {
  await page.goto("/");
  await page.locator("#li-email").fill(CUENTA.email);
  await page.locator("#li-pass").fill(CUENTA.pass);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: /Buen[oa]s/ })).toBeVisible();
}

/** Revisa la página con axe contra WCAG 2.1 A y AA; devuelve un resumen legible. */
async function violaciones(page) {
  const r = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return r.violations.map(v =>
    `${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(" ")).join(", ")}`);
}

module.exports = { CUENTA, entrar, violaciones };
```

**3. Crea `portal-permisos/calidad/tests/accesibilidad.spec.js`**

```js
// @ts-check
const { test, expect } = require("@playwright/test");
const { entrar, violaciones } = require("./ayuda");

/**
 * Sistema visual: identidad oficial, contraste AA en ambos temas y controles
 * cómodos para el dedo. axe revisa WCAG 2.1 A y AA de forma automática.
 */

for (const tema of ["light", "dark"]) {
  test.describe(`Tema ${tema === "light" ? "claro" : "oscuro"}`, () => {
    test.use({ colorScheme: tema });

    test("La pantalla de acceso cumple WCAG 2.1 AA", async ({ page }) => {
      await page.goto("/");
      expect(await violaciones(page)).toEqual([]);
    });

    test("El panel de inicio cumple WCAG 2.1 AA", async ({ page }) => {
      await entrar(page);
      expect(await violaciones(page)).toEqual([]);
    });
  });
}

test("La franja oficial identifica al Municipio en todas las pantallas", async ({ page }) => {
  await page.goto("/");
  const franja = page.getByRole("note", { name: "Sitio oficial" });
  await expect(franja).toContainText("Portal oficial del Municipio de Panamá");
  await entrar(page);
  await expect(franja).toBeVisible();
});

test("Campos y botones principales miden al menos 44 px de alto", async ({ page }) => {
  await page.goto("/");
  for (const sel of ["#li-email", "#li-pass", '#pane-login button[type="submit"]']) {
    const caja = await page.locator(sel).boundingBox();
    expect(caja?.height, sel).toBeGreaterThanOrEqual(44);
  }
});

test("Los avisos usan íconos, no emojis, y los errores se anuncian", async ({ page }) => {
  await page.goto("/");
  const aviso = page.locator("#li-err");
  await expect(aviso).toHaveAttribute("role", "alert");
  await expect(aviso.locator("svg")).toHaveCount(1);
  expect(await page.locator(".notice").evaluateAll(ns => ns.some(n => /[⚠✓]/.test(n.textContent || "")))).toBe(false);
});
```

Instala la dependencia nueva después de editar `package.json`: `npm install`.

- [ ] **Step 2: Verificar que fallan**

Run (desde `portal-permisos/calidad`): `npx playwright test --project=chromium tests/accesibilidad.spec.js`
Expected: `3 failed`, `4 passed` (las 4 de axe ya pasan: son la protección que impide empeorar el contraste)

- [ ] **Step 3: Implementar**

**1. Tokens nuevos, tema claro.** En `portal-permisos/index.html`, reemplaza:

```html
  --shadow:0 1px 2px rgba(21,33,44,.06), 0 8px 24px -16px rgba(21,33,44,.28);
```

por:

```html
  --shadow:0 1px 2px rgba(21,33,44,.06), 0 8px 24px -16px rgba(21,33,44,.28);
  --accent-soft:#f8ecdb;
  --franja:#0a3f6f;
  --ring:0 0 0 3px rgba(11,79,138,.28);
  --tap:44px;               /* alto mínimo de lo que se toca con el dedo */
```

**2. Tokens nuevos, tema oscuro (los dos bloques).** En `portal-permisos/index.html` (todas las apariciones), reemplaza:

```html
0 8px 24px -16px rgba(0,0,0,.8);
```

por:

```html
0 8px 24px -16px rgba(0,0,0,.8);
  --accent-soft:#33260f; --franja:#0d2d4a; --ring:0 0 0 3px rgba(79,161,224,.35);
```

**3. 16 px de base: se lee mejor y el celular no hace zoom al escribir.** En `portal-permisos/index.html`, reemplaza:

```html
  font-size:15px;
```

por:

```html
  font-size:16px;
```

**4. Foco visible más claro.** En `portal-permisos/index.html`, reemplaza:

```html
:focus-visible{outline:2px solid var(--brand);outline-offset:2px;border-radius:4px}
```

por:

```html
:focus-visible{outline:3px solid var(--brand);outline-offset:2px;border-radius:4px}
.ic{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none !important;transition:none !important;scroll-behavior:auto !important}
}
```

**5. Los rótulos pequeños llevan el azul institucional.** En `portal-permisos/index.html`, reemplaza:

```html
  letter-spacing:.11em;text-transform:uppercase;color:var(--ink-2);
```

por:

```html
  letter-spacing:.11em;text-transform:uppercase;color:var(--brand);
```

**6. Campos de 44 px, texto de 16 px y foco con halo.** En `portal-permisos/index.html`, reemplaza:

```html
  width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:7px;
  background:var(--surface);color:var(--ink);font:inherit;font-size:.92rem;
}
```

por:

```html
  width:100%;min-height:var(--tap);padding:10px 12px;border:1px solid var(--line);border-radius:8px;
  background:var(--surface);color:var(--ink);font:inherit;font-size:1rem;
  transition:border-color .15s ease, box-shadow .15s ease;
}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--brand);box-shadow:var(--ring)}
input[type=checkbox]{min-width:20px;height:20px;accent-color:var(--brand);flex:none}
```

**7. Botones de 44 px.** En `portal-permisos/index.html`, reemplaza:

```html
  padding:9px 18px;border-radius:7px;border:1px solid transparent;
```

por:

```html
  min-height:var(--tap);padding:10px 20px;border-radius:8px;border:1px solid transparent;
```

**8. Botones discretos de al menos 36 px.** En `portal-permisos/index.html`, reemplaza:

```html
.btn.plain{background:transparent;color:var(--ink-2);border-color:transparent;padding:6px 10px}
```

por:

```html
.btn.plain{background:transparent;color:var(--ink-2);border-color:transparent;padding:6px 10px;min-height:36px}
```

**9. El sello lleva el acento ámbar.** En `portal-permisos/index.html`, reemplaza:

```html
  letter-spacing:.02em;background:var(--brand-soft);
}
```

por:

```html
  letter-spacing:.02em;background:var(--brand-soft);
  box-shadow:0 0 0 3px var(--accent-soft);
}
```

**10. Ícono de los avisos.** En `portal-permisos/index.html`, reemplaza:

```html
.notice{display:flex;gap:10px;padding:11px 13px;border-radius:9px;font-size:.85rem;align-items:flex-start}
```

por:

```html
.notice{display:flex;gap:10px;padding:11px 13px;border-radius:9px;font-size:.9rem;align-items:flex-start}
.notice .ni{width:18px;height:18px;flex:none;margin-top:2px}

/* ---------- franja oficial ---------- */
.franja{background:var(--franja);color:#fff;font-size:.8rem;border-bottom:3px solid var(--accent)}
.franja-in{max-width:1040px;margin:0 auto;padding:6px 16px;display:flex;gap:8px;align-items:center}
.franja svg{width:16px;height:16px;flex:none}
```

**11. Sprite de íconos y franja oficial.** En `portal-permisos/index.html`, reemplaza:

```html
</head>
<body>
```

por:

```html
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
  <symbol id="i-alerta" viewBox="0 0 24 24"><path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17.5v.01"/></symbol>
  <symbol id="i-ok" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16 10"/></symbol>
  <symbol id="i-escudo" viewBox="0 0 24 24"><path d="M12 3 4 6v5c0 5 3.4 8.6 8 10 4.6-1.4 8-5 8-10V6z"/><path d="m9 12 2 2 4-4"/></symbol>
</svg>

<div class="franja" role="note" aria-label="Sitio oficial">
  <div class="franja-in">
    <svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-escudo"/></svg>
    <span>Portal oficial del <b>Municipio de Panamá</b> · Dirección de Permisos y Cumplimiento</span>
  </div>
</div>
```

**12. Avisos de error: ícono y role=alert.** En `portal-permisos/index.html` (todas las apariciones), reemplaza:

```html
class="notice crit" hidden><span>⚠</span>
```

por:

```html
class="notice crit" role="alert" hidden><svg class="ic ni" aria-hidden="true"><use href="#i-alerta"/></svg>
```

**13. Avisos de éxito: ícono.** En `portal-permisos/index.html` (todas las apariciones), reemplaza:

```html
<span>✓</span>
```

por:

```html
<svg class="ic ni" aria-hidden="true"><use href="#i-ok"/></svg>
```

- [ ] **Step 4: Verificar que pasan**

Run: `npx playwright test`
Expected: `54 passed`, 0 failed, 0 flaky

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "feat(portal): sistema visual con franja oficial, íconos y controles accesibles" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Navegación: barra inferior en el celular, tema recordado y foco en cada sección

**Files:**
- Create: `portal-permisos/calidad/tests/navegacion.spec.js`
- Modify: `portal-permisos/index.html`

**Por qué:**

- **En el celular no había forma de cerrar sesión ni de cambiar el tema:** esos botones se ocultaban con `display:none`. Pasan al encabezado como íconos con nombre accesible.
- **El menú baja a una barra fija inferior** con las cinco secciones siempre a la vista. Es **el mismo `<nav>`** reubicado con CSS: duplicar los botones rompería las pruebas que buscan «Citas» o «Contacto» por nombre.
- **El bloque CSS móvil va *después* de la regla base de los botones.** Si va antes, la base le gana y las etiquetas se enciman; la prueba «caben en su botón» lo vigila.
- **El conmutador «Tema oscuro»** anuncia su estado con `aria-pressed` y se recuerda en `localStorage`, aunque el navegador lo bloquee (modo privado).
- **Al cambiar de sección**, el foco va al título y cambia el título de la pestaña: así un lector de pantalla sabe dónde está.
- **Enlace «Saltar al contenido»** para quien navega con teclado.

- [ ] **Step 1: Escribir las pruebas**

**1. Crea `portal-permisos/calidad/tests/navegacion.spec.js`**

```js
// @ts-check
const { test, expect } = require("@playwright/test");
const { entrar, violaciones } = require("./ayuda");

/** Navegación: barra inferior en el celular, tema recordado y foco en cada sección. */

test.describe("En el celular", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("Las cinco secciones están siempre a la vista en la barra inferior", async ({ page }) => {
    await entrar(page);
    const menu = page.getByRole("navigation", { name: /Secciones/ });
    const caja = await menu.boundingBox();
    expect(Math.round((caja?.y ?? 0) + (caja?.height ?? 0))).toBeGreaterThanOrEqual(840);
    for (const nombre of ["Inicio", "Solicitar permiso", "Mis solicitudes", "Citas", "Contacto"]) {
      await expect(menu.getByRole("button", { name: nombre })).toBeInViewport({ ratio: 1 });
    }
  });

  test("Las etiquetas del menú caben en su botón sin encimarse", async ({ page }) => {
    await entrar(page);
    const desbordan = await page.locator("nav.menu button").evaluateAll(bs =>
      bs.filter(b => b.scrollWidth > b.clientWidth + 1).map(b => b.textContent?.trim()));
    expect(desbordan).toEqual([]);
  });

  test("Se puede cerrar sesión", async ({ page }) => {
    await entrar(page);
    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
  });

  test("La barra no tapa el final de la página", async ({ page }) => {
    await entrar(page);
    await page.getByRole("button", { name: "Contacto" }).click();
    await page.getByRole("button", { name: "Enviar mensaje" }).scrollIntoViewIfNeeded();
    const boton = await page.getByRole("button", { name: "Enviar mensaje" }).boundingBox();
    const barra = await page.getByRole("navigation", { name: /Secciones/ }).boundingBox();
    expect((boton?.y ?? 0) + (boton?.height ?? 0)).toBeLessThanOrEqual(barra?.y ?? 0);
  });

  test("La barra inferior cumple WCAG 2.1 AA", async ({ page }) => {
    await entrar(page);
    expect(await violaciones(page)).toEqual([]);
  });
});

test("El tema oscuro se activa, se anuncia y se recuerda", async ({ page }) => {
  await entrar(page);
  const boton = page.getByRole("button", { name: "Tema oscuro" });
  await expect(boton).toHaveAttribute("aria-pressed", "false");
  await boton.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(boton).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("El tema cambia aunque el navegador bloquee el almacenamiento (modo privado)", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", { get() { throw new Error("almacenamiento bloqueado"); } });
  });
  await entrar(page);
  await page.getByRole("button", { name: "Tema oscuro" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("Al cambiar de sección el foco va al título y la pestaña lo dice", async ({ page }) => {
  await entrar(page);
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Citas" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Citas" })).toBeFocused();
  await expect(page).toHaveTitle(/^Citas · Ventanilla Única/);
});

test("Hay un enlace para saltar al contenido", async ({ page }) => {
  await entrar(page);
  const saltar = page.getByRole("link", { name: "Saltar al contenido" });
  await saltar.focus();
  await expect(saltar).toBeInViewport();
  await saltar.press("Enter");
  await expect(page.locator("#contenido")).toBeFocused();
});
```

- [ ] **Step 2: Verificar que fallan**

Run (desde `portal-permisos/calidad`): `npx playwright test --project=chromium tests/navegacion.spec.js`
Expected: `7 failed`, `2 passed` (pasan la de axe y la de etiquetas: son protecciones)

- [ ] **Step 3: Implementar**

**1. Aplica el tema guardado antes de pintar (sin parpadeo).** En `portal-permisos/index.html`, reemplaza:

```html
<title>Ventanilla Única Municipal</title>
```

por:

```html
<title>Ventanilla Única Municipal</title>
<script>try{var t=localStorage.getItem("vum-tema");if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
```

**2. Encabezado compacto en el celular.** En `portal-permisos/index.html`, reemplaza:

```html
@media (max-width:900px){
  .side{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);
    padding:14px 16px;gap:14px}
}
```

por:

```html
@media (max-width:900px){
  .side{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);
    padding:10px 16px;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px}
}
```

**3. Quita la cinta horizontal del menú (la reemplaza la barra inferior).** En `portal-permisos/index.html`, elimina este bloque:

```html
@media (max-width:900px){
  nav.menu{flex-direction:row;overflow-x:auto;gap:4px;scrollbar-width:none}
  nav.menu button{width:auto;flex:none}
  nav.menu::-webkit-scrollbar{display:none}
}
```

**4. Menú como barra inferior fija en el celular (después de la regla base, para ganarle).** En `portal-permisos/index.html`, reemplaza:

```html
nav.menu svg{width:17px;height:17px;flex:none;stroke:currentColor;fill:none;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
```

por:

```html
nav.menu svg{width:17px;height:17px;flex:none;stroke:currentColor;fill:none;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
@media (max-width:900px){
  /* El mismo menú, fijo abajo: las cinco secciones siempre al alcance del pulgar.
     Va después de la regla base de los botones para poder cambiar su tamaño y ajuste. */
  nav.menu{position:fixed;left:0;right:0;bottom:0;z-index:40;display:grid;
    grid-template-columns:repeat(5,minmax(0,1fr));gap:2px;background:var(--surface);
    border-top:1px solid var(--line);padding:4px 4px calc(4px + env(safe-area-inset-bottom,0px));
    box-shadow:0 -6px 20px -14px rgba(21,33,44,.35)}
  nav.menu button{flex-direction:column;justify-content:center;gap:3px;min-height:56px;padding:6px 2px;
    text-align:center;white-space:normal;font-size:.68rem;line-height:1.15;overflow-wrap:anywhere}
  nav.menu svg{width:20px;height:20px}
  html{scroll-padding-bottom:96px}
}
```

**5. En el celular, tema y cierre de sesión como íconos en el encabezado.** En `portal-permisos/index.html`, reemplaza:

```html
@media (max-width:900px){.side .foot{display:none}}
```

por:

```html
@media (max-width:900px){
  .side .foot{margin:0;flex-direction:row;gap:4px}
  .side .foot .who,.side .foot .opsbar{display:none}
  .side .foot .btn{width:44px;min-height:44px;padding:0}
  .side .foot .lbl{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
}
.side .foot .btn svg{width:18px;height:18px;flex:none}
```

**6. Espacio para la barra inferior y el aviso flotante por encima.** En `portal-permisos/index.html`, reemplaza:

```html
@media (max-width:640px){.main{padding:20px 16px 56px}}
```

por:

```html
@media (max-width:640px){.main{padding:20px 16px 56px}}
@media (max-width:900px){
  .main{padding-bottom:104px}
  .toast{bottom:calc(84px + env(safe-area-inset-bottom,0px))}
}
.saltar{position:absolute;left:16px;top:-60px;z-index:70;background:var(--brand);color:var(--on-brand);
  padding:10px 16px;border-radius:8px;font-weight:600;text-decoration:none}
.saltar:focus{top:12px}
.main:focus{outline:none}
[data-page] h1:focus{outline:none}
```

**7. Enlace para saltar al contenido.** En `portal-permisos/index.html`, reemplaza:

```html
<div id="view-app" class="shell" hidden>
```

por:

```html
<div id="view-app" class="shell" hidden>
  <a class="saltar" href="#contenido">Saltar al contenido</a>
```

**8. Destino del enlace.** En `portal-permisos/index.html`, reemplaza:

```html
  <main class="main">
```

por:

```html
  <main class="main" id="contenido" tabindex="-1">
```

**9. Conmutador de tema con ícono y estado.** En `portal-permisos/index.html`, reemplaza:

```html
<button class="btn plain" id="btn-theme" style="justify-content:flex-start">Cambiar tema</button>
```

por:

```html
<button class="btn plain" id="btn-theme" aria-pressed="false" style="justify-content:flex-start">
        <svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg><span class="lbl">Tema oscuro</span></button>
```

**10. Cerrar sesión con ícono.** En `portal-permisos/index.html`, reemplaza:

```html
<button class="btn plain" id="btn-logout" style="justify-content:flex-start">Cerrar sesión</button>
```

por:

```html
<button class="btn plain" id="btn-logout" style="justify-content:flex-start">
        <svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H4"/></svg><span class="lbl">Cerrar sesión</span></button>
```

**11. El tema se conmuta, se anuncia y se guarda.** En `portal-permisos/index.html`, reemplaza:

```html
$("#btn-theme").addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const oscuro = cur === "dark" ||
    (!cur && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", oscuro ? "light" : "dark");
});
```

por:

```html
function temaOscuro(){
  const cur = document.documentElement.getAttribute("data-theme");
  return cur === "dark" || (!cur && matchMedia("(prefers-color-scheme: dark)").matches);
}
function pintarBotonTema(){ $("#btn-theme").setAttribute("aria-pressed", String(temaOscuro())); }
$("#btn-theme").addEventListener("click", () => {
  const nuevo = temaOscuro() ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", nuevo);
  try { localStorage.setItem("vum-tema", nuevo); } catch {}   // modo privado: sólo no se recuerda
  pintarBotonTema();
});
pintarBotonTema();
```

**12. Foco al título y título de la pestaña en cada sección.** En `portal-permisos/index.html`, reemplaza:

```html
    b.dataset.nav === pagina ? b.setAttribute("aria-current","page") : b.removeAttribute("aria-current"));
  window.scrollTo({ top:0, behavior:"smooth" });
}
```

por:

```html
    b.dataset.nav === pagina ? b.setAttribute("aria-current","page") : b.removeAttribute("aria-current"));
  window.scrollTo({ top:0, behavior:"smooth" });
  // Lectores de pantalla y teclado: el foco llega al título de la sección nueva.
  const titulo = $(`[data-page="${pagina}"] h1`);
  if (titulo){ titulo.tabIndex = -1; titulo.focus({ preventScroll:true }); }
  const nombre = $(`nav.menu [data-nav="${pagina}"]`)?.textContent.trim();
  document.title = `${nombre} · Ventanilla Única Municipal`;
}
```

- [ ] **Step 4: Verificar que pasan**

Run: `npx playwright test`
Expected: `72 passed`, 0 failed, 0 flaky

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "feat(portal): barra de navegación móvil, tema recordado y foco por sección" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Formularios que guían: el error señala el campo exacto

**Files:**
- Create: `portal-permisos/calidad/tests/formularios.spec.js`
- Modify: `portal-permisos/calidad/tests/ayuda.js`
- Modify: `portal-permisos/index.html`

**Por qué:**

Hoy todos los errores salen en un solo aviso al final del formulario y el usuario tiene que buscar qué campo falló. Además, `input:invalid` pinta de rojo el correo **mientras se escribe**, lo que reprocha al usuario antes de tiempo.
- Cada validación le pasa a `showErr` el campo que falló.
- Ese campo queda con `aria-invalid`, unido al mensaje por `aria-describedby`, y recibe el foco.
- La marca se quita en cuanto el usuario corrige.
- Una contraseña equivocada **no** marca ningún campo, para no revelar si el correo existe.
- Se agrega un botón «Mostrar contraseña».

- [ ] **Step 1: Escribir las pruebas**

**1. Crea `portal-permisos/calidad/tests/formularios.spec.js`**

```js
// @ts-check
const { test, expect } = require("@playwright/test");
const { entrar, irAPaso2, llenarPaso2 } = require("./ayuda");

/** Formularios que guían: el error señala el campo exacto y se va al corregirlo. */

test("El error del registro lleva el foco al campo que hay que corregir", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Crear cuenta" }).click();
  await page.locator("#su-nombre").fill("Ana");
  await page.locator("#su-apellido").fill("Pérez");
  await page.locator("#su-edad").fill("16");
  await page.getByRole("button", { name: /Crear cuenta y entrar/ }).click();

  const edad = page.locator("#su-edad");
  await expect(edad).toBeFocused();
  await expect(edad).toHaveAttribute("aria-invalid", "true");
  await expect(edad).toHaveAttribute("aria-describedby", "su-err");

  await edad.fill("30");                                   // al corregir, deja de marcarse
  await expect(edad).not.toHaveAttribute("aria-invalid", "true");
});

test("En el asistente el foco va al campo con el error", async ({ page }) => {
  await entrar(page);
  await irAPaso2(page);
  await llenarPaso2(page, { motivo: "Evento" });
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.locator("#f-motivo")).toBeFocused();
  await expect(page.locator("#f-motivo")).toHaveAttribute("aria-invalid", "true");
});

test("Entrar sin datos señala el correo", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.locator("#li-email")).toBeFocused();
});

test("Una contraseña equivocada no señala ningún campo (no revela cuál falló)", async ({ page }) => {
  await page.goto("/");
  await page.locator("#li-email").fill("demo@mupa.gob.pa");
  await page.locator("#li-pass").fill("equivocada");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.locator('#pane-login [aria-invalid="true"]')).toHaveCount(0);
});

test("La contraseña se puede mostrar y volver a ocultar", async ({ page }) => {
  await page.goto("/");
  const clave = page.locator("#li-pass");
  const ver = page.locator("#pane-login").getByRole("button", { name: "Mostrar contraseña" });
  await clave.fill("demo1234");
  await ver.click();
  await expect(clave).toHaveAttribute("type", "text");
  await expect(ver).toHaveAttribute("aria-pressed", "true");
  await ver.click();
  await expect(clave).toHaveAttribute("type", "password");
});

test("Un correo a medio escribir no se pinta de rojo", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });    // sin transición: se lee el color final
  await page.goto("/");
  await page.getByRole("tab", { name: "Crear cuenta" }).click();
  const correo = page.locator("#su-email");
  await correo.fill("ana@");
  await page.locator("#su-nombre").focus();
  const borde = await correo.evaluate(e => getComputedStyle(e).borderTopColor);
  expect(borde).not.toBe("rgb(165, 34, 24)");              // --crit del tema claro
});
```

**2. Ayudantes del asistente para las pruebas nuevas.** En `portal-permisos/calidad/tests/ayuda.js`, reemplaza:

```js
module.exports = { CUENTA, entrar, violaciones };
```

por:

```js
async function irAPaso2(page, categoria = /Espectáculos y eventos públicos/, permiso = /menos de 4,000/) {
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Solicitar permiso" }).click();
  await page.getByRole("button", { name: categoria }).click();
  await page.getByRole("button", { name: permiso }).click();
  await page.locator("#s1-next").click();
  await expect(page.locator('[data-step="2"]')).toBeVisible();
}

async function llenarPaso2(page, cambios = {}) {
  const v = {
    corregimiento: "San Francisco", tipoActo: "Concierto o presentación musical",
    lugar: "Parque Omar, calle 74 San Francisco",
    fecha: new Date(Date.now() + 40 * 86400000).toISOString().slice(0, 10),
    aforo: "800", tel: "+507 6000-0000",
    motivo: "Concierto benéfico al aire libre organizado por una fundación local.",
    ...cambios,
  };
  await page.locator("#f-corregimiento").selectOption(v.corregimiento);
  await page.locator("#f-tipoacto").selectOption(v.tipoActo);
  await page.locator("#f-lugar").fill(v.lugar);
  await page.locator("#f-fecha").fill(v.fecha);
  await page.locator("#f-aforo").fill(v.aforo);
  await page.locator("#f-tel").fill(v.tel);
  await page.locator("#f-motivo").fill(v.motivo);
}

module.exports = { CUENTA, entrar, violaciones, irAPaso2, llenarPaso2 };
```

- [ ] **Step 2: Verificar que fallan**

Run (desde `portal-permisos/calidad`): `npx playwright test --project=chromium tests/formularios.spec.js`
Expected: `5 failed`, `1 passed` (pasa «una contraseña equivocada no señala ningún campo»: esa conducta ya era correcta y debe mantenerse)

- [ ] **Step 3: Implementar**

**1. Rojo sólo cuando la validación lo dice, no mientras se escribe.** En `portal-permisos/index.html`, reemplaza:

```html
input:invalid:not(:placeholder-shown){border-color:var(--crit)}
```

por:

```html
[aria-invalid="true"]{border-color:var(--crit) !important;box-shadow:0 0 0 3px var(--crit-soft) !important}
.pass-wrap{position:relative}
.pass-wrap input{padding-right:50px}
.ver-clave{position:absolute;right:2px;top:50%;transform:translateY(-50%);width:44px;height:44px;
  border:0;border-radius:6px;background:transparent;color:var(--ink-2);cursor:pointer;display:grid;place-items:center}
.ver-clave:hover{color:var(--ink);background:var(--surface-2)}
.ver-clave svg{width:20px;height:20px}
.ver-clave[aria-pressed="true"]{color:var(--brand)}
```

**2. Mostrar contraseña (acceso).** En `portal-permisos/index.html`, reemplaza:

```html
          <input id="li-pass" type="password" autocomplete="current-password" placeholder="••••••••" required>
```

por:

```html
          <div class="pass-wrap">
            <input id="li-pass" type="password" autocomplete="current-password" placeholder="••••••••" required>
            <button type="button" class="ver-clave" aria-controls="li-pass" aria-pressed="false" aria-label="Mostrar contraseña"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
          </div>
```

**3. Mostrar contraseña (registro).** En `portal-permisos/index.html`, reemplaza:

```html
            <input id="su-pass" type="password" autocomplete="new-password" placeholder="Mínimo 8 caracteres" minlength="8" required>
```

por:

```html
            <div class="pass-wrap">
              <input id="su-pass" type="password" autocomplete="new-password" placeholder="Mínimo 8 caracteres" minlength="8" required>
              <button type="button" class="ver-clave" aria-controls="su-pass" aria-pressed="false" aria-label="Mostrar contraseña"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
            </div>
```

**4. ShowErr marca, describe y enfoca el campo.** En `portal-permisos/index.html`, reemplaza:

```html
function showErr(el, msg){
  if (!msg){ el.hidden = true; return; }
  el.hidden = false; el.lastElementChild.textContent = msg;
  el.scrollIntoView({ behavior:"smooth", block:"nearest" });
}
```

por:

```html
function showErr(el, msg, campoId){
  const zona = el.closest("form, .card") || document;
  $$('[aria-invalid="true"]', zona).forEach(limpiarCampo);
  if (!msg){ el.hidden = true; return; }
  el.hidden = false; el.lastElementChild.textContent = msg;
  const campo = campoId && $("#" + campoId);
  if (campo){
    // El error queda unido al campo: se ve marcado, el lector de pantalla lee
    // el mensaje y el foco llega justo donde hay que corregir.
    campo.setAttribute("aria-invalid", "true");
    campo.setAttribute("aria-describedby", el.id);
    campo.focus();
  } else {
    el.scrollIntoView({ behavior:"smooth", block:"nearest" });
  }
}
function limpiarCampo(c){
  c.removeAttribute("aria-invalid");
  if (/-err$/.test(c.getAttribute("aria-describedby") || "")) c.removeAttribute("aria-describedby");
}
["input", "change"].forEach(ev => document.addEventListener(ev, e => {
  if (e.target instanceof Element && e.target.getAttribute("aria-invalid") === "true") limpiarCampo(e.target);
}));
document.addEventListener("click", e => {
  const b = e.target.closest(".ver-clave"); if (!b) return;
  const campo = $("#" + b.getAttribute("aria-controls"));
  const ver = campo.type === "password";
  campo.type = ver ? "text" : "password";
  b.setAttribute("aria-pressed", String(ver));
});
```

**5. Acceso: correo o contraseña vacíos.** En `portal-permisos/index.html`, reemplaza:

```html
if (!email || !pass) return showErr($("#li-err"), "Escribe tu correo y tu contraseña.");
```

por:

```html
if (!email || !pass) return showErr($("#li-err"), "Escribe tu correo y tu contraseña.", email ? "li-pass" : "li-email");
```

**6. Registro: nombre.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Escribe tu nombre y tu apellido.");
```

por:

```html
return showErr(err, "Escribe tu nombre y tu apellido.", campos.nombre ? "su-apellido" : "su-nombre");
```

**7. Registro: edad mínima.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Debes tener al menos 18 años para tramitar un permiso.");
```

por:

```html
return showErr(err, "Debes tener al menos 18 años para tramitar un permiso.", "su-edad");
```

**8. Registro: edad máxima.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Revisa la edad ingresada.");
```

por:

```html
return showErr(err, "Revisa la edad ingresada.", "su-edad");
```

**9. Registro: organización.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Indica el lugar donde colaboras, o escribe «Independiente».");
```

por:

```html
return showErr(err, "Indica el lugar donde colaboras, o escribe «Independiente».", "su-org");
```

**10. Registro: correo.** En `portal-permisos/index.html`, reemplaza:

```html
test(campos.email))
    return showErr(err, "El correo electrónico no tiene un formato válido.");
```

por:

```html
test(campos.email))
    return showErr(err, "El correo electrónico no tiene un formato válido.", "su-email");
```

**11. Registro: correo repetido.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Ya existe una cuenta con ese correo. Inicia sesión.");
```

por:

```html
return showErr(err, "Ya existe una cuenta con ese correo. Inicia sesión.", "su-email");
```

**12. Registro: largo de clave.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "La contraseña debe tener al menos 8 caracteres.");
```

por:

```html
return showErr(err, "La contraseña debe tener al menos 8 caracteres.", "su-pass");
```

**13. Registro: claves distintas.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Las contraseñas no coinciden.");
```

por:

```html
return showErr(err, "Las contraseñas no coinciden.", "su-pass2");
```

**14. Registro: consentimiento.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Debes autorizar el tratamiento de tus datos para continuar.");
```

por:

```html
return showErr(err, "Debes autorizar el tratamiento de tus datos para continuar.", "su-ok");
```

**15. Paso 2: corregimiento.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Selecciona el corregimiento donde se realizará el acto.");
```

por:

```html
return showErr(err, "Selecciona el corregimiento donde se realizará el acto.", "f-corregimiento");
```

**16. Paso 2: tipo de acto.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Selecciona el tipo de acto.");
```

por:

```html
return showErr(err, "Selecciona el tipo de acto.", "f-tipoacto");
```

**17. Paso 2: lugar.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Describe el lugar exacto con un poco más de detalle.");
```

por:

```html
return showErr(err, "Describe el lugar exacto con un poco más de detalle.", "f-lugar");
```

**18. Paso 2: fecha vacía.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Indica el día del acto.");
```

por:

```html
return showErr(err, "Indica el día del acto.", "f-fecha");
```

**19. Paso 2: fecha próxima.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "La fecha debe tener al menos 15 días hábiles de antelación.");
```

por:

```html
return showErr(err, "La fecha debe tener al menos 15 días hábiles de antelación.", "f-fecha");
```

**20. Paso 2: horas.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Indica la hora de inicio y la de cierre.");
```

por:

```html
return showErr(err, "Indica la hora de inicio y la de cierre.", d.hIni ? "f-hfin" : "f-hini");
```

**21. Paso 2: orden de horas.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "La hora de cierre debe ser posterior a la de inicio.");
```

por:

```html
return showErr(err, "La hora de cierre debe ser posterior a la de inicio.", "f-hfin");
```

**22. Paso 2: aforo vacío.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Indica el aforo estimado.");
```

por:

```html
return showErr(err, "Indica el aforo estimado.", "f-aforo");
```

**23. Paso 2: aforo fuera de rango.** En `portal-permisos/index.html`, reemplaza:

```html
personas. Cambia el tipo de permiso o corrige el aforo.`);
```

por:

```html
personas. Cambia el tipo de permiso o corrige el aforo.`, "f-aforo");
```

**24. Paso 2: responsable.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Indica quién será el responsable en sitio.");
```

por:

```html
return showErr(err, "Indica quién será el responsable en sitio.", "f-resp");
```

**25. Paso 2: teléfono.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Escribe un teléfono de contacto válido, por ejemplo +507 6000-0000.");
```

por:

```html
return showErr(err, "Escribe un teléfono de contacto válido, por ejemplo +507 6000-0000.", "f-tel");
```

**26. Paso 2: motivo.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "El motivo debe tener al menos 20 caracteres.");
```

por:

```html
return showErr(err, "El motivo debe tener al menos 20 caracteres.", "f-motivo");
```

**27. Citas: sede.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Selecciona la sede a la que asistirás.");
```

por:

```html
return showErr(err, "Selecciona la sede a la que asistirás.", "c-sede");
```

**28. Citas: motivo.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Indica el motivo de la cita.");
```

por:

```html
return showErr(err, "Indica el motivo de la cita.", "c-motivo");
```

**29. Citas: fecha.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Selecciona la fecha de la cita.");
```

por:

```html
return showErr(err, "Selecciona la fecha de la cita.", "c-fecha");
```

**30. Citas: fin de semana.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "La atención presencial es de lunes a viernes. Elige otro día.");
```

por:

```html
return showErr(err, "La atención presencial es de lunes a viernes. Elige otro día.", "c-fecha");
```

**31. Contacto: nombre.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Escribe tu nombre completo.");
```

por:

```html
return showErr(err, "Escribe tu nombre completo.", "ct-nombre");
```

**32. Contacto: correo.** En `portal-permisos/index.html`, reemplaza:

```html
test(V("ct-email")))
    return showErr(err, "El correo electrónico no tiene un formato válido.");
```

por:

```html
test(V("ct-email")))
    return showErr(err, "El correo electrónico no tiene un formato válido.", "ct-email");
```

**33. Contacto: tema.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Selecciona el tema de tu mensaje.");
```

por:

```html
return showErr(err, "Selecciona el tema de tu mensaje.", "ct-tema");
```

**34. Contacto: mensaje.** En `portal-permisos/index.html`, reemplaza:

```html
return showErr(err, "Cuéntanos un poco más; el mensaje es muy corto.");
```

por:

```html
return showErr(err, "Cuéntanos un poco más; el mensaje es muy corto.", "ct-msg");
```

- [ ] **Step 4: Verificar que pasan**

Run: `npx playwright test`
Expected: `84 passed`, 0 failed, 0 flaky

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "feat(portal): errores de formulario unidos al campo y mostrar contraseña" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Asistente: buscador de trámites, avance visible y resumen editable

**Files:**
- Create: `portal-permisos/calidad/tests/asistente.spec.js`
- Modify: `portal-permisos/index.html`

**Por qué:**

- **Buscador de trámites.** Con 35 trámites en 8 categorías, quien no conoce el nombre oficial tiene que abrir categoría por categoría. El buscador no distingue tildes ni mayúsculas, exige todas las palabras y, al elegir un resultado, marca su categoría y su trámite como si se hubieran tocado.
- **Avance visible.** «Paso 2 de 4 · Datos del acto» con barra de progreso; en el celular sólo se ve la etiqueta del paso actual.
- **Resumen editable.** El resumen permite volver a cambiar el permiso, los datos o el documento sin perder lo escrito.

- [ ] **Step 1: Escribir las pruebas**

**1. Crea `portal-permisos/calidad/tests/asistente.spec.js`**

```js
// @ts-check
const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { entrar, irAPaso2, llenarPaso2 } = require("./ayuda");

/** Asistente: encontrar el trámite rápido, saber cuánto falta y poder corregir. */

test.beforeEach(async ({ page }) => {
  await entrar(page);
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Solicitar permiso" }).click();
});

test("El buscador encuentra el trámite y lo deja elegido", async ({ page }) => {
  await page.getByLabel("Buscar un trámite").fill("chiva");
  await page.locator("#q-res").getByRole("button", { name: "Chiva Parrandera" }).click();
  await expect(page.getByRole("button", { name: /Espectáculos y eventos públicos/ })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#req-wrap")).toContainText("Registro vehicular y revisado vigente");
  await expect(page.locator("#s1-next")).toBeEnabled();
  await expect(page.locator("#q-res")).toBeHidden();
});

test("El buscador no distingue tildes ni mayúsculas", async ({ page }) => {
  await page.getByLabel("Buscar un trámite").fill("NOCTURNO categoria b");
  await expect(page.locator("#q-res").getByRole("button", { name: "Permiso Nocturno Categoría B" })).toBeVisible();
});

test("Si no hay coincidencias, lo dice y sugiere qué hacer", async ({ page }) => {
  await page.getByLabel("Buscar un trámite").fill("helicóptero");
  await expect(page.getByText(/No encontramos trámites/)).toBeVisible();
});

test("El avance se muestra como «Paso N de 4»", async ({ page }) => {
  const progreso = page.getByRole("progressbar", { name: "Avance de la solicitud" });
  await expect(progreso).toHaveAttribute("aria-valuenow", "1");
  await page.getByRole("button", { name: /Espectáculos y eventos públicos/ }).click();
  await page.getByRole("button", { name: /menos de 4,000/ }).click();
  await page.locator("#s1-next").click();
  await expect(page.locator("#paso-de")).toHaveText("Paso 2 de 4 · Datos del acto");
  await expect(progreso).toHaveAttribute("aria-valuenow", "2");
});

test("Desde el resumen se vuelve a corregir sin perder lo escrito", async ({ page }) => {
  await page.getByRole("button", { name: /Espectáculos y eventos públicos/ }).click();
  await page.getByRole("button", { name: /menos de 4,000/ }).click();
  await page.locator("#s1-next").click();
  await llenarPaso2(page, { lugar: "Parque Omar, frente a la cancha" });
  await page.getByRole("button", { name: "Continuar" }).click();

  const pdf = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "vum-")), "requisitos.pdf");
  fs.writeFileSync(pdf, "%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n");
  await page.locator("#file-in").setInputFiles(pdf);
  await expect(page.locator("#scan-pill")).toHaveText("Verificado", { timeout: 15_000 });
  await page.locator("#s3-next").click();

  await page.getByRole("button", { name: "Cambiar datos" }).click();
  await expect(page.locator('[data-step="2"]')).toBeVisible();
  await expect(page.locator("#f-lugar")).toHaveValue("Parque Omar, frente a la cancha");
});
```

- [ ] **Step 2: Verificar que fallan**

Run (desde `portal-permisos/calidad`): `npx playwright test --project=chromium tests/asistente.spec.js`
Expected: `5 failed`

- [ ] **Step 3: Implementar**

**1. Progreso y buscador.** En `portal-permisos/index.html`, reemplaza:

```html
.stepper .lbl{font-size:.8rem;color:var(--ink-2);font-weight:500}
```

por:

```html
.stepper .lbl{font-size:.8rem;color:var(--ink-2);font-weight:500}
@media (max-width:640px){.stepper .s:not([data-state="on"]) .lbl{display:none}}
.progreso{height:6px;border-radius:999px;background:var(--surface-2);overflow:hidden;margin-top:10px}
.progreso span{display:block;height:100%;width:25%;background:var(--brand);border-radius:inherit;transition:width .3s ease}
.paso-de{font-size:.85rem;color:var(--ink-2);margin-top:6px;font-weight:500}
.buscador input{padding-left:40px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%23556676' stroke-width='2' stroke-linecap='round' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:12px center}
```

**2. «Paso N de 4» y barra de avance.** En `portal-permisos/index.html`, reemplaza:

```html
          <div class="s"><span class="num">4</span><span class="lbl">Revisión y envío</span></div>
        </div>
```

por:

```html
          <div class="s"><span class="num">4</span><span class="lbl">Revisión y envío</span></div>
        </div>
        <div class="progreso" id="progreso" role="progressbar" aria-label="Avance de la solicitud"
             aria-valuemin="1" aria-valuemax="4" aria-valuenow="1"><span></span></div>
        <p class="paso-de" id="paso-de" aria-live="polite">Paso 1 de 4 · Tipo de permiso</p>
```

**3. Buscador de trámites antes de las categorías.** En `portal-permisos/index.html`, reemplaza:

```html
          <div>
            <span class="eyebrow">1 · Categoría</span>
```

por:

```html
          <div class="field buscador">
            <label for="q-tramite">Buscar un trámite</label>
            <input id="q-tramite" type="search" autocomplete="off" placeholder="Ej. aceras, nocturno, chiva, plagas">
            <span class="hint">Escribe una palabra o elige una categoría abajo.</span>
          </div>
          <div class="opt-list" id="q-res" hidden></div>
          <p class="notice info" id="q-vacio" hidden>No encontramos trámites con esas palabras. Prueba con otra palabra o elige una categoría.</p>
          <p class="sr" id="q-cuenta" aria-live="polite"></p>
          <div>
            <span class="eyebrow">1 · Categoría</span>
```

**4. Volver a corregir desde el resumen.** En `portal-permisos/index.html`, reemplaza:

```html
          <dl class="summary" id="sum"></dl>
```

por:

```html
          <dl class="summary" id="sum"></dl>
          <div class="actions" style="gap:6px">
            <span class="small muted">¿Algo no está bien?</span>
            <button class="btn plain" type="button" data-back="1">Cambiar permiso</button>
            <button class="btn plain" type="button" data-back="2">Cambiar datos</button>
            <button class="btn plain" type="button" data-back="3">Cambiar documento</button>
          </div>
```

**5. El avance acompaña a cada paso.** En `portal-permisos/index.html`, reemplaza:

```html
  $("#stepper").hidden = n === 5;
```

por:

```html
  $("#stepper").hidden = n === 5;
  const nombres = ["Tipo de permiso", "Datos del acto", "Documentos", "Revisión y envío"];
  const actual = Math.min(n, 4);
  $("#paso-de").textContent = `Paso ${actual} de 4 · ${nombres[actual - 1]}`;
  $("#progreso").setAttribute("aria-valuenow", String(actual));
  $("#progreso span").style.width = `${actual * 25}%`;
  $("#paso-de").hidden = $("#progreso").hidden = n === 5;
```

**6. Buscador: sin tildes, todas las palabras, hasta 8 resultados.** En `portal-permisos/index.html`, reemplaza:

```html
$("#s1-next").addEventListener("click", () => {
```

por:

```html
const sinTildes = s => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

$("#q-tramite").addEventListener("input", e => {
  const q = sinTildes(e.target.value.trim());
  const res = $("#q-res"), vacio = $("#q-vacio");
  if (q.length < 2){ res.hidden = vacio.hidden = true; $("#q-cuenta").textContent = ""; return; }
  const palabras = q.split(/\s+/);
  const hallados = ALL_PERMS
    .filter(p => { const t = sinTildes(`${p.n} ${p.cat}`); return palabras.every(w => t.includes(w)); })
    .slice(0, 8);
  res.innerHTML = hallados.map((p, i) =>
    `<button type="button" class="opt" data-buscar="${esc(p.id)}" aria-label="${esc(p.n)}" aria-describedby="qd-${i}">
       <span class="radio"></span>
       <span><span class="on">${esc(p.n)}</span><span class="od" id="qd-${i}">${esc(p.cat)} · ${p.d} días háb.</span></span>
     </button>`).join("");
  res.hidden = !hallados.length;
  vacio.hidden = hallados.length > 0;
  $("#q-cuenta").textContent = hallados.length ? `${hallados.length} trámites encontrados` : "Sin resultados";
});

$("#q-res").addEventListener("click", e => {
  const b = e.target.closest("[data-buscar]"); if (!b) return;
  const p = ALL_PERMS.find(x => x.id === b.dataset.buscar);
  $(`.cat[data-cat="${CATALOGO.findIndex(c => c.cat === p.cat)}"]`).click();   // pinta su categoría
  $(`#perms [data-perm="${CSS.escape(p.id)}"]`).click();                      // y marca el trámite
  $("#q-tramite").value = ""; $("#q-res").hidden = true; $("#q-cuenta").textContent = "";
  $("#req-wrap").scrollIntoView({ behavior:"smooth", block:"nearest" });
});

$("#s1-next").addEventListener("click", () => {
```

**7. Reiniciar también limpia la búsqueda.** En `portal-permisos/index.html`, reemplaza:

```html
  state.sel = { cat:null, perm:null, datos:null, doc:null };
  $$(".cat")
```

por:

```html
  state.sel = { cat:null, perm:null, datos:null, doc:null };
  $("#q-tramite").value = ""; $("#q-res").hidden = $("#q-vacio").hidden = true;
  $$(".cat")
```

- [ ] **Step 4: Verificar que pasan**

Run: `npx playwright test`
Expected: `94 passed`, 0 failed, 0 flaky

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "feat(portal): buscador de trámites, avance del asistente y resumen editable" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Inicio y expedientes: qué requiere atención, detalle y «qué sigue»

**Files:**
- Create: `portal-permisos/calidad/tests/expedientes.spec.js`
- Modify: `portal-permisos/index.html`

**Por qué:**

Hoy un expediente en «Subsanación» sólo muestra una etiqueta roja; el usuario no sabe qué hacer. Los expedientes no se pueden abrir, aunque la página promete «historial de revisión».
- **«Requiere tu atención»** en el inicio, con un botón «Resolver» por expediente.
- **Contadores que filtran:** tocar «Aprobados» abre la lista ya filtrada.
- **Detalle en un `<dialog>` nativo**, que atrapa el foco, se cierra con Escape y devuelve el foco al botón. Muestra la línea de tiempo, «Qué sigue» en lenguaje claro, los datos y la huella del documento.
- **«Agendar cita para subsanar»** llega a Citas con el motivo y el expediente ya elegidos.

- [ ] **Step 1: Escribir las pruebas**

**1. Crea `portal-permisos/calidad/tests/expedientes.spec.js`**

```js
// @ts-check
const { test, expect } = require("@playwright/test");
const { entrar, violaciones } = require("./ayuda");

/** Inicio y expedientes: qué requiere atención, qué sigue y cómo resolverlo. */

test.beforeEach(async ({ page }) => { await entrar(page); });

test("El inicio avisa qué expediente requiere atención y cómo resolverlo", async ({ page }) => {
  const atencion = page.getByRole("region", { name: "Requiere tu atención" });
  await expect(atencion).toContainText("EXP-2026-004055");
  await expect(atencion).toContainText("Falta póliza de responsabilidad civil vigente");
  await atencion.getByRole("button", { name: "Resolver EXP-2026-004055" }).click();
  await expect(page.getByRole("dialog", { name: "Permiso Nocturno Categoría B" })).toBeVisible();
});

test("Tocar un contador abre la lista filtrada por ese estado", async ({ page }) => {
  await page.getByRole("button", { name: /Aprobados/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Mis solicitudes" })).toBeVisible();
  await expect(page.locator("#q-est")).toHaveValue("Aprobado");
  await expect(page.locator("#all-exp .exp")).toHaveCount(1);
  await expect(page.locator("#all-exp")).toContainText("Uso Temporal de Aceras");
});

test("El detalle muestra la línea de tiempo, la huella y qué sigue", async ({ page }) => {
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Mis solicitudes" }).click();
  await page.getByRole("button", { name: "Ver detalle de EXP-2026-004182" }).click();
  const detalle = page.getByRole("dialog", { name: "Espectáculo Público — menos de 4,000 personas" });
  await expect(detalle).toBeVisible();
  await expect(detalle.locator('[aria-current="step"]')).toHaveText(/En revisión/);
  await expect(detalle).toContainText("9f2c41ab77d0e5b3c8a1f64e2d9b0357cc84e1a6b2f7d3905e8c6a4b1d7f2093");
  await expect(detalle.getByRole("heading", { name: "Qué sigue" })).toBeVisible();
  expect(await violaciones(page)).toEqual([]);
});

test("Escape cierra el detalle y el foco vuelve al botón", async ({ page }) => {
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Mis solicitudes" }).click();
  const abrir = page.getByRole("button", { name: "Ver detalle de EXP-2026-003914" });
  await abrir.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(abrir).toBeFocused();
});

test("Desde un expediente en subsanación se agenda la cita ya preparada", async ({ page }) => {
  await page.getByRole("button", { name: "Resolver EXP-2026-004055" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Agendar cita para subsanar" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Citas" })).toBeVisible();
  await expect(page.locator("#c-motivo")).toHaveValue("Subsanación de expediente");
  await expect(page.locator("#c-exp")).toHaveValue(/^EXP-2026-004055/);
});
```

- [ ] **Step 2: Verificar que fallan**

Run (desde `portal-permisos/calidad`): `npx playwright test --project=chromium tests/expedientes.spec.js`
Expected: `5 failed`

- [ ] **Step 3: Implementar**

**1. Contadores que se pueden tocar.** En `portal-permisos/index.html`, reemplaza:

```html
.stat{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 15px;
  display:flex;flex-direction:column;gap:2px}
```

por:

```html
.stat{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 15px;
  display:flex;flex-direction:column;gap:2px;font:inherit;color:inherit;text-align:left;cursor:pointer;
  transition:border-color .15s ease, box-shadow .15s ease}
.stat:hover{border-color:var(--brand);box-shadow:var(--shadow)}
```

**2. Tarjeta con acción, bloque de atención y diálogo de detalle.** En `portal-permisos/index.html`, reemplaza:

```html
.exp{
  background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--line);
  border-radius:10px;padding:14px 16px;display:grid;
  grid-template-columns:1fr auto;gap:8px 16px;align-items:start;
}
```

por:

```html
.exp{
  background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--line);
  border-radius:10px;padding:14px 16px;display:grid;
  grid-template-columns:1fr auto;gap:8px 16px;align-items:start;
}
.exp-der{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.exp .ver{min-height:36px;padding:6px 12px;font-size:.84rem}

.atencion{border-left:4px solid var(--crit);display:flex;flex-direction:column;gap:12px}
.atencion .at-h{display:flex;gap:10px;align-items:center;color:var(--crit)}
.atencion .at-h svg{width:22px;height:22px;flex:none}
.atencion .at-h h2{color:var(--ink)}
.at-r{display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap;
  padding-top:12px;border-top:1px solid var(--line)}
.at-r .code{font-family:var(--mono);font-size:.76rem;color:var(--ink-2)}
.at-r .name{font-weight:600}

dialog.detalle{border:0;border-radius:14px;padding:0;width:min(580px,calc(100vw - 32px));
  max-height:calc(100dvh - 32px);background:var(--surface);color:var(--ink);
  box-shadow:0 24px 60px -20px rgba(0,0,0,.55)}
dialog.detalle::backdrop{background:rgba(12,20,27,.55)}
.det-h{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;
  padding:18px 20px;border-bottom:1px solid var(--line)}
.det-h .code{font-family:var(--mono);font-size:.78rem;color:var(--ink-2)}
.det-b{padding:18px 20px 22px;display:flex;flex-direction:column;gap:18px}
.linea{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.linea li{font-size:.8rem;color:var(--ink-2);padding-top:10px;border-top:4px solid var(--surface-2)}
.linea li[data-s="done"]{border-top-color:var(--ok);color:var(--ink)}
.linea li[data-s="on"]{border-top-color:var(--brand);color:var(--ink);font-weight:600}
.linea li[data-s="on"].crit{border-top-color:var(--crit)}
.sigue{background:var(--surface-2);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.sigue p{font-size:.9rem;color:var(--ink-2)}
```

**3. Contadores como botones que filtran.** En `portal-permisos/index.html`, reemplaza:

```html
          <div class="stat"><span class="v" id="k-total">0</span><span class="k">Expedientes</span></div>
          <div class="stat s-warn"><span class="v" id="k-rev">0</span><span class="k">En revisión</span></div>
          <div class="stat s-ok"><span class="v" id="k-apr">0</span><span class="k">Aprobados</span></div>
          <div class="stat s-crit"><span class="v" id="k-sub">0</span><span class="k">Subsanación</span></div>
```

por:

```html
          <button type="button" class="stat" data-filtro=""><span class="v" id="k-total">0</span><span class="k">Expedientes</span></button>
          <button type="button" class="stat s-warn" data-filtro="En revisión"><span class="v" id="k-rev">0</span><span class="k">En revisión</span></button>
          <button type="button" class="stat s-ok" data-filtro="Aprobado"><span class="v" id="k-apr">0</span><span class="k">Aprobados</span></button>
          <button type="button" class="stat s-crit" data-filtro="Subsanación"><span class="v" id="k-sub">0</span><span class="k">Subsanación</span></button>
```

**4. Bloque «Requiere tu atención».** En `portal-permisos/index.html`, reemplaza:

```html
          <h2 style="margin-bottom:10px">Movimiento reciente</h2>
```

por:

```html
          <section class="card atencion" id="atencion" aria-labelledby="at-titulo" hidden style="margin-bottom:22px">
            <div class="at-h"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-alerta"/></svg>
              <h2 id="at-titulo">Requiere tu atención</h2></div>
            <div id="at-lista"></div>
          </section>
          <h2 style="margin-bottom:10px">Movimiento reciente</h2>
```

**5. Diálogo de detalle del expediente.** En `portal-permisos/index.html`, reemplaza:

```html
  </main>
```

por:

```html
  </main>

  <dialog class="detalle" id="detalle" aria-labelledby="det-titulo">
    <div class="det-h">
      <div style="min-width:0">
        <div class="code" id="det-code">—</div>
        <h2 id="det-titulo">—</h2>
      </div>
      <button type="button" class="btn plain" id="det-cerrar">Cerrar</button>
    </div>
    <div class="det-b" id="det-cuerpo"></div>
  </dialog>
```

**6. Tarjeta con «Ver detalle».** En `portal-permisos/index.html`, reemplaza:

```html
    <span class="pill ${estadoClase(x.estado)}">${esc(x.estado)}</span>
  </article>`;
```

por:

```html
    <div class="exp-der">
      <span class="pill ${estadoClase(x.estado)}">${esc(x.estado)}</span>
      <button type="button" class="btn ghost ver" data-exp="${esc(x.code)}" aria-label="Ver detalle de ${esc(x.code)}">Ver detalle</button>
    </div>
  </article>`;
```

**7. Pinta el bloque de atención.** En `portal-permisos/index.html`, reemplaza:

```html
  $("#recent").innerHTML    = e.slice(0, 3).map(tarjetaExpediente).join("");
```

por:

```html
  $("#recent").innerHTML    = e.slice(0, 3).map(tarjetaExpediente).join("");
  const pendientes = e.filter(x => x.estado === "Subsanación");
  $("#atencion").hidden = !pendientes.length;
  $("#at-lista").innerHTML = pendientes.map(x =>
    `<div class="at-r">
       <div style="min-width:0"><div class="code">${esc(x.code)}</div>
         <div class="name">${esc(x.permiso)}</div><p class="small muted">${esc(x.etapa)}</p></div>
       <button type="button" class="btn" data-exp="${esc(x.code)}" aria-label="Resolver ${esc(x.code)}">Resolver</button>
     </div>`).join("");
```

**8. Contadores, detalle y cita preparada.** En `portal-permisos/index.html`, reemplaza:

```html
$("#q").addEventListener("input", filtrarExpedientes);
```

por:

```html
$("#q").addEventListener("input", filtrarExpedientes);

document.addEventListener("click", e => {
  const s = e.target.closest(".stat[data-filtro]"); if (!s) return;
  ir("expedientes");
  $("#q").value = ""; $("#q-est").value = s.dataset.filtro;
  filtrarExpedientes();
});

/* ---------- detalle del expediente ---------- */
const QUE_SIGUE = {
  "Recibido":    () => "Tu solicitud está en cola para asignarse a un revisor. Por ahora no tienes que hacer nada.",
  "En revisión": () => "Un revisor de la Dirección está evaluando tu expediente. Si necesita algo, te escribirá a tu correo.",
  "Subsanación": x  => `Falta algo para continuar: ${x.etapa}. Entrégalo en una cita y la revisión sigue desde donde quedó.`,
  "Aprobado":    x  => `Tu permiso fue aprobado. ${x.etapa}.`,
  "Rechazado":   x  => `La solicitud no fue aprobada. ${x.etapa}. Puedes escribirnos si tienes dudas.`,
};

function lineaDeTiempo(x){
  const actual = x.estado === "Recibido" ? 0 : ["En revisión", "Subsanación"].includes(x.estado) ? 1 : 2;
  const pasos = ["Recibido", x.estado === "Subsanación" ? "Subsanación pendiente" : "En revisión",
                 ["Aprobado", "Rechazado"].includes(x.estado) ? x.estado : "Resolución"];
  return `<ol class="linea" aria-label="Avance del trámite">${pasos.map((p, i) =>
    `<li data-s="${i < actual ? "done" : i === actual ? "on" : ""}"
         class="${i === actual && x.estado === "Subsanación" ? "crit" : ""}"
         ${i === actual ? 'aria-current="step"' : ""}>${esc(p)}</li>`).join("")}</ol>`;
}

function abrirDetalle(code){
  const x = state.expedientes.find(e => e.code === code); if (!x) return;
  $("#det-code").textContent = x.code;
  $("#det-titulo").textContent = x.permiso;
  $("#det-cuerpo").innerHTML = `
    <div><span class="pill ${estadoClase(x.estado)}">${esc(x.estado)}</span></div>
    ${lineaDeTiempo(x)}
    <div class="sigue"><h3>Qué sigue</h3><p>${esc(QUE_SIGUE[x.estado]?.(x) ?? x.etapa)}</p></div>
    <dl class="summary">
      ${[["Lugar", x.lugar], ["Día del acto", fechaLarga(x.fecha)], ["Recibido el", fechaLarga(x.creado)],
         ["Etapa actual", x.etapa]].map(([k, v]) =>
        `<div class="r"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}
      <div class="r"><dt>Huella del documento</dt><dd class="mono" style="font-size:.76rem">${esc(x.hash)}</dd></div>
    </dl>
    ${x.estado === "Subsanación"
      ? `<div class="actions"><button type="button" class="btn" id="det-cita">Agendar cita para subsanar</button></div>` : ""}`;
  $("#det-cita")?.addEventListener("click", () => {
    $("#detalle").close();
    ir("citas");
    $("#c-motivo").value = "Subsanación de expediente";
    $("#c-exp").value = `${x.code} — ${x.permiso}`;
  });
  $("#detalle").showModal();                 // modal nativo: atrapa el foco y Escape lo cierra
}

document.addEventListener("click", e => {
  const b = e.target.closest("[data-exp]"); if (b) abrirDetalle(b.dataset.exp);
});
$("#det-cerrar").addEventListener("click", () => $("#detalle").close());
```

- [ ] **Step 4: Verificar que pasan**

Run: `npx playwright test`
Expected: `104 passed`, 0 failed, 0 flaky

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "feat(portal): atención pendiente, detalle del expediente y cita preparada" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Citas y barrido final de accesibilidad

**Files:**
- Create: `portal-permisos/calidad/tests/citas.spec.js`
- Modify: `portal-permisos/calidad/tests/accesibilidad.spec.js`
- Modify: `portal-permisos/index.html`

**Por qué:**

- **Atajos de fecha:** los próximos 5 días hábiles se eligen con un toque.
- **Leyenda de horarios:** explica disponible, ocupado y elegido.
- **Corrección de «hoy»:** hoy se calcula con `toISOString()` (UTC). Después de las 7 p. m. en Panamá el portal cree que ya es mañana y corre un día la fecha mínima del acto y de las citas.
- **axe en todas las secciones y en los dos temas**, y una prueba de reflujo a 320 px (WCAG 1.4.10). Esas pruebas ya pasan antes de esta tarea: protegen el trabajo de las anteriores.

- [ ] **Step 1: Escribir las pruebas**

**1. Crea `portal-permisos/calidad/tests/citas.spec.js`**

```js
// @ts-check
const { test, expect } = require("@playwright/test");
const { entrar } = require("./ayuda");

/** Citas: elegir fecha con un toque y entender los horarios de un vistazo. */

test.beforeEach(async ({ page }) => {
  await entrar(page);
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Citas" }).click();
});

test("Los atajos ofrecen los próximos cinco días hábiles", async ({ page }) => {
  const atajos = page.getByRole("group", { name: "Próximos días hábiles" }).getByRole("button");
  await expect(atajos).toHaveCount(5);
  for (const f of await atajos.evaluateAll(bs => bs.map(b => b.getAttribute("data-fecha")))) {
    const dia = new Date(`${f}T12:00:00`).getDay();
    expect(dia === 0 || dia === 6, `${f} cae en fin de semana`).toBe(false);
  }
});

test("Tocar un atajo fija la fecha y lo marca como elegido", async ({ page }) => {
  const segundo = page.getByRole("group", { name: "Próximos días hábiles" }).getByRole("button").nth(1);
  await segundo.click();
  await expect(page.locator("#c-fecha")).toHaveValue(await segundo.getAttribute("data-fecha") ?? "");
  await expect(segundo).toHaveAttribute("aria-pressed", "true");
});

test("La leyenda explica los estados de los horarios", async ({ page }) => {
  const leyenda = page.locator("#leyenda-slots");
  for (const t of ["Disponible", "Ocupado", "Elegido"]) await expect(leyenda).toContainText(t);
});

test("«Hoy» es la fecha local de Panamá, también de noche", async ({ page }) => {
  // 23:30 en Panamá ya es el día siguiente en UTC: la fecha mínima no debe saltar.
  await page.clock.setFixedTime(new Date("2026-10-06T23:30:00-05:00"));
  await page.reload();
  await expect.poll(() => page.evaluate(() => hoyISO())).toBe("2026-10-06");
});
```

**2. Axe en cada sección y en ambos temas.** En `portal-permisos/calidad/tests/accesibilidad.spec.js`, reemplaza:

```js
test("La franja oficial identifica al Municipio en todas las pantallas"
```

por:

```js
for (const tema of ["light", "dark"]) {
  for (const seccion of ["Solicitar permiso", "Mis solicitudes", "Citas", "Contacto"]) {
    test(`«${seccion}» cumple WCAG 2.1 AA (tema ${tema === "light" ? "claro" : "oscuro"})`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: tema });
      await entrar(page);
      await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: seccion }).click();
      expect(await violaciones(page)).toEqual([]);
    });
  }
}

test("A 320 px ninguna sección obliga a desplazarse de lado (WCAG 1.4.10)", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await entrar(page);
  for (const seccion of ["Inicio", "Solicitar permiso", "Mis solicitudes", "Citas", "Contacto"]) {
    await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: seccion }).click();
    const desborda = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(desborda, seccion).toBe(false);
  }
});

test("La franja oficial identifica al Municipio en todas las pantallas"
```

- [ ] **Step 2: Verificar que fallan**

Run (desde `portal-permisos/calidad`): `npx playwright test --project=chromium tests/citas.spec.js`
Expected: `4 failed` en `citas.spec.js` (las 10 pruebas nuevas de `accesibilidad.spec.js` ya pasan: son protecciones de las tareas 3 a 6)

- [ ] **Step 3: Implementar**

**1. Atajos de fecha y leyenda de horarios.** En `portal-permisos/index.html`, reemplaza:

```html
.slot:disabled{opacity:.38;cursor:not-allowed;text-decoration:line-through}
```

por:

```html
.slot:disabled{opacity:.38;cursor:not-allowed;text-decoration:line-through}
.atajos{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.chip{min-height:36px;padding:6px 12px;border:1px solid var(--line);border-radius:999px;background:var(--surface);
  color:var(--ink);font:inherit;font-size:.84rem;cursor:pointer}
.chip:hover{border-color:var(--brand)}
.chip[aria-pressed="true"]{background:var(--brand);border-color:var(--brand);color:var(--on-brand);font-weight:600}
.leyenda{display:flex;gap:14px;flex-wrap:wrap;align-items:center;font-size:.8rem;color:var(--ink-2);margin-top:10px}
.leyenda span{display:inline-flex;align-items:center;gap:6px}
.leyenda i{width:14px;height:14px;border-radius:4px;border:1px solid var(--line);background:var(--surface)}
.leyenda i.ocup{opacity:.38;background:repeating-linear-gradient(135deg,var(--line) 0 2px,transparent 2px 5px)}
.leyenda i.sel{background:var(--brand);border-color:var(--brand)}
```

**2. Atajos bajo la fecha.** En `portal-permisos/index.html`, reemplaza:

```html
              <input id="c-fecha" type="date" required>
              <span class="hint">Atención en días hábiles (L–V).</span>
```

por:

```html
              <input id="c-fecha" type="date" required>
              <span class="hint">Atención en días hábiles (L–V).</span>
              <div class="atajos" id="c-atajos" role="group" aria-label="Próximos días hábiles"></div>
```

**3. Leyenda de horarios.** En `portal-permisos/index.html`, reemplaza:

```html
            <p class="small muted" style="margin-top:8px">Turnos de 30 minutos · 8:00 a.m. – 3:30 p.m. Los tachados ya están ocupados.</p>
```

por:

```html
            <div class="leyenda" id="leyenda-slots">
              <span><i aria-hidden="true"></i>Disponible</span>
              <span><i class="ocup" aria-hidden="true"></i>Ocupado</span>
              <span><i class="sel" aria-hidden="true"></i>Elegido</span>
            </div>
            <p class="small muted" style="margin-top:6px">Turnos de 30 minutos · 8:00 a.m. – 3:30 p.m.</p>
```

**4. «hoy» en hora local, no en UTC.** En `portal-permisos/index.html`, reemplaza:

```html
function hoyISO(off = 0){
  const d = new Date(); d.setDate(d.getDate() + off);
  return d.toISOString().slice(0,10);
}
```

por:

```html
// Fecha local (Panamá). toISOString() usa UTC: después de las 7 p. m. daba el día siguiente.
function aISO(d){
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function hoyISO(off = 0){
  const d = new Date(); d.setDate(d.getDate() + off);
  return aISO(d);
}
```

**5. Atajos de los próximos días hábiles.** En `portal-permisos/index.html`, reemplaza:

```html
$("#c-fecha").addEventListener("change", pintarSlots);
```

por:

```html
const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
function pintarAtajos(){
  const elegida = $("#c-fecha").value, dias = [];
  for (const d = new Date(); dias.length < 5; ){
    d.setDate(d.getDate() + 1);
    if (d.getDay() % 6) dias.push(new Date(d));            // ni domingo (0) ni sábado (6)
  }
  $("#c-atajos").innerHTML = dias.map(d => {
    const iso = aISO(d);
    return `<button type="button" class="chip" data-fecha="${iso}" aria-pressed="${iso === elegida}"
              aria-label="${DIAS[d.getDay()]} ${fechaLarga(iso)}">${DIAS[d.getDay()]} ${d.getDate()}</button>`;
  }).join("");
}
$("#c-atajos").addEventListener("click", e => {
  const b = e.target.closest("[data-fecha]"); if (!b) return;
  $("#c-fecha").value = b.dataset.fecha;
  pintarSlots(); pintarAtajos();
});
$("#c-fecha").addEventListener("change", () => { pintarSlots(); pintarAtajos(); });
```

**6. Pinta los atajos al arrancar.** En `portal-permisos/index.html`, reemplaza:

```html

pintarSlots();
```

por:

```html

pintarSlots();
pintarAtajos();
```

- [ ] **Step 4: Verificar que pasan**

Run: `npx playwright test`
Expected: `130 passed`, 0 failed, 0 flaky

- [ ] **Step 5: Revisión manual (lo que las pruebas no pueden ver)**

| Revisión | Cómo | Qué debe pasar |
|---|---|---|
| Lector de pantalla | NVDA con Chrome o Edge | Al enviar un formulario con error se anuncia el mensaje y el foco cae en el campo. Al cambiar de sección se lee el título. El diálogo del expediente se anuncia con su nombre. |
| iPhone / Safari | Un iPhone real, o temporalmente el proyecto `{ name: "iphone", use: { ...devices["iPhone 13"] } }` con `npx playwright install webkit` | La barra inferior no queda bajo la barra de inicio del iPhone; el `<dialog>` abre, se desplaza y cierra; la franja no desborda. |
| Zoom al 200 % | Escritorio, Ctrl + + hasta 200 % | Todo se lee sin cortes ni superposiciones (WCAG 1.4.4). |
| Contraste | Tema oscuro, pantallas con el diálogo abierto y el buscador con resultados | Nada se ve borroso ni con poco contraste. |

- [ ] **Step 6: Commit**

```bash
git add portal-permisos/index.html portal-permisos/calidad
git commit -m "feat(portal): atajos de fecha, leyenda de horarios y fecha local de Panamá" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Fuera de alcance (planes siguientes)

- **Conectar el portal a la API (Fase 4):** reemplazar el objeto `state` y la simulación de ClamAV por llamadas reales; el plan de base de datos deja la API lista.
- **Panel del funcionario** (`portal-Panel_Control_Permisos`): bandeja del revisor, aprobar, subsanar y rechazar.
- **Casos nuevos en Qase:** las pruebas nuevas no llevan `qase.id`. Si se quieren en Qase, agrégalas a `calidad/casos-qase.md` y ponles su número.
- **`webServer` en `playwright.config.js`**, para que las pruebas levanten el servidor solas en CI.

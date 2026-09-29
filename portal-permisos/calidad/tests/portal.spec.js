// @ts-check
const { test, expect } = require("@playwright/test");
const { qase } = require("playwright-qase-reporter");
const path = require("node:path");
const fs = require("node:fs");

/**
 * Pruebas de la Ventanilla Única Municipal.
 *
 * Cada prueba lleva qase.id(N), que la amarra al caso del mismo número en Qase.
 * Los casos están descritos en calidad/casos-qase.md — súbelos primero a Qase
 * y ajusta los números si el proyecto te asigna otros.
 */

const CUENTA = { email: "demo@mupa.gob.pa", pass: "demo1234" };
const TMP = path.join(__dirname, "..", ".tmp");

/** Genera archivos de prueba sin depender de binarios externos. */
function archivo(nombre, contenido) {
  fs.mkdirSync(TMP, { recursive: true });
  const ruta = path.join(TMP, nombre);
  fs.writeFileSync(ruta, contenido);
  return ruta;
}

const PDF_VALIDO = () =>
  archivo("requisitos.pdf",
    "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
    "2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n");

// Cadena EICAR: archivo de prueba estándar que TODO antivirus debe detectar.
// No es un virus real; existe justamente para probar que ClamAV está activo.
const EICAR = () =>
  archivo("eicar-prueba.pdf",
    "%PDF-1.4\nX5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*\n%%EOF\n");

const FALSO_PDF = () => archivo("documento.pdf", "Esto no es un PDF, es texto plano.");

async function entrar(page) {
  await page.goto("/");
  await page.getByLabel(/Correo electrónico/).first().fill(CUENTA.email);
  await page.getByLabel(/Contraseña/).first().fill(CUENTA.pass);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: /Buen[oa]s/ })).toBeVisible();
}

// ───────────────────────────── Autenticación ─────────────────────────────

test.describe("Autenticación", () => {

  test("Inicio de sesión con credenciales válidas", async ({ page }) => {
    qase.id(1);
    qase.title("Un usuario registrado entra al portal");
    await entrar(page);
    await expect(page.getByRole("navigation", { name: /Secciones/ })).toBeVisible();
  });

  test("Inicio de sesión con contraseña incorrecta", async ({ page }) => {
    qase.id(2);
    await page.goto("/");
    await page.getByLabel(/Correo electrónico/).first().fill(CUENTA.email);
    await page.getByLabel(/Contraseña/).first().fill("clave-equivocada");
    await page.getByRole("button", { name: "Iniciar sesión" }).click();
    await expect(page.getByText(/no coinciden/i)).toBeVisible();
    // No debe entrar
    await expect(page.getByRole("navigation", { name: /Secciones/ })).toBeHidden();
  });

  test("Registro rechaza a un menor de edad", async ({ page }) => {
    qase.id(3);
    await page.goto("/");
    await page.getByRole("tab", { name: "Crear cuenta" }).click();
    await page.getByLabel("Nombre", { exact: false }).first().fill("Ana");
    await page.getByLabel("Apellido").fill("Pérez");
    await page.getByLabel("Edad").fill("16");
    await page.getByLabel(/Lugar donde colabora/).fill("Independiente");
    await page.getByLabel(/Correo electrónico/).last().fill("ana.prueba@correo.com");
    await page.getByLabel("Contraseña", { exact: false }).first().fill("clave12345");
    await page.getByLabel(/Repetir contraseña/).fill("clave12345");
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Crear cuenta y entrar/ }).click();
    await expect(page.getByText(/al menos 18 años/i)).toBeVisible();
  });

  test("Registro exige que las contraseñas coincidan", async ({ page }) => {
    qase.id(4);
    await page.goto("/");
    await page.getByRole("tab", { name: "Crear cuenta" }).click();
    await page.getByLabel("Nombre", { exact: false }).first().fill("Luis");
    await page.getByLabel("Apellido").fill("Gómez");
    await page.getByLabel("Edad").fill("30");
    await page.getByLabel(/Lugar donde colabora/).fill("Municipio de Panamá");
    await page.getByLabel(/Correo electrónico/).last().fill("luis.prueba@correo.com");
    await page.getByLabel("Contraseña", { exact: false }).first().fill("clave12345");
    await page.getByLabel(/Repetir contraseña/).fill("otraclave99");
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Crear cuenta y entrar/ }).click();
    await expect(page.getByText(/no coinciden/i)).toBeVisible();
  });
});

// ────────────────────────── Solicitud de permiso ──────────────────────────

test.describe("Solicitud de permiso", () => {

  test.beforeEach(async ({ page }) => { await entrar(page); });

  test("El catálogo carga los trámites de la MUPA", async ({ page }) => {
    qase.id(10);
    await page.getByRole("button", { name: "Solicitar permiso" }).click();
    await page.getByRole("button", { name: /Espectáculos y eventos públicos/ }).click();
    await expect(page.getByText("Espectáculo Público — menos de 500 personas")).toBeVisible();
    await expect(page.getByText("Chiva Parrandera")).toBeVisible();
  });

  test("Al elegir un permiso se listan sus requisitos", async ({ page }) => {
    qase.id(11);
    await page.getByRole("button", { name: "Solicitar permiso" }).click();
    await page.getByRole("button", { name: /Permisos nocturnos/ }).click();
    await page.getByRole("button", { name: /Permiso Nocturno Categoría A$/ }).click();
    await expect(page.getByText("Paz y Salvo Municipal")).toBeVisible();
    await expect(page.getByText(/25 días hábiles/)).toBeVisible();
  });

  test("Se rechaza una fecha con menos de 15 días de antelación", async ({ page }) => {
    qase.id(12);
    await irAPaso2(page);
    const manana = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    await page.locator("#f-fecha").fill(manana);
    await page.locator("#f-lugar").fill("Plaza Catedral, San Felipe");
    await page.locator("#f-corregimiento").selectOption("San Felipe");
    await page.locator("#f-tipoacto").selectOption("Actividad cultural o artística");
    await page.locator("#f-aforo").fill("200");
    await page.locator("#f-tel").fill("+507 6000-0000");
    await page.locator("#f-motivo").fill("Presentación de danza folclórica organizada por el grupo cultural.");
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText(/15 días hábiles de antelación/)).toBeVisible();
  });

  test("El aforo debe caber en el rango del permiso elegido", async ({ page }) => {
    qase.id(13);
    // «menos de 500 personas» con aforo 1200 debe fallar
    await irAPaso2(page, "Espectáculos y eventos públicos", /menos de 500 personas/);
    await llenarPaso2(page, { aforo: "1200" });
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText(/el aforo debe estar entre/i)).toBeVisible();
  });

  test("El motivo exige un mínimo de detalle", async ({ page }) => {
    qase.id(14);
    await irAPaso2(page);
    await llenarPaso2(page, { motivo: "Evento" });
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText(/al menos 20 caracteres/)).toBeVisible();
  });
});

// ──────────────────── Seguridad documental (ClamAV) ────────────────────

test.describe("Verificación de documentos", () => {

  test.beforeEach(async ({ page }) => { await entrar(page); });

  test("Un PDF válido supera las cinco verificaciones", async ({ page }) => {
    qase.id(20);
    qase.title("Cadena de verificación completa sobre un PDF limpio");
    await irAPaso3(page);
    await page.locator("#file-in").setInputFiles(PDF_VALIDO());
    await expect(page.locator("#scan-pill")).toHaveText("Verificado", { timeout: 15_000 });
    await expect(page.locator('.chk[data-c="av"][data-s="ok"]')).toBeVisible();
    await expect(page.locator('.chk[data-c="hash"][data-s="ok"]')).toBeVisible();
    await expect(page.locator("#s3-next")).toBeEnabled();
  });

  test("Un archivo que no es PDF se rechaza aunque tenga extensión .pdf", async ({ page }) => {
    qase.id(21);
    qase.title("La validación mira los bytes mágicos, no sólo la extensión");
    await irAPaso3(page);
    await page.locator("#file-in").setInputFiles(FALSO_PDF());
    await expect(page.locator('.chk[data-c="fmt"][data-s="bad"]')).toBeVisible();
    await expect(page.locator("#scan-pill")).toHaveText("Rechazado");
    await expect(page.locator("#s3-next")).toBeDisabled();
  });

  test("ClamAV detiene el archivo de prueba EICAR", async ({ page }) => {
    qase.id(22);
    qase.title("Un documento con firma de amenaza no entra al expediente");
    await irAPaso3(page);
    await page.locator("#file-in").setInputFiles(EICAR());
    await expect(page.locator("#scan-pill")).toHaveText("Rechazado", { timeout: 15_000 });
    await expect(page.getByText(/amenaza|cuarentena/i)).toBeVisible();
    await expect(page.locator("#s3-next")).toBeDisabled();
  });

  test("La huella SHA-256 se muestra y viaja al resumen", async ({ page }) => {
    qase.id(23);
    await irAPaso3(page);
    await page.locator("#file-in").setInputFiles(PDF_VALIDO());
    await expect(page.locator("#scan-pill")).toHaveText("Verificado", { timeout: 15_000 });
    await page.locator("#s3-next").click();
    const huella = page.locator("#sum").getByText(/^[0-9a-f]{64}$/);
    await expect(huella).toBeVisible();
  });
});

// ──────────────────────────── Citas y contacto ────────────────────────────

test.describe("Citas", () => {

  test.beforeEach(async ({ page }) => {
    await entrar(page);
    await page.getByRole("button", { name: "Citas" }).click();
  });

  test("No se puede reservar sin elegir horario", async ({ page }) => {
    qase.id(30);
    await page.locator("#c-sede").selectOption({ index: 1 });
    await page.locator("#c-motivo").selectOption({ index: 1 });
    await page.getByRole("button", { name: "Confirmar cita" }).click();
    await expect(page.getByText(/Elige uno de los horarios/)).toBeVisible();
  });

  test("Una cita confirmada aparece en la lista", async ({ page }) => {
    qase.id(31);
    await page.locator("#c-sede").selectOption({ index: 1 });
    await page.locator("#c-motivo").selectOption({ index: 1 });
    await page.locator(".slot:not([disabled])").first().click();
    await page.getByRole("button", { name: "Confirmar cita" }).click();
    await expect(page.locator("#citas-list article")).toHaveCount(1);
    await expect(page.getByText("Confirmada")).toBeVisible();
  });

  test("Se rechaza una cita en fin de semana", async ({ page }) => {
    qase.id(32);
    const d = new Date();
    d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7 || 7));   // próximo sábado
    await page.locator("#c-sede").selectOption({ index: 1 });
    await page.locator("#c-motivo").selectOption({ index: 1 });
    await page.locator("#c-fecha").fill(d.toISOString().slice(0, 10));
    await page.locator(".slot:not([disabled])").first().click();
    await page.getByRole("button", { name: "Confirmar cita" }).click();
    await expect(page.getByText(/lunes a viernes/)).toBeVisible();
  });
});

test.describe("Contacto", () => {

  test("El formulario devuelve un número de seguimiento", async ({ page }) => {
    qase.id(40);
    await entrar(page);
    await page.getByRole("button", { name: "Contacto" }).click();
    await page.locator("#ct-tema").selectOption({ index: 1 });
    await page.locator("#ct-msg").fill("Quisiera saber el estado de mi expediente de uso de aceras.");
    await page.getByRole("button", { name: "Enviar mensaje" }).click();
    await expect(page.getByText(/MSG-\d{6}/)).toBeVisible();
  });

  test("Un mensaje demasiado corto se rechaza", async ({ page }) => {
    qase.id(41);
    await entrar(page);
    await page.getByRole("button", { name: "Contacto" }).click();
    await page.locator("#ct-tema").selectOption({ index: 1 });
    await page.locator("#ct-msg").fill("Hola");
    await page.getByRole("button", { name: "Enviar mensaje" }).click();
    await expect(page.getByText(/muy corto/)).toBeVisible();
  });
});

// ──────────────────────────── Accesibilidad ────────────────────────────

test.describe("Accesibilidad y responsivo", () => {

  test("El portal es usable a 400 px sin desplazamiento horizontal", async ({ page }) => {
    qase.id(50);
    await page.setViewportSize({ width: 400, height: 850 });
    await entrar(page);
    const desborda = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(desborda).toBe(false);
  });

  test("Se puede navegar el formulario de acceso sólo con el teclado", async ({ page }) => {
    qase.id(51);
    await page.goto("/");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    const enfocado = await page.evaluate(() => document.activeElement?.id);
    expect(["li-email", "tab-login", "tab-signup"]).toContain(enfocado);
  });
});

// ──────────────────────────── Auxiliares ────────────────────────────

async function irAPaso2(page, categoria = "Espectáculos y eventos públicos", permiso = /menos de 4,000/) {
  await page.getByRole("button", { name: "Solicitar permiso" }).click();
  await page.getByRole("button", { name: new RegExp(categoria) }).click();
  await page.getByRole("button", { name: permiso }).click();
  await page.locator("#s1-next").click();
  await expect(page.locator('[data-step="2"]')).toBeVisible();
}

async function llenarPaso2(page, sobrescribir = {}) {
  const d = new Date(Date.now() + 40 * 86400000).toISOString().slice(0, 10);
  const v = {
    corregimiento: "San Francisco", tipoActo: "Concierto o presentación musical",
    lugar: "Parque Omar, calle 74 San Francisco", fecha: d, aforo: "800",
    tel: "+507 6000-0000",
    motivo: "Concierto benéfico al aire libre organizado por una fundación local.",
    ...sobrescribir,
  };
  await page.locator("#f-corregimiento").selectOption(v.corregimiento);
  await page.locator("#f-tipoacto").selectOption(v.tipoActo);
  await page.locator("#f-lugar").fill(v.lugar);
  await page.locator("#f-fecha").fill(v.fecha);
  await page.locator("#f-aforo").fill(v.aforo);
  await page.locator("#f-tel").fill(v.tel);
  await page.locator("#f-motivo").fill(v.motivo);
}

async function irAPaso3(page) {
  await irAPaso2(page);
  await llenarPaso2(page);
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.locator('[data-step="3"]')).toBeVisible();
}

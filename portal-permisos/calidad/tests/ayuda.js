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

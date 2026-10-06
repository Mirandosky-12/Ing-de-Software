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

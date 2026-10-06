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

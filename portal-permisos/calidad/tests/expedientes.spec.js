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

test("El detalle descarga la constancia de la solicitud en PDF", async ({ page }) => {
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Mis solicitudes" }).click();
  await page.getByRole("button", { name: "Ver detalle de EXP-2026-004182" }).click();
  const [descarga] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("dialog").getByRole("button", { name: "Descargar constancia" }).click(),
  ]);
  expect(descarga.suggestedFilename()).toBe("constancia-EXP-2026-004182.pdf");
  const fs = require("fs");
  const pdf = fs.readFileSync(await descarga.path() ?? "").toString("latin1");
  expect(pdf.startsWith("%PDF-1.4")).toBe(true);
  for (const dato of ["EXP-2026-004182", "9f2c41ab77d0e5b3c8a1f64e2d9b0357cc84e1a6b2f7d3905e8c6a4b1d7f2093",
                      "Panamá", "Espectáculo Público"]) {
    expect(pdf, dato).toContain(dato);
  }
  const inicio = Number(pdf.slice(pdf.lastIndexOf("startxref") + 9).trim().split(/\s/)[0]);
  expect(pdf.slice(inicio, inicio + 4)).toBe("xref");            // el archivo abre en cualquier lector
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

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

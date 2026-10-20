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

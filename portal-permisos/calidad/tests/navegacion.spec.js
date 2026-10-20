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

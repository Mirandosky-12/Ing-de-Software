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

test("La fecha propuesta es un día hábil aunque falten pocos días para el fin de semana", async ({ page }) => {
  // Un miércoles: hoy + 3 días caería en sábado.
  await page.clock.setFixedTime(new Date("2026-10-07T09:00:00-05:00"));
  await page.reload();
  await entrar(page);
  await page.getByRole("navigation", { name: /Secciones/ }).getByRole("button", { name: "Citas" }).click();
  await expect(page.locator("#c-fecha")).toHaveValue("2026-10-12");            // lunes, el tercer día hábil
  await expect(page.getByRole("group", { name: "Próximos días hábiles" })
    .getByRole("button").nth(2)).toHaveAttribute("aria-pressed", "true");
});

test("«Hoy» es la fecha local de Panamá, también de noche", async ({ page }) => {
  // 23:30 en Panamá ya es el día siguiente en UTC: la fecha mínima no debe saltar.
  await page.clock.setFixedTime(new Date("2026-10-06T23:30:00-05:00"));
  await page.reload();
  await expect.poll(() => page.evaluate(() => hoyISO())).toBe("2026-10-06");
});

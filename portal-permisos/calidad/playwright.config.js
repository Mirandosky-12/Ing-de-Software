// @ts-check
const { defineConfig, devices } = require("@playwright/test");

/**
 * Playwright ejecuta las pruebas; playwright-qase-reporter las sube a Qase.
 *
 * Antes de correr con Qase:
 *   1. Crea el proyecto en Qase y anota su código (ej. VUM).
 *   2. Perfil → API tokens → genera un token.
 *   3. export QASE_TESTOPS_API_TOKEN=...
 *      export QASE_MODE=testops
 *   4. npm run test:qase
 *
 * Con QASE_MODE sin definir, las pruebas corren en local y no suben nada.
 */
module.exports = defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,

  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["playwright-qase-reporter", {
      mode: process.env.QASE_MODE || "off",          // off | testops
      debug: false,
      testops: {
        api: { token: process.env.QASE_TESTOPS_API_TOKEN },
        project: process.env.QASE_PROJECT || "VUM",  // código del proyecto en Qase
        uploadAttachments: true,                     // sube capturas de los fallos
        run: {
          title: `Portal de permisos · ${new Date().toISOString().slice(0, 16).replace("T", " ")}`,
          complete: true,
        },
      },
      framework: { browser: { addAsParameter: true, parameterName: "navegador" } },
    }],
  ],

  use: {
    baseURL: process.env.BASE_URL || "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "es-PA",
    timezoneId: "America/Panama",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "movil",    use: { ...devices["Pixel 7"] } },
  ],
});

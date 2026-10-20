"use strict";

/* ============================================================
   1. DATOS — catálogo oficial de la Dirección de Permisos
      y Cumplimiento del Municipio de Panamá (35 trámites).
   ============================================================ */

const DOCS = {
  nota:   "Nota de solicitud dirigida al Alcalde de Panamá",
  ced:    "Copia de cédula o pasaporte del solicitante",
  aviso:  "Aviso de Operación vigente",
  paz:    "Paz y Salvo Municipal",
  rp:     "Certificado del Registro Público (personas jurídicas)",
  poliza: "Póliza de responsabilidad civil",
  bomb:   "Visto bueno del Cuerpo de Bomberos de Panamá",
  plano:  "Plano de ubicación o croquis del sitio",
  idoneo: "Idoneidad del personal técnico responsable",
  minsa:  "Registro sanitario del MINSA",
  ficha:  "Ficha técnica de los productos a utilizar",
  ipf:    "Informe Previo Favorable vigente",
  ruta:   "Ruta y horario detallado del recorrido",
  veh:    "Registro vehicular y revisado vigente",
  seg:    "Plan de seguridad y evacuación",
  ambos:  "Nota de no objeción del corregimiento"
};

const CATALOGO = [
  { cat:"Espectáculos y eventos públicos", icon:"evento", items:[
    { id:"ESP-500-",  n:"Espectáculo Público — menos de 500 personas", d:15, aforo:[1,499],
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.poliza,DOCS.bomb] },
    { id:"ESP-4000",  n:"Espectáculo Público — menos de 4,000 personas", d:20, aforo:[500,3999],
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.poliza,DOCS.bomb,DOCS.seg,DOCS.plano] },
    { id:"ESP-500+",  n:"Espectáculo Público — más de 500 personas", d:25, aforo:[500,60000],
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.poliza,DOCS.bomb,DOCS.seg,DOCS.plano,DOCS.rp] },
    { id:"FEST",      n:"Festividad", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.ambos,DOCS.poliza,DOCS.bomb] },
    { id:"BANDAS",    n:"Práctica de Bandas Independientes", d:10,
      req:[DOCS.nota,DOCS.ced,DOCS.ambos,DOCS.ruta] },
    { id:"PASEO",     n:"Paseo o Excursiones", d:10,
      req:[DOCS.nota,DOCS.ced,DOCS.ruta,DOCS.veh,DOCS.poliza] },
    { id:"CHIVA",     n:"Chiva Parrandera", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.veh,DOCS.poliza,DOCS.ruta,DOCS.aviso] },
    { id:"INVIT",     n:"Invitación de la Alcaldía de Panamá", d:8,
      req:[DOCS.nota,DOCS.ced] }
  ]},
  { cat:"Publicidad y uso de espacio público", items:[
    { id:"PUB-TEMP",  n:"Instalación de Publicidad Eventual o Temporal", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.plano,DOCS.ipf] },
    { id:"BANDEROLA", n:"Instalación de Banderolas Móviles", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.plano] },
    { id:"ESP-EST",   n:"Uso de Espacio Público para Estacionamiento", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.plano,DOCS.poliza] },
    { id:"ACERA",     n:"Uso Temporal de Aceras", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.plano] },
    { id:"CASCO",     n:"Uso Temporal de Espacio Público — Casco Antiguo", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.plano,DOCS.poliza,"Visto bueno de la Oficina del Casco Antiguo"] }
  ]},
  { cat:"Sonido y unidades móviles", items:[
    { id:"SON-TEMP",  n:"Servicio de Unidad Móvil de Sonido u Audio — Temporal", d:10,
      req:[DOCS.nota,DOCS.ced,DOCS.veh,DOCS.ruta] },
    { id:"SON-PERM",  n:"Servicio de Unidad Móvil de Sonido u Audio", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.veh,DOCS.ruta] }
  ]},
  { cat:"Permisos nocturnos", items:[
    { id:"NOC-A",     n:"Permiso Nocturno Categoría A", d:25,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.rp,DOCS.bomb,DOCS.ipf,DOCS.plano] },
    { id:"NOC-A-REN", n:"Renovación de Permiso Nocturno Categoría A", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.paz,"Permiso nocturno del período anterior",DOCS.bomb] },
    { id:"NOC-B",     n:"Permiso Nocturno Categoría B", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.bomb,DOCS.ipf] },
    { id:"NOC-C",     n:"Permiso Nocturno Categoría C", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.bomb,DOCS.ipf] },
    { id:"NOC-D",     n:"Permiso Nocturno Categoría D", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.bomb,DOCS.ipf] }
  ]},
  { cat:"Talleres", items:[
    { id:"TAL-INST",  n:"Instalación y Operación de Taller", d:25,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.ipf,DOCS.plano,DOCS.bomb] },
    { id:"TAL-HOR",   n:"Extensión de Horario para Taller", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,"Permiso de operación del taller"] },
    { id:"TAL-MOV",   n:"Operación de Taller Móvil", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.veh,DOCS.idoneo] },
    { id:"TAL-COMB",  n:"Taller — Extensión de Horario y Taller Móvil", d:18,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.veh,DOCS.idoneo] }
  ]},
  { cat:"Salud y saneamiento ambiental", items:[
    { id:"DESINF",    n:"Permiso de Desinfección", d:15,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.minsa,DOCS.idoneo,DOCS.ficha] },
    { id:"DESINF-A",  n:"Actualización de Desinfección", d:10,
      req:[DOCS.nota,DOCS.ced,DOCS.minsa,DOCS.ficha] },
    { id:"GICP",      n:"Gestión Integral de Control de Plagas", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.minsa,DOCS.idoneo,DOCS.ficha,DOCS.paz] },
    { id:"GICP-REN",  n:"Renovación de Gestión Integral de Control de Plagas", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.paz,DOCS.minsa,"Permiso GICP del período anterior"] },
    { id:"GICP-ACT",  n:"Actualización de Gestión Integral de Control de Plagas", d:10,
      req:[DOCS.nota,DOCS.ced,DOCS.minsa,DOCS.ficha,DOCS.idoneo] }
  ]},
  { cat:"Comercio y actividades especiales", items:[
    { id:"GANADO",    n:"Guía de Traslado de Ganado", d:5,
      req:[DOCS.nota,DOCS.ced,"Certificado de salud animal del MIDA",DOCS.veh,DOCS.ruta] },
    { id:"GRUAS",     n:"Inscripción de Grúas y Almacenamiento", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.rp,DOCS.veh,DOCS.poliza] },
    { id:"NAVIDAD",   n:"Venta de Árboles de Navidad", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz,DOCS.plano,"Permiso fitosanitario del MIDA"] },
    { id:"FERRETE",   n:"Ferrete", d:8,
      req:[DOCS.nota,DOCS.ced,DOCS.aviso,DOCS.paz] }
  ]},
  { cat:"Informes previos", items:[
    { id:"IPF",       n:"Informe Previo Favorable", d:20,
      req:[DOCS.nota,DOCS.ced,DOCS.rp,DOCS.plano,"Certificación de uso de suelo",DOCS.bomb] },
    { id:"IPF-ACT",   n:"Actualización de Informe Previo Favorable", d:12,
      req:[DOCS.nota,DOCS.ced,DOCS.ipf,DOCS.plano] }
  ]}
];

const CORREGIMIENTOS = ["24 de Diciembre","Alcalde Díaz","Ancón","Bella Vista","Betania","Caimitillo",
  "Calidonia","Chilibre","Curundú","Don Bosco","El Chorrillo","Ernesto Córdoba Campos","Juan Díaz",
  "Las Cumbres","Las Garzas","Las Mañanitas","Pacora","Parque Lefevre","Pedregal","Pueblo Nuevo",
  "Río Abajo","Rufina Alfaro","San Felipe","San Francisco","San Martín","Santa Ana","Tocumen","Ernesto Córdoba"];

const TIPOS_ACTO = ["Concierto o presentación musical","Feria o exposición comercial","Actividad deportiva",
  "Actividad religiosa","Desfile o pasacalle","Actividad cultural o artística","Verbena o baile popular",
  "Rodaje audiovisual","Actividad corporativa privada","Actividad benéfica","Instalación o montaje",
  "Operación comercial permanente","Servicio técnico o de saneamiento","Otro"];

const MAX_MB = 10;

/* ============================================================
   2. ESTADO
   ============================================================ */

const state = {
  user: null,
  cuentas: [{ nombre:"Diego", apellido:"López", edad:22, cedula:"8-912-345",
              org:"Universidad Tecnológica de Panamá", email:"demo@mupa.gob.pa", pass:"demo1234" }],
  expedientes: [
    { code:"EXP-2026-004182", permiso:"Espectáculo Público — menos de 4,000 personas",
      lugar:"Parque Omar, San Francisco", fecha:"2026-10-18", estado:"En revisión",
      etapa:"Revisión técnica · Dirección de Permisos", creado:"2026-09-12",
      hash:"9f2c41ab77d0e5b3c8a1f64e2d9b0357cc84e1a6b2f7d3905e8c6a4b1d7f2093" },
    { code:"EXP-2026-003914", permiso:"Uso Temporal de Aceras",
      lugar:"Ave. Central, Santa Ana", fecha:"2026-09-30", estado:"Aprobado",
      etapa:"Permiso emitido · descargable en ventanilla", creado:"2026-08-28",
      hash:"3b7e19c4a5d82f60b1e93c7a0d4f8256be31a9c705d2e6f8143b0c9a7e5d2f61" },
    { code:"EXP-2026-004055", permiso:"Permiso Nocturno Categoría B",
      lugar:"Calle Uruguay, Bella Vista", fecha:"2026-11-02", estado:"Subsanación",
      etapa:"Falta póliza de responsabilidad civil vigente", creado:"2026-09-05",
      hash:"c41d8a0b62f7e395d0a7c8b41e6f2039a75db3c0e18f6425bd93a0c7e214f8d6" }
  ],
  citas: [],
  sel: { cat:null, perm:null, datos:null, doc:null },
  step: 1
};

/* ============================================================
   3. UTILIDADES
   ============================================================ */

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));

const ALL_PERMS = CATALOGO.flatMap(c => c.items.map(i => ({ ...i, cat:c.cat })));

function toast(msg){
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg; t.setAttribute("role","status");
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
function showErr(el, msg, campoId){
  const zona = el.closest("form, .card") || document;
  $$('[aria-invalid="true"]', zona).forEach(limpiarCampo);
  if (!msg){ el.hidden = true; return; }
  el.hidden = false; el.lastElementChild.textContent = msg;
  const campo = campoId && $("#" + campoId);
  if (campo){
    // El error queda unido al campo: se ve marcado, el lector de pantalla lee
    // el mensaje y el foco llega justo donde hay que corregir.
    campo.setAttribute("aria-invalid", "true");
    campo.setAttribute("aria-describedby", el.id);
    campo.focus();
  } else {
    el.scrollIntoView({ behavior:"smooth", block:"nearest" });
  }
}
function limpiarCampo(c){
  c.removeAttribute("aria-invalid");
  if (/-err$/.test(c.getAttribute("aria-describedby") || "")) c.removeAttribute("aria-describedby");
}
["input", "change"].forEach(ev => document.addEventListener(ev, e => {
  if (e.target instanceof Element && e.target.getAttribute("aria-invalid") === "true") limpiarCampo(e.target);
}));
document.addEventListener("click", e => {
  const b = e.target.closest(".ver-clave"); if (!b) return;
  const campo = $("#" + b.getAttribute("aria-controls"));
  const ver = campo.type === "password";
  campo.type = ver ? "text" : "password";
  b.setAttribute("aria-pressed", String(ver));
});
function fechaLarga(iso){
  if (!iso) return "—";
  const [y,m,d] = iso.split("-").map(Number);
  const meses = ["enero","febrero","marzo","abril","mayo","junio","julio",
                 "agosto","septiembre","octubre","noviembre","diciembre"];
  return `${d} de ${meses[m-1]} de ${y}`;
}
// Fecha local (Panamá). toISOString() usa UTC: después de las 7 p. m. daba el día siguiente.
function aISO(d){
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function hoyISO(off = 0){
  const d = new Date(); d.setDate(d.getDate() + off);
  return aISO(d);
}
function estadoClase(e){
  return { "Aprobado":"ok", "En revisión":"warn", "Subsanación":"crit", "Recibido":"info" }[e] || "info";
}
function nuevoExpediente(){
  const n = String(4200 + state.expedientes.length * 7 + Math.floor(Math.random()*90)).padStart(6,"0");
  return `EXP-2026-${n}`;
}

/* ============================================================
   4. TEMA
   ============================================================ */

function temaOscuro(){
  const cur = document.documentElement.getAttribute("data-theme");
  return cur === "dark" || (!cur && matchMedia("(prefers-color-scheme: dark)").matches);
}
function pintarBotonTema(){ $("#btn-theme").setAttribute("aria-pressed", String(temaOscuro())); }
$("#btn-theme").addEventListener("click", () => {
  const nuevo = temaOscuro() ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", nuevo);
  try { localStorage.setItem("vum-tema", nuevo); } catch {}   // modo privado: sólo no se recuerda
  pintarBotonTema();
});
pintarBotonTema();

/* ============================================================
   5. AUTENTICACIÓN
   ============================================================ */

function mostrarPanel(cual){
  const login = cual === "login";
  $("#tab-login").setAttribute("aria-selected", login);
  $("#tab-signup").setAttribute("aria-selected", !login);
  $("#pane-login").hidden = !login;
  $("#pane-signup").hidden = login;
  $("#pane-login").classList.add("display-flex");
  $("#pane-signup").classList.add("display-flex");
}
$("#tab-login").addEventListener("click", () => mostrarPanel("login"));
$("#tab-signup").addEventListener("click", () => mostrarPanel("signup"));
$("#go-signup").addEventListener("click", e => { e.preventDefault(); mostrarPanel("signup"); });
$("#go-login").addEventListener("click", e => { e.preventDefault(); mostrarPanel("login"); });

$("#pane-login").addEventListener("submit", e => {
  e.preventDefault();
  const email = $("#li-email").value.trim().toLowerCase();
  const pass  = $("#li-pass").value;
  if (!email || !pass) return showErr($("#li-err"), "Escribe tu correo y tu contraseña.", email ? "li-pass" : "li-email");
  const u = state.cuentas.find(c => c.email.toLowerCase() === email);
  if (!u || u.pass !== pass)
    return showErr($("#li-err"), "El correo o la contraseña no coinciden. Revisa e inténtalo de nuevo.");
  showErr($("#li-err"), null);
  entrar(u);
});

$("#pane-signup").addEventListener("submit", e => {
  e.preventDefault();
  const v = id => $("#" + id).value.trim();
  const err = $("#su-err");
  const campos = { nombre:v("su-nombre"), apellido:v("su-apellido"), edad:v("su-edad"),
                   cedula:v("su-cedula"), org:v("su-org"), email:v("su-email").toLowerCase() };

  if (!campos.nombre || !campos.apellido) return showErr(err, "Escribe tu nombre y tu apellido.", campos.nombre ? "su-apellido" : "su-nombre");
  const edad = Number(campos.edad);
  if (!edad || edad < 18) return showErr(err, "Debes tener al menos 18 años para tramitar un permiso.", "su-edad");
  if (edad > 110) return showErr(err, "Revisa la edad ingresada.", "su-edad");
  if (!campos.org) return showErr(err, "Indica el lugar donde colaboras, o escribe «Independiente».", "su-org");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(campos.email))
    return showErr(err, "El correo electrónico no tiene un formato válido.", "su-email");
  if (state.cuentas.some(c => c.email.toLowerCase() === campos.email))
    return showErr(err, "Ya existe una cuenta con ese correo. Inicia sesión.", "su-email");
  const p1 = $("#su-pass").value, p2 = $("#su-pass2").value;
  if (p1.length < 8) return showErr(err, "La contraseña debe tener al menos 8 caracteres.", "su-pass");
  if (p1 !== p2) return showErr(err, "Las contraseñas no coinciden.", "su-pass2");
  if (!$("#su-ok").checked) return showErr(err, "Debes autorizar el tratamiento de tus datos para continuar.", "su-ok");

  showErr(err, null);
  const cuenta = { ...campos, edad, pass:p1 };
  state.cuentas.push(cuenta);
  entrar(cuenta);
  toast("Cuenta creada. ¡Bienvenido!");
});

function entrar(u){
  state.user = u;
  $("#view-auth").hidden = true;
  $("#view-app").hidden = false;
  $("#u-name").textContent = `${u.nombre} ${u.apellido}`;
  $("#u-org").textContent  = u.org;
  $("#u-ini").textContent  = (u.nombre[0] + u.apellido[0]).toUpperCase();
  const h = new Date().getHours();
  $("#greet").textContent = `${h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches"}, ${u.nombre}`;
  $("#ct-nombre").value = `${u.nombre} ${u.apellido}`;
  $("#ct-email").value  = u.email;
  $("#f-resp").value    = `${u.nombre} ${u.apellido}`;
  ir("inicio");
  pintarTodo();
  window.scrollTo(0, 0);
}

$("#btn-logout").addEventListener("click", () => {
  state.user = null;
  $("#view-app").hidden = true;
  $("#view-auth").hidden = false;
  $("#li-pass").value = "";
  mostrarPanel("login");
  window.scrollTo(0, 0);
});

/* ============================================================
   6. NAVEGACIÓN
   ============================================================ */

function ir(pagina){
  $$("[data-page]").forEach(s => s.hidden = s.dataset.page !== pagina);
  $$("nav.menu button").forEach(b =>
    b.dataset.nav === pagina ? b.setAttribute("aria-current","page") : b.removeAttribute("aria-current"));
  window.scrollTo({ top:0, behavior:"smooth" });
  // Lectores de pantalla y teclado: el foco llega al título de la sección nueva.
  const titulo = $(`[data-page="${pagina}"] h1`);
  if (titulo){ titulo.tabIndex = -1; titulo.focus({ preventScroll:true }); }
  const nombre = $(`nav.menu [data-nav="${pagina}"]`)?.textContent.trim();
  document.title = `${nombre} · Ventanilla Única Municipal`;
}
document.addEventListener("click", e => {
  const b = e.target.closest("[data-nav]");
  if (b) ir(b.dataset.nav);
});

/* ============================================================
   7. PANEL E INDICADORES
   ============================================================ */

function tarjetaExpediente(x){
  return `<article class="exp st-${estadoClase(x.estado)}">
    <div class="ancho-flexible">
      <div class="code">${esc(x.code)}</div>
      <div class="name">${esc(x.permiso)}</div>
      <div class="meta"><i>${esc(x.lugar)}</i><i>${fechaLarga(x.fecha)}</i><i>${esc(x.etapa)}</i></div>
    </div>
    <div class="exp-der">
      <span class="pill ${estadoClase(x.estado)}">${esc(x.estado)}</span>
      <button type="button" class="btn ghost ver" data-exp="${esc(x.code)}" aria-label="Ver detalle de ${esc(x.code)}">Ver detalle</button>
    </div>
  </article>`;
}

function pintarTodo(){
  const e = state.expedientes;
  $("#k-total").textContent = e.length;
  $("#k-rev").textContent   = e.filter(x => x.estado === "En revisión").length;
  $("#k-apr").textContent   = e.filter(x => x.estado === "Aprobado").length;
  $("#k-sub").textContent   = e.filter(x => x.estado === "Subsanación").length;
  $("#recent").innerHTML    = e.slice(0, 3).map(tarjetaExpediente).join("");
  const pendientes = e.filter(x => x.estado === "Subsanación");
  $("#atencion").hidden = !pendientes.length;
  $("#at-lista").innerHTML = pendientes.map(x =>
    `<div class="at-r">
       <div class="ancho-flexible"><div class="code">${esc(x.code)}</div>
         <div class="name">${esc(x.permiso)}</div><p class="small muted">${esc(x.etapa)}</p></div>
       <button type="button" class="btn" data-exp="${esc(x.code)}" aria-label="Resolver ${esc(x.code)}">Resolver</button>
     </div>`).join("");
  filtrarExpedientes();
  pintarCitas();
  const sel = $("#c-exp");
  sel.innerHTML = '<option value="">Ninguno / consulta general</option>' +
    e.map(x => `<option>${esc(x.code)} — ${esc(x.permiso)}</option>`).join("");
}

function filtrarExpedientes(){
  const q   = $("#q").value.trim().toLowerCase();
  const est = $("#q-est").value;
  const r = state.expedientes.filter(x =>
    (!est || x.estado === est) &&
    (!q || x.code.toLowerCase().includes(q) || x.permiso.toLowerCase().includes(q) ||
     x.lugar.toLowerCase().includes(q)));
  $("#all-exp").innerHTML = r.map(tarjetaExpediente).join("");
  $("#no-exp").hidden = r.length > 0;
}
$("#q").addEventListener("input", filtrarExpedientes);

document.addEventListener("click", e => {
  const s = e.target.closest(".stat[data-filtro]"); if (!s) return;
  ir("expedientes");
  $("#q").value = ""; $("#q-est").value = s.dataset.filtro;
  filtrarExpedientes();
});

/* ---------- detalle del expediente ---------- */
const QUE_SIGUE = {
  "Recibido":    () => "Tu solicitud está en cola para asignarse a un revisor. Por ahora no tienes que hacer nada.",
  "En revisión": () => "Un revisor de la Dirección está evaluando tu expediente. Si necesita algo, te escribirá a tu correo.",
  "Subsanación": x  => `Falta algo para continuar: ${x.etapa}. Entrégalo en una cita y la revisión sigue desde donde quedó.`,
  "Aprobado":    x  => `Tu permiso fue aprobado. ${x.etapa}.`,
  "Rechazado":   x  => `La solicitud no fue aprobada. ${x.etapa}. Puedes escribirnos si tienes dudas.`,
};

function lineaDeTiempo(x){
  const actual = x.estado === "Recibido" ? 0 : ["En revisión", "Subsanación"].includes(x.estado) ? 1 : 2;
  const pasos = ["Recibido", x.estado === "Subsanación" ? "Subsanación pendiente" : "En revisión",
                 ["Aprobado", "Rechazado"].includes(x.estado) ? x.estado : "Resolución"];
  return `<ol class="linea" aria-label="Avance del trámite">${pasos.map((p, i) =>
    `<li data-s="${i < actual ? "done" : i === actual ? "on" : ""}"
         class="${i === actual && x.estado === "Subsanación" ? "crit" : ""}"
         ${i === actual ? 'aria-current="step"' : ""}>${esc(p)}</li>`).join("")}</ol>`;
}

function abrirDetalle(code){
  const x = state.expedientes.find(e => e.code === code); if (!x) return;
  $("#det-code").textContent = x.code;
  $("#det-titulo").textContent = x.permiso;
  $("#det-cuerpo").innerHTML = `
    <div><span class="pill ${estadoClase(x.estado)}">${esc(x.estado)}</span></div>
    ${lineaDeTiempo(x)}
    <div class="sigue"><h3>Qué sigue</h3><p>${esc(QUE_SIGUE[x.estado]?.(x) ?? x.etapa)}</p></div>
    <dl class="summary">
      ${[["Lugar", x.lugar], ["Día del acto", fechaLarga(x.fecha)], ["Recibido el", fechaLarga(x.creado)],
         ["Etapa actual", x.etapa]].map(([k, v]) =>
        `<div class="r"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}
      <div class="r"><dt>Huella del documento</dt><dd class="mono huella-documento">${esc(x.hash)}</dd></div>
    </dl>
    <div class="actions">
      ${x.estado === "Subsanación"
        ? `<button type="button" class="btn" id="det-cita">Agendar cita para subsanar</button>` : ""}
      <button type="button" class="btn ghost" id="det-pdf">Descargar constancia</button>
    </div>`;
  $("#det-pdf").addEventListener("click", () => descargarConstancia(x));
  $("#det-cita")?.addEventListener("click", () => {
    $("#detalle").close();
    ir("citas");
    $("#c-motivo").value = "Subsanación de expediente";
    $("#c-exp").value = `${x.code} — ${x.permiso}`;
  });
  $("#detalle").showModal();                 // modal nativo: atrapa el foco y Escape lo cierra
}

document.addEventListener("click", e => {
  const b = e.target.closest("[data-exp]"); if (b) abrirDetalle(b.dataset.exp);
});
$("#det-cerrar").addEventListener("click", () => $("#detalle").close());

/* ---------- constancia en PDF, generada en el navegador ----------
   Mismo diseño que la de la API (backend/constancia.py): PDF escrito a mano,
   A4, Helvetica y Courier en WinAnsiEncoding (tildes y eñes). Mientras el
   portal no esté conectado a la API no hay sello de la bitácora; en su lugar
   va un código de verificación: el SHA-256 de los datos de la constancia. */
const WIN_ANSI = { "€":0x80, "‚":0x82, "„":0x84, "…":0x85, "‘":0x91, "’":0x92,
                   "“":0x93, "”":0x94, "•":0x95, "–":0x96, "—":0x97 };

// Texto → cadena literal de PDF, un carácter por byte.
function cadenaPDF(t){
  const escapado = String(t).replace(/[\\()]/g, m => "\\" + m);
  return Array.from(escapado, c => {
    const n = c.codePointAt(0);
    return String.fromCharCode(WIN_ANSI[c] ?? (n < 256 ? n : 0x3f));
  }).join("");
}

function envolver(t, ancho){
  const lineas = []; let actual = "";
  for (const palabra of String(t).split(/\s+/).filter(Boolean)) {
    if (actual && (actual + " " + palabra).length > ancho) { lineas.push(actual); actual = palabra; }
    else actual = actual ? `${actual} ${palabra}` : palabra;
  }
  if (actual) lineas.push(actual);
  return lineas.length ? lineas : ["—"];
}

function constanciaPDF(x, u, verificacion){
  const A = 595, H = 842, M = 56, COL = M + 150;
  const AZUL = "0.043 0.310 0.541", GRIS = "0.30 0.34 0.38";
  const ops = []; let y;
  const texto = (t, { f = "F1", tam = 10, en = M, color = "0 0 0" } = {}) =>
    ops.push(`BT ${color} rg /${f} ${tam} Tf ${en} ${y.toFixed(1)} Td (${cadenaPDF(t)}) Tj ET`);
  const seccion = t => {
    y -= 10; texto(t.toUpperCase(), { f: "F2", tam: 9, color: AZUL }); y -= 6;
    ops.push(`0.80 G 0.6 w ${M} ${y.toFixed(1)} m ${A - M} ${y.toFixed(1)} l S`); y -= 16;
  };
  const fila = (k, v, mono = false) => {
    const tam = mono ? 8 : 10;                     // en Courier 8 una huella de 64 cabe en una línea
    texto(k, { f: "F2", tam: 9.5, color: GRIS });
    envolver(v, Math.floor((A - M - COL) / (tam * (mono ? 0.6 : 0.5)))).forEach((l, i) => {
      if (i) y -= 13;
      texto(l, { f: mono ? "F3" : "F1", tam, en: COL });
    });
    y -= 17;
  };

  // franja oficial, igual que en el portal
  ops.push(`${AZUL} rg 0 ${H - 40} ${A} 40 re f`, `0.722 0.439 0.110 rg 0 ${H - 43} ${A} 3 re f`);
  y = H - 26; texto("Municipio de Panamá · Dirección de Permisos y Cumplimiento", { f: "F2", color: "1 1 1" });
  y = H - 87; texto("Constancia de solicitud", { f: "F2", tam: 20 });
  y -= 22;    texto(x.code, { f: "F3", tam: 12, color: AZUL });
  y -= 18;    texto(`Recibida el ${fechaLarga(x.creado)} · Estado: ${x.estado}`, { color: GRIS });
  y -= 14;

  seccion("Solicitud");
  fila("Trámite", x.permiso);
  fila("Titular", `${u.nombre} ${u.apellido} (${u.email})`);
  if (x.resp) fila("Responsable", `${x.resp} · ${x.tel}`);
  if (x.tipoActo) fila("Tipo de acto", x.tipoActo);
  fila("Lugar", x.lugar);
  fila("Fecha del acto", fechaLarga(x.fecha) + (x.hIni ? `, de ${x.hIni} a ${x.hFin}` : ""));
  if (x.aforo) fila("Aforo", `${x.aforo.toLocaleString("es-PA")} personas`);
  fila("Etapa actual", x.etapa);
  if (x.motivo) fila("Motivo", x.motivo);

  seccion("Documento adjunto");
  fila("Huella SHA-256", x.hash, true);

  seccion("Verificación");
  if (x.sello) fila("Sellado", `${x.sello} UTC`);
  fila("Código", verificacion, true);

  y -= 8;
  envolver("Esta constancia acredita que la solicitud fue recibida por la Ventanilla Única Municipal; " +
           "no es el permiso. La huella del documento identifica el PDF entregado: cualquier cambio en " +
           "el archivo produce otra huella. El código de verificación es el SHA-256 de los datos de esta " +
           "constancia; la que emite la API lleva además el sello de la bitácora de auditoría.",
           Math.floor((A - 2 * M) / 4.25)).forEach(l => { texto(l, { tam: 8.5, color: GRIS }); y -= 11.9; });

  // catálogo, página, contenido, tres fuentes estándar, información, xref y trailer
  const contenido = ops.join("\n");
  const fuente = n => `<< /Type /Font /Subtype /Type1 /BaseFont /${n} /Encoding /WinAnsiEncoding >>`;
  const objetos = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${A} ${H}] /Contents 4 0 R ` +
      "/Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> >>",
    `<< /Length ${contenido.length} >>\nstream\n${contenido}\nendstream`,
    fuente("Helvetica"), fuente("Helvetica-Bold"), fuente("Courier"),
    `<< /Title (${cadenaPDF("Constancia " + x.code)}) /Producer (Ventanilla Unica Municipal) >>`,
  ];
  let pdf = "%PDF-1.4\n%\xe2\xe3\xcf\xd3\n";
  const posiciones = objetos.map((o, i) => { const p = pdf.length; pdf += `${i + 1} 0 obj\n${o}\nendobj\n`; return p; });
  const xref = pdf.length;
  pdf += `xref\n0 ${objetos.length + 1}\n0000000000 65535 f \n` +
         posiciones.map(p => `${String(p).padStart(10, "0")} 00000 n \n`).join("") +
         `trailer\n<< /Size ${objetos.length + 1} /Root 1 0 R /Info ${objetos.length} 0 R >>\n` +
         `startxref\n${xref}\n%%EOF\n`;
  return Uint8Array.from(pdf, c => c.charCodeAt(0));
}

async function descargarConstancia(x){
  const u = state.user;
  let verificacion = "No disponible en este navegador";
  try {           // crypto.subtle sólo existe en contextos seguros (https o localhost)
    const datos = JSON.stringify([x.code, x.permiso, x.lugar, x.fecha, x.creado, x.hash, u.email]);
    const huella = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(datos));
    verificacion = Array.from(new Uint8Array(huella), b => b.toString(16).padStart(2, "0")).join("");
  } catch {}
  const url = URL.createObjectURL(new Blob([constanciaPDF(x, u, verificacion)], { type: "application/pdf" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: `constancia-${x.code}.pdf` });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(`Constancia de ${x.code} descargada.`);
}
$("#q-est").addEventListener("change", filtrarExpedientes);

/* ============================================================
   8. ASISTENTE — PASO 1: TIPO DE PERMISO
   ============================================================ */

$("#fact-tramites").textContent = ALL_PERMS.length;

$("#cats").innerHTML = CATALOGO.map((c, i) =>
  `<button type="button" class="cat" data-cat="${i}" aria-pressed="false">
     <span class="cn">${esc(c.cat)}</span>
     <span class="cc">${c.items.length} trámite${c.items.length > 1 ? "s" : ""}</span>
   </button>`).join("");

$("#cats").addEventListener("click", e => {
  const b = e.target.closest(".cat"); if (!b) return;
  $$(".cat").forEach(x => x.setAttribute("aria-pressed", x === b));
  state.sel.cat = Number(b.dataset.cat);
  state.sel.perm = null;
  $("#perm-wrap").hidden = false;
  $("#req-wrap").hidden = true;
  $("#s1-next").disabled = true;
  $("#perms").innerHTML = CATALOGO[state.sel.cat].items.map((p, i) =>
    `<button type="button" class="opt" data-perm="${esc(p.id)}" aria-pressed="false"
             aria-label="${esc(p.n)}" aria-describedby="od-${i} dd-${i}">
       <span class="radio"></span>
       <span><span class="on">${esc(p.n)}</span><span class="od" id="od-${i}">${p.req.length} documentos requeridos</span></span>
       <span class="days" id="dd-${i}">${p.d} días háb.</span>
     </button>`).join("");
});

$("#perms").addEventListener("click", e => {
  const b = e.target.closest(".opt"); if (!b) return;
  $$(".opt", $("#perms")).forEach(x => x.setAttribute("aria-pressed", x === b));
  state.sel.perm = ALL_PERMS.find(p => p.id === b.dataset.perm);
  $("#s1-next").disabled = false;
  const html = requisitosHTML(state.sel.perm);
  $("#req-wrap").innerHTML = html; $("#req-wrap").hidden = false;
});

function requisitosHTML(p){
  return `<div class="req-box">
    <span class="eyebrow">Requisitos · ${esc(p.n)}</span>
    <ul>${p.req.map(r => `<li>${esc(r)}</li>`).join("")}</ul>
    <p class="small muted margen-superior-10">Reúne estos documentos en <b>un solo archivo PDF</b>.
      Plazo estimado de resolución: <b>${p.d} días hábiles</b>.</p>
  </div>`;
}

const sinTildes = s => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

$("#q-tramite").addEventListener("input", e => {
  const q = sinTildes(e.target.value.trim());
  const res = $("#q-res"), vacio = $("#q-vacio");
  if (q.length < 2){ res.hidden = vacio.hidden = true; $("#q-cuenta").textContent = ""; return; }
  const palabras = q.split(/\s+/);
  const hallados = ALL_PERMS
    .filter(p => { const t = sinTildes(`${p.n} ${p.cat}`); return palabras.every(w => t.includes(w)); })
    .slice(0, 8);
  res.innerHTML = hallados.map((p, i) =>
    `<button type="button" class="opt" data-buscar="${esc(p.id)}" aria-label="${esc(p.n)}" aria-describedby="qd-${i}">
       <span class="radio"></span>
       <span><span class="on">${esc(p.n)}</span><span class="od" id="qd-${i}">${esc(p.cat)} · ${p.d} días háb.</span></span>
     </button>`).join("");
  res.hidden = !hallados.length;
  vacio.hidden = hallados.length > 0;
  $("#q-cuenta").textContent = hallados.length ? `${hallados.length} trámites encontrados` : "Sin resultados";
});

$("#q-res").addEventListener("click", e => {
  const b = e.target.closest("[data-buscar]"); if (!b) return;
  const p = ALL_PERMS.find(x => x.id === b.dataset.buscar);
  $(`.cat[data-cat="${CATALOGO.findIndex(c => c.cat === p.cat)}"]`).click();   // pinta su categoría
  $(`#perms [data-perm="${CSS.escape(p.id)}"]`).click();                      // y marca el trámite
  $("#q-tramite").value = ""; $("#q-res").hidden = true; $("#q-cuenta").textContent = "";
  $("#req-wrap").scrollIntoView({ behavior:"smooth", block:"nearest" });
});

$("#s1-next").addEventListener("click", () => {
  const p = state.sel.perm;
  $("#s2-sub").textContent = p.n;
  if (p.aforo){
    $("#f-aforo").min = p.aforo[0]; $("#f-aforo").max = p.aforo[1];
    $("#aforo-hint").textContent = `Este permiso aplica de ${p.aforo[0]} a ${p.aforo[1].toLocaleString("es-PA")} personas.`;
  } else {
    $("#f-aforo").min = 1; $("#f-aforo").max = 60000;
    $("#aforo-hint").textContent = "Número de personas esperadas.";
  }
  paso(2);
});

/* ============================================================
   9. ASISTENTE — PASO 2: DATOS DEL ACTO
   ============================================================ */

$("#f-corregimiento").insertAdjacentHTML("beforeend",
  CORREGIMIENTOS.map(c => `<option>${esc(c)}</option>`).join(""));
$("#f-tipoacto").insertAdjacentHTML("beforeend",
  TIPOS_ACTO.map(t => `<option>${esc(t)}</option>`).join(""));
$("#f-fecha").min = hoyISO(15);
$("#f-motivo").addEventListener("input", e => {
  if (e.target.value.length > 600) e.target.value = e.target.value.slice(0, 600);
  $("#motivo-n").textContent = e.target.value.length;
});

$('[data-step="2"]').addEventListener("submit", e => {
  e.preventDefault();
  const err = $("#s2-err"), V = id => $("#" + id).value.trim();
  const d = {
    corregimiento:V("f-corregimiento"), tipoActo:V("f-tipoacto"), lugar:V("f-lugar"),
    fecha:V("f-fecha"), hIni:V("f-hini"), hFin:V("f-hfin"),
    aforo:Number(V("f-aforo")), resp:V("f-resp"), tel:V("f-tel"), motivo:V("f-motivo")
  };
  if (!d.corregimiento) return showErr(err, "Selecciona el corregimiento donde se realizará el acto.", "f-corregimiento");
  if (!d.tipoActo)      return showErr(err, "Selecciona el tipo de acto.", "f-tipoacto");
  if (d.lugar.length < 5) return showErr(err, "Describe el lugar exacto con un poco más de detalle.", "f-lugar");
  if (!d.fecha)         return showErr(err, "Indica el día del acto.", "f-fecha");
  if (d.fecha < hoyISO(15))
    return showErr(err, "La fecha debe tener al menos 15 días hábiles de antelación.", "f-fecha");
  if (!d.hIni || !d.hFin) return showErr(err, "Indica la hora de inicio y la de cierre.", d.hIni ? "f-hfin" : "f-hini");
  if (d.hFin <= d.hIni && d.hFin > "06:00")
    return showErr(err, "La hora de cierre debe ser posterior a la de inicio.", "f-hfin");
  const p = state.sel.perm;
  if (!d.aforo || d.aforo < 1) return showErr(err, "Indica el aforo estimado.", "f-aforo");
  if (p.aforo && (d.aforo < p.aforo[0] || d.aforo > p.aforo[1]))
    return showErr(err, `Para «${p.n}» el aforo debe estar entre ${p.aforo[0]} y ${p.aforo[1].toLocaleString("es-PA")} personas. Cambia el tipo de permiso o corrige el aforo.`, "f-aforo");
  if (!d.resp)  return showErr(err, "Indica quién será el responsable en sitio.", "f-resp");
  if (!/[0-9]{7,}/.test(d.tel.replace(/[^0-9]/g,"")))
    return showErr(err, "Escribe un teléfono de contacto válido, por ejemplo +507 6000-0000.", "f-tel");
  if (d.motivo.length < 20) return showErr(err, "El motivo debe tener al menos 20 caracteres.", "f-motivo");

  showErr(err, null);
  state.sel.datos = d;
  $("#req-wrap-3").innerHTML = requisitosHTML(state.sel.perm);
  paso(3);
});

/* ============================================================
   10. ASISTENTE — PASO 3: DOCUMENTO PDF
       Cadena de verificación: formato → tamaño → antivirus
       (ClamAV) → huella SHA-256 → sellado en bitácora.
   ============================================================ */

const drop = $("#drop"), fileIn = $("#file-in");
drop.addEventListener("click", () => fileIn.click());
["dragenter","dragover"].forEach(ev =>
  drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave","drop"].forEach(ev =>
  drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", e => {
  const f = e.dataTransfer?.files?.[0]; if (f) verificar(f);
});
fileIn.addEventListener("change", e => { const f = e.target.files[0]; if (f) verificar(f); });

const NUM_CHK = { fmt:"1", size:"2", av:"3", hash:"4", log:"5" };
function marcar(c, estado, valor){
  const el = $(`.chk[data-c="${c}"]`);
  el.dataset.s = estado;
  el.querySelector(".ic").textContent =
    estado === "ok" ? "✓" : estado === "bad" ? "✕" : estado === "run" ? "◠" : NUM_CHK[c];
  if (valor !== undefined) el.querySelector(".cv").textContent = valor;
}
const espera = ms => new Promise(r => setTimeout(r, ms));

async function sha256(buf){
  const h = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2,"0")).join("");
}

async function verificar(file){
  try { await verificarPasos(file); }
  catch {
    // El archivo cambió o desapareció del disco mientras se leía (carpeta
    // sincronizada, memoria USB retirada…): se rechaza en vez de quedar en «Verificando».
    const c = $('.chk[data-s="run"]')?.dataset.c || "fmt";
    marcar(c, "bad", "No se pudo leer");
    $("#scan-pill").className = "pill crit"; $("#scan-pill").textContent = "Rechazado";
    showErr($("#s3-err"), "No pudimos leer el archivo. Vuelve a seleccionarlo.");
    fileIn.value = "";
  }
}

async function verificarPasos(file){
  showErr($("#s3-err"), null);
  state.sel.doc = null;
  $("#s3-next").disabled = true;
  $("#scan").hidden = false;
  $("#scan-name").textContent = file.name;
  $("#scan-pill").className = "pill info"; $("#scan-pill").textContent = "Verificando";
  ["fmt","size","av","hash","log"].forEach(c => marcar(c, "wait", ""));

  const fallar = (c, msg, corto) => {
    marcar(c, "bad", corto);
    $("#scan-pill").className = "pill crit"; $("#scan-pill").textContent = "Rechazado";
    showErr($("#s3-err"), msg);
    fileIn.value = "";
  };

  // 1 · Formato real del archivo: extensión, tipo MIME y firma binaria %PDF-
  marcar("fmt","run"); await espera(340);
  const cab = new Uint8Array(await file.slice(0, 5).arrayBuffer());
  const firma = String.fromCharCode(...cab);
  const extOK = /\.pdf$/i.test(file.name);
  if (!extOK || firma !== "%PDF-")
    return fallar("fmt", "El archivo no es un PDF válido. Sube un documento con extensión .pdf.", "No es un PDF");
  marcar("fmt","ok","%PDF-");

  // 2 · Tamaño
  marcar("size","run"); await espera(240);
  const mb = file.size / 1048576;
  if (mb > MAX_MB)
    return fallar("size", `El archivo pesa ${mb.toFixed(1)} MB y el límite es ${MAX_MB} MB. Comprime el PDF e inténtalo de nuevo.`, "Supera 10 MB");
  if (file.size === 0) return fallar("size", "El archivo está vacío.", "Vacío");
  marcar("size","ok", `${mb.toFixed(2)} MB`);

  // 3 · Antivirus. En producción este paso llama a POST /api/documentos/escanear,
  //     que entrega el archivo al demonio clamd de ClamAV (INSTREAM) y devuelve
  //     {limpio:true|false, firma:"…"}. Aquí se simula la respuesta del servicio.
  marcar("av","run"); await espera(1100);
  const sospechoso = /eicar|virus|malware|test-?infected/i.test(file.name);
  if (sospechoso)
    return fallar("av", "ClamAV detectó una amenaza en el archivo (Eicar-Test-Signature). El documento fue puesto en cuarentena y no se adjuntó al expediente.", "Bloqueado");
  marcar("av","ok","Sin amenazas");

  // 4 · Huella de integridad, calculada realmente sobre el contenido del archivo
  marcar("hash","run");
  const hash = await sha256(await file.arrayBuffer());
  await espera(260);
  marcar("hash","ok", hash.slice(0, 24) + "…");

  // 5 · Sellado en bitácora
  marcar("log","run"); await espera(300);
  const sello = new Date().toISOString().replace("T"," ").slice(0, 19);
  marcar("log","ok", sello + " UTC");

  $("#scan-pill").className = "pill ok"; $("#scan-pill").textContent = "Verificado";
  state.sel.doc = { nombre:file.name, bytes:file.size, mb:mb.toFixed(2), hash, sello };
  $("#s3-next").disabled = false;
}

$("#s3-next").addEventListener("click", () => {
  if (!state.sel.doc) return showErr($("#s3-err"), "Adjunta y verifica un PDF antes de continuar.");
  const p = state.sel.perm, d = state.sel.datos, doc = state.sel.doc;
  $("#sum").innerHTML = [
    ["Permiso solicitado", p.n],
    ["Categoría", p.cat],
    ["Solicitante", `${state.user.nombre} ${state.user.apellido} · ${state.user.org}`],
    ["Corregimiento", d.corregimiento],
    ["Lugar del acto", d.lugar],
    ["Tipo de acto", d.tipoActo],
    ["Día y horario", `${fechaLarga(d.fecha)} · ${d.hIni} a ${d.hFin}`],
    ["Aforo estimado", `${d.aforo.toLocaleString("es-PA")} personas`],
    ["Responsable en sitio", `${d.resp} · ${d.tel}`],
    ["Motivo", d.motivo],
    ["Documento adjunto", `${doc.nombre} (${doc.mb} MB) · verificado`],
    ["Huella SHA-256", `<span class="mono huella-documento">${doc.hash}</span>`],
    ["Plazo estimado", `${p.d} días hábiles`]
  ].map(([k,v]) => `<div class="r"><dt>${esc(k)}</dt><dd>${k === "Huella SHA-256" ? v : esc(v)}</dd></div>`).join("");
  paso(4);
});

$("#s4-ok").addEventListener("change", e => { $("#s4-send").disabled = !e.target.checked; });

$("#s4-send").addEventListener("click", () => {
  const p = state.sel.perm, d = state.sel.datos, doc = state.sel.doc;
  const code = nuevoExpediente();
  state.expedientes.unshift({
    code, permiso:p.n, lugar:`${d.lugar}, ${d.corregimiento}`, fecha:d.fecha,
    estado:"Recibido", etapa:"En cola de asignación · Dirección de Permisos",
    creado:hoyISO(), hash:doc.hash, sello:doc.sello,
    tipoActo:d.tipoActo, hIni:d.hIni, hFin:d.hFin, aforo:d.aforo, resp:d.resp, tel:d.tel, motivo:d.motivo
  });
  $("#receipt").innerHTML = [
    ["Número de expediente", `<span class="mono numero-expediente">${esc(code)}</span>`],
    ["Permiso", esc(p.n)],
    ["Recibido el", fechaLarga(hoyISO())],
    ["Estado", "Recibido"],
    ["Documento sellado", `<span class="mono huella-documento">${esc(doc.hash)}</span>`],
    ["Resolución estimada", `${p.d} días hábiles`]
  ].map(([k,v]) => `<div class="r"><dt>${k}</dt><dd>${v}</dd></div>`).join("");
  pintarTodo();
  paso(5);
  toast(`Expediente ${code} generado`);
});

$("#new-again").addEventListener("click", reiniciarAsistente);

function reiniciarAsistente(){
  state.sel = { cat:null, perm:null, datos:null, doc:null };
  $("#q-tramite").value = ""; $("#q-res").hidden = $("#q-vacio").hidden = true;
  $$(".cat").forEach(x => x.setAttribute("aria-pressed","false"));
  $("#perm-wrap").hidden = true; $("#req-wrap").hidden = true;
  $("#s1-next").disabled = true; $("#s3-next").disabled = true; $("#s4-send").disabled = true;
  $("#s4-ok").checked = false;
  $("#scan").hidden = true; fileIn.value = "";
  $('[data-step="2"]').reset();
  $("#f-resp").value = `${state.user.nombre} ${state.user.apellido}`;
  $("#f-hini").value = "18:00"; $("#f-hfin").value = "23:00";
  $("#motivo-n").textContent = "0";
  [ "#s2-err","#s3-err" ].forEach(s => showErr($(s), null));
  paso(1);
}

function paso(n){
  state.step = n;
  for (let i = 1; i <= 5; i++) $(`[data-step="${i}"]`).hidden = i !== n;
  $(`[data-step="${n}"]`).classList.add("display-flex");
  $$("#stepper .s").forEach((s, i) => {
    s.dataset.state = n > 4 ? "done" : (i + 1 === n ? "on" : i + 1 < n ? "done" : "");
    if (i + 1 < n || n > 4) s.querySelector(".num").textContent = "✓";
    else s.querySelector(".num").textContent = String(i + 1);
  });
  $("#stepper").hidden = n === 5;
  const nombres = ["Tipo de permiso", "Datos del acto", "Documentos", "Revisión y envío"];
  const actual = Math.min(n, 4);
  $("#paso-de").textContent = `Paso ${actual} de 4 · ${nombres[actual - 1]}`;
  $("#progreso").setAttribute("aria-valuenow", String(actual));
  // El ancho visual se deriva de aria-valuenow en style.css.
  $("#paso-de").hidden = $("#progreso").hidden = n === 5;
  $(`[data-step="${n}"]`).scrollIntoView({ behavior:"smooth", block:"start" });
}
$$("[data-back]").forEach(b => b.addEventListener("click", () => paso(Number(b.dataset.back))));

/* ============================================================
   11. CITAS
   ============================================================ */

const HORAS = ["08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30",
               "13:00","13:30","14:00","14:30","15:00","15:30"];
let horaSel = null;

// Los próximos n días hábiles a partir de mañana (ni sábado ni domingo).
function diasHabiles(n){
  const dias = [];
  for (const d = new Date(); dias.length < n; ){
    d.setDate(d.getDate() + 1);
    if (d.getDay() % 6) dias.push(new Date(d));            // ni domingo (0) ni sábado (6)
  }
  return dias;
}

// Se propone el tercer día hábil: «hoy + 3» caía en fin de semana de miércoles a viernes.
$("#c-fecha").min = hoyISO(1);
$("#c-fecha").value = aISO(diasHabiles(3)[2]);

function pintarSlots(){
  const f = $("#c-fecha").value || aISO(diasHabiles(3)[2]);
  // Ocupación determinista a partir de la fecha, para que el ejemplo sea estable.
  const semilla = f.split("-").reduce((a,b) => a + Number(b), 0);
  horaSel = null;
  $("#slots").innerHTML = HORAS.map((h, i) => {
    const ocupado = (semilla + i * 5) % 7 < 2 ||
      state.citas.some(c => c.fecha === f && c.hora === h);
    return `<button type="button" class="slot" data-h="${h}" aria-pressed="false" ${ocupado ? "disabled" : ""}>${h}</button>`;
  }).join("");
}
const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
function pintarAtajos(){
  const elegida = $("#c-fecha").value;
  $("#c-atajos").innerHTML = diasHabiles(5).map(d => {
    const iso = aISO(d);
    return `<button type="button" class="chip" data-fecha="${iso}" aria-pressed="${iso === elegida}"
              aria-label="${DIAS[d.getDay()]} ${fechaLarga(iso)}">${DIAS[d.getDay()]} ${d.getDate()}</button>`;
  }).join("");
}
$("#c-atajos").addEventListener("click", e => {
  const b = e.target.closest("[data-fecha]"); if (!b) return;
  $("#c-fecha").value = b.dataset.fecha;
  pintarSlots(); pintarAtajos();
});
$("#c-fecha").addEventListener("change", () => { pintarSlots(); pintarAtajos(); });
$("#slots").addEventListener("click", e => {
  const b = e.target.closest(".slot"); if (!b || b.disabled) return;
  $$(".slot").forEach(x => x.setAttribute("aria-pressed", x === b));
  horaSel = b.dataset.h;
});
pintarSlots();
pintarAtajos();

$("#cita-form").addEventListener("submit", e => {
  e.preventDefault();
  const err = $("#c-err");
  const sede = $("#c-sede").value, motivo = $("#c-motivo").value, fecha = $("#c-fecha").value;
  if (!sede)   return showErr(err, "Selecciona la sede a la que asistirás.", "c-sede");
  if (!motivo) return showErr(err, "Indica el motivo de la cita.", "c-motivo");
  if (!fecha)  return showErr(err, "Selecciona la fecha de la cita.", "c-fecha");
  const dia = new Date(fecha + "T12:00:00").getDay();
  if (dia === 0 || dia === 6)
    return showErr(err, "La atención presencial es de lunes a viernes. Elige otro día.", "c-fecha");
  if (!horaSel) return showErr(err, "Elige uno de los horarios disponibles.");

  showErr(err, null);
  const turno = "CT-" + String(1000 + state.citas.length * 3 + (new Date(fecha).getDate())).slice(0,4);
  state.citas.unshift({ turno, sede, motivo, fecha, hora:horaSel, exp:$("#c-exp").value });
  pintarCitas(); pintarSlots();
  $("#c-sede").value = ""; $("#c-motivo").value = ""; $("#c-exp").value = "";
  toast(`Cita ${turno} reservada`);
});

function pintarCitas(){
  $("#citas-list").innerHTML = state.citas.map(c =>
    `<article class="exp st-info">
      <div class="ancho-flexible">
        <div class="code">Turno ${esc(c.turno)}${c.exp ? " · " + esc(c.exp.split(" — ")[0]) : ""}</div>
        <div class="name">${esc(c.motivo)}</div>
        <div class="meta"><i>${esc(c.sede)}</i><i>${fechaLarga(c.fecha)}</i><i>${esc(c.hora)}</i></div>
      </div>
      <span class="pill info">Confirmada</span>
    </article>`).join("");
  $("#no-citas").hidden = state.citas.length > 0;
}

/* ============================================================
   12. CONTACTO
   ============================================================ */

$("#ct-form").addEventListener("submit", e => {
  e.preventDefault();
  const err = $("#ct-err"), ok = $("#ct-ok");
  ok.hidden = true;
  const V = id => $("#" + id).value.trim();
  if (!V("ct-nombre")) return showErr(err, "Escribe tu nombre completo.", "ct-nombre");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(V("ct-email")))
    return showErr(err, "El correo electrónico no tiene un formato válido.", "ct-email");
  if (!V("ct-tema")) return showErr(err, "Selecciona el tema de tu mensaje.", "ct-tema");
  if (V("ct-msg").length < 15) return showErr(err, "Cuéntanos un poco más; el mensaje es muy corto.", "ct-msg");
  showErr(err, null);
  const ticket = "MSG-" + Math.floor(100000 + Math.random() * 899999);
  ok.hidden = false;
  ok.lastElementChild.innerHTML =
    `<b>Mensaje enviado.</b> Tu número de seguimiento es <span class="mono">${ticket}</span>. Respondemos en un plazo de 3 días hábiles.`;
  $("#ct-msg").value = ""; $("#ct-exp").value = ""; $("#ct-tema").value = "";
});

document.addEventListener("click", async e => {
  const b = e.target.closest("[data-copy]"); if (!b) return;
  const txt = $("#" + b.dataset.copy).textContent.trim();
  try { await navigator.clipboard.writeText(txt); toast("Copiado: " + txt); }
  catch { const r = document.createRange(); r.selectNode($("#" + b.dataset.copy));
          getSelection().removeAllRanges(); getSelection().addRange(r);
          toast("Selecciona y copia con el teclado"); }
});

/* ============================================================
   13. ARRANQUE
   ============================================================ */
mostrarPanel("login");
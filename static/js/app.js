/**
 * app.js — UNIMAR · Sistema de Evaluaciones
 */

// ─── ESTADO GLOBAL ─────────────────────────────────────────────
const state = {
  usuario:          null,
  cuestionarioId:   null,
  preguntasActuales:[],
  timerInterval:    null,
  timerSegs:        0,
};
const SEGS_POR_PREGUNTA = 45;

// ─── LIMPIAR TODOS LOS FORMULARIOS ─────────────────────────────
// Se llama SIEMPRE antes de cambiar de vista para que ningún dato
// de un usuario previo quede expuesto al siguiente (UX & privacidad).
function limpiarFormularios() {
  // Login
  const le = document.getElementById("login-email");
  const lp = document.getElementById("login-password");
  const lerr = document.getElementById("login-error");
  if (le) le.value = "";
  if (lp) lp.value = "";
  if (lerr) { lerr.textContent = ""; lerr.classList.add("hidden"); }

  // Registro
  const rn  = document.getElementById("reg-name");
  const re  = document.getElementById("reg-email");
  const rp  = document.getElementById("reg-password");
  const rerr = document.getElementById("reg-error");
  if (rn) rn.value = "";
  if (re) re.value = "";
  if (rp) rp.value = "";
  if (rerr) { rerr.textContent = ""; rerr.classList.add("hidden"); }

  // Nuevo cuestionario
  const nt = document.getElementById("nq-titulo");
  const nd = document.getElementById("nq-descripcion");
  const nerr = document.getElementById("nq-error");
  if (nt) nt.value = "";
  if (nd) nd.value = "";
  if (nerr) { nerr.textContent = ""; nerr.classList.add("hidden"); }
  const preguntas = document.getElementById("nq-preguntas-list");
  if (preguntas) preguntas.innerHTML = "";
}

// ─── ROUTER ────────────────────────────────────────────────────
function mostrarVista(id) {
  limpiarFormularios();
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${id}`).classList.add("active");
}

// ─── TOAST ─────────────────────────────────────────────────────
let _toastTimer;
function toast(msg, ms = 3200) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), ms);
}

// ─── HEADER ────────────────────────────────────────────────────
function actualizarHeader(usuario) {
  const hdr = document.getElementById("header-user");
  if (!usuario) {
    hdr.classList.add("hidden");
    hdr.classList.remove("flex");
    return;
  }
  hdr.classList.remove("hidden");
  hdr.classList.add("flex");
  document.getElementById("header-name").textContent = usuario.nombre;
  document.getElementById("header-role").textContent = usuario.rol;
}

// ─── AUTH ───────────────────────────────────────────────────────
async function checkSesionActiva() {
  const r = await fetch("/auth/me").then(r => r.json()).catch(() => ({}));
  if (!r.autenticado) return;
  state.usuario = { id: r.id, rol: r.rol, nombre: "" };
  actualizarHeader(state.usuario);
  await irDashboard();
}

async function login() {
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const errEl    = document.getElementById("login-error");
  errEl.classList.add("hidden");

  const r    = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await r.json();
  if (!r.ok) {
    errEl.textContent = "Credenciales incorrectas. Verifica tu correo y contraseña.";
    errEl.classList.remove("hidden");
    return;
  }
  state.usuario = data;
  actualizarHeader(data);
  await irDashboard();
}

async function registro() {
  const nombre   = document.getElementById("reg-name").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const errEl    = document.getElementById("reg-error");
  errEl.classList.add("hidden");

  if (!nombre || !email || !password) {
    errEl.textContent = "Todos los campos son obligatorios.";
    errEl.classList.remove("hidden");
    return;
  }

  // El rol se fija en "estudiante" desde el cliente;
  // los profesores se crean exclusivamente vía seed.py / administración interna.
  const r    = await fetch("/auth/registro", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, email, password, rol: "estudiante" }),
  });
  const data = await r.json();
  if (!r.ok) {
    errEl.textContent = data.error || "No se pudo completar el registro.";
    errEl.classList.remove("hidden");
    return;
  }
  state.usuario = data;
  actualizarHeader(data);
  toast("Bienvenid@ a UNIMAR. Tu cuenta ha sido creada.");
  await irDashboard();
}

async function logout() {
  await fetch("/auth/logout", { method: "POST" });
  state.usuario = null;
  detenerTimer();
  actualizarHeader(null);
  mostrarVista("login");
}

// ─── DASHBOARD ──────────────────────────────────────────────────
async function irDashboard() {
  mostrarVista("dashboard");

  const btnNuevo = document.getElementById("btn-nuevo-quiz");
  state.usuario?.rol === "profesor"
    ? btnNuevo.classList.remove("hidden")
    : btnNuevo.classList.add("hidden");

  const container = document.getElementById("quiz-list");
  container.innerHTML = `<p class="text-sm text-slate-500 sm:col-span-2">Cargando cuestionarios…</p>`;

  const r = await fetch("/cuestionarios");
  if (r.status === 401) { mostrarVista("login"); return; }
  const lista = await r.json();

  if (!lista.length) {
    container.innerHTML = `
      <div class="glass p-8 text-center sm:col-span-2">
        <p class="text-slate-400 text-sm">No hay cuestionarios publicados aún.</p>
      </div>`;
    return;
  }

  const iconos = [
    { from:"#6366f1", to:"#a855f7" },
    { from:"#06b6d4", to:"#0891b2" },
    { from:"#10b981", to:"#059669" },
    { from:"#f59e0b", to:"#d97706" },
    { from:"#ef4444", to:"#dc2626" },
    { from:"#ec4899", to:"#db2777" },
  ];

  container.innerHTML = lista.map((q, i) => {
    const ic   = iconos[i % iconos.length];
    const init = q.titulo.trim()[0]?.toUpperCase() || "Q";
    return `
      <div class="quiz-card p-5 flex gap-4 items-start"
           onclick="iniciarQuiz(${q.id})" role="button" tabindex="0"
           onkeydown="if(event.key==='Enter')iniciarQuiz(${q.id})">
        <div class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0
                    font-display font-700 text-lg text-white"
             style="background:linear-gradient(135deg,${ic.from},${ic.to})">
          ${init}
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-600 text-sm text-slate-100 leading-snug">${q.titulo}</p>
          ${q.descripcion
            ? `<p class="text-xs text-slate-500 mt-1 truncate">${q.descripcion}</p>`
            : ""}
        </div>
        <svg class="flex-shrink-0 mt-0.5 text-slate-600" width="18" height="18"
             fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
        </svg>
      </div>`;
  }).join("");
}

// ─── QUIZ ────────────────────────────────────────────────────────
async function iniciarQuiz(id) {
  state.cuestionarioId = id;
  const r = await fetch(`/cuestionario/${id}`);
  if (!r.ok) { toast("No se pudo cargar el cuestionario. Intenta de nuevo."); return; }
  const data = await r.json();

  state.preguntasActuales = data.preguntas;
  mostrarVista("quiz");
  document.getElementById("quiz-title-bar").textContent = data.titulo;
  document.getElementById("questions-container").innerHTML =
    data.preguntas.map((p, i) => renderPregunta(p, i, data.preguntas.length)).join("");
  document.getElementById("btn-submit").disabled = false;
  iniciarTimer(data.preguntas.length * SEGS_POR_PREGUNTA);
}

function renderPregunta(pregunta, idx, total) {
  const esMultiple = pregunta.tipo === "opcion_multiple";
  const itype  = esMultiple ? "checkbox" : "radio";
  const nombre = `p-${pregunta.id}`;
  const hint   = esMultiple
    ? "Selecciona todas las opciones correctas"
    : "Selecciona una opción";

  const opciones = pregunta.opciones.map(o => `
    <label class="option-row">
      <input type="${itype}" name="${nombre}" value="${o.clave}">
      <span class="text-sm text-slate-200">${o.texto}</span>
    </label>`).join("");

  return `
    <div class="glass p-5">
      <div class="flex items-center gap-2 mb-3">
        <span class="text-xs font-700 px-2.5 py-0.5 rounded-full
                     bg-indigo-500/10 text-indigo-400">${idx + 1} / ${total}</span>
        <span class="text-xs text-slate-500">${hint}</span>
      </div>
      <p class="text-slate-100 text-[0.95rem] font-500 leading-snug mb-4">
        ${pregunta.enunciado}
      </p>
      <div class="space-y-1">${opciones}</div>
    </div>`;
}

function recolectarRespuestas() {
  const respuestas = {};
  state.preguntasActuales.forEach(p => {
    const checked = [...document.querySelectorAll(`input[name="p-${p.id}"]:checked`)];
    if (!checked.length) return;
    respuestas[p.id] = p.tipo === "opcion_multiple"
      ? checked.map(i => i.value)
      : checked[0].value;
  });
  return respuestas;
}

async function enviarRespuestas() {
  detenerTimer();
  const btn = document.getElementById("btn-submit");
  btn.disabled = true;
  btn.textContent = "Calificando…";

  const r    = await fetch(`/evaluar/${state.cuestionarioId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ respuestas: recolectarRespuestas() }),
  });
  const data = await r.json();
  btn.textContent = "Enviar respuestas";

  if (!r.ok) {
    toast(`Error: ${data.error}`);
    btn.disabled = false;
    return;
  }
  mostrarResultados(data);
}

// ─── TEMPORIZADOR ────────────────────────────────────────────────
function iniciarTimer(totalSegs) {
  detenerTimer();
  state.timerSegs = totalSegs;
  const label = document.getElementById("timer-label");
  const fill  = document.getElementById("timer-bar-fill");

  function tick() {
    const m = Math.floor(state.timerSegs / 60).toString().padStart(2, "0");
    const s = (state.timerSegs % 60).toString().padStart(2, "0");
    label.textContent = `${m}:${s}`;
    fill.style.width = `${(state.timerSegs / totalSegs) * 100}%`;
    fill.classList.toggle("urgent", state.timerSegs / totalSegs < 0.2);
    if (state.timerSegs <= 0) { detenerTimer(); enviarRespuestas(); return; }
    state.timerSegs--;
  }
  tick();
  state.timerInterval = setInterval(tick, 1000);
}

function detenerTimer() {
  clearInterval(state.timerInterval);
  state.timerInterval = null;
}

// ─── RESULTADOS ──────────────────────────────────────────────────
function mostrarResultados(resultado) {
  mostrarVista("results");

  const pct = Math.round(resultado.porcentaje);
  document.getElementById("result-percent").textContent = `${pct}%`;
  document.getElementById("result-summary").textContent =
    `Puntaje: ${resultado.puntaje_total} / ${resultado.puntaje_maximo} puntos`;

  const msg = document.getElementById("result-msg");
  if      (pct >= 90) { msg.textContent = "Excelente desempeño ✦";  msg.style.color = "#34d399"; }
  else if (pct >= 70) { msg.textContent = "Buen resultado ✓";        msg.style.color = "#a5b4fc"; }
  else if (pct >= 50) { msg.textContent = "Puedes mejorar";           msg.style.color = "#fbbf24"; }
  else                { msg.textContent = "Requiere más preparación"; msg.style.color = "#f87171"; }

  // Animar anillo
  const ring   = document.getElementById("score-ring");
  const offset = 565 * (1 - pct / 100);
  ring.style.setProperty("--offset", offset);
  ring.classList.remove("drawn");
  requestAnimationFrame(() => requestAnimationFrame(() => ring.classList.add("drawn")));

  const enunciados = Object.fromEntries(
    state.preguntasActuales.map(p => [p.id, p.enunciado])
  );

  document.getElementById("feedback-list").innerHTML = Object.entries(resultado.detalle)
    .map(([id, r]) => {
      const ok  = r.es_correcta;
      const col = ok ? "#34d399" : "#f87171";
      const bg  = ok ? "rgba(16,185,129,0.06)"  : "rgba(239,68,68,0.06)";
      const bdr = ok ? "rgba(16,185,129,0.18)"  : "rgba(239,68,68,0.18)";
      return `
        <div class="flex gap-3 items-start p-4 rounded-xl border"
             style="background:${bg};border-color:${bdr}">
          <span class="font-700 text-base flex-shrink-0" style="color:${col}">
            ${ok ? "✓" : "✗"}
          </span>
          <div>
            <p class="text-sm font-500 text-slate-200">
              ${enunciados[id] ?? `Pregunta ${id}`}
            </p>
            <p class="text-xs mt-1 text-slate-500">
              ${r.retroalimentacion} ·
              <span style="color:${col}">${r.puntaje} pts</span>
            </p>
          </div>
        </div>`;
    }).join("");
}

// ─── HISTORIAL ───────────────────────────────────────────────────
async function irHistorial() {
  mostrarVista("historial");
  const container = document.getElementById("historial-list");
  container.innerHTML = `<p class="text-sm text-slate-500">Cargando historial…</p>`;

  const lista = await fetch("/historial").then(r => r.json());
  if (!lista.length) {
    container.innerHTML = `
      <div class="glass p-8 text-center">
        <p class="text-slate-400 text-sm">No hay evaluaciones registradas aún.</p>
      </div>`;
    return;
  }

  const esProfesor = state.usuario?.rol === "profesor";
  container.innerHTML = lista.map(item => {
    const pct   = Math.round(item.porcentaje);
    const cls   = pct >= 70 ? "badge-green" : pct >= 40 ? "badge-amber" : "badge-red";
    const fecha = new Date(item.fecha)
      .toLocaleString("es", { dateStyle: "medium", timeStyle: "short" });
    return `
      <div class="glass p-4 flex items-center gap-4">
        <div class="flex-1 min-w-0">
          <p class="text-sm font-600 text-slate-100 truncate">${item.cuestionario_titulo}</p>
          ${esProfesor
            ? `<p class="text-xs text-indigo-400 mt-0.5">Estudiante: ${item.usuario_nombre}</p>`
            : ""}
          <p class="text-xs text-slate-600 mt-0.5">${fecha}</p>
        </div>
        <div class="text-right flex-shrink-0">
          <span class="badge ${cls}">${pct}%</span>
          <p class="text-xs text-slate-600 mt-1">
            ${item.puntaje_total}/${item.puntaje_maximo} pts
          </p>
        </div>
      </div>`;
  }).join("");
}

// ─── NUEVO CUESTIONARIO (solo profesor) ──────────────────────────
let nqCounter = 0;

function irNuevoQuiz() {
  nqCounter = 0;
  mostrarVista("nuevo-quiz");
  agregarPreguntaForm();
}

function agregarPreguntaForm() {
  nqCounter++;
  const n   = nqCounter;
  const div = document.createElement("div");
  div.id        = `nqp-${n}`;
  div.className = "glass p-5 space-y-4";
  div.innerHTML = `
    <div class="flex justify-between items-center">
      <span class="text-xs font-700 uppercase tracking-wide text-slate-400">
        Pregunta ${n}
      </span>
      <button onclick="document.getElementById('nqp-${n}').remove()"
              class="btn btn-danger text-xs px-2.5 py-1">✕ Eliminar</button>
    </div>
    <div>
      <label class="field-label">Enunciado</label>
      <input class="field text-sm nq-enunciado" type="text"
             placeholder="Escribe aquí el enunciado de la pregunta">
    </div>
    <div class="flex gap-3">
      <div class="flex-1">
        <label class="field-label">Tipo de pregunta</label>
        <select class="field text-sm nq-tipo" onchange="actualizarOpcionesForm(${n})">
          <option value="opcion_unica">Opción única</option>
          <option value="verdadero_falso">Verdadero / Falso</option>
          <option value="opcion_multiple">Opción múltiple</option>
        </select>
      </div>
      <div style="width:90px">
        <label class="field-label">Puntos</label>
        <input class="field text-sm nq-puntos" type="number" min="0.5" step="0.5" value="1">
      </div>
    </div>
    <div id="nq-opciones-${n}" class="space-y-2"></div>
    <button id="nq-add-opcion-${n}" onclick="agregarOpcionForm(${n})"
            class="btn btn-ghost text-xs px-0 text-indigo-400 hover:text-indigo-300">
      + Agregar opción
    </button>`;
  document.getElementById("nq-preguntas-list").appendChild(div);
  actualizarOpcionesForm(n);
}

function actualizarOpcionesForm(n) {
  const tipo   = document.querySelector(`#nqp-${n} .nq-tipo`).value;
  const cont   = document.getElementById(`nq-opciones-${n}`);
  const addBtn = document.getElementById(`nq-add-opcion-${n}`);
  cont.innerHTML = "";

  if (tipo === "verdadero_falso") {
    addBtn.style.display = "none";
    [["v","Verdadero"], ["f","Falso"]].forEach(([c, t]) =>
      cont.insertAdjacentHTML("beforeend", opcionHTML(n, c, t, "radio", false))
    );
  } else {
    addBtn.style.display = "";
    const itype = tipo === "opcion_multiple" ? "checkbox" : "radio";
    ["a","b"].forEach(c =>
      cont.insertAdjacentHTML("beforeend", opcionHTML(n, c, "", itype, true))
    );
  }
}

function opcionHTML(pn, clave, textoVal, inputType, editable) {
  return `
    <div class="flex items-center gap-2">
      <input type="${inputType}" name="nq-correct-${pn}" value="${clave}"
             style="accent-color:#6366f1;width:1rem;height:1rem;flex-shrink:0">
      <input type="hidden" class="nq-clave" value="${clave}">
      <input class="field text-sm flex-1 nq-opcion-texto" type="text"
             placeholder="Texto de la opción" value="${textoVal}"
             ${editable ? "" : "readonly"}>
      ${editable
        ? `<button onclick="this.parentElement.remove()"
                   class="btn btn-danger text-xs px-2.5 py-1 flex-shrink-0">✕</button>`
        : ""}
    </div>`;
}

function agregarOpcionForm(n) {
  const cont   = document.getElementById(`nq-opciones-${n}`);
  const tipo   = document.querySelector(`#nqp-${n} .nq-tipo`).value;
  const itype  = tipo === "opcion_multiple" ? "checkbox" : "radio";
  const claves = ["a","b","c","d","e","f"];
  const usadas = [...cont.querySelectorAll(".nq-clave")].map(e => e.value);
  const sig    = claves.find(c => !usadas.includes(c));
  if (!sig) { toast("Máximo 6 opciones por pregunta."); return; }
  cont.insertAdjacentHTML("beforeend", opcionHTML(n, sig, "", itype, true));
}

async function guardarNuevoQuiz() {
  const titulo      = document.getElementById("nq-titulo").value.trim();
  const descripcion = document.getElementById("nq-descripcion").value.trim();
  const errEl       = document.getElementById("nq-error");
  errEl.classList.add("hidden");

  if (!titulo) {
    errEl.textContent = "El título del cuestionario es obligatorio.";
    errEl.classList.remove("hidden");
    return;
  }

  const bloques = document.querySelectorAll("#nq-preguntas-list > div");
  if (!bloques.length) {
    errEl.textContent = "Agrega al menos una pregunta al cuestionario.";
    errEl.classList.remove("hidden");
    return;
  }

  const preguntas = [];
  for (const bloque of bloques) {
    const tipo      = bloque.querySelector(".nq-tipo").value;
    const enunciado = bloque.querySelector(".nq-enunciado").value.trim();
    const puntos    = parseFloat(bloque.querySelector(".nq-puntos").value) || 1;

    if (!enunciado) {
      errEl.textContent = "Todos los enunciados son obligatorios.";
      errEl.classList.remove("hidden");
      return;
    }

    const nId    = bloque.id.split("-")[1];
    const opRows = [...bloque.querySelectorAll(`#nq-opciones-${nId} > div`)];
    const opciones = opRows.map(row => ({
      clave:       row.querySelector(".nq-clave").value,
      texto:       row.querySelector(".nq-opcion-texto").value.trim(),
      es_correcta: row.querySelector(`input[type="radio"],input[type="checkbox"]`)?.checked ?? false,
    }));

    if (opciones.some(o => !o.texto)) {
      errEl.textContent = "El texto de todas las opciones es obligatorio.";
      errEl.classList.remove("hidden");
      return;
    }
    preguntas.push({ tipo, enunciado, puntos, opciones });
  }

  const btn = document.getElementById("btn-guardar-quiz");
  btn.disabled = true;
  btn.textContent = "Guardando…";

  const r    = await fetch("/cuestionarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ titulo, descripcion, preguntas }),
  });
  const data = await r.json();
  btn.disabled = false;
  btn.textContent = "Guardar y publicar cuestionario";

  if (!r.ok) {
    errEl.textContent = data.error;
    errEl.classList.remove("hidden");
    return;
  }
  toast(`Cuestionario "${titulo}" publicado correctamente.`);
  await irDashboard();
}

// ─── EVENTOS ─────────────────────────────────────────────────────
document.getElementById("btn-login").onclick     = login;
document.getElementById("btn-register").onclick  = registro;
document.getElementById("btn-logout").onclick    = logout;

document.getElementById("btn-go-register").onclick = () => mostrarVista("register");
document.getElementById("btn-go-login").onclick    = () => mostrarVista("login");

document.getElementById("login-password").onkeydown =
  e => { if (e.key === "Enter") login(); };
document.getElementById("login-email").onkeydown    =
  e => { if (e.key === "Enter") document.getElementById("login-password").focus(); };

document.getElementById("btn-submit").onclick        = enviarRespuestas;
document.getElementById("btn-retry").onclick         = () => iniciarQuiz(state.cuestionarioId);
document.getElementById("btn-back-to-dash").onclick  = irDashboard;

document.getElementById("btn-historial").onclick          = irHistorial;
document.getElementById("btn-back-from-historial").onclick = irDashboard;

document.getElementById("btn-nuevo-quiz").onclick       = irNuevoQuiz;
document.getElementById("btn-back-from-nuevo").onclick  = irDashboard;
document.getElementById("btn-add-pregunta").onclick     = agregarPreguntaForm;
document.getElementById("btn-guardar-quiz").onclick     = guardarNuevoQuiz;

// ─── ARRANQUE ────────────────────────────────────────────────────
checkSesionActiva();

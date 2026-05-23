const TASK_TYPES = [
  "classification",
  "simple_extraction",
  "high_volume_extraction",
  "coding_debug",
  "workflow_debug",
  "product_design",
  "architecture",
  "visual_analysis",
  "long_document",
  "google_workspace_processing",
  "complex_reasoning",
  "custom_tool_agent",
  "realtime_voice",
  "text_to_speech",
  "image_generation",
  "final_validation",
];

const state = {
  apiBase: localStorage.getItem("ants_api_base") || window.location.origin,
  apiKey: localStorage.getItem("ants_api_key") || "",
};

const $ = (id) => document.getElementById(id);

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function setOutput(id, value) {
  $(id).textContent = typeof value === "string" ? value : pretty(value);
}

function headers() {
  const result = { "Content-Type": "application/json" };
  if (state.apiKey) {
    result["X-ANTS-API-Key"] = state.apiKey;
  }
  return result;
}

async function request(path, options = {}) {
  const response = await fetch(`${state.apiBase}${path}`, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  const text = await response.text();
  let payload = text;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { raw: text };
  }
  if (!response.ok) {
    throw new Error(pretty({ status: response.status, payload }));
  }
  return payload;
}

function renderTable(targetId, columns, rows) {
  if (!rows.length) {
    $(targetId).innerHTML = "<p>No records returned.</p>";
    return;
  }
  const head = columns.map((column) => `<th>${column.label}</th>`).join("");
  const body = rows
    .map((row) => {
      const cells = columns.map((column) => `<td>${column.render(row)}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  $(targetId).innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function pill(value, okWhen = true) {
  const status = Boolean(value) === okWhen ? "ok" : "warn";
  return `<span class="pill ${status}">${String(value)}</span>`;
}

async function refreshHealth() {
  setOutput("health-output", "Loading...");
  setOutput("health-output", await request("/health", { headers: {} }));
}

async function refreshDependencies() {
  setOutput("dependencies-output", "Loading...");
  setOutput("dependencies-output", await request("/dependencies"));
}

async function refreshCredentials() {
  setOutput("credentials-output", "Loading...");
  setOutput("credentials-output", await request("/executors/credentials/status"));
}

async function refreshModels() {
  setOutput("models-output", "Loading...");
  const payload = await request("/models");
  const models = Object.entries(payload.models || {}).map(([name, config]) => ({ name, ...config }));
  renderTable("models-table", [
    { label: "Model", render: (row) => row.name },
    { label: "Provider", render: (row) => row.provider || "-" },
    { label: "Enabled", render: (row) => pill(row.enabled ?? row.available, true) },
    { label: "Executable", render: (row) => pill(row.execution_enabled ?? true, true) },
    { label: "Fallback", render: (row) => row.fallback || "-" },
  ], models);
  setOutput("models-output", payload);
}

async function refreshExecutors() {
  setOutput("executors-output", "Loading...");
  const payload = await request("/executors");
  renderTable("executors-table", [
    { label: "Executor", render: (row) => row.name },
    { label: "Enabled", render: (row) => pill(row.enabled, true) },
    { label: "Role", render: (row) => row.role },
    { label: "Mode", render: (row) => row.execution_mode },
    { label: "Shell", render: (row) => pill(row.allow_shell, true) },
    { label: "Notes", render: (row) => row.notes || "-" },
  ], payload.executors || []);
  setOutput("executors-output", payload);
}

async function refreshSessions() {
  setOutput("sessions-output", "Loading...");
  const payload = await request("/executors/sessions");
  renderTable("sessions-table", [
    { label: "Executor", render: (row) => row.executor },
    { label: "Label", render: (row) => row.label },
    { label: "Status", render: (row) => `<span class="pill">${row.status}</span>` },
    { label: "Storage", render: (row) => row.credential_storage },
    { label: "Reason", render: (row) => row.last_status_reason },
  ], payload.sessions || []);
  setOutput("sessions-output", payload);
}

async function runPreflight() {
  setOutput("preflight-output", "Running...");
  const payload = await request("/preflight", {
    method: "POST",
    body: JSON.stringify({
      task_id: $("task-id").value,
      task_type: $("task-type").value,
      user_request: $("user-request").value,
      context: {},
      budget: {},
      requested_context_scope: $("context-scope").value,
      explicitly_authorized: $("explicitly-authorized").checked,
      model: "auto",
    }),
  });
  setOutput("preflight-output", payload);
}

async function runSmoke() {
  setOutput("smoke-output", "Running...");
  const payload = await request("/executors/smoke-test", {
    method: "POST",
    body: JSON.stringify({
      executor: $("smoke-executor").value,
      mode: $("smoke-mode").value,
      timeout_seconds: Number($("smoke-timeout").value),
    }),
  });
  setOutput("smoke-output", payload);
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      $(`tab-${button.dataset.tab}`).classList.add("active");
    });
  });
}

function bindActions() {
  const actionMap = {
    health: refreshHealth,
    dependencies: refreshDependencies,
    credentials: refreshCredentials,
    models: refreshModels,
    executors: refreshExecutors,
    sessions: refreshSessions,
  };

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await actionMap[button.dataset.action]();
      } catch (error) {
        setOutput(`${button.dataset.action}-output`, error.message);
      }
    });
  });

  $("run-preflight").addEventListener("click", () => runPreflight().catch((error) => setOutput("preflight-output", error.message)));
  $("run-smoke").addEventListener("click", () => runSmoke().catch((error) => setOutput("smoke-output", error.message)));
}

function initSettings() {
  $("api-base").value = state.apiBase;
  $("api-key").value = state.apiKey;
  $("settings-form").addEventListener("submit", (event) => {
    event.preventDefault();
    state.apiBase = $("api-base").value.replace(/\/$/, "") || window.location.origin;
    state.apiKey = $("api-key").value.trim();
    localStorage.setItem("ants_api_base", state.apiBase);
    localStorage.setItem("ants_api_key", state.apiKey);
    setOutput("health-output", { saved: true, apiBase: state.apiBase, keyConfigured: Boolean(state.apiKey) });
  });
}

function initTaskTypes() {
  $("task-type").innerHTML = TASK_TYPES.map((type) => `<option value="${type}">${type}</option>`).join("");
  $("task-type").value = "coding_debug";
}

initSettings();
initTaskTypes();
bindTabs();
bindActions();
refreshHealth().catch((error) => setOutput("health-output", error.message));

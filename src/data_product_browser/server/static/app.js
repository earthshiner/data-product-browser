"use strict";

// Data Product Browser — step 1 frontend.
// Fetches a DataProduct snapshot from the API and renders a navigable
// module/entity tree with a per-entity schema detail pane. Deterministic:
// everything shown is read straight from the metadata, no AI in the loop.

const state = {
  product: null,
  data: null, // the DataProduct object
  activeEntity: null, // entity_metadata_id
  activeTab: "schema",
  view: "ops", // "ops" | "entity"
};

const el = (id) => document.getElementById(id);

async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      detail = (await resp.json()).detail || detail;
    } catch (_) {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return resp.json();
}

function setStatus(msg) {
  el("status").textContent = msg || "";
}

async function loadProductList() {
  const select = el("product-select");
  try {
    const { products } = await fetchJSON("/api/products");
    if (!products.length) {
      select.innerHTML = '<option value="">No products found</option>';
      return;
    }
    select.innerHTML =
      '<option value="">Select a product…</option>' +
      products
        .map((p) => {
          const v = p.product_version ? ` (v${p.product_version})` : "";
          return `<option value="${p.product_name}">${p.product_name}${v}</option>`;
        })
        .join("");
  } catch (err) {
    select.innerHTML = '<option value="">Error loading products</option>';
    setStatus("⚠ " + err.message);
  }
}

async function loadProduct(name) {
  if (!name) return;
  state.product = name;
  state.activeEntity = null;
  setStatus("Loading " + name + "…");
  el("tree").innerHTML = "";
  el("detail").innerHTML = '<div class="empty">Loading metadata…</div>';
  try {
    const { data_product, warnings } = await fetchJSON(
      "/api/products/" + encodeURIComponent(name),
    );
    state.data = data_product;
    state.warnings = warnings || [];
    state.view = "ops";
    state.activeEntity = null;
    renderTree();
    showOps();
    const counts = data_product;
    setStatus(
      `${counts.entities.length} entities · ${counts.columns.length} columns · ` +
        `${counts.recipes.length} recipes`,
    );
  } catch (err) {
    el("detail").innerHTML = `<div class="banner">Could not load "${name}":\n\n${err.message}</div>`;
    setStatus("");
  }
}

function renderWarnings() {
  if (!state.warnings || !state.warnings.length) return;
  const banner = document.createElement("div");
  banner.className = "banner";
  banner.textContent = state.warnings.join("\n\n");
  el("detail").prepend(banner);
}

// Group entities by their owning module for the navigation tree.
function entitiesByModule() {
  const groups = new Map();
  for (const e of state.data.entities) {
    const key = e.module_name || "Other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  }
  return groups;
}

function renderTree() {
  const filter = el("filter").value.trim().toLowerCase();
  const tree = el("tree");
  tree.innerHTML = "";

  const ops = document.createElement("div");
  ops.className = "nav-special" + (state.view === "ops" ? " active" : "");
  ops.innerHTML = "<span>📊</span><span>Operations</span>";
  ops.onclick = () => {
    state.view = "ops";
    state.activeEntity = null;
    renderTree();
    showOps();
    el("detail").scrollTop = 0;
  };
  tree.appendChild(ops);

  const erd = document.createElement("div");
  erd.className = "nav-special" + (state.view === "erd" ? " active" : "");
  erd.innerHTML = "<span>🗺</span><span>Entity map (ERD)</span>";
  erd.onclick = () => {
    state.view = "erd";
    state.activeEntity = null;
    renderTree();
    showErd();
    el("detail").scrollTop = 0;
  };
  tree.appendChild(erd);

  const cookbook = document.createElement("div");
  cookbook.className = "nav-special" + (state.view === "cookbook" ? " active" : "");
  const recipeCount = (state.data.recipes || []).length;
  cookbook.innerHTML = `<span>📖</span><span>Cookbook</span><span class="count">${recipeCount}</span>`;
  cookbook.onclick = () => {
    state.view = "cookbook";
    state.activeEntity = null;
    renderTree();
    showCookbook();
    el("detail").scrollTop = 0;
  };
  tree.appendChild(cookbook);

  for (const [moduleName, entities] of entitiesByModule()) {
    const visible = entities.filter(
      (e) => !filter || e.entity_name.toLowerCase().includes(filter),
    );
    if (!visible.length) continue;

    const head = document.createElement("div");
    head.className = "module-name";
    head.textContent = moduleName;
    tree.appendChild(head);

    for (const e of visible) {
      const item = document.createElement("div");
      item.className = "entity" + (e.entity_metadata_id === state.activeEntity ? " active" : "");
      const cols = columnsFor(e).length;
      item.innerHTML = `<span>${e.entity_name}</span><span class="count">${cols}</span>`;
      item.onclick = () => selectEntity(e.entity_metadata_id);
      tree.appendChild(item);
    }
  }
}

function columnsFor(entity) {
  return state.data.columns.filter(
    (c) => c.database_name === entity.database_name && c.table_name === entity.table_name,
  );
}

function selectEntity(key) {
  state.activeEntity = key;
  state.view = "entity";
  renderTree();
  const entity = state.data.entities.find((e) => e.entity_metadata_id === key);
  if (!entity) return;
  renderEntity(entity);
  el("detail").scrollTop = 0;
}

function esc(s) {
  return (s ?? "").toString().replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
}

// --- cross-link helpers ------------------------------------------------------

const sameTable = (db, table, e) =>
  e.database_name === db && (e.table_name || "").toLowerCase() === (table || "").toLowerCase();

function findEntityByTable(db, table) {
  return state.data.entities.find((e) => sameTable(db, table, e)) || null;
}

// Jump to the entity backing a given database.table, if one exists.
function jump(db, table) {
  const target = findEntityByTable(db, table);
  if (target) selectEntity(target.entity_metadata_id);
}
window.__jump = jump; // referenced by inline onclick handlers

// Render a database.table reference as a clickable link when an entity exists.
function tableLink(db, table) {
  const fq = `${esc(db)}.${esc(table)}`;
  if (findEntityByTable(db, table)) {
    return `<a class="jump" onclick="window.__jump('${esc(db)}','${esc(table)}')"><code>${fq}</code></a>`;
  }
  return `<code>${fq}</code>`;
}

function relationshipsFor(entity) {
  const out = [];
  for (const r of state.data.relationships) {
    if (sameTable(r.source_database, r.source_table, entity)) {
      out.push({ dir: "→", thisCol: r.source_column, db: r.target_database, table: r.target_table, col: r.target_column, r });
    } else if (sameTable(r.target_database, r.target_table, entity)) {
      out.push({ dir: "←", thisCol: r.target_column, db: r.source_database, table: r.source_table, col: r.source_column, r });
    }
  }
  return out;
}

function glossaryFor(entity) {
  const t = (entity.table_name || "").toLowerCase();
  return state.data.glossary.filter((g) => (g.related_table || "").toLowerCase() === t);
}

function decisionsFor(entity) {
  const t = (entity.table_name || "").toLowerCase();
  return state.data.decisions.filter((d) => (d.affects_table || "").toLowerCase() === t);
}

// Views exposing this entity's base table (1:M), primary first.
function viewsFor(entity) {
  const db = entity.database_name;
  const t = (entity.table_name || "").toLowerCase();
  return (state.data.view_metadata || [])
    .filter((v) => v.base_database === db && (v.base_table || "").toLowerCase() === t)
    .sort((a, b) => (b.is_primary || 0) - (a.is_primary || 0));
}

// --- detail pane -------------------------------------------------------------

function renderEntity(entity) {
  const counts = {
    schema: columnsFor(entity).length,
    views: viewsFor(entity).length,
    relationships: relationshipsFor(entity).length,
    glossary: glossaryFor(entity).length,
    decisions: decisionsFor(entity).length,
  };
  const tab = (id, label) =>
    `<div class="tab ${state.activeTab === id ? "active" : ""}" data-tab="${id}">
       ${label}<span class="badge">${counts[id]}</span></div>`;

  el("detail").innerHTML = `
    <h2>${esc(entity.entity_name)}</h2>
    <p class="sub">${esc(entity.entity_description) || ""}</p>
    <dl class="meta-grid">
      <dt>Object</dt><dd><code>${esc(entity.database_name)}.${esc(entity.table_name)}</code></dd>
      <dt>Module</dt><dd>${esc(entity.module_name)}</dd>
      <dt>View</dt><dd>${entity.view_name ? `<code>${esc(entity.view_name)}</code>` : "—"}</dd>
      <dt>Natural key</dt><dd><code>${esc(entity.natural_key_column) || "—"}</code></dd>
      <dt>Temporal pattern</dt><dd>${esc(entity.temporal_pattern) || "—"}</dd>
      <dt>Industry standard</dt><dd>${esc(entity.industry_standard) || "—"}</dd>
    </dl>
    <div class="tabs">
      ${tab("schema", "Schema")}${tab("views", "Views")}${tab("relationships", "Relationships")}
      ${tab("glossary", "Glossary")}${tab("decisions", "Decisions")}
    </div>
    <div id="tab-body"></div>`;

  el("detail")
    .querySelectorAll(".tab")
    .forEach((t) =>
      t.addEventListener("click", () => {
        state.activeTab = t.dataset.tab;
        renderEntity(entity);
      }),
    );
  renderTabBody(entity);
}

function renderTabBody(entity) {
  const body = el("tab-body");
  const empty = (msg) => `<div class="empty">${msg}</div>`;
  if (state.activeTab === "schema") body.innerHTML = schemaHTML(entity);
  else if (state.activeTab === "views") body.innerHTML = viewsHTML(entity) || empty("No views catalogued for this table.");
  else if (state.activeTab === "relationships") body.innerHTML = relationshipsHTML(entity) || empty("No relationships defined.");
  else if (state.activeTab === "glossary") body.innerHTML = glossaryHTML(entity) || empty("No glossary terms reference this entity.");
  else if (state.activeTab === "decisions") body.innerHTML = decisionsHTML(entity) || empty("No design decisions affect this entity.");
}

function viewsHTML(entity) {
  const views = viewsFor(entity);
  if (!views.length) return "";
  const rows = views
    .map(
      (v) => `<tr>
        <td class="col-name">${esc(v.view_name)}${v.is_primary ? '<span class="tag req">PRIMARY</span>' : ""}</td>
        <td><code>${esc(v.view_database)}</code></td>
        <td>${v.view_type ? `<span class="pill">${esc(v.view_type)}</span>` : ""}</td>
        <td class="desc">${esc(v.view_purpose) || ""}</td>
      </tr>`,
    )
    .join("");
  return `<table>
      <thead><tr><th>View</th><th>Database</th><th>Type</th><th>Purpose</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
}

function schemaHTML(entity) {
  const rows = columnsFor(entity)
    .map((c) => {
      const tags =
        (c.is_pii ? '<span class="tag pii">PII</span>' : "") +
        (c.is_sensitive ? '<span class="tag pii">SENSITIVE</span>' : "") +
        (c.is_required ? '<span class="tag req">REQUIRED</span>' : "");
      return `<tr>
        <td class="col-name">${esc(c.column_name)}${tags}</td>
        <td><code>${esc(c.data_type) || "—"}</code></td>
        <td class="desc">${esc(c.business_description) || ""}</td>
        <td class="desc">${esc(c.data_classification) || ""}</td>
      </tr>`;
    })
    .join("");
  return `<table>
      <thead><tr><th>Column</th><th>Type</th><th>Description</th><th>Classification</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="4" class="desc">No column metadata.</td></tr>'}</tbody>
    </table>`;
}

function relationshipsHTML(entity) {
  const rels = relationshipsFor(entity);
  if (!rels.length) return "";
  return rels
    .map(
      (x) => `<div class="card">
        <h4><code>${esc(x.thisCol)}</code> ${x.dir} ${tableLink(x.db, x.table)}.<code>${esc(x.col)}</code></h4>
        <div>
          ${x.r.relationship_type ? `<span class="pill">${esc(x.r.relationship_type)}</span>` : ""}
          ${x.r.cardinality ? `<span class="pill">${esc(x.r.cardinality)}</span>` : ""}
          ${x.r.is_mandatory ? '<span class="pill">mandatory</span>' : ""}
        </div>
        ${x.r.relationship_meaning ? `<p class="desc">${esc(x.r.relationship_meaning)}</p>` : ""}
      </div>`,
    )
    .join("");
}

function glossaryHTML(entity) {
  const terms = glossaryFor(entity);
  if (!terms.length) return "";
  return terms
    .map(
      (g) => `<div class="card">
        <h4>${esc(g.term)} <span class="pill">${esc(g.term_category)}</span></h4>
        <p class="desc">${esc(g.definition)}</p>
        ${g.business_context ? `<p class="desc"><em>${esc(g.business_context)}</em></p>` : ""}
        ${g.related_column ? `<div><span class="pill">column</span><code>${esc(g.related_column)}</code></div>` : ""}
      </div>`,
    )
    .join("");
}

function decisionsHTML(entity) {
  const decisions = decisionsFor(entity);
  if (!decisions.length) return "";
  return decisions
    .map(
      (d) => `<div class="card">
        <h4>${esc(d.decision_title)}
          <span class="pill">${esc(d.decision_status)}</span>
          <span class="pill">${esc(d.decision_category)}</span></h4>
        ${d.decision_description ? `<p class="desc">${esc(d.decision_description)}</p>` : ""}
        ${d.rationale ? `<p class="desc"><strong>Rationale:</strong> ${esc(d.rationale)}</p>` : ""}
        ${d.consequences ? `<p class="desc"><strong>Consequences:</strong> ${esc(d.consequences)}</p>` : ""}
      </div>`,
    )
    .join("");
}

// --- operations dashboard ----------------------------------------------------

const MAX_ROWS = 50; // cap long observability tables

function fmtNum(n) {
  return n == null ? "—" : Number(n).toLocaleString();
}

function fmtDate(s) {
  if (!s) return "—";
  return String(s).replace("T", " ").slice(0, 16);
}

// Human-friendly age between an ISO timestamp and the snapshot's generated time.
function ago(s, now) {
  if (!s) return "—";
  const then = new Date(s).getTime();
  const ms = now - then;
  if (isNaN(ms)) return "—";
  const h = ms / 3.6e6;
  if (h < 1) return Math.max(0, Math.round(h * 60)) + "m ago";
  if (h < 48) return Math.round(h) + "h ago";
  return Math.round(h / 24) + "d ago";
}

const isFailed = (status) => /fail|error/i.test(status || "");
const isSuccess = (status) => /success|ok|positive|accept|complete/i.test(status || "");

// --- inline SVG charts (zero dependencies) ----------------------------------

function sparkline(values, { w = 200, h = 40, stroke = "var(--accent)" } = {}) {
  if (!values.length) return "";
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const step = values.length > 1 ? w / (values.length - 1) : 0;
  const pts = values
    .map((v, i) => `${(i * step).toFixed(1)},${(h - ((v - min) / span) * (h - 6) - 3).toFixed(1)}`)
    .join(" ");
  return `<svg class="chart" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <polyline fill="none" stroke="${stroke}" stroke-width="1.5" points="${pts}" /></svg>`;
}

function barChart(bars, { w = 260, h = 64 } = {}) {
  if (!bars.length) return "";
  const max = Math.max(...bars.map((b) => b.value), 1);
  const bw = w / bars.length;
  const rects = bars
    .map((b, i) => {
      const bh = b.value > 0 ? Math.max(1, (b.value / max) * (h - 4)) : 0;
      const x = i * bw;
      const fill = b.bad ? "var(--pii)" : "var(--accent)";
      return `<rect x="${(x + 0.5).toFixed(1)}" y="${(h - bh).toFixed(1)}" width="${Math.max(1, bw - 1).toFixed(1)}" height="${bh.toFixed(1)}" fill="${fill}"><title>${esc(b.label)}: ${b.value}</title></rect>`;
    })
    .join("");
  return `<svg class="chart" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${rects}</svg>`;
}

// Bucket items into the last `days` calendar days by an ISO timestamp field.
function countByDay(items, field, now, days = 14) {
  const dayMs = 86400000;
  const end = new Date(now);
  end.setUTCHours(0, 0, 0, 0);
  const buckets = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(end.getTime() - i * dayMs);
    buckets.push({ key: d.toISOString().slice(0, 10), label: d.toISOString().slice(5, 10), value: 0 });
  }
  const index = new Map(buckets.map((b) => [b.key, b]));
  for (const it of items) {
    const v = it[field];
    if (!v) continue;
    const b = index.get(String(v).slice(0, 10));
    if (b) b.value += 1;
  }
  return buckets;
}

// Daily quality pass-rate (%) over the window, for a trend sparkline.
function dailyPassRate(metrics, now, days = 14) {
  const buckets = countByDay(metrics, "measured_dts", now, days).map((b) => ({ ...b, pass: 0, total: 0 }));
  const index = new Map(buckets.map((b) => [b.key, b]));
  for (const m of metrics) {
    if (m.is_threshold_met == null || !m.measured_dts) continue;
    const b = index.get(String(m.measured_dts).slice(0, 10));
    if (!b) continue;
    b.total += 1;
    if (m.is_threshold_met) b.pass += 1;
  }
  return buckets.map((b) => (b.total ? Math.round((b.pass / b.total) * 100) : 0));
}

function chartCard(title, svg, caption) {
  return `<div class="chart-card">
    <div class="chart-title">${esc(title)}</div>
    ${svg || '<div class="desc">No data.</div>'}
    ${caption ? `<div class="chart-caption">${caption}</div>` : ""}
  </div>`;
}

function showOps() {
  const d = state.data;
  const now = new Date(d.generated_dts).getTime();

  // is_threshold_met === 0 means the metric failed its threshold.
  const qScored = d.quality_metrics.filter((m) => m.is_threshold_met != null);
  const qPass = qScored.filter((m) => m.is_threshold_met).length;
  const qRate = qScored.length ? Math.round((qPass / qScored.length) * 100) : null;
  // Run telemetry now comes from lineage_run (Observability); data_lineage is definitional.
  const runs = (d.lineage_run || [])
    .filter((r) => r.run_dts)
    .sort((a, b) => (a.run_dts < b.run_dts ? 1 : -1));
  const failedRuns = runs.filter((r) => isFailed(r.run_status)).length;
  const lastRun = runs[0];

  const outcomes = d.agent_outcomes || [];
  const scored = outcomes.filter((o) => o.outcome_status);
  const agentOk = scored.filter((o) => isSuccess(o.outcome_status)).length;
  const agentRate = scored.length ? Math.round((agentOk / scored.length) * 100) : null;

  const stat = (cls, big, lbl) =>
    `<div class="stat ${cls}"><div class="big">${big}</div><div class="lbl">${lbl}</div></div>`;

  const t = d.trust;
  const trustCard = t
    ? stat(
        t.agent_use_allowed ? "ok" : "bad",
        t.data_product_trust_score != null ? `${t.data_product_trust_score}` : esc(t.trust_status) || "—",
        `Trust${t.trust_status ? " · " + esc(t.trust_status) : ""}`,
      )
    : "";

  const cards = `<div class="summary-cards">
    ${trustCard}
    ${stat(qRate != null && qRate < 100 ? "warn" : "ok", qRate == null ? "—" : qRate + "%", "Quality pass rate")}
    ${stat(failedRuns ? "bad" : "ok", failedRuns, "Failed lineage runs")}
    ${stat("", lastRun ? ago(lastRun.run_dts, now) : "—", "Last lineage run")}
    ${stat("", d.change_events.length, "Change events (window)")}
    ${stat("", agentRate == null ? "—" : agentRate + "%", "Agent success rate")}
  </div>`;

  const passSeries = dailyPassRate(d.quality_metrics, now);
  const changeBars = countByDay(d.change_events, "change_dts", now);
  const runBars = runs
    .slice(0, 20)
    .reverse()
    .map((r) => ({ label: r.job_name || "run", value: r.records_written || 0, bad: isFailed(r.run_status) }));

  const charts = `<div class="charts-row">
    ${chartCard("Quality pass-rate trend (14d)", sparkline(passSeries), passSeries.length ? `latest ${passSeries[passSeries.length - 1]}%` : "")}
    ${chartCard("Change volume (14d)", barChart(changeBars), `${d.change_events.length} events`)}
    ${chartCard("Records written per run", barChart(runBars), `${runs.length} runs · ${failedRuns} failed`)}
  </div>`;

  el("detail").innerHTML = `
    <h2>${esc(d.product_name)} — Operations</h2>
    <p class="sub">Snapshot ${fmtDate(d.generated_dts)} UTC · ${esc((d.registry && d.registry.product_version) || "")}</p>
    ${cards}
    ${charts}
    ${trustDetail(t)}
    ${qualityTable(d)}
    ${lineageTable(d, now)}
    ${changeTable(d)}
    ${agentTable(d, now)}`;
  renderWarnings();
}

function trustDetail(t) {
  if (!t) return "";
  const checks =
    t.total_checks != null ? `${t.passed_count ?? "—"}/${t.total_checks} checks passed` : "";
  const scores = [
    ["Trust", t.data_product_trust_score],
    ["Performance readiness", t.performance_readiness_score],
    ["Operational readiness", t.operational_readiness_score],
  ]
    .filter((s) => s[1] != null)
    .map((s) => `<span class="pill">${s[0]}: ${s[1]}</span>`)
    .join(" ");
  return `<div class="card">
    <h4>Trust engine <span class="pill">${esc(t.trust_status) || "—"}</span>
      ${t.agent_use_allowed ? '<span class="pill">agent use allowed</span>' : '<span class="pill">agent use blocked</span>'}</h4>
    <p class="desc">${checks}${t.failed_count ? ` · ${t.failed_count} failed` : ""}${t.critical_failure_count ? ` · ${t.critical_failure_count} critical` : ""}</p>
    <div>${scores}</div>
  </div>`;
}

function truncNote(total) {
  return total > MAX_ROWS ? `<p class="sub">Showing ${MAX_ROWS} of ${total}.</p>` : "";
}

function qualityTable(d) {
  if (!d.quality_metrics.length) return "";
  const statusCell = (m) => {
    if (m.is_threshold_met == null) return '<td class="desc">—</td>';
    return m.is_threshold_met
      ? '<td class="status-ok">OK</td>'
      : '<td class="status-bad">FAILED</td>';
  };
  const rows = d.quality_metrics
    .slice(0, MAX_ROWS)
    .map(
      (m) => `<tr>
        <td><code>${esc(m.database_name)}.${esc(m.table_name)}</code></td>
        <td>${esc(m.metric_name)}${m.column_name ? ` <span class="desc">(${esc(m.column_name)})</span>` : ""}</td>
        <td class="num">${fmtNum(m.metric_value)}</td>
        <td class="num">${fmtNum(m.quality_threshold)}</td>
        ${statusCell(m)}
        <td>${fmtDate(m.measured_dts)}</td>
      </tr>`,
    )
    .join("");
  return `<h3 class="section-title">Data quality</h3>${truncNote(d.quality_metrics.length)}
    <table><thead><tr><th>Object</th><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th><th>Measured</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function lineageTable(d, now) {
  const runs = d.lineage_run || [];
  if (!runs.length) return "";
  // Resolve target object from the definitional data_lineage by lineage_id.
  const flowById = new Map((d.data_lineage || []).map((f) => [f.lineage_id, f]));
  const rows = runs
    .slice(0, MAX_ROWS)
    .map((r) => {
      const status = r.run_status || "—";
      const cls = r.run_status ? (isFailed(status) ? "status-bad" : "status-ok") : "desc";
      const flow = flowById.get(r.lineage_id);
      const target = flow ? `${esc(flow.target_database) || ""}.${esc(flow.target_table)}` : "—";
      return `<tr>
        <td>${esc(r.job_name) || (flow ? esc(flow.job_name) : "—")}</td>
        <td><code>${target}</code></td>
        <td class="${cls}">${esc(status)}</td>
        <td>${r.run_dts ? ago(r.run_dts, now) : "—"}</td>
        <td class="num">${fmtNum(r.records_read)}</td>
        <td class="num">${fmtNum(r.records_written)}</td>
        <td class="num">${fmtNum(r.records_rejected)}</td>
      </tr>`;
    })
    .join("");
  return `<h3 class="section-title">Lineage runs</h3>${truncNote(runs.length)}
    <table><thead><tr><th>Job</th><th>Target</th><th>Status</th><th>When</th><th>Read</th><th>Written</th><th>Rejected</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function changeTable(d) {
  if (!d.change_events.length) return "";
  const rows = d.change_events
    .slice(0, MAX_ROWS)
    .map(
      (c) => `<tr>
        <td>${fmtDate(c.change_dts)}</td>
        <td><code>${esc(c.database_name)}.${esc(c.table_name)}</code></td>
        <td>${esc(c.change_type)}</td>
        <td class="num">${fmtNum(c.records_affected)}</td>
        <td>${esc(c.changed_by) || "—"}</td>
        <td>${esc(c.change_source) || "—"}</td>
      </tr>`,
    )
    .join("");
  return `<h3 class="section-title">Change activity</h3>${truncNote(d.change_events.length)}
    <table><thead><tr><th>When</th><th>Object</th><th>Type</th><th>Rows</th><th>By</th><th>Source</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function agentTable(d, now) {
  const outcomes = d.agent_outcomes || [];
  if (!outcomes.length) return "";

  // Status breakdown pills.
  const counts = {};
  for (const o of outcomes) {
    const k = o.outcome_status || "unknown";
    counts[k] = (counts[k] || 0) + 1;
  }
  const pills = Object.entries(counts)
    .map(([k, n]) => `<span class="pill ${isSuccess(k) ? "ok" : isFailed(k) ? "bad" : ""}">${esc(k)}: ${n}</span>`)
    .join(" ");

  const rows = outcomes
    .slice(0, MAX_ROWS)
    .map((o) => {
      const cls = o.outcome_status
        ? isSuccess(o.outcome_status)
          ? "status-ok"
          : isFailed(o.outcome_status)
            ? "status-bad"
            : "desc"
        : "desc";
      return `<tr>
        <td>${fmtDate(o.action_dts)}</td>
        <td>${esc(o.action_type) || "—"}</td>
        <td class="${cls}">${esc(o.outcome_status) || "—"}</td>
        <td class="num">${fmtNum(o.execution_time_ms)}</td>
        <td class="num">${fmtNum(o.records_processed)}</td>
      </tr>`;
    })
    .join("");
  return `<h3 class="section-title">Agent outcomes</h3>
    <div class="pill-row">${pills}</div>${truncNote(outcomes.length)}
    <table><thead><tr><th>When</th><th>Action</th><th>Outcome</th><th>Exec ms</th><th>Records</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

// --- entity map (ERD) --------------------------------------------------------

const ERD_COLOURS = ["#4aa8ff", "#3fb950", "#d29922", "#ff7b72", "#a371f7", "#39c5cf", "#e3b341"];
const erdKey = (db, table) => `${db}|${(table || "").toLowerCase()}`;

window.__erdSelect = (id) => selectEntity(id);

const ERD_NODE_W = 180;
const ERD_NODE_H = 38;
const ERD_COL_GAP = 110;
const ERD_ROW_GAP = 22;
const ERD_PAD = 24;
const ERD_HEAD = 34;
const erdColW = ERD_NODE_W + ERD_COL_GAP;
const erdRowH = ERD_NODE_H + ERD_ROW_GAP;

function erdNodeSvg(n) {
  const name =
    n.e.entity_name.length > 22 ? n.e.entity_name.slice(0, 21) + "…" : n.e.entity_name;
  const cols = columnsFor(n.e).length;
  return `<g class="erd-node" onclick="window.__erdSelect(${n.e.entity_metadata_id})">
    <rect x="${n.x}" y="${n.y}" width="${ERD_NODE_W}" height="${ERD_NODE_H}" rx="7"
          fill="var(--panel-2)" stroke="${n.colour}" stroke-width="1.5"/>
    <rect x="${n.x}" y="${n.y}" width="4" height="${ERD_NODE_H}" rx="2" fill="${n.colour}"/>
    <text class="erd-label" x="${n.x + 14}" y="${n.y + 17}">${esc(name)}</text>
    <text class="erd-sub" x="${n.x + 14}" y="${n.y + 30}">${esc(n.e.table_name)} · ${cols} cols</text>
    <title>${esc(n.e.database_name)}.${esc(n.e.table_name)}</title>
  </g>`;
}

// Longest-path layering: referenced tables sit left, dependents flow right.
function erdLayers(byKey, out, inn) {
  const layer = new Map();
  const visiting = new Set();
  const calc = (k) => {
    if (layer.has(k)) return layer.get(k);
    if (visiting.has(k)) return 0; // cycle guard
    visiting.add(k);
    let L = 0;
    for (const t of out.get(k)) L = Math.max(L, calc(t) + 1);
    visiting.delete(k);
    layer.set(k, L);
    return L;
  };
  const connected = [...byKey.keys()].filter((k) => out.get(k).size || inn.get(k).size);
  connected.forEach(calc);
  const maxLayer = connected.length ? Math.max(...connected.map((k) => layer.get(k))) : 0;
  const layers = Array.from({ length: maxLayer + 1 }, () => []);
  connected.forEach((k) => layers[layer.get(k)].push(k));
  return { layers, layer };
}

function showErd() {
  const d = state.data;
  if (!d.entities.length) {
    el("detail").innerHTML = `<h2>Entity map</h2><div class="empty">No entities to map.</div>`;
    return;
  }

  // Module → colour, and node objects keyed by db|table.
  const moduleColour = new Map();
  [...entitiesByModule()].forEach(([mod], i) =>
    moduleColour.set(mod, ERD_COLOURS[i % ERD_COLOURS.length]),
  );
  const byKey = new Map();
  for (const e of d.entities) {
    byKey.set(erdKey(e.database_name, e.table_name), {
      e,
      mod: e.module_name || "Other",
      colour: moduleColour.get(e.module_name) || ERD_COLOURS[0],
    });
  }

  // Adjacency over edges whose both endpoints are mapped entities.
  const out = new Map();
  const inn = new Map();
  for (const k of byKey.keys()) {
    out.set(k, new Set());
    inn.set(k, new Set());
  }
  const rels = [];
  for (const r of d.relationships) {
    const sk = erdKey(r.source_database, r.source_table);
    const tk = erdKey(r.target_database, r.target_table);
    if (!byKey.has(sk) || !byKey.has(tk) || sk === tk) continue;
    out.get(sk).add(tk);
    inn.get(tk).add(sk);
    rels.push({ sk, tk, r });
  }

  const { layers } = erdLayers(byKey, out, inn);
  const isolated = [...byKey.keys()].filter((k) => !out.get(k).size && !inn.get(k).size);

  // Order within each layer: start alphabetical, then one barycenter sweep
  // (by mean rank of a node's targets) to reduce edge crossings.
  const nameOf = (k) => byKey.get(k).e.entity_name;
  layers.forEach((ls) =>
    ls.sort((a, b) => (byKey.get(a).mod + nameOf(a)).localeCompare(byKey.get(b).mod + nameOf(b))),
  );
  const rank = new Map();
  const setRanks = () => layers.forEach((ls) => ls.forEach((k, i) => rank.set(k, i)));
  setRanks();
  for (let L = 1; L < layers.length; L++) {
    layers[L].sort((a, b) => barycenter(a, out, rank) - barycenter(b, out, rank));
    setRanks();
  }

  // Positions: x by layer, y centred per column.
  const maxCount = Math.max(1, ...layers.map((l) => l.length));
  const topY = ERD_PAD + ERD_HEAD;
  for (let L = 0; L < layers.length; L++) {
    const ls = layers[L];
    const startY = topY + ((maxCount - ls.length) * erdRowH) / 2;
    ls.forEach((k, i) => {
      const n = byKey.get(k);
      n.x = ERD_PAD + L * erdColW;
      n.y = startY + i * erdRowH;
    });
  }
  const layeredW = ERD_PAD * 2 + Math.max(0, layers.length - 1) * erdColW + ERD_NODE_W;
  let contentH = topY + maxCount * erdRowH;

  // Isolated entities: wrapped grid below the layered graph.
  let isoSvg = "";
  if (isolated.length) {
    const perRow = Math.max(1, Math.floor((layeredW - ERD_PAD * 2 + ERD_COL_GAP) / erdColW));
    const isoTop = contentH + 18;
    isoSvg += `<text class="erd-head" x="${ERD_PAD}" y="${isoTop}">Unconnected (${isolated.length})</text>`;
    isolated.sort((a, b) => nameOf(a).localeCompare(nameOf(b)));
    isolated.forEach((k, i) => {
      const n = byKey.get(k);
      n.x = ERD_PAD + (i % perRow) * erdColW;
      n.y = isoTop + 10 + Math.floor(i / perRow) * erdRowH;
    });
    const rows = Math.ceil(isolated.length / perRow);
    contentH = isoTop + 10 + rows * erdRowH;
    isoSvg += isolated.map((k) => erdNodeSvg(byKey.get(k))).join("");
  }

  // Edges: source (dependent, right) → target (referenced, left), arrow at target.
  let edges = "";
  for (const { sk, tk, r } of rels) {
    const s = byKey.get(sk);
    const t = byKey.get(tk);
    const sMidY = s.y + ERD_NODE_H / 2;
    const tMidY = t.y + ERD_NODE_H / 2;
    const rightward = t.x >= s.x;
    const sx = rightward ? s.x + ERD_NODE_W : s.x;
    const tx = rightward ? t.x : t.x + ERD_NODE_W;
    const co = rightward ? 50 : -50;
    edges += `<path class="erd-edge" d="M ${sx} ${sMidY} C ${sx + co} ${sMidY} ${tx - co} ${tMidY} ${tx} ${tMidY}" marker-end="url(#erd-arrow)"><title>${esc(r.relationship_meaning || r.relationship_type || "related")}</title></path>`;
  }

  // Module colour legend.
  let lx = ERD_PAD;
  const legend = [...moduleColour.entries()]
    .map(([mod, colour]) => {
      const item = `<rect x="${lx}" y="${ERD_PAD - 2}" width="11" height="11" rx="3" fill="${colour}"/><text class="erd-legend" x="${lx + 16}" y="${ERD_PAD + 7}">${esc(mod)}</text>`;
      lx += 30 + mod.length * 7;
      return item;
    })
    .join("");

  const layered = [];
  for (const ls of layers) for (const k of ls) layered.push(erdNodeSvg(byKey.get(k)));

  const width = Math.max(layeredW, lx + ERD_PAD);
  el("detail").innerHTML = `
    <h2>${esc(d.product_name)} — Entity map</h2>
    <p class="sub">${byKey.size} entities · ${rels.length} relationships · left = referenced, right = dependent · click a node to open it</p>
    <div class="erd-scroll">
      <svg class="erd" width="${width}" height="${contentH}" viewBox="0 0 ${width} ${contentH}">
        <defs>
          <marker id="erd-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--muted)"/>
          </marker>
        </defs>
        ${legend}${edges}${layered.join("")}${isoSvg}
      </svg>
    </div>`;
  renderWarnings();
}

function barycenter(k, out, rank) {
  const ts = [...out.get(k)].map((t) => rank.get(t)).filter((v) => v != null);
  return ts.length ? ts.reduce((s, v) => s + v, 0) / ts.length : (rank.get(k) ?? 0);
}

// --- cookbook ----------------------------------------------------------------

// prettier-ignore
const SQL_KEYWORDS = new Set([
  "SELECT","FROM","WHERE","GROUP","BY","ORDER","HAVING","QUALIFY","JOIN","LEFT","RIGHT",
  "INNER","OUTER","FULL","CROSS","ON","AND","OR","NOT","IN","AS","IS","NULL","LIKE",
  "BETWEEN","EXISTS","UNION","ALL","DISTINCT","CASE","WHEN","THEN","ELSE","END","WITH",
  "OVER","PARTITION","ROW_NUMBER","RANK","COUNT","SUM","AVG","MIN","MAX","CAST","COALESCE",
  "CURRENT_DATE","CURRENT_TIMESTAMP","INTERVAL","DESC","ASC","SAMPLE","TOP","LIMIT","USING",
]);

let cookbookQuery = "";

// Lightweight SQL syntax highlighter (escapes first, then wraps tokens).
function highlightSql(sql) {
  return esc(sql).replace(
    /('(?:[^']|'')*')|(--[^\n]*)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)/g,
    (m, str, com, num, word) => {
      if (str) return `<span class="sql-string">${m}</span>`;
      if (com) return `<span class="sql-comment">${m}</span>`;
      if (num) return `<span class="sql-number">${m}</span>`;
      if (word && SQL_KEYWORDS.has(word.toUpperCase())) return `<span class="sql-keyword">${m}</span>`;
      return m;
    },
  );
}

window.__copySql = (i, btn) => {
  const r = state.data.recipes[i];
  if (!r) return;
  navigator.clipboard.writeText(r.sql_template).then(() => {
    const old = btn.textContent;
    btn.textContent = "Copied!";
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = old;
      btn.disabled = false;
    }, 1200);
  });
};

function complexityClass(c) {
  const v = (c || "").toUpperCase();
  if (v === "SIMPLE") return "ok";
  if (v === "COMPLEX" || v === "ADVANCED") return "bad";
  return "";
}

// Build the HTML for one recipe card. `i` indexes state.data.recipes for copy.
function recipeCard(r, i) {
  return `<div class="recipe">
    <h4>${esc(r.recipe_title)}
      <span class="pill ${complexityClass(r.complexity)}">${esc(r.complexity) || "—"}</span>
      ${r.target_module ? `<span class="pill">${esc(r.target_module)}</span>` : ""}</h4>
    ${r.recipe_description ? `<p class="desc">${esc(r.recipe_description)}</p>` : ""}
    ${r.use_case ? `<p class="desc"><strong>Use case:</strong> ${esc(r.use_case)}</p>` : ""}
    <div class="code-head">
      <span class="recipe-id">${esc(r.recipe_id)}</span>
      <button class="copy-btn" onclick="window.__copySql(${i}, this)">Copy SQL</button>
    </div>
    <pre class="sql"><code>${highlightSql(r.sql_template || "")}</code></pre>
    ${r.parameter_descriptions ? `<p class="desc"><strong>Parameters:</strong> ${esc(r.parameter_descriptions)}</p>` : ""}
    ${r.performance_notes ? `<p class="desc">⚡ ${esc(r.performance_notes)}</p>` : ""}
  </div>`;
}

function recipeListHtml() {
  const q = cookbookQuery.trim().toLowerCase();
  const match = (r) =>
    !q ||
    [r.recipe_title, r.recipe_description, r.use_case, r.target_module, r.sql_template].some((f) =>
      (f || "").toLowerCase().includes(q),
    );
  const cards = (state.data.recipes || [])
    .map((r, i) => ({ r, i }))
    .filter(({ r }) => match(r))
    .map(({ r, i }) => recipeCard(r, i))
    .join("");
  return cards || '<div class="empty">No recipes match.</div>';
}

function showCookbook() {
  const d = state.data;
  el("detail").innerHTML = `
    <h2>${esc(d.product_name)} — Cookbook</h2>
    <p class="sub">${(d.recipes || []).length} recipes · ready-to-run query templates from the standard's Memory module</p>
    <input id="cookbook-search" class="cookbook-search" type="search" placeholder="Search recipes…" value="${esc(cookbookQuery)}" />
    <div id="recipe-list">${recipeListHtml()}</div>`;

  const search = el("cookbook-search");
  search.addEventListener("input", () => {
    cookbookQuery = search.value;
    el("recipe-list").innerHTML = recipeListHtml(); // keeps the search box focused
  });
  renderWarnings();
}

el("product-select").addEventListener("change", (e) => loadProduct(e.target.value));
el("filter").addEventListener("input", () => state.data && renderTree());

loadProductList();

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

// Case-insensitive match against all entity-name variants — accepts the table,
// the companion view, the entity name, and the same with SCD2 suffixes stripped.
// Also tolerates qualified "<db>.<table>" values in column_metadata.
function columnsFor(entity) {
  const variants = _entityNameVariants(entity);
  return state.data.columns.filter((c) => _qualifiedMatches(c.table_name, variants));
}

// Surface near-misses so the user knows whether curated rows exist at all.
// Returns a list of {table_name, count} for any column_metadata table whose name
// shares a token with the entity but didn't match — i.e. probably a casing or
// suffix mismatch the matcher couldn't recover from.
function columnsDiagnostic(entity) {
  if (columnsFor(entity).length) return null;
  const variants = _entityNameVariants(entity);
  const tokens = new Set();
  variants.forEach((v) => v.split(/[_.]/).filter((t) => t.length >= 3).forEach((t) => tokens.add(t)));
  if (!tokens.size) return null;
  const counts = new Map();
  for (const c of state.data.columns) {
    const ct = (c.table_name || "").toLowerCase();
    const last = ct.includes(".") ? ct.slice(ct.lastIndexOf(".") + 1) : ct;
    if ([...tokens].some((t) => last.includes(t))) {
      counts.set(c.table_name, (counts.get(c.table_name) || 0) + 1);
    }
  }
  return counts.size ? [...counts.entries()].map(([table_name, count]) => ({ table_name, count })) : null;
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

// Strip the SCD2 history suffix so curated terms tagged against the logical entity
// (e.g. "Call_Summary") still match the deployed *_H table.
function _entityNameVariants(entity) {
  const out = new Set();
  const push = (s) => s && out.add(s.toLowerCase());
  push(entity.table_name);
  push(entity.view_name);
  push(entity.entity_name);
  if (entity.table_name) push(entity.table_name.replace(/_H$/i, ""));
  if (entity.view_name) push(entity.view_name.replace(/_Current$/i, ""));
  return out;
}

// Accept either a bare table name or a qualified "<database>.<table>" value —
// curated metadata sometimes drifts between the two.
function _qualifiedMatches(value, variants) {
  if (!value) return false;
  const v = value.toLowerCase();
  if (variants.has(v)) return true;
  const dot = v.lastIndexOf(".");
  return dot >= 0 && variants.has(v.slice(dot + 1));
}

function glossaryFor(entity) {
  const variants = _entityNameVariants(entity);
  return state.data.glossary.filter((g) => _qualifiedMatches(g.related_table, variants));
}

function decisionsFor(entity) {
  const variants = _entityNameVariants(entity);
  return state.data.decisions.filter((d) => _qualifiedMatches(d.affects_table, variants));
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
  let diag = "";
  if (!rows) {
    const near = columnsDiagnostic(entity);
    if (near && near.length) {
      const list = near
        .sort((a, b) => b.count - a.count)
        .slice(0, 6)
        .map((n) => `<li><code>${esc(n.table_name)}</code> — ${n.count} column${n.count === 1 ? "" : "s"}</li>`)
        .join("");
      diag = `<div class="diagnostic">
        <strong>No column_metadata rows match this entity exactly.</strong>
        Curated rows tagged against similar names (likely a deployed-vs-logical
        prefix mismatch — see <code>docs/fixes/business-glossary-related-table-realign.sql</code>
        for the same pattern on the Glossary):
        <ul>${list}</ul>
      </div>`;
    } else {
      diag = `<div class="diagnostic">
        <strong>No column_metadata rows curated for this entity.</strong>
        Confirm by querying <code>&lt;semantic&gt;.column_metadata</code> for
        <code>${esc(entity.table_name)}</code> directly.
      </div>`;
    }
  }
  return `${diag}<table>
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
  const status = (t.trust_status || "").toUpperCase();
  const trusted = status === "TRUSTED";
  const mood = trusted ? "trusted" : "untrusted";
  const checks =
    t.total_checks != null ? `${t.passed_count ?? "—"}/${t.total_checks} checks passed` : "";
  const scores = [
    ["Trust", t.data_product_trust_score],
    ["Performance readiness", t.performance_readiness_score],
    ["Operational readiness", t.operational_readiness_score],
  ]
    .filter((s) => s[1] != null)
    .map((s) => `<span class="trust-score">${s[0]}: <strong>${s[1]}</strong></span>`)
    .join("");
  const agent = t.agent_use_allowed
    ? '<span class="trust-agent ok">✓ agent use allowed</span>'
    : '<span class="trust-agent bad">⛔ agent use blocked</span>';
  return `<section class="trust-banner trust-${mood}">
    <div class="trust-banner-head">
      <span class="trust-status-badge">${esc(t.trust_status) || "—"}</span>
      <span class="trust-banner-title">Trust engine</span>
      ${agent}
    </div>
    <p class="trust-banner-checks">${checks}${t.failed_count ? ` · <span class="bad-num">${t.failed_count} failed</span>` : ""}${t.critical_failure_count ? ` · <span class="crit-num">${t.critical_failure_count} critical</span>` : ""}</p>
    <div class="trust-scores">${scores}</div>
  </section>`;
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
  return `<details class="ops-section ops-quality">
    <summary>Data quality<span class="count">${d.quality_metrics.length} metrics</span></summary>
    <div class="ops-body">${truncNote(d.quality_metrics.length)}
    <table><thead><tr><th>Object</th><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th><th>Measured</th></tr></thead>
    <tbody>${rows}</tbody></table></div></details>`;
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
  return `<details class="ops-section ops-lineage">
    <summary>Lineage runs<span class="count">${runs.length} runs</span></summary>
    <div class="ops-body">${truncNote(runs.length)}
    <table><thead><tr><th>Job</th><th>Target</th><th>Status</th><th>When</th><th>Read</th><th>Written</th><th>Rejected</th></tr></thead>
    <tbody>${rows}</tbody></table></div></details>`;
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
  return `<details class="ops-section ops-change">
    <summary>Change activity<span class="count">${d.change_events.length} events</span></summary>
    <div class="ops-body">${truncNote(d.change_events.length)}
    <table><thead><tr><th>When</th><th>Object</th><th>Type</th><th>Rows</th><th>By</th><th>Source</th></tr></thead>
    <tbody>${rows}</tbody></table></div></details>`;
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
  return `<details class="ops-section ops-agent">
    <summary>Agent outcomes<span class="count">${outcomes.length} outcomes</span></summary>
    <div class="ops-body">
    <div class="pill-row">${pills}</div>${truncNote(outcomes.length)}
    <table><thead><tr><th>When</th><th>Action</th><th>Outcome</th><th>Exec ms</th><th>Records</th></tr></thead>
    <tbody>${rows}</tbody></table></div></details>`;
}

// --- entity map (ERD) --------------------------------------------------------

const ERD_COLOURS = ["#4aa8ff", "#3fb950", "#d29922", "#ff7b72", "#a371f7", "#39c5cf", "#e3b341"];
const erdKey = (db, table) => `${db}|${(table || "").toLowerCase()}`;

window.__erdSelect = (id) => selectEntity(id);

// Hover highlight: emphasise a box's relationships and dim everything else.
window.__erdHi = (key) => {
  const svg = document.querySelector("svg.erd");
  if (!svg) return;
  const conn = new Set([key]);
  svg.querySelectorAll(".erd-edge").forEach((ed) => {
    const f = ed.getAttribute("data-from");
    const t = ed.getAttribute("data-to");
    if (f === key || t === key) {
      conn.add(f);
      conn.add(t);
    }
  });
  svg.querySelectorAll(".erd-box").forEach((b) =>
    b.classList.toggle("erd-dimmed", !conn.has(b.getAttribute("data-key"))),
  );
  svg.querySelectorAll(".erd-edge").forEach((ed) => {
    const on = ed.getAttribute("data-from") === key || ed.getAttribute("data-to") === key;
    ed.classList.toggle("erd-dimmed", !on);
    ed.classList.toggle("erd-on", on);
  });
};
window.__erdHiOff = () => {
  const svg = document.querySelector("svg.erd");
  if (!svg) return;
  svg.querySelectorAll(".erd-dimmed").forEach((n) => n.classList.remove("erd-dimmed"));
  svg.querySelectorAll(".erd-on").forEach((n) => n.classList.remove("erd-on"));
};

// Collapse/expand a single entity between attribute-level and entity-level.
window.__erdToggle = (ev, id) => {
  if (ev) ev.stopPropagation(); // don't also open the entity
  if (!state.erdCollapsed) state.erdCollapsed = new Set();
  if (state.erdCollapsed.has(id)) state.erdCollapsed.delete(id);
  else state.erdCollapsed.add(id);
  showErd();
};

// Collapse all / expand all (one toggle, based on current state).
window.__erdToggleAll = () => {
  if (!state.erdCollapsed) state.erdCollapsed = new Set();
  const ids = (state.data && state.data.entities ? state.data.entities : []).map(
    (e) => e.entity_metadata_id,
  );
  const allCollapsed = ids.length > 0 && ids.every((id) => state.erdCollapsed.has(id));
  state.erdCollapsed = new Set(allCollapsed ? [] : ids);
  showErd();
};

// Attribute-level box geometry (matches the data-model-erd skill).
const ERD_BOX_W = 300;
const ERD_ROW_H = 22;
const ERD_HEAD_H = 38;
const ERD_BOX_GAP = 30; // vertical gap between boxes within a lane
const ERD_COL_GAP = 150; // horizontal gap between lanes (room for edges + labels)
const ERD_PAD = 24;
const ERD_HEAD = 50; // top band reserved for the legend
const erdColW = ERD_BOX_W + ERD_COL_GAP;

// Resolve per-column attribute flags from entity + relationship metadata.
// PI and identity are intentionally omitted — the browser does not collect them.
function erdColumns(n) {
  const e = n.e;
  const sk = (e.surrogate_key_column || "").toUpperCase();
  const nk = (e.natural_key_column || "").toUpperCase();
  const fkCols = new Set();
  for (const r of state.data.relationships) {
    if (r.is_active === 0) continue;
    if (erdKey(r.source_database, r.source_table) === n.key) {
      fkCols.add((r.source_column || "").toUpperCase());
    }
  }
  return columnsFor(e).map((c) => {
    const up = (c.column_name || "").toUpperCase();
    return {
      name: c.column_name,
      type: c.data_type || "",
      pk: !!sk && up === sk,
      nk: !!nk && up === nk,
      fk: fkCols.has(up),
      pii: !!c.is_pii,
      sens: !!c.is_sensitive,
      nn: !!c.is_required,
    };
  });
}

function erdBoxHeight(n) {
  if (n.collapsed) return ERD_HEAD_H + 4; // entity-level: header only
  return ERD_HEAD_H + Math.max(1, n.cols.length) * ERD_ROW_H + 8;
}

// y-centre of a given column row (for anchoring edges to specific columns).
// A collapsed entity has no visible rows, so edges anchor to the header centre.
function erdRowYOf(n, col) {
  if (n.collapsed) return n.y + n.h / 2;
  const up = (col || "").toUpperCase();
  const i = n.cols.findIndex((c) => (c.name || "").toUpperCase() === up);
  if (i < 0) return n.y + n.h / 2;
  return n.y + ERD_HEAD_H + i * ERD_ROW_H + ERD_ROW_H / 2;
}

function erdBadgeChips(col) {
  const chips = [];
  if (col.pk) chips.push(["PK", "bg", "pk"]);
  if (col.nk) chips.push(["NK", "ol", "nk"]);
  if (col.fk) chips.push(["FK", "bg", "fk"]);
  if (col.pii) chips.push(["PII", "bg", "pii"]);
  if (col.sens) chips.push(["SENS", "ol", "sens"]);
  if (col.nn) chips.push(["NN", "ol", "nn"]);
  return chips;
}

function erdBoxSvg(n) {
  const x = n.x;
  const y = n.y;
  const W = ERD_BOX_W;
  const h = n.h;
  const collapsed = n.collapsed;
  const name =
    n.e.entity_name.length > 26 ? n.e.entity_name.slice(0, 25) + "…" : n.e.entity_name;
  const p = [];
  p.push(
    `<g class="erd-box" data-key="${esc(n.key)}" onclick="window.__erdSelect(${n.e.entity_metadata_id})">`,
  );
  p.push(`<rect class="erd-box-bg" x="${x}" y="${y}" width="${W}" height="${h}" rx="9"/>`);
  // Header band with rounded top corners, faintly tinted by the module colour.
  p.push(
    `<path class="erd-box-hd" d="M${x} ${y + 9} a9 9 0 0 1 9 -9 h${W - 18} a9 9 0 0 1 9 9 v${ERD_HEAD_H - 9} h-${W} z" fill="${n.colour}26"/>`,
  );
  p.push(`<rect x="${x}" y="${y}" width="4" height="${h}" fill="${n.colour}"/>`);
  // Collapse / expand toggle (top-right of the header).
  const tg = collapsed ? "+" : "\u2212";
  const bxr = x + W - 24;
  const byr = y + (ERD_HEAD_H - 16) / 2;
  p.push(
    `<g class="erd-toggle" onclick="window.__erdToggle(event, ${n.e.entity_metadata_id})">` +
      `<rect class="erd-toggle-bg" x="${bxr}" y="${byr}" width="17" height="16" rx="4"/>` +
      `<text class="erd-toggle-t" x="${bxr + 8.5}" y="${byr + 12}" text-anchor="middle">${tg}</text>` +
      `<title>${collapsed ? "Expand to attributes" : "Collapse to entity"}</title></g>`,
  );
  p.push(`<text class="erd-box-name" x="${x + 14}" y="${y + 18}">${esc(name)}</text>`);
  const sub = collapsed
    ? `${esc(n.mod)} · ${esc(n.e.table_name)} · ${n.cols.length} col${n.cols.length === 1 ? "" : "s"}`
    : `${esc(n.mod)} · ${esc(n.e.table_name)}`;
  p.push(`<text class="erd-box-sub" x="${x + 14}" y="${y + 31}">${sub}</text>`);

  if (!collapsed) {
    if (!n.cols.length) {
      p.push(`<text class="erd-ct" x="${x + 14}" y="${y + ERD_HEAD_H + 15}">no column metadata</text>`);
    }
    n.cols.forEach((c, i) => {
      const ry = y + ERD_HEAD_H + i * ERD_ROW_H;
      if (i > 0)
        p.push(`<line class="erd-rowline" x1="${x + 10}" y1="${ry}" x2="${x + W - 10}" y2="${ry}"/>`);
      p.push(
        `<text class="${c.fk ? "erd-cn fk" : "erd-cn"}" x="${x + 14}" y="${ry + 15}">${esc(c.name)}</text>`,
      );
      const chips = erdBadgeChips(c);
      const widths = chips.map(([lbl]) => Math.round(lbl.length * 6.4 + 8) + 4);
      let bx = x + W - 12 - widths.reduce((a, b) => a + b, 0);
      const typeRight = bx - 6;
      chips.forEach(([lbl, fillKind, key], j) => {
        const w = widths[j] - 4;
        const cls = fillKind === "bg" ? `erd-bg-${key}` : `erd-ol-${key}`;
        p.push(`<rect class="${cls}" x="${bx}" y="${ry + 4}" width="${w}" height="15" rx="4"/>`);
        p.push(
          `<text class="erd-badge-t erd-tx-${key}" x="${bx + w / 2}" y="${ry + 15}" text-anchor="middle">${lbl}</text>`,
        );
        bx += widths[j];
      });
      p.push(
        `<text class="erd-ct" x="${typeRight}" y="${ry + 15}" text-anchor="end">${esc(c.type)}</text>`,
      );
    });
  }
  p.push(`<title>${esc(n.e.database_name)}.${esc(n.e.table_name)}</title>`);
  p.push(`</g>`);
  return p.join("");
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

  // Module → colour, and node objects keyed by db|table (with columns + height).
  if (!state.erdCollapsed) state.erdCollapsed = new Set();
  const moduleColour = new Map();
  [...entitiesByModule()].forEach(([mod], i) =>
    moduleColour.set(mod, ERD_COLOURS[i % ERD_COLOURS.length]),
  );
  const byKey = new Map();
  for (const e of d.entities) {
    const key = erdKey(e.database_name, e.table_name);
    const n = {
      e,
      key,
      mod: e.module_name || "Other",
      colour: moduleColour.get(e.module_name) || ERD_COLOURS[0],
    };
    n.cols = erdColumns(n);
    n.collapsed = state.erdCollapsed.has(e.entity_metadata_id);
    n.h = erdBoxHeight(n);
    byKey.set(key, n);
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

  // Order within each layer: alphabetical, then one barycenter sweep to reduce crossings.
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

  // Positions: x by layer (lane); stack variable-height boxes top-down within a lane.
  const topY = ERD_PAD + ERD_HEAD;
  let contentH = topY;
  for (let L = 0; L < layers.length; L++) {
    let y = topY;
    for (const k of layers[L]) {
      const n = byKey.get(k);
      n.x = ERD_PAD + L * erdColW;
      n.y = y;
      y += n.h + ERD_BOX_GAP;
    }
    contentH = Math.max(contentH, y);
  }
  const layeredW = ERD_PAD * 2 + Math.max(0, layers.length - 1) * erdColW + ERD_BOX_W;

  // Isolated entities: wrapped grid below the layered graph (advances by tallest in row).
  let isoSvg = "";
  if (isolated.length) {
    const perRow = Math.max(1, Math.floor((Math.max(layeredW, 600) - ERD_PAD * 2 + ERD_COL_GAP) / erdColW));
    const isoTop = contentH + 28;
    isoSvg += `<text class="erd-head" x="${ERD_PAD}" y="${isoTop}">Unconnected (${isolated.length})</text>`;
    isolated.sort((a, b) => nameOf(a).localeCompare(nameOf(b)));
    let rowTop = isoTop + 14;
    let rowMaxH = 0;
    isolated.forEach((k, i) => {
      const col = i % perRow;
      if (col === 0 && i > 0) {
        rowTop += rowMaxH + ERD_BOX_GAP;
        rowMaxH = 0;
      }
      const n = byKey.get(k);
      n.x = ERD_PAD + col * erdColW;
      n.y = rowTop;
      rowMaxH = Math.max(rowMaxH, n.h);
    });
    contentH = rowTop + rowMaxH + ERD_PAD;
    isoSvg = isoSvg + isolated.map((k) => erdBoxSvg(byKey.get(k))).join("");
  }

  // Edges (drawn beneath boxes): anchored at the actual key columns; labels added on top.
  let edges = "";
  const edgeLabels = [];
  for (const { sk, tk, r } of rels) {
    const s = byKey.get(sk);
    const t = byKey.get(tk);
    const sy = erdRowYOf(s, r.source_column);
    const ty = erdRowYOf(t, r.target_column);
    const rightward = t.x >= s.x;
    const sx = rightward ? s.x + ERD_BOX_W : s.x;
    const tx = rightward ? t.x : t.x + ERD_BOX_W;
    const co = rightward ? 60 : -60;
    const hard = (r.relationship_type || "").toUpperCase() === "FK" || !!r.is_mandatory;
    const cls = hard ? "hard" : "soft";
    edges +=
      `<path class="erd-edge ${cls}" data-from="${esc(sk)}" data-to="${esc(tk)}" ` +
      `d="M ${sx} ${sy} C ${sx + co} ${sy} ${tx - co} ${ty} ${tx} ${ty}">` +
      `<title>${esc(r.relationship_meaning || r.relationship_type || "related")}</title></path>` +
      `<circle class="erd-dot ${cls}" cx="${sx}" cy="${sy}" r="3"/>` +
      `<circle class="erd-dot ${cls}" cx="${tx}" cy="${ty}" r="3"/>`;
    let label = r.cardinality || "";
    const meaning = (r.relationship_meaning || "").trim();
    const gap = Math.abs(tx - sx);
    if (meaning) {
      const candidate = label ? `${label} · ${meaning}` : meaning;
      if (candidate.length * 5.2 + 10 <= gap * 0.95) label = candidate;
    }
    if (label) edgeLabels.push({ x: (sx + tx) / 2, y: (sy + ty) / 2, text: label });
  }
  const labelSvg = edgeLabels
    .map((l) => {
      const w = l.text.length * 5.2 + 10;
      return (
        `<rect class="erd-card-bg" x="${l.x - w / 2}" y="${l.y - 8}" width="${w}" height="15" rx="5"/>` +
        `<text class="erd-card" x="${l.x}" y="${l.y + 3}" text-anchor="middle">${esc(l.text)}</text>`
      );
    })
    .join("");

  // Legend row 1: module colours.  Row 2: attribute badges + edge styles.
  let lx = ERD_PAD;
  const modLegend = [...moduleColour.entries()]
    .map(([mod, colour]) => {
      const item = `<rect x="${lx}" y="${ERD_PAD - 4}" width="11" height="11" rx="3" fill="${colour}"/><text class="erd-legend" x="${lx + 16}" y="${ERD_PAD + 5}">${esc(mod)}</text>`;
      lx += 30 + mod.length * 7;
      return item;
    })
    .join("");

  const by = ERD_PAD + 18;
  let bxL = ERD_PAD;
  const badgeLegend = [
    ["PK", "bg", "pk", "key"],
    ["NK", "ol", "nk", "natural"],
    ["FK", "bg", "fk", "foreign"],
    ["PII", "bg", "pii", ""],
    ["SENS", "ol", "sens", ""],
    ["NN", "ol", "nn", "not null"],
  ]
    .map(([lbl, kind, key, note]) => {
      const w = Math.round(lbl.length * 6.4 + 8);
      const cls = kind === "bg" ? `erd-bg-${key}` : `erd-ol-${key}`;
      let s = `<rect class="${cls}" x="${bxL}" y="${by - 9}" width="${w}" height="14" rx="4"/><text class="erd-badge-t erd-tx-${key}" x="${bxL + w / 2}" y="${by + 1}" text-anchor="middle">${lbl}</text>`;
      bxL += w + 4;
      if (note) {
        s += `<text class="erd-legend" x="${bxL}" y="${by + 1}">${note}</text>`;
        bxL += note.length * 6 + 12;
      } else {
        bxL += 8;
      }
      return s;
    })
    .join("");
  let edgeLegend =
    `<line class="erd-edge hard" x1="${bxL}" y1="${by - 4}" x2="${bxL + 22}" y2="${by - 4}"/>` +
    `<text class="erd-legend" x="${bxL + 27}" y="${by + 1}">FK</text>`;
  bxL += 27 + 22;
  edgeLegend +=
    `<line class="erd-edge soft" x1="${bxL}" y1="${by - 4}" x2="${bxL + 22}" y2="${by - 4}"/>` +
    `<text class="erd-legend" x="${bxL + 27}" y="${by + 1}">soft</text>`;
  bxL += 27 + 30;

  const boxes = [];
  for (const ls of layers) for (const k of ls) boxes.push(erdBoxSvg(byKey.get(k)));

  const width = Math.max(layeredW, lx + ERD_PAD, bxL + ERD_PAD);
  const allIds = d.entities.map((e) => e.entity_metadata_id);
  const allCollapsed = allIds.length > 0 && allIds.every((id) => state.erdCollapsed.has(id));
  el("detail").innerHTML = `
    <h2>${esc(d.product_name)} — Entity map</h2>
    <p class="sub">${byKey.size} entities · ${rels.length} relationships · left = referenced, right = dependent · hover to trace, click to open</p>
    <div class="erd-toolbar">
      <button class="erd-btn" onclick="window.__erdToggleAll()">${allCollapsed ? "＋ Expand all" : "－ Collapse all"}</button>
      <span class="erd-toolhint">use the +/− on each entity to collapse or expand its attributes</span>
    </div>
    <div class="erd-scroll">
      <svg class="erd" width="${width}" height="${contentH}" viewBox="0 0 ${width} ${contentH}">
        ${modLegend}${badgeLegend}${edgeLegend}${edges}${boxes.join("")}${labelSvg}${isoSvg}
      </svg>
    </div>`;

  // Wire hover-highlight after the SVG is in the DOM.
  el("detail")
    .querySelectorAll(".erd-box")
    .forEach((b) => {
      const key = b.getAttribute("data-key");
      b.addEventListener("mouseenter", () => window.__erdHi(key));
      b.addEventListener("mouseleave", () => window.__erdHiOff());
    });
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
let cookbookMode = "all"; // "all" | "interactive" | "batch"

// Prefer the explicit Query_Cookbook.is_batch column; fall back to a param-presence heuristic.
function recipeMode(r) {
  if (r.is_batch === 1 || r.is_batch === true) return "batch";
  if (r.is_batch === 0 || r.is_batch === false) return "interactive";
  return /:[A-Za-z_][A-Za-z0-9_]*/.test(r.sql_template || "") ? "interactive" : "batch";
}

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
  if (v === "SIMPLE" || v === "LOW" || v === "EASY") return "ok";
  if (v === "MED" || v === "MEDIUM" || v === "MODERATE") return "warn";
  if (v === "COMPLEX" || v === "ADVANCED" || v === "HIGH" || v === "HARD") return "bad";
  return "";
}

// Deterministic colour assignment for target_module pills so each module is
// visually distinct in the cookbook.
const MODULE_PILL_PALETTE = [
  "mod-purple",
  "mod-teal",
  "mod-amber",
  "mod-pink",
  "mod-lime",
  "mod-violet",
  "mod-cyan",
];
const _modulePillCache = new Map();
function modulePillClass(name) {
  const k = (name || "").toLowerCase();
  if (!k) return "";
  if (_modulePillCache.has(k)) return _modulePillCache.get(k);
  let h = 0;
  for (let i = 0; i < k.length; i++) h = (h * 31 + k.charCodeAt(i)) >>> 0;
  const cls = MODULE_PILL_PALETTE[h % MODULE_PILL_PALETTE.length];
  _modulePillCache.set(k, cls);
  return cls;
}

// Build the HTML for one recipe card. `i` indexes state.data.recipes for copy.
function recipeCard(r, i) {
  const mode = recipeMode(r);
  const modeLabel = mode === "interactive" ? "Interactive" : "Batch";
  return `<details class="recipe ${mode === "batch" ? "is-batch" : ""}">
    <summary>
      <span class="recipe-title">${esc(r.recipe_title)}</span>
      <span class="pill mode-${mode}">${modeLabel}</span>
      <span class="pill ${complexityClass(r.complexity)}">${esc(r.complexity) || "—"}</span>
      ${r.target_module ? `<span class="pill ${modulePillClass(r.target_module)}">${esc(r.target_module)}</span>` : ""}
    </summary>
    <div class="recipe-body">
      ${r.recipe_description ? `<p class="business-q">${esc(r.recipe_description)}</p>` : ""}
      ${r.use_case ? `<p class="use-case"><strong>Use case:</strong> ${esc(r.use_case)}</p>` : ""}
      <div class="code-head">
        <span class="recipe-id">${esc(r.recipe_id)}</span>
        <button class="copy-btn" onclick="window.__copySql(${i}, this)">Copy SQL</button>
      </div>
      <pre class="sql"><code>${highlightSql(r.sql_template || "")}</code></pre>
      ${r.parameter_descriptions ? `<p class="params-note"><strong>Parameters:</strong> ${esc(r.parameter_descriptions)}</p>` : ""}
      ${r.performance_notes ? `<p class="perf-note">⚡ ${esc(r.performance_notes)}</p>` : ""}
    </div>
  </details>`;
}

function recipeListHtml() {
  const q = cookbookQuery.trim().toLowerCase();
  const match = (r) =>
    !q ||
    [r.recipe_title, r.recipe_description, r.use_case, r.target_module, r.sql_template].some((f) =>
      (f || "").toLowerCase().includes(q),
    );
  const modeMatch = (r) => cookbookMode === "all" || recipeMode(r) === cookbookMode;
  const cards = (state.data.recipes || [])
    .map((r, i) => ({ r, i }))
    .filter(({ r }) => match(r) && modeMatch(r))
    .map(({ r, i }) => recipeCard(r, i))
    .join("");
  return cards || '<div class="empty">No recipes match.</div>';
}

window.__toggleRecipes = (open) => {
  document.querySelectorAll("#recipe-list details.recipe").forEach((d) => {
    if (open) d.setAttribute("open", "");
    else d.removeAttribute("open");
  });
};

window.__setCookbookMode = (mode) => {
  cookbookMode = mode;
  document.querySelectorAll(".mode-filter button").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  el("recipe-list").innerHTML = recipeListHtml();
};

function showCookbook() {
  const d = state.data;
  const all = d.recipes || [];
  const interactive = all.filter((r) => recipeMode(r) === "interactive").length;
  const batch = all.length - interactive;
  const btn = (mode, label, n) =>
    `<button data-mode="${mode}" class="${cookbookMode === mode ? "active" : ""}" onclick="window.__setCookbookMode('${mode}')">${label} (${n})</button>`;
  el("detail").innerHTML = `
    <h2>${esc(d.product_name)} — Cookbook</h2>
    <p class="sub">${all.length} recipes · ready-to-run query templates from the standard's Memory module</p>
    <div class="cookbook-toolbar">
      <input id="cookbook-search" class="cookbook-search" type="search" placeholder="Search recipes…" value="${esc(cookbookQuery)}" />
      <div class="mode-filter">
        ${btn("all", "All", all.length)}
        ${btn("interactive", "Interactive", interactive)}
        ${btn("batch", "Batch", batch)}
      </div>
      <div class="cookbook-tools">
        <button onclick="window.__toggleRecipes(true)">Expand all</button>
        <button onclick="window.__toggleRecipes(false)">Collapse all</button>
      </div>
    </div>
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

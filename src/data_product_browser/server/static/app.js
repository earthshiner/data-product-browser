"use strict";

// Data Product Browser — step 1 frontend.
// Fetches a DataProduct snapshot from the API and renders a navigable
// module/entity tree with a per-entity schema detail pane. Deterministic:
// everything shown is read straight from the metadata, no AI in the loop.

const state = {
  product: null,
  data: null, // the DataProduct object
  activeEntity: null, // entity_metadata_key
  activeTab: "schema",
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
      products.map((p) => `<option value="${p}">${p}</option>`).join("");
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
    renderTree();
    el("detail").innerHTML =
      '<div class="empty">Select an entity from the left to view its schema.</div>';
    renderWarnings();
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
      item.className = "entity" + (e.entity_metadata_key === state.activeEntity ? " active" : "");
      const cols = columnsFor(e).length;
      item.innerHTML = `<span>${e.entity_name}</span><span class="count">${cols}</span>`;
      item.onclick = () => selectEntity(e.entity_metadata_key);
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
  renderTree();
  const entity = state.data.entities.find((e) => e.entity_metadata_key === key);
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
  if (target) selectEntity(target.entity_metadata_key);
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
    if (sameTable(r.from_database, r.from_table, entity)) {
      out.push({ dir: "→", thisCol: r.from_column, db: r.to_database, table: r.to_table, col: r.to_column, r });
    } else if (sameTable(r.to_database, r.to_table, entity)) {
      out.push({ dir: "←", thisCol: r.to_column, db: r.from_database, table: r.from_table, col: r.from_column, r });
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

// --- detail pane -------------------------------------------------------------

function renderEntity(entity) {
  const counts = {
    schema: columnsFor(entity).length,
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
      <dt>Category</dt><dd>${esc(entity.entity_category) || "—"}</dd>
      <dt>Natural key</dt><dd><code>${esc(entity.natural_key_column) || "—"}</code></dd>
      <dt>Approx. rows</dt><dd>${entity.record_count_approx ?? "—"}</dd>
    </dl>
    <div class="tabs">
      ${tab("schema", "Schema")}${tab("relationships", "Relationships")}
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
  else if (state.activeTab === "relationships") body.innerHTML = relationshipsHTML(entity) || empty("No relationships defined.");
  else if (state.activeTab === "glossary") body.innerHTML = glossaryHTML(entity) || empty("No glossary terms reference this entity.");
  else if (state.activeTab === "decisions") body.innerHTML = decisionsHTML(entity) || empty("No design decisions affect this entity.");
}

function schemaHTML(entity) {
  const rows = columnsFor(entity)
    .map((c) => {
      const tags =
        (c.is_pii ? '<span class="tag pii">PII</span>' : "") +
        (c.is_required ? '<span class="tag req">REQUIRED</span>' : "");
      return `<tr>
        <td class="col-name">${esc(c.column_name)}${tags}</td>
        <td><code>${esc(c.data_type) || "—"}</code></td>
        <td class="desc">${esc(c.business_description) || ""}</td>
        <td class="desc">${esc(c.sample_values) || ""}</td>
      </tr>`;
    })
    .join("");
  return `<table>
      <thead><tr><th>Column</th><th>Type</th><th>Description</th><th>Samples</th></tr></thead>
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
          <span class="pill">${esc(x.r.relationship_type)}</span>
          ${x.r.cardinality ? `<span class="pill">${esc(x.r.cardinality)}</span>` : ""}
          <span class="pill">${esc(x.r.join_type)} JOIN</span>
          ${x.r.is_mandatory ? '<span class="pill">mandatory</span>' : ""}
        </div>
        ${x.r.relationship_desc ? `<p class="desc">${esc(x.r.relationship_desc)}</p>` : ""}
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

el("product-select").addEventListener("change", (e) => loadProduct(e.target.value));
el("filter").addEventListener("input", () => state.data && renderTree());

loadProductList();

"use strict";

// Data Product Browser — step 1 frontend.
// Fetches a DataProduct snapshot from the API and renders a navigable
// module/entity tree with a per-entity schema detail pane. Deterministic:
// everything shown is read straight from the metadata, no AI in the loop.

const state = {
  product: null,
  data: null, // the DataProduct object
  activeEntity: null, // entity_metadata_key
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
}

function esc(s) {
  return (s ?? "").toString().replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
}

function renderEntity(entity) {
  const cols = columnsFor(entity);
  const rows = cols
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
    <table>
      <thead><tr><th>Column</th><th>Type</th><th>Description</th><th>Samples</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="4" class="desc">No column metadata.</td></tr>'}</tbody>
    </table>`;
}

el("product-select").addEventListener("change", (e) => loadProduct(e.target.value));
el("filter").addEventListener("input", () => state.data && renderTree());

loadProductList();

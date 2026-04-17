const els = {
  apiBase: document.getElementById("apiBase"),
  source: document.getElementById("source"),
  limit: document.getElementById("limit"),
  removeStopwords: document.getElementById("removeStopwords"),
  queryMode: document.getElementById("queryMode"),
  topicQid: document.getElementById("topicQid"),
  topicField: document.getElementById("topicField"),
  topK: document.getElementById("topK"),
  nodeWeight: document.getElementById("nodeWeight"),
  edgeWeight: document.getElementById("edgeWeight"),
  queryText: document.getElementById("queryText"),
  loadBtn: document.getElementById("loadBtn"),
  statusBtn: document.getElementById("statusBtn"),
  searchBtn: document.getElementById("searchBtn"),
  evalBtn: document.getElementById("evalBtn"),
  statusBox: document.getElementById("statusBox"),
  metrics: document.getElementById("metrics"),
  resultRows: document.getElementById("resultRows"),
};

const LS_KEY = "graph_ir_api_base";
els.apiBase.value = localStorage.getItem(LS_KEY) || "";

function getApiBase() {
  return els.apiBase.value.replace(/\/+$/, "");
}

function showStatus(value, isError = false) {
  els.statusBox.textContent = value;
  els.statusBox.classList.toggle("error", isError);
}

function toNum(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

async function apiFetch(path, options = {}) {
  const base = getApiBase();
  if (!base) {
    throw new Error("Please enter Render API base URL first.");
  }
  localStorage.setItem(LS_KEY, base);

  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data?.detail || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function renderMetrics(items) {
  if (!items || !items.length) {
    els.metrics.innerHTML = "";
    return;
  }
  els.metrics.innerHTML = items
    .map(
      (item) => `
      <div class="metric">
        <div class="label">${item.label}</div>
        <div class="value">${item.value}</div>
      </div>
    `
    )
    .join("");
}

function renderRows(results) {
  if (!results || !results.length) {
    els.resultRows.innerHTML = `<tr><td colspan="5" class="muted">No results.</td></tr>`;
    return;
  }
  els.resultRows.innerHTML = results
    .map(
      (r) => `
      <tr>
        <td>${r.docno}</td>
        <td>${Number(r.score).toFixed(4)}</td>
        <td>${Number(r.node_similarity).toFixed(4)}</td>
        <td>${Number(r.edge_similarity).toFixed(4)}</td>
        <td>${r.title || "(no title)"}</td>
      </tr>
    `
    )
    .join("");
}

async function refreshTopics() {
  try {
    const data = await apiFetch("/api/v1/topics?limit=300");
    const topics = data?.topics || [];
    if (!topics.length) {
      els.topicQid.innerHTML = `<option value="">(no topics loaded)</option>`;
      return;
    }

    els.topicQid.innerHTML = topics
      .map((t) => {
        const title = (t.title || t.description || "").slice(0, 70);
        const loadedRel = Number(t.relevant_in_loaded_subset ?? 0);
        const totalRel = Number(t.relevant_total_qrels ?? 0);
        const relTag = totalRel > 0 ? ` [rel:${loadedRel}/${totalRel}]` : "";
        return `<option value="${t.qid}">${t.qid}${relTag}${title ? " - " + title : ""}</option>`;
      })
      .join("");

    const firstUsable = topics.find((t) => Number(t.relevant_in_loaded_subset ?? 0) > 0);
    if (firstUsable?.qid) {
      els.topicQid.value = String(firstUsable.qid);
    }
  } catch {
    els.topicQid.innerHTML = `<option value="">(topics unavailable)</option>`;
  }
}

async function loadCorpus() {
  try {
    showStatus("Loading corpus...");
    const payload = {
      source: els.source.value,
      limit: toNum(els.limit.value, 1000),
      remove_stopwords: els.removeStopwords.checked,
    };
    const data = await apiFetch("/api/v1/corpus/load", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showStatus(JSON.stringify(data.status, null, 2));
    await refreshTopics();
  } catch (err) {
    renderMetrics([]);
    showStatus(err.message, true);
  }
}

async function checkStatus() {
  try {
    showStatus("Checking status...");
    const data = await apiFetch("/api/v1/status");
    showStatus(JSON.stringify(data, null, 2));
  } catch (err) {
    showStatus(err.message, true);
  }
}

async function runSearch() {
  try {
    showStatus("Running retrieval...");
    const payload = {
      source: els.source.value,
      limit: toNum(els.limit.value, 1000),
      remove_stopwords: els.removeStopwords.checked,
      query: els.queryText.value,
      top_k: toNum(els.topK.value, 5),
      node_weight: toNum(els.nodeWeight.value, 0.7),
      edge_weight: toNum(els.edgeWeight.value, 0.3),
      qid: els.queryMode.value === "topic" ? els.topicQid.value || null : null,
      topic_field: els.topicField.value,
    };
    const data = await apiFetch("/api/v1/search", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    renderRows(data.results || []);
    renderMetrics([
      { label: "Source", value: data.source || "-" },
      { label: "Query Nodes", value: data.query_nodes ?? 0 },
      { label: "Query Relations", value: data.query_relations ?? 0 },
      { label: "Top-K", value: data.top_k ?? payload.top_k },
    ]);
    showStatus(JSON.stringify(data.status, null, 2));
  } catch (err) {
    renderRows([]);
    showStatus(err.message, true);
  }
}

async function runEvaluation() {
  try {
    if (els.source.value !== "trec-covid") {
      throw new Error("Evaluation is available only for trec-covid source.");
    }
    if (els.queryMode.value !== "topic") {
      throw new Error("Switch Query Mode to 'topic' for evaluation.");
    }

    const qid = els.topicQid.value;
    if (!qid) {
      throw new Error("Select a qid to evaluate.");
    }

    showStatus("Evaluating...");
    const payload = {
      source: els.source.value,
      limit: toNum(els.limit.value, 1000),
      remove_stopwords: els.removeStopwords.checked,
      qid,
      auto_pick_qid: true,
      topic_field: els.topicField.value,
      top_k: toNum(els.topK.value, 5),
      node_weight: toNum(els.nodeWeight.value, 0.7),
      edge_weight: toNum(els.edgeWeight.value, 0.3),
    };
    const data = await apiFetch("/api/v1/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    renderMetrics([
      { label: "QID Used", value: data.qid || "-" },
      { label: `Precision@${data.top_k}`, value: Number(data.precision_at_k).toFixed(4) },
      { label: `Recall@${data.top_k}`, value: Number(data.recall_at_k).toFixed(4) },
      { label: `F1@${data.top_k}`, value: Number(data.f1_at_k).toFixed(4) },
      {
        label: "Relevant Docs (Loaded/Total)",
        value: `${data.relevant_docs_in_loaded_subset ?? 0}/${data.relevant_docs_total_qrels ?? 0}`,
      },
    ]);
    const statusParts = [];
    if (data.auto_selection_reason) {
      statusParts.push(`Auto-QID: ${data.auto_selection_reason}`);
    }
    statusParts.push(JSON.stringify(data.status, null, 2));
    showStatus(statusParts.join("\n\n"));
  } catch (err) {
    renderMetrics([]);
    showStatus(err.message, true);
  }
}

els.loadBtn.addEventListener("click", loadCorpus);
els.statusBtn.addEventListener("click", checkStatus);
els.searchBtn.addEventListener("click", runSearch);
els.evalBtn.addEventListener("click", runEvaluation);
els.source.addEventListener("change", () => {
  if (els.source.value !== "trec-covid") {
    els.queryMode.value = "custom";
  }
});

checkStatus();

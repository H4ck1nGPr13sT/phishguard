/*
 * PhishGuard web UI — single-sample analysis flow (paste + file upload).
 *
 * CSP constraint: `default-src 'self'` with no inline scripts allowed
 * (see src/web/templates/index.html and the security-headers middleware).
 * This file is the ONLY place JS may live; there must be no inline
 * <script> blocks and no inline event-handler attributes in the HTML.
 *
 * XSS rule (non-negotiable): every piece of user-supplied or
 * model-returned text (pasted URL/email/SMS text, explanation, rule
 * matched_values, content previews, error messages, etc.) is rendered
 * using `el.textContent = ...` or by building elements with
 * `document.createElement` + `textContent` ONLY. This file must never
 * use raw-HTML-injection DOM sinks (the "set markup from a string"
 * property, the "insert adjacent markup" method, or the document-level
 * streaming-write API) anywhere — a contract test enforces this at the
 * served-asset level.
 */

/* ---------------------------------------------------------------------
 * Response normalization
 * ------------------------------------------------------------------- */

/**
 * Normalize the two response shapes (MultiParadigmResponse and
 * EmailSMSResponse) into a single view model used by renderResult().
 */
function normalize(d) {
  const probability = d.final_probability ?? d.phishing_probability ?? d.ensemble_probability;
  const prediction = d.final_prediction ?? d.prediction ?? d.ensemble_prediction;
  const confidence = d.confidence ?? d.ensemble_confidence;
  const explanation = d.explanation ?? "";
  const rules = d.active_rules ?? [];
  return {
    prediction: prediction,
    probability: probability,
    confidence: confidence,
    explanation: explanation,
    rules: rules,
    contentType: d.content_type ?? "url",
  };
}

/**
 * Derive a Low/Medium/High/Critical severity band label from a
 * phishing probability in [0, 1]. These are UI presentation bands only
 * (see the footer disclaimer in index.html) — not a calibrated risk
 * score.
 *
 * Thresholds: p < 0.25 -> Low; p < 0.5 -> Medium; p < 0.75 -> High;
 * otherwise -> Critical.
 */
function severityBand(p) {
  if (p < 0.25) return "Low";
  if (p < 0.5) return "Medium";
  if (p < 0.75) return "High";
  return "Critical";
}

/* ---------------------------------------------------------------------
 * Network helpers
 * ------------------------------------------------------------------- */

/**
 * POST JSON body to `url`, parse the JSON response, and throw a plain
 * Error with a STRING message on failure. FastAPI 422 responses return
 * `detail` as an array of objects — never surface that object directly
 * (it would render as "[object Object]"); fall back to a generic
 * message instead.
 */
async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data && data.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Request failed (" + resp.status + ")"
    );
  }
  return data;
}

/**
 * POST a File as multipart/form-data to `url`. Never set a manual
 * Content-Type header — the browser must generate the multipart
 * boundary itself, or the upload will be malformed server-side.
 */
async function postForm(url, file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(url, {
    method: "POST",
    body: form,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data && data.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Request failed (" + resp.status + ")"
    );
  }
  return data;
}

/* ---------------------------------------------------------------------
 * Safe DOM rendering
 * ------------------------------------------------------------------- */

/** Set an element's text content safely (never via a raw-markup sink). */
function setText(el, s) {
  el.textContent = String(s);
}

/**
 * Clear #result and render the normalized view model into it using
 * only textContent/createElement — never a raw-markup sink.
 */
function renderResult(view) {
  const result = document.getElementById("result");
  result.replaceChildren();

  const verdictEl = document.createElement("p");
  verdictEl.className = "result-verdict";
  const verdictLabel = document.createElement("strong");
  setText(verdictLabel, view.prediction === "phishing" ? "Phishing" : "Legitimate");
  verdictEl.appendChild(verdictLabel);
  result.appendChild(verdictEl);

  const band = severityBand(view.probability);
  const bandEl = document.createElement("span");
  bandEl.className = "sev-" + band.toLowerCase();
  setText(bandEl, band + " severity");
  const bandWrap = document.createElement("p");
  bandWrap.className = "result-severity";
  bandWrap.appendChild(bandEl);
  result.appendChild(bandWrap);

  const confidenceEl = document.createElement("p");
  confidenceEl.className = "result-confidence";
  const confidencePct =
    typeof view.confidence === "number" ? (view.confidence * 100).toFixed(1) + "%" : "n/a";
  setText(confidenceEl, "Certainty of verdict: " + confidencePct);
  result.appendChild(confidenceEl);

  if (view.explanation) {
    const explanationEl = document.createElement("p");
    explanationEl.className = "result-explanation";
    setText(explanationEl, view.explanation);
    result.appendChild(explanationEl);
  }

  if (view.rules && view.rules.length > 0) {
    const rulesHeading = document.createElement("h3");
    setText(rulesHeading, "Fired rules");
    result.appendChild(rulesHeading);

    const rulesList = document.createElement("ul");
    rulesList.className = "result-rules";
    for (const rule of view.rules) {
      const item = document.createElement("li");

      const nameEl = document.createElement("strong");
      setText(nameEl, rule.name ?? "");
      item.appendChild(nameEl);

      if (rule.description) {
        const descEl = document.createElement("span");
        setText(descEl, " — " + rule.description);
        item.appendChild(descEl);
      }

      const weightEl = document.createElement("span");
      setText(weightEl, " (weight " + rule.weight + ")");
      item.appendChild(weightEl);

      if (rule.matched_values && rule.matched_values.length > 0) {
        const matchedEl = document.createElement("div");
        matchedEl.className = "result-rule-matched";
        setText(matchedEl, "Matched: " + rule.matched_values.join(", "));
        item.appendChild(matchedEl);
      }

      rulesList.appendChild(item);
    }
    result.appendChild(rulesList);
  }

  result.hidden = false;
}

/** Render a plain-text error message into #result (textContent only). */
function renderError(message) {
  const result = document.getElementById("result");
  result.replaceChildren();
  const errorEl = document.createElement("p");
  errorEl.className = "result-error";
  setText(errorEl, message);
  result.appendChild(errorEl);
  result.hidden = false;
}

/* ---------------------------------------------------------------------
 * Paste-text flow (url/email/sms)
 * ------------------------------------------------------------------- */

async function analyzePastedInput() {
  const typeSelect = document.getElementById("input-type");
  const textArea = document.getElementById("input-text");
  const type = typeSelect.value;
  const text = textArea.value;

  try {
    let data;
    if (type === "url") {
      data = await postJSON("/predict/multi-paradigm", { url: text });
    } else if (type === "email") {
      data = await postJSON("/predict/email", { raw_email: text });
    } else if (type === "sms") {
      data = await postJSON("/predict/sms", { message: text });
    } else {
      throw new Error("Unknown content type");
    }
    renderResult(normalize(data));
  } catch (err) {
    const message = err && err.message ? err.message : "";
    if (message.toLowerCase().includes("field required") || message === "") {
      renderError("Invalid input for " + type);
    } else {
      renderError(message);
    }
  }
}

/* ---------------------------------------------------------------------
 * File-upload flow (.eml / image)
 * ------------------------------------------------------------------- */

async function analyzeEmlFile() {
  const input = document.getElementById("file-eml");
  const file = input.files && input.files[0];
  if (!file) {
    renderError("Choose an .eml file first");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".eml")) {
    renderError("Invalid file type: expected .eml");
    return;
  }
  try {
    const data = await postForm("/predict/email/file", file);
    renderResult(normalize(data));
  } catch (err) {
    renderError(err && err.message ? err.message : "Email file analysis failed");
  }
}

async function analyzeImageFile() {
  const input = document.getElementById("file-image");
  const file = input.files && input.files[0];
  if (!file) {
    renderError("Choose an image file first");
    return;
  }
  const lowerName = file.name.toLowerCase();
  const allowedExt = lowerName.endsWith(".png") || lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg");
  if (!allowedExt) {
    renderError("Invalid file type: expected .png, .jpg, or .jpeg");
    return;
  }
  try {
    const data = await postForm("/predict/image", file);
    renderResult(normalize(data));
  } catch (err) {
    renderError(err && err.message ? err.message : "Image analysis failed");
  }
}

/* ---------------------------------------------------------------------
 * Batch (CSV) flow — upload, poll, incremental results table
 * ------------------------------------------------------------------- */

const BATCH_POLL_INTERVAL_MS = 1000;

let batchPollTimer = null;
let batchPollInFlight = false;
let batchRowsRendered = 0;

/** Show a generic error message in the batch area (textContent only). */
function renderBatchError(message) {
  const errorEl = document.getElementById("batch-error");
  setText(errorEl, message);
  errorEl.hidden = false;
}

function clearBatchError() {
  const errorEl = document.getElementById("batch-error");
  errorEl.hidden = true;
  setText(errorEl, "");
}

/** Build the results table skeleton once via createElement and append
 * it into #batch-results (cleared first). Returns the <tbody> to append
 * rows into. */
function buildBatchResultsTable() {
  const container = document.getElementById("batch-results");
  container.replaceChildren();

  const scrollWrap = document.createElement("div");
  scrollWrap.className = "table-scroll";

  const table = document.createElement("table");
  table.className = "results-table";
  table.id = "batch-results-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const label of ["Row", "Type", "Content", "Verdict", "Probability", "Error"]) {
    const th = document.createElement("th");
    setText(th, label);
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  table.appendChild(tbody);

  scrollWrap.appendChild(table);
  container.appendChild(scrollWrap);

  return tbody;
}

/** Update the progress bar + text (numeric values only). */
function updateBatchProgress(done, total) {
  const progressWrap = document.getElementById("batch-progress");
  const bar = document.getElementById("batch-progress-bar");
  const text = document.getElementById("batch-progress-text");
  progressWrap.hidden = false;
  bar.max = total > 0 ? total : 1;
  bar.value = done;
  setText(text, done + " / " + total);
}

/** Append one result row via textContent/createElement only (row data —
 * content_preview / error — is attacker-controlled CSV content). */
function appendBatchRow(tbody, row) {
  const tr = document.createElement("tr");
  if (row.error) {
    tr.className = "batch-row-error";
  }

  const rowCell = document.createElement("td");
  setText(rowCell, row.row);
  tr.appendChild(rowCell);

  const typeCell = document.createElement("td");
  setText(typeCell, row.type ?? "");
  tr.appendChild(typeCell);

  const contentCell = document.createElement("td");
  setText(contentCell, row.content_preview ?? "");
  tr.appendChild(contentCell);

  const verdictCell = document.createElement("td");
  setText(verdictCell, row.prediction ?? "");
  tr.appendChild(verdictCell);

  const probCell = document.createElement("td");
  if (typeof row.probability === "number" && !row.error) {
    const band = severityBand(row.probability);
    const chip = document.createElement("span");
    chip.className = "sev-" + band.toLowerCase();
    setText(chip, (row.probability * 100).toFixed(1) + "% " + band);
    probCell.appendChild(chip);
  } else {
    setText(probCell, "n/a");
  }
  tr.appendChild(probCell);

  const errorCell = document.createElement("td");
  setText(errorCell, row.error ?? "");
  tr.appendChild(errorCell);

  tbody.appendChild(tr);
}

function stopBatchPolling() {
  if (batchPollTimer !== null) {
    clearTimeout(batchPollTimer);
    batchPollTimer = null;
  }
}

/** One polling tick: GET /batch/{id}?offset=<rowsRendered>, append new
 * rows, update progress, and either schedule the next tick or stop. */
async function pollBatchJob(jobId, tbody) {
  if (batchPollInFlight) {
    return;
  }
  batchPollInFlight = true;
  try {
    const resp = await fetch("/batch/" + jobId + "?offset=" + batchRowsRendered);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const detail = data && data.detail;
      renderBatchError(typeof detail === "string" ? detail : "Batch status check failed");
      stopBatchPolling();
      return;
    }

    updateBatchProgress(data.done ?? 0, data.total ?? 0);

    const rows = data.rows ?? [];
    for (const row of rows) {
      appendBatchRow(tbody, row);
    }
    batchRowsRendered += rows.length;

    if (data.status === "done") {
      stopBatchPolling();
    } else if (data.status === "failed") {
      renderBatchError("Batch processing failed");
      stopBatchPolling();
    } else {
      batchPollTimer = setTimeout(() => pollBatchJob(jobId, tbody), BATCH_POLL_INTERVAL_MS);
    }
  } catch (err) {
    renderBatchError("Batch status check failed");
    stopBatchPolling();
  } finally {
    batchPollInFlight = false;
  }
}

async function analyzeCsvBatch() {
  const input = document.getElementById("file-csv");
  const file = input.files && input.files[0];
  clearBatchError();

  if (!file) {
    renderBatchError("Choose a .csv file first");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".csv")) {
    renderBatchError("Invalid file type: expected .csv");
    return;
  }

  stopBatchPolling();
  batchRowsRendered = 0;

  let data;
  try {
    data = await postForm("/batch", file);
  } catch (err) {
    renderBatchError(err && err.message ? err.message : "Batch upload failed");
    return;
  }

  const jobId = data.job_id;
  const total = data.total ?? 0;
  updateBatchProgress(0, total);
  const tbody = buildBatchResultsTable();

  pollBatchJob(jobId, tbody);
}

/* ---------------------------------------------------------------------
 * Bindings
 * ------------------------------------------------------------------- */

function initSingleSampleFlow() {
  const form = document.getElementById("analyze-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      analyzePastedInput();
    });
  }

  const emlBtn = document.getElementById("analyze-eml-btn");
  if (emlBtn) {
    emlBtn.addEventListener("click", (event) => {
      event.preventDefault();
      analyzeEmlFile();
    });
  }

  const imageBtn = document.getElementById("analyze-image-btn");
  if (imageBtn) {
    imageBtn.addEventListener("click", (event) => {
      event.preventDefault();
      analyzeImageFile();
    });
  }

  const batchBtn = document.getElementById("batch-btn");
  if (batchBtn) {
    batchBtn.addEventListener("click", (event) => {
      event.preventDefault();
      analyzeCsvBatch();
    });
  }
}

document.addEventListener("DOMContentLoaded", initSingleSampleFlow);

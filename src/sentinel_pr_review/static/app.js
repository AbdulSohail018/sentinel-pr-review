import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
});

const sampleDiff = `diff --git a/app/auth.py b/app/auth.py
index 1111111..2222222 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -10,3 +10,8 @@ def login(username, password):
     user = db.execute(f"SELECT * FROM users WHERE name='{username}'")
+    api_key = "sk-live-1234567890"
+    for row in user:
+        if row.password == password:
+            return issue_token(row)
     return None
`;

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");
const healthPill = document.getElementById("health-pill");
const agentsNode = document.getElementById("agents");
const labelsNode = document.getElementById("labels");
const commentPreview = document.getElementById("comment-preview");
const recommendationNode = document.getElementById("metric-recommendation");
const riskNode = document.getElementById("metric-risk");
const costNode = document.getElementById("metric-cost");

async function renderArchitecture() {
  const diagram = document.getElementById("architecture-diagram");
  if (!diagram || diagram.dataset.rendered === "true") {
    return;
  }
  const { svg } = await mermaid.render("sentinel-architecture", diagram.textContent.trim());
  diagram.innerHTML = svg;
  diagram.dataset.rendered = "true";
}

function setActivePanel(panelId) {
  tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.panel === panelId);
  });
  panels.forEach((panel) => {
    panel.classList.toggle("active", panel.id === panelId);
  });
  if (panelId === "architecture-panel") {
    void renderArchitecture();
  }
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setActivePanel(tab.dataset.panel));
});

function severityClass(severity) {
  return severity.toLowerCase();
}

function renderLabels(labels) {
  labelsNode.innerHTML = "";
  if (!labels.length) {
    return;
  }
  labels.forEach((label) => {
    const badge = document.createElement("span");
    badge.className = "badge low";
    badge.textContent = label;
    labelsNode.appendChild(badge);
  });
}

function renderFindings(findings) {
  if (!findings.length) {
    return "<p>No findings for this agent.</p>";
  }
  return findings
    .map(
      (finding) => `
        <article class="finding-card">
          <header>
            <strong>${finding.title}</strong>
            <span class="badge ${severityClass(finding.severity)}">${finding.severity}</span>
          </header>
          <p>${finding.evidence}</p>
          <small>Confidence ${finding.confidence.toFixed(2)}${
            finding.file ? ` · ${finding.file}:${finding.line_start ?? "?"}` : ""
          }</small>
        </article>
      `
    )
    .join("");
}

function renderAgents(agentRuns) {
  agentsNode.classList.remove("empty-state");
  agentsNode.innerHTML = agentRuns
    .map(
      (agent) => `
        <article class="agent-card">
          <header>
            <strong>${agent.agent}</strong>
            <span class="badge ${agent.invoked ? "low" : "medium"}">${
              agent.invoked ? "invoked" : "skipped"
            }</span>
          </header>
          <p>${agent.reason}</p>
          <small>Tokens ${agent.token_usage}/${agent.token_budget}</small>
          ${renderFindings(agent.findings)}
        </article>
      `
    )
    .join("");
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error("health check failed");
    }
    healthPill.textContent = "API ready";
  } catch (_error) {
    healthPill.textContent = "API unavailable";
  }
}

async function runReview() {
  const payload = {
    title: document.getElementById("title").value,
    description: document.getElementById("description").value,
    diff: document.getElementById("diff").value,
    confidence_threshold: Number(document.getElementById("confidence").value),
    seed: Number(document.getElementById("seed").value),
  };

  const response = await fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    commentPreview.textContent = "Review request failed. Check the diff input and try again.";
    return;
  }

  const data = await response.json();
  recommendationNode.textContent = data.recommendation;
  riskNode.textContent = data.risk_assessment;
  costNode.textContent = `$${data.cost_report_usd.toFixed(4)}`;
  renderLabels(data.labels);
  renderAgents(data.agents);
  commentPreview.textContent = data.consolidated_comment_markdown;
}

document.getElementById("run-review").addEventListener("click", () => {
  void runReview();
});

document.getElementById("load-sample").addEventListener("click", () => {
  document.getElementById("diff").value = sampleDiff;
});

void checkHealth();

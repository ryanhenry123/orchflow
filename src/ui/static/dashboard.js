(() => {
  const viewport = document.getElementById("viewport");
  const canvas = document.getElementById("canvas");
  const edgesSvg = document.getElementById("pipeline-edges");
  const inspectorTitle = document.getElementById("inspector-title");
  const inspectorMeta = document.getElementById("inspector-meta");
  const inspectorBody = document.getElementById("inspector-body");
  const liveBadge = document.getElementById("live-badge");
  const fitViewBtn = document.getElementById("fit-view");

  if (!viewport || !canvas) {
    return;
  }

  let panX = 0;
  let panY = 0;
  let scale = 1;
  let dragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let panStartX = 0;
  let panStartY = 0;
  let selectedNode = null;
  let selectedWave = null;
  let edgeFrame = 0;

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  const allNodes = () => [...document.querySelectorAll(".stage-node")];

  const scheduleEdges = () => {
    if (edgeFrame) {
      return;
    }
    edgeFrame = requestAnimationFrame(() => {
      edgeFrame = 0;
      drawEdges();
    });
  };

  const applyTransform = () => {
    canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    scheduleEdges();
  };

  const formatLocalTimes = (root = document) => {
    for (const el of root.querySelectorAll("time.local-time")) {
      const iso = el.getAttribute("datetime");
      if (!iso) {
        continue;
      }
      const date = new Date(iso);
      el.textContent = date.toLocaleString(undefined, {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      el.title = date.toLocaleString();
    }
  };

  const formatDuration = (startedIso, finishedIso) => {
    if (!startedIso) {
      return "";
    }
    const start = new Date(startedIso).getTime();
    const end = finishedIso ? new Date(finishedIso).getTime() : Date.now();
    const seconds = Math.max(0, Math.round((end - start) / 1000));
    if (seconds < 60) {
      return `${seconds}s`;
    }
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  const updateDurations = () => {
    for (const run of document.querySelectorAll(".pipeline-run")) {
      const el = run.querySelector("[data-run-duration]");
      if (!el) {
        continue;
      }
      const label = formatDuration(
        run.dataset.started,
        run.dataset.finished || null,
      );
      el.textContent = label ? `· ${label}` : "";
    }
  };

  const ensureEdgeMarkers = () => {
    if (!edgesSvg || edgesSvg.querySelector("defs")) {
      return;
    }
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `
      <marker id="edge-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
        <path d="M0,0 L7,3.5 L0,7 Z" fill="#3d4b5f"></path>
      </marker>
      <marker id="edge-arrow-active" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
        <path d="M0,0 L7,3.5 L0,7 Z" fill="#42b4ff"></path>
      </marker>
    `;
    edgesSvg.appendChild(defs);
  };

  const nodeAnchor = (node, side) => {
    const canvasRect = canvas.getBoundingClientRect();
    const nodeRect = node.getBoundingClientRect();
    const x =
      side === "out"
        ? (nodeRect.right - canvasRect.left) / scale
        : (nodeRect.left - canvasRect.left) / scale;
    const y = (nodeRect.top - canvasRect.top + nodeRect.height / 2) / scale;
    return { x, y };
  };

  const drawEdges = () => {
    if (!edgesSvg) {
      return;
    }

    ensureEdgeMarkers();
    const defs = edgesSvg.querySelector("defs");
    edgesSvg.replaceChildren(defs ?? document.createDocumentFragment());
    if (!edgesSvg.querySelector("defs")) {
      ensureEdgeMarkers();
    }

    const selectedRunId = selectedNode?.dataset.runId ?? null;
    const selectedStep = selectedNode?.dataset.step ?? null;

    for (const run of document.querySelectorAll(".pipeline-run")) {
      const runId = run.dataset.runId;
      const nodes = new Map(
        [...run.querySelectorAll(".stage-node")].map((node) => [node.dataset.step, node]),
      );

      for (const node of nodes.values()) {
        const dependsOn = (node.dataset.dependsOn ?? "")
          .split(",")
          .map((dep) => dep.trim())
          .filter(Boolean);

        for (const dep of dependsOn) {
          const from = nodes.get(dep);
          const to = node;
          if (!from || !to) {
            continue;
          }

          const start = nodeAnchor(from, "out");
          const end = nodeAnchor(to, "in");
          const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
          const midX = (start.x + end.x) / 2;
          path.setAttribute(
            "d",
            `M ${start.x} ${start.y} C ${midX} ${start.y}, ${midX} ${end.y}, ${end.x} ${end.y}`,
          );

          const isActive =
            selectedRunId === runId &&
            (selectedStep === dep ||
              selectedStep === to.dataset.step ||
              from.classList.contains("wave-highlight") ||
              to.classList.contains("wave-highlight"));
          path.setAttribute(
            "marker-end",
            isActive ? "url(#edge-arrow-active)" : "url(#edge-arrow)",
          );
          if (isActive) {
            path.classList.add("active");
          }
          edgesSvg.appendChild(path);
        }
      }
    }
  };

  const renderInspector = (node) => {
    const title = node.querySelector("h3")?.textContent ?? "Stage";
    const caller = node.querySelector(".stage-caller")?.textContent ?? "";
    const status = node.querySelector(".step-badge")?.textContent ?? "";
    const evalRole = node.dataset.eval;
    const failRole = node.dataset.onFailure;
    const roles = [];
    if (evalRole) {
      roles.push(`eval · ${evalRole}`);
    }
    if (failRole) {
      roles.push(`fail · ${failRole}`);
    }
    const roleText = roles.length ? ` · ${roles.join(" · ")}` : "";
    const template = node.querySelector("template.stage-details");

    inspectorTitle.textContent = title;
    inspectorMeta.textContent = `${caller} · ${status}${roleText}`;
    inspectorBody.replaceChildren();
    if (template?.content) {
      inspectorBody.append(template.content.cloneNode(true));
    }
    formatLocalTimes(inspectorBody);
  };

  const clearWaveHighlight = () => {
    selectedWave = null;
    for (const node of document.querySelectorAll(".stage-node.wave-highlight")) {
      node.classList.remove("wave-highlight");
    }
    for (const chip of document.querySelectorAll(".wave-chip.selected")) {
      chip.classList.remove("selected");
    }
    scheduleEdges();
  };

  const highlightWave = (runEl, waveIndex, steps) => {
    if (!runEl) {
      return;
    }
    selectedWave = { runId: runEl.dataset.runId, index: waveIndex };
    for (const node of runEl.querySelectorAll(".stage-node")) {
      node.classList.toggle("wave-highlight", steps.includes(node.dataset.step));
    }
    for (const chip of runEl.querySelectorAll(".wave-chip")) {
      chip.classList.toggle("selected", Number(chip.dataset.wave) === waveIndex);
    }
    scheduleEdges();
  };

  const bindWaveChips = (runEl, waves) => {
    const running = waves?.find((wave) => wave.status === "running");
    for (const chip of runEl.querySelectorAll(".wave-chip")) {
      const waveIndex = Number(chip.dataset.wave);
      const wave = waves?.find((item) => item.index === waveIndex);
      chip.classList.toggle(
        "active",
        Boolean(running && running.index === waveIndex),
      );
      chip.onclick = (event) => {
        event.stopPropagation();
        if (!wave) {
          return;
        }
        if (
          selectedWave?.runId === runEl.dataset.runId &&
          selectedWave.index === waveIndex
        ) {
          clearWaveHighlight();
          return;
        }
        highlightWave(runEl, waveIndex, wave.steps);
      };
    }
  };

  const selectNode = (node) => {
    if (!node) {
      return;
    }
    clearWaveHighlight();
    selectedNode?.classList.remove("selected");
    selectedNode = node;
    selectedNode.classList.add("selected");
    renderInspector(node);
    scheduleEdges();
  };

  const selectRelative = (offset) => {
    const nodes = allNodes();
    if (!nodes.length) {
      return;
    }
    const index = selectedNode ? nodes.indexOf(selectedNode) : -1;
    const next = nodes[(index + offset + nodes.length) % nodes.length];
    selectNode(next);
    next.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  };

  for (const node of allNodes()) {
    node.addEventListener("click", (event) => {
      event.stopPropagation();
      selectNode(node);
    });
    node.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectNode(node);
      }
    });
  }

  const canPan = (target) =>
    !target.closest("button, a, input, textarea, select, .stage-node");

  viewport.addEventListener("mousedown", (event) => {
    if (event.button !== 0 || !canPan(event.target)) {
      return;
    }
    dragging = true;
    dragStartX = event.clientX;
    dragStartY = event.clientY;
    panStartX = panX;
    panStartY = panY;
    viewport.classList.add("grabbing");
  });

  window.addEventListener("mousemove", (event) => {
    if (!dragging) {
      return;
    }
    panX = panStartX + (event.clientX - dragStartX);
    panY = panStartY + (event.clientY - dragStartY);
    applyTransform();
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
    viewport.classList.remove("grabbing");
  });

  viewport.addEventListener(
    "wheel",
    (event) => {
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        const delta = event.deltaY > 0 ? -0.06 : 0.06;
        scale = clamp(scale + delta, 0.5, 1.5);
        applyTransform();
        return;
      }
      panX -= event.deltaX;
      panY -= event.deltaY;
      applyTransform();
    },
    { passive: false },
  );

  const fitView = () => {
    const target = document.querySelector(".pipeline-run") ?? document.querySelector(".empty-state");
    if (!target) {
      return;
    }
    scale = 1;
    const vp = viewport.getBoundingClientRect();
    const rect = target.getBoundingClientRect();
    panX = (vp.width - rect.width) / 2 - (rect.left - vp.left - panX);
    panY = Math.max(24, (vp.height - rect.height) / 2 - (rect.top - vp.top - panY));
    applyTransform();
  };

  fitViewBtn?.addEventListener("click", fitView);

  window.addEventListener("keydown", (event) => {
    if (event.target.closest("input, textarea, select, button")) {
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      selectRelative(1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      selectRelative(-1);
    } else if (event.key === "0") {
      fitView();
    } else if (event.key === "Escape") {
      clearWaveHighlight();
    } else if (event.key === "w" || event.key === "W") {
      const runEl =
        selectedNode?.closest(".pipeline-run") ??
        document.querySelector(".pipeline-run");
      if (!runEl) {
        return;
      }
      const chips = [...runEl.querySelectorAll(".wave-chip")];
      if (!chips.length) {
        return;
      }
      event.preventDefault();
      const currentIndex = selectedWave?.runId === runEl.dataset.runId
        ? chips.findIndex((chip) => Number(chip.dataset.wave) === selectedWave.index)
        : -1;
      const nextChip = chips[(currentIndex + 1) % chips.length];
      nextChip?.click();
    }
  });

  const statusClass = (node, status) => {
    node.classList.remove(
      "status-pending",
      "status-running",
      "status-completed",
      "status-skipped",
      "status-failed",
      "status-eval_failed",
      "status-handled",
    );
    node.classList.add(`status-${status}`);
    const badge = node.querySelector(".step-badge");
    if (badge) {
      badge.textContent = status.replace("_", " ");
      badge.className = `badge ${status} step-badge`;
    }
  };

  const renderEvents = (events) => {
    if (!events.length) {
      return '<p class="meta">Waiting for events.</p>';
    }
    const items = events
      .map((event) => {
        const detail = event.detail
          ? `<span class="notify-detail">${event.detail}</span>`
          : "";
        return `<li class="event-${event.phase}">
          <span class="badge notify-${event.phase}">${event.phase}</span>
          <time class="local-time" datetime="${event.at}"></time>
          ${detail}
        </li>`;
      })
      .join("");
    return `<ul class="notify-list">${items}</ul>`;
  };

  const renderRoleRail = (step) => {
    const chips = [];
    if (step.eval) {
      chips.push(`<span class="role-chip eval">eval · ${step.eval}</span>`);
    }
    if (step.on_failure) {
      chips.push(`<span class="role-chip failure">fail · ${step.on_failure}</span>`);
    }
    if (!chips.length) {
      return "";
    }
    return `<div class="role-rail detail-roles">${chips.join("")}</div>`;
  };

  const updateStepTemplate = (node, step) => {
    let template = node.querySelector("template.stage-details");
    if (!template) {
      template = document.createElement("template");
      template.className = "stage-details";
      node.append(template);
    }
    const upstream = step.depends_on?.length
      ? `<p class="meta">Upstream: ${step.depends_on.join(", ")}</p>`
      : "";
    const output = step.output
      ? `<div class="output-block"><h4>Output</h4><pre>${step.output}</pre></div>`
      : "";
    template.innerHTML = `${renderRoleRail(step)}${upstream}${output}<div class="notify-block"><h4>Events</h4>${renderEvents(step.events ?? [])}</div>`;
    if (step.eval) {
      node.dataset.eval = step.eval;
    }
    if (step.on_failure) {
      node.dataset.onFailure = step.on_failure;
    }
    statusClass(node, step.status);
  };

  const updateWaveRail = (runEl, waves) => {
    let rail = runEl.querySelector(".wave-rail");
    if (!waves?.length) {
      rail?.remove();
      return;
    }
    if (!rail) {
      rail = document.createElement("div");
      rail.className = "wave-rail";
      rail.setAttribute("aria-label", "Execution loops");
      runEl.querySelector(".pipeline-head")?.after(rail);
    }
    rail.innerHTML = waves
      .map(
        (wave) => `<button type="button" class="wave-chip status-${wave.status}" data-wave="${wave.index}" title="Highlight loop ${wave.index + 1}">
          <span class="wave-label">Loop ${wave.index + 1}</span>
          <span class="wave-steps">${wave.steps.join(" · ")}</span>
        </button>`,
      )
      .join("");
    bindWaveChips(runEl, waves);
  };

  const updateHistoryLinks = (history, runs) => {
    for (const runEl of document.querySelectorAll(".pipeline-run")) {
      const workflowName = runEl.querySelector(".run-history")?.dataset.workflowName
        ?? runEl.querySelector("h2")?.textContent?.trim();
      if (!workflowName) {
        continue;
      }
      const entries = history[workflowName] ?? [];
      let nav = runEl.querySelector(".run-history");
      if (entries.length <= 1) {
        nav?.remove();
        continue;
      }
      if (!nav) {
        nav = document.createElement("nav");
        nav.className = "run-history";
        nav.dataset.workflowName = workflowName;
        nav.setAttribute("aria-label", `${workflowName} run history`);
        runEl.querySelector(".pipeline-head div")?.append(nav);
      }
      const visibleRun = runs.find((run) => run.workflow_id === runEl.dataset.runId);
      const latestId = entries[0]?.workflow_id;
      const selected = document.body.dataset.selectedRun ?? "";
      const latestActive =
        !selected || visibleRun?.workflow_id === latestId;
      nav.innerHTML = `<a href="/" class="run-link${latestActive ? " active" : ""}">latest</a>${entries
        .map((entry) => {
          const active = entry.workflow_id === runEl.dataset.runId;
          const title = entry.started_at ? ` title="${entry.started_at}"` : "";
          return `<a href="/?run=${entry.workflow_id}" class="run-link${active ? " active" : ""}"${title}><code>${entry.workflow_id.slice(0, 8)}</code></a>`;
        })
        .join("")}`;
    }
  };

  const runsApiUrl = () => {
    const selected = document.body.dataset.selectedRun;
    return selected ? `/api/runs?run=${encodeURIComponent(selected)}` : "/api/runs";
  };

  const applyRuns = (payload) => {
    const runs = payload.runs ?? [];
    const history = payload.history ?? {};
    const visibleIds = runs
      .map((run) => run.workflow_id)
      .sort()
      .join(",");
    const currentIds = [...document.querySelectorAll(".pipeline-run")]
      .map((el) => el.dataset.runId)
      .sort()
      .join(",");
    if (visibleIds !== currentIds) {
      const selected = payload.selected ?? document.body.dataset.selectedRun ?? "";
      window.location.href = selected
        ? `/?run=${encodeURIComponent(selected)}`
        : "/";
      return;
    }

    updateHistoryLinks(history, runs);

    let anyRunning = false;
    for (const run of runs) {
      anyRunning ||= run.status === "running";
      const row = document.querySelector(`.pipeline-run[data-run-id="${run.workflow_id}"]`);
      if (!row) {
        continue;
      }
      row.classList.remove("status-running", "status-completed", "status-failed", "status-idle");
      row.classList.add(`status-${run.status}`);
      if (run.started_at) {
        row.dataset.started = run.started_at;
      }
      if (run.finished_at) {
        row.dataset.finished = run.finished_at;
      }
      const runBadge = row.querySelector(".run-badge");
      if (runBadge) {
        runBadge.textContent = run.status;
        runBadge.className = `badge ${run.status} run-badge`;
      }
      updateWaveRail(row, run.waves);
      for (const step of run.steps) {
        const node = row.querySelector(`.stage-node[data-step="${step.name}"]`);
        if (node) {
          updateStepTemplate(node, step);
        }
      }
    }

    if (liveBadge) {
      liveBadge.textContent = anyRunning ? "live" : "idle";
      liveBadge.classList.toggle("live", anyRunning);
    }
    document.body.dataset.live = anyRunning ? "true" : "false";

    updateDurations();
    if (selectedNode) {
      renderInspector(selectedNode);
    }
    scheduleEdges();
  };

  const pollRuns = async () => {
    if (document.body.dataset.live !== "true") {
      return;
    }
    try {
      const response = await fetch(runsApiUrl());
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      applyRuns(payload);
    } catch {
      /* ignore transient network errors */
    }
  };

  window.addEventListener("resize", scheduleEdges);
  formatLocalTimes();
  updateDurations();
  fitView();
  scheduleEdges();

  for (const runEl of document.querySelectorAll(".pipeline-run")) {
    const waves = [...runEl.querySelectorAll(".wave-chip")].map((chip) => ({
      index: Number(chip.dataset.wave),
      steps: (chip.querySelector(".wave-steps")?.textContent ?? "")
        .split("·")
        .map((step) => step.trim())
        .filter(Boolean),
      status: [...chip.classList]
        .find((name) => name.startsWith("status-"))
        ?.replace("status-", "") ?? "completed",
    }));
    bindWaveChips(runEl, waves);
  }

  const firstNode = document.querySelector(".stage-node");
  if (firstNode) {
    selectNode(firstNode);
  }

  setInterval(pollRuns, 1500);
  setInterval(updateDurations, 1000);
  pollRuns();
})();

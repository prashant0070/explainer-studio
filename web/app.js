const $ = (id) => document.getElementById(id);

let current = null;
let pollTimer = null;

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return res;
}

async function loadHealth() {
  try {
    const data = await (await api("/api/health")).json();
    const llm = data.llm_ready ? "LLM ready" : "Add LLM_API_KEY to generate scripts";
    const stock = data.stock_ready ? "stock footage on" : "free AI images";
    $("status").textContent = `${llm} · ${stock} · free voiceover · ${data.model}`;
    const voiceSel = $("voice");
    voiceSel.innerHTML = "";
    for (const voice of data.voices || []) {
      const opt = document.createElement("option");
      opt.value = voice.id;
      opt.textContent = voice.label;
      voiceSel.appendChild(opt);
    }
  } catch {
    $("status").textContent = "Server not reachable";
  }
}

async function loadRecent() {
  const data = await (await api("/api/projects")).json();
  const list = $("recent");
  list.innerHTML = "";
  const demoBtn = document.createElement("li");
  demoBtn.innerHTML = `<button class="ghost">Icarus demo</button>`;
  demoBtn.querySelector("button").onclick = () => openProject("demo-icarus");
  list.appendChild(demoBtn);
  for (const row of data.projects || []) {
    if (row.id === "demo-icarus") continue;
    const item = document.createElement("li");
    item.innerHTML = `<button class="ghost">${escapeHtml(row.title || row.topic)} · ${row.scene_count} scenes</button>`;
    item.querySelector("button").onclick = () => openProject(row.id);
    list.appendChild(item);
  }
}

async function openProject(id) {
  $("form-error").textContent = "";
  const project = await (await api(`/api/projects/${id}`)).json();
  renderPack(project);
  resumeRenderIfRunning(id);
}

function renderPack(project) {
  current = project;
  $("empty").hidden = true;
  $("pack").hidden = false;
  $("pack-style").textContent = project.style === "dark_vault" ? "Dark Vault" : "Odyssey explainer";
  $("pack-title").textContent = (project.titles && project.titles[0]) || project.topic;
  $("pack-meta").textContent = `${project.scenes.length} scenes · ${project.word_count} words · ~${Math.round(project.runtime_seconds / 60)} min`;
  $("pack-hook").textContent = project.hook;
  $("pack-thesis").textContent = project.thesis ? `Thesis: ${project.thesis}` : "";
  $("narration").textContent = project.full_narration;
  $("research").textContent = researchBlock(project);
  $("youtube").textContent = youtubeBlock(project);
  renderScenes(project);
  renderVideo(project);
}

function renderVideo(project) {
  const wrap = $("video-wrap");
  if (project.video_path) {
    wrap.hidden = false;
    const player = $("player");
    const src = `${project.video_path}?t=${Date.now()}`;
    if (!player.src.includes(project.video_path)) player.src = src;
    $("qc-report").innerHTML = qcBlock(project.qc);
  } else {
    wrap.hidden = true;
  }
}

function qcBlock(qc) {
  if (!qc) return "";
  const rows = (qc.checks || [])
    .map(
      (c) =>
        `<li class="qc-${c.status}"><strong>${escapeHtml(c.name)}</strong> — ${escapeHtml(c.detail)}</li>`
    )
    .join("");
  const review = qc.llm_review
    ? `<p class="qc-review">${escapeHtml(qc.llm_review)}</p>`
    : "";
  return `<p class="qc-verdict qc-${qc.verdict}">QC ${qc.verdict.toUpperCase()} · ${escapeHtml(qc.summary || "")}</p><ul>${rows}</ul>${review}`;
}

function researchBlock(project) {
  const r = project.research;
  if (!r) return "No auto-research stored for this project.";
  const parts = [];
  if (r.summary) parts.push(`OVERVIEW\n${r.summary}`);
  if (r.facts && r.facts.length) parts.push(`VERIFIED FACTS\n${r.facts.map((f) => `- ${f}`).join("\n")}`);
  if (r.timeline && r.timeline.length) parts.push(`TIMELINE\n${r.timeline.map((t) => `- ${t}`).join("\n")}`);
  if (r.disputed && r.disputed.length) parts.push(`DISPUTED\n${r.disputed.map((d) => `- ${d}`).join("\n")}`);
  if (r.sources && r.sources.length) parts.push(`SOURCES\n${r.sources.map((s) => `- ${s.title}: ${s.url}`).join("\n")}`);
  return parts.join("\n\n");
}

function renderScenes(project) {
  const root = $("scenes");
  root.innerHTML = "";
  if (project.thumbnail_prompt) {
    root.appendChild(sceneCard({
      id: "thumb",
      section: "thumbnail",
      visual_type: project.thumbnail_text || "title card",
      narration: (project.titles || []).join(" · "),
      image_prompt: project.thumbnail_prompt,
      image_path: project.thumbnail_path,
      duration_seconds: 0,
    }));
  }
  for (const scene of project.scenes) {
    root.appendChild(sceneCard(scene));
  }
}

function sceneCard(scene) {
  const el = document.createElement("article");
  el.className = "scene";
  const art = scene.image_path
    ? `<img src="${scene.image_path}" alt="" />`
    : "Prompt ready";
  const duration = scene.duration_seconds ? ` · ${scene.duration_seconds}s` : "";
  el.innerHTML = `
    <div class="scene-art">${art}</div>
    <div class="scene-body">
      <p class="scene-kicker">Scene ${scene.id}${duration} · ${escapeHtml(scene.visual_type)}</p>
      <p>${escapeHtml(scene.narration)}</p>
      <p class="prompt">${escapeHtml(scene.image_prompt)}</p>
    </div>`;
  return el;
}

function youtubeBlock(project) {
  const chapters = (project.chapters || []).map((c) => `${c.time} ${c.title}`).join("\n");
  const tags = (project.tags || []).join(", ");
  return `${(project.titles || [])[0] || ""}\n\n${project.youtube_description || ""}\n\n${chapters}\n\n${tags}`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// ------------------------------------------------------------ research ideas

$("ideas-btn").onclick = async () => {
  $("form-error").textContent = "";
  const niche = $("niche").value.trim();
  if (!niche) {
    $("form-error").textContent = "Describe your niche first";
    return;
  }
  $("ideas-btn").disabled = true;
  $("ideas-btn").textContent = "Researching…";
  try {
    const data = await (await api("/api/research/ideas", {
      method: "POST",
      body: JSON.stringify({ niche, count: 6 }),
    })).json();
    const list = $("ideas");
    list.innerHTML = "";
    for (const idea of data.ideas || []) {
      const item = document.createElement("li");
      item.innerHTML = `<button class="ghost" title="${escapeHtml(idea.why)}">${escapeHtml(idea.title || idea.topic)}</button>`;
      item.querySelector("button").onclick = () => {
        $("topic").value = idea.topic;
        $("style").value = idea.style === "dark_vault" ? "dark_vault" : "odyssey";
        $("angle").value = idea.hook || "";
      };
      list.appendChild(item);
    }
  } catch (err) {
    $("form-error").textContent = err.message;
  } finally {
    $("ideas-btn").disabled = false;
    $("ideas-btn").textContent = "Research topic ideas";
  }
};

// ------------------------------------------------------------------ generate

$("generate").onclick = async () => {
  $("form-error").textContent = "";
  $("generate").disabled = true;
  $("generate").textContent = $("auto-research").checked ? "Researching + writing…" : "Writing…";
  try {
    const project = await (await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({
        topic: $("topic").value,
        style: $("style").value,
        duration: $("duration").value,
        angle: $("angle").value,
        notes: $("notes").value,
        research: $("auto-research").checked,
      }),
    })).json();
    renderPack(project);
    await loadRecent();
  } catch (err) {
    $("form-error").textContent = err.message;
  } finally {
    $("generate").disabled = false;
    $("generate").textContent = "Generate script";
  }
};

$("demo").onclick = () => openProject("demo-icarus");

// -------------------------------------------------------------------- render

$("render-btn").onclick = async () => {
  if (!current) return;
  $("form-error").textContent = "";
  try {
    await api(`/api/projects/${current.id}/render`, {
      method: "POST",
      body: JSON.stringify({
        voice: $("voice").value,
        captions: $("opt-captions").checked,
        music: $("opt-music").checked,
        stock_video: true,
      }),
    });
    startPolling(current.id);
  } catch (err) {
    $("form-error").textContent = err.message;
  }
};

function startPolling(projectId) {
  stopPolling();
  $("render-progress").hidden = false;
  $("render-btn").disabled = true;
  pollTimer = setInterval(async () => {
    try {
      const status = await (await api(`/api/projects/${projectId}/render/status`)).json();
      updateProgress(status);
      if (status.state === "done" || status.state === "error") {
        stopPolling();
        $("render-btn").disabled = false;
        if (status.state === "done") {
          const project = await (await api(`/api/projects/${projectId}`)).json();
          renderPack(project);
        } else {
          $("form-error").textContent = status.message || "Render failed";
        }
      }
    } catch {
      /* transient poll failure — keep trying */
    }
  }, 2000);
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

function updateProgress(status) {
  const pct = Math.round((status.overall || 0) * 100);
  $("bar-fill").style.width = `${pct}%`;
  $("render-message").textContent = `${pct}% · ${status.stage || ""} — ${status.message || ""}`;
}

async function resumeRenderIfRunning(projectId) {
  try {
    const status = await (await api(`/api/projects/${projectId}/render/status`)).json();
    if (status.state === "running") {
      startPolling(projectId);
      updateProgress(status);
    } else {
      $("render-progress").hidden = status.state !== "done";
      if (status.state === "done") updateProgress(status);
    }
  } catch {
    /* no status yet */
  }
}

// -------------------------------------------------------------------- images

$("make-images").onclick = async () => {
  if (!current) return;
  $("form-error").textContent = "";
  $("make-images").disabled = true;
  $("make-images").textContent = "Rendering…";
  try {
    const data = await (await api(`/api/projects/${current.id}/images`, {
      method: "POST",
      body: JSON.stringify({ include_thumbnail: true, limit: 8 }),
    })).json();
    renderPack(data.project);
    if (data.errors && data.errors.length) {
      $("form-error").textContent = data.errors[0];
    }
  } catch (err) {
    $("form-error").textContent = err.message;
  } finally {
    $("make-images").disabled = false;
    $("make-images").textContent = "Generate 8 images";
  }
};

$("export").onclick = () => {
  if (!current) return;
  window.location.href = `/api/projects/${current.id}/export`;
};

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $("tab-scenes").hidden = btn.dataset.tab !== "scenes";
    $("tab-narration").hidden = btn.dataset.tab !== "narration";
    $("tab-research").hidden = btn.dataset.tab !== "research";
    $("tab-youtube").hidden = btn.dataset.tab !== "youtube";
  };
});

loadHealth();
loadRecent();

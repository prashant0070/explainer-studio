const $ = (id) => document.getElementById(id);

let current = null;

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
    const images = data.images_ready ? "images ready" : "no image key";
    $("status").textContent = `${llm} · ${images} · ${data.model}`;
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
  $("youtube").textContent = youtubeBlock(project);
  renderScenes(project);
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

$("generate").onclick = async () => {
  $("form-error").textContent = "";
  $("generate").disabled = true;
  $("generate").textContent = "Writing…";
  try {
    const project = await (await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({
        topic: $("topic").value,
        style: $("style").value,
        duration: $("duration").value,
        angle: $("angle").value,
        notes: $("notes").value,
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
    $("tab-youtube").hidden = btn.dataset.tab !== "youtube";
  };
});

loadHealth();
loadRecent();

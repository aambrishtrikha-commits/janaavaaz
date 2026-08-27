const api = (p, opt) => fetch("/api" + p, opt).then(async (r) => {
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
});

const $ = (id) => document.getElementById(id);

async function init() {
  const policy = await api("/policy");
  $("banner").textContent = policy.banner + " " + policy.gemini;
  const dist = await api("/districts");
  $("lgd").innerHTML =
    `<option value="">District (LGD)</option>` +
    dist.districts
      .map((d) => `<option value="${d.lgd_code}">${d.state_iso2} · ${d.name_en}${d.is_aspirational ? " · ADP" : ""}</option>`)
      .join("");
  document.querySelectorAll("nav button").forEach((b) => {
    b.onclick = () => {
      document.querySelectorAll("nav button").forEach((x) => x.classList.remove("on"));
      b.classList.add("on");
      document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
      document.getElementById("view-" + b.dataset.view).classList.remove("hidden");
      if (b.dataset.view === "officer") loadBoard();
      if (b.dataset.view === "packs") loadPacks();
    };
  });
  $("fileBtn").onclick = fileVoice;
}

function renderFile(rec) {
  $("filepad").classList.remove("hidden");
  $("pnr").textContent = rec.pnr;
  $("status").textContent = rec.status;
  $("rawOut").textContent = rec.raw_text;
  $("title").textContent = rec.brief?.title_en || "";
  $("brief").textContent = rec.brief?.brief_en || "";
  $("build").textContent = rec.brief?.build_case || "";
  $("dissent").textContent = rec.brief?.dissent || "";
  $("score").textContent = rec.score ? `Priority S = ${rec.score.score}` : "";
  $("glassLine").textContent = rec.glass
    ? `${rec.glass.model} · ${rec.glass.region} · tools: ${(rec.glass.tools_called || []).join(", ")}`
    : "";
  $("cites").innerHTML = (rec.brief?.citations || [])
    .map((c) => `<li><a href="${c.url}" target="_blank">${c.label}</a> · ${c.vintage}</li>`)
    .join("");
  $("echo").innerHTML = (rec.echo || [])
    .map((e) => `<p class="model">Echo · ${e.pnr} · ${e.line}</p>`)
    .join("");
}

async function fileVoice() {
  $("fileBtn").disabled = true;
  try {
    const rec = await api("/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_text: $("raw").value,
        source_lang: $("lang").value,
        lgd_code: $("lgd").value ? Number($("lgd").value) : null,
        client_request_id: crypto.randomUUID(),
      }),
    });
    renderFile(rec);
  } catch (err) {
    alert(err.message);
  } finally {
    $("fileBtn").disabled = false;
  }
}

async function loadBoard() {
  const data = await api("/board");
  $("board").innerHTML = (data.files.length ? data.files : data.all)
    .map((f) => {
      const s = f.score?.score ?? "—";
      return `<div class="card"><strong>${f.pnr}</strong> · ${f.status} · S=${s}<p>${f.hearing?.need_one_line || f.raw_text}</p><p class="red">${f.brief?.dissent || ""}</p><button onclick="decide('${f.ticket_id}','publish')">Publish</button><button onclick="decide('${f.ticket_id}','send_back')">Send back</button><button onclick="decide('${f.ticket_id}','merge')">Merge</button></div>`;
    })
    .join("");
}

async function decide(id, action) {
  const token = localStorage.getItem("ja_officer") || "jan-demo-board";
  await api(`/tickets/${id}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Officer-Token": token },
    body: JSON.stringify({ action, reason: "board" }),
  });
  loadBoard();
}

async function loadPacks() {
  const p = await api("/packs");
  $("packHealth").innerHTML = p.packs
    .map((x) => `<div class="card">${x.state_iso2} · ${x.state_name} · <b>${x.status}</b> · ${x.districts} districts · ${x.indicator_rows} cells</div>`)
    .join("");
  const h = await api("/hotspots");
  $("hot").innerHTML = h.hotspots
    .map((x) => `<div class="card">${x.state_iso2} ${x.name_en} · ${x.sector} · voices ${x.ticket_count ?? "k-anon"} ${x.is_aspirational ? "· ADP" : ""}</div>`)
    .join("");
}

window.decide = decide;
init();

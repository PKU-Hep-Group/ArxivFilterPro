from __future__ import annotations

import json
import os
from typing import Any

from .id_utils import version_number


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ArxivFilterPro</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/markdown-it-texmath@1.0.0/css/texmath.css" />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1>ArxivFilterPro</h1>
      <div class="section">
        <label for="searchInput">关键词检索</label>
        <input id="searchInput" type="text" placeholder="输入关键词后回车" />
      </div>
      <div class="section">
        <p>日期筛选</p>
        <label><input type="radio" name="dateFilter" value="7" checked /> 最近1周</label>
        <label><input type="radio" name="dateFilter" value="30" /> 最近1个月</label>
        <label><input type="radio" name="dateFilter" value="90" /> 最近3个月</label>
        <label><input type="radio" name="dateFilter" value="180" /> 最近6个月</label>
        <label><input type="radio" name="dateFilter" value="365" /> 最近12个月</label>
      </div>
    </aside>
    <main>
      <div id="cardCount"></div>
      <div id="cards" class="cards"></div>
    </main>
  </div>

  <div id="modal" class="modal hidden">
    <div class="modal-content">
      <button id="closeModal" class="close-btn">关闭</button>
      <div id="modalHeader"></div>
      <section class="analysis-panel">
        <div class="panel-head">
          <div>
            <div class="panel-eyebrow">Structured Reading</div>
            <h2 class="panel-title">论文摘要视图</h2>
          </div>
        </div>
        <div class="tabs">
          <button data-tab="ai_abstract">AI摘要</button>
          <button data-tab="problem">问题</button>
          <button data-tab="method">方法</button>
          <button data-tab="result">结果</button>
          <button data-tab="keypoint">要点</button>
          <button data-tab="abstract">原文摘要</button>
        </div>
        <article id="tabContent" class="subcard analysis-body"></article>
      </section>
      <section class="content-panel">
        <div class="panel-head">
          <div>
            <div class="panel-eyebrow">Long-form Overview</div>
            <h2 class="panel-title">正文概述</h2>
          </div>
        </div>
        <article id="fullContent" class="subcard content-body"></article>
      </section>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/markdown-it-texmath@1.0.0/texmath.min.js"></script>
  <script src="app.js"></script>
</body>
</html>
"""


STYLES_CSS = """* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Source Han Sans SC", "Noto Sans SC", "Helvetica Neue", sans-serif;
  color: #1f2a37;
  background: linear-gradient(165deg, #f6f8fb 0%, #eef2f9 100%);
}
.layout { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
.sidebar {
  padding: 24px;
  border-right: 1px solid #d8dee9;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(4px);
}
h1 { margin: 0 0 20px 0; font-family: Georgia, "Times New Roman", serif; font-size: 1.6rem; }
.section { margin-bottom: 20px; display: flex; flex-direction: column; gap: 10px; }
.section p { margin: 0; font-weight: 700; }
.section input[type="text"] {
  border: 1px solid #b5c1d3;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
}
main { padding: 24px; }
#cardCount { margin-bottom: 14px; color: #425466; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
.card {
  background: #ffffff;
  border: 1px solid #d6dde8;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 8px 20px rgba(14, 30, 60, 0.08);
  cursor: pointer;
  overflow: hidden;
}
.title-en { font-size: 1rem; font-weight: 700; margin-bottom: 6px; }
.title-zh { font-size: 0.93rem; color: #31435d; margin-bottom: 8px; }
.authors { font-size: 0.82rem; color: #5a6b84; margin-bottom: 10px; }
.card-body { font-size: 0.92rem; line-height: 1.6; color: #202b3a; }
.abs-link { margin-left: 6px; text-decoration: none; }
.meta-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.badge { font-size: 0.75rem; background: #e8eef8; color: #1f3f71; padding: 2px 8px; border-radius: 999px; }
.badge.category {
  background: #edf4ec;
  color: #2f5c3b;
}
.header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0 12px 0;
}
.modal {
  position: fixed;
  inset: 0;
  background: rgba(20, 30, 44, 0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px;
}
.hidden { display: none; }
.modal-content {
  width: min(960px, 96vw);
  max-height: 92vh;
  overflow: auto;
  background: #fff;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 26px 70px rgba(18, 30, 50, 0.22);
}
.close-btn {
  float: right;
  border: none;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  background: #eef3f9;
  color: #31435d;
}
.analysis-panel,
.content-panel {
  border-radius: 16px;
  margin-top: 18px;
}
.analysis-panel {
  border: 1px solid #cfdae8;
  background:
    linear-gradient(180deg, rgba(247, 250, 255, 0.96) 0%, rgba(240, 245, 252, 0.96) 100%);
  padding: 18px;
}
.content-panel {
  border: 1px solid #dde5f0;
  background: #ffffff;
  padding: 18px;
}
.panel-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.panel-eyebrow {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #667892;
  margin-bottom: 0.2rem;
}
.panel-title {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.15rem;
  color: #213146;
}
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }
.tabs button {
  border: 1px solid #c5d1e4;
  background: rgba(255, 255, 255, 0.72);
  border-radius: 999px;
  padding: 7px 13px;
  cursor: pointer;
  color: #33465f;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}
.tabs .active {
  background: #24466f;
  border-color: #24466f;
  color: #f8fbff;
}
.subcard {
  border: 1px solid #d8dfeb;
  border-radius: 12px;
  padding: 14px;
  line-height: 1.65;
  overflow-x: auto;
}
.analysis-body {
  margin-top: 6px;
  background: rgba(255, 255, 255, 0.9);
  border-color: #d4deec;
}
.content-body {
  margin-top: 4px;
  background: #ffffff;
  border-color: #e1e7f1;
}
.markdown-body > :first-child { margin-top: 0; }
.markdown-body > :last-child { margin-bottom: 0; }
.markdown-body p,
.markdown-body ul,
.markdown-body ol,
.markdown-body blockquote,
.markdown-body pre,
.markdown-body table {
  margin: 0 0 0.9rem 0;
}
.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4 {
  margin: 1.1rem 0 0.65rem 0;
  line-height: 1.3;
  font-family: Georgia, "Times New Roman", serif;
}
.markdown-body ul,
.markdown-body ol {
  padding-left: 1.3rem;
}
.markdown-body li + li {
  margin-top: 0.35rem;
}
.markdown-body code {
  background: #eef3fb;
  border-radius: 6px;
  padding: 0.12rem 0.35rem;
  font-size: 0.9em;
}
.markdown-body pre {
  background: #f4f7fc;
  border: 1px solid #d8dfeb;
  border-radius: 10px;
  padding: 12px;
  overflow-x: auto;
}
.markdown-body pre code {
  background: transparent;
  padding: 0;
}
.markdown-body blockquote {
  border-left: 3px solid #97add1;
  padding-left: 0.9rem;
  color: #465b76;
}
.markdown-body a {
  color: #174a8b;
}
.markdown-body img {
  max-width: 100%;
}
.markdown-body table {
  border-collapse: collapse;
  width: 100%;
}
.markdown-body th,
.markdown-body td {
  border: 1px solid #d8dfeb;
  padding: 0.45rem 0.6rem;
  text-align: left;
}
.markdown-body .katex-display {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0.3rem 0;
}
.card-body .markdown-body {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 10;
  overflow: hidden;
}
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { border-right: none; border-bottom: 1px solid #d8dee9; }
  .modal-content { padding: 18px; }
  .analysis-panel,
  .content-panel { padding: 14px; }
}
"""


APP_JS = """let allCards = [];
let currentSearch = "";
let md = window.markdownit({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
});
if (window.texmath && window.katex) {
  md = md.use(window.texmath, {
    engine: window.katex,
    delimiters: "dollars",
    katexOptions: { throwOnError: false },
  });
}

function daysBetween(a, b) {
  return Math.floor((a - b) / (1000 * 60 * 60 * 24));
}

function escapeHtml(str) {
  return (str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderMarkdown(markdown) {
  return `<div class="markdown-body">${md.render(markdown || "")}</div>`;
}

function renderCards() {
  const cardsRoot = document.getElementById("cards");
  const dayValue = Number(document.querySelector('input[name="dateFilter"]:checked').value);
  const now = new Date();
  const filtered = allCards.filter((card) => {
    const cardDate = new Date(card.date + "T00:00:00");
    const byDate = daysBetween(now, cardDate) <= dayValue;
    const byText = !currentSearch || card.search_text.includes(currentSearch.toLowerCase());
    return byDate && byText;
  });

  document.getElementById("cardCount").textContent = `当前展示 ${filtered.length} / 总计 ${allCards.length}`;
  cardsRoot.innerHTML = filtered.map((card) => `
    <article class="card" data-id="${card.id}">
      <div class="meta-row">
        <span class="badge">${card.tag}</span>
        <span class="badge category">${card.primary_category}</span>
        <span class="badge">${card.date}</span>
      </div>
      <div class="title-en">${escapeHtml(card.title_en)}</div>
      <div class="title-zh">${escapeHtml(card.title_zh)}</div>
      <div class="authors">${escapeHtml(card.authors_short)}
        <a class="abs-link" href="${card.abs_url}" target="_blank" title="${card.abs_url}" onclick="event.stopPropagation()">🔗</a>
      </div>
      <div class="card-body">${renderMarkdown(card.ai_abstract)}</div>
    </article>
  `).join("");

  for (const cardEl of cardsRoot.querySelectorAll(".card")) {
    cardEl.addEventListener("click", () => openModal(cardEl.getAttribute("data-id")));
  }
}

function setTab(card, tabName) {
  for (const btn of document.querySelectorAll(".tabs button")) {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
  }
  document.getElementById("tabContent").innerHTML = renderMarkdown(card[tabName] || "");
}

function openModal(id) {
  const card = allCards.find((c) => c.id === id);
  if (!card) return;
  document.getElementById("modalHeader").innerHTML = `
    <div class="header-meta">
      <span class="badge">${card.tag}</span>
      <span class="badge category">${card.primary_category}</span>
      <span class="badge">${card.date}</span>
    </div>
    <div class="title-en">${escapeHtml(card.title_en)}</div>
    <div class="title-zh">${escapeHtml(card.title_zh)}</div>
    <div class="authors">${escapeHtml(card.authors_full)} <a class="abs-link" href="${card.abs_url}" target="_blank">🔗</a></div>
  `;
  setTab(card, "ai_abstract");
  document.getElementById("fullContent").innerHTML = renderMarkdown(card.content || "");
  document.getElementById("modal").classList.remove("hidden");

  for (const btn of document.querySelectorAll(".tabs button")) {
    btn.onclick = () => setTab(card, btn.getAttribute("data-tab"));
  }
}

async function init() {
  const resp = await fetch("data/cards.json", { cache: "no-cache" });
  allCards = await resp.json();
  renderCards();

  document.getElementById("closeModal").addEventListener("click", () => {
    document.getElementById("modal").classList.add("hidden");
  });
  document.getElementById("searchInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      currentSearch = e.target.value.trim();
      renderCards();
    }
  });
  for (const radio of document.querySelectorAll('input[name="dateFilter"]')) {
    radio.addEventListener("change", renderCards);
  }
}

init();
"""


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _load_existing_cards(cards_json_path: str) -> list[dict[str, Any]]:
    if not os.path.exists(cards_json_path):
        return []
    with open(cards_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _author_short(authors: list[str]) -> str:
    full = ", ".join(authors)
    if len(full) <= 100:
        return full
    return full[:100] + "..."


def ensure_site_scaffold(site_path: str) -> None:
    os.makedirs(site_path, exist_ok=True)
    os.makedirs(os.path.join(site_path, "data"), exist_ok=True)
    with open(os.path.join(site_path, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    with open(os.path.join(site_path, "styles.css"), "w", encoding="utf-8") as f:
        f.write(STYLES_CSS)
    with open(os.path.join(site_path, "app.js"), "w", encoding="utf-8") as f:
        f.write(APP_JS)


def _build_card_from_paper_dir(paper_dir: str) -> dict[str, Any]:
    metadata_path = os.path.join(paper_dir, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    arxiv_id = metadata["arxiv_id"]
    authors = metadata["authors"]
    title_en = metadata["title"]
    title_zh = _read_text(os.path.join(paper_dir, "title_zh.md"))
    abstract = _read_text(os.path.join(paper_dir, "abstract.md"))
    ai_abstract = _read_text(os.path.join(paper_dir, "ai_abstract.md"))
    problem = _read_text(os.path.join(paper_dir, "problem.md"))
    method = _read_text(os.path.join(paper_dir, "method.md"))
    result = _read_text(os.path.join(paper_dir, "result.md"))
    keypoint = _read_text(os.path.join(paper_dir, "keypoint.md"))
    content = _read_text(os.path.join(paper_dir, "content.md"))
    tag = "new" if version_number(arxiv_id) == 1 else "update"

    search_text = "\n".join(
        [
            arxiv_id,
            title_en,
            title_zh,
            ", ".join(authors),
            abstract,
            ai_abstract,
            problem,
            method,
            result,
            keypoint,
            content,
        ]
    ).lower()

    return {
        "id": arxiv_id,
        "date": metadata["date"],
        "tag": tag,
        "primary_category": metadata["primary_category"],
        "title_en": title_en,
        "title_zh": title_zh,
        "authors_full": ", ".join(authors),
        "authors_short": _author_short(authors),
        "abs_url": metadata["abs_url"],
        "abstract": abstract,
        "ai_abstract": ai_abstract,
        "problem": problem,
        "method": method,
        "result": result,
        "keypoint": keypoint,
        "content": content,
        "search_text": search_text,
    }


def update_cards(
    site_path: str,
    cards_json_relpath: str,
    successful_paper_dirs: list[str],
) -> list[dict[str, Any]]:
    ensure_site_scaffold(site_path)
    cards_json_path = os.path.join(site_path, cards_json_relpath)
    os.makedirs(os.path.dirname(cards_json_path), exist_ok=True)

    existing = _load_existing_cards(cards_json_path)
    cards_map = {card["id"]: card for card in existing}

    updated_today: list[dict[str, Any]] = []
    for paper_dir in successful_paper_dirs:
        card = _build_card_from_paper_dir(paper_dir)
        cards_map[card["id"]] = card
        updated_today.append(card)

    cards = sorted(
        cards_map.values(),
        key=lambda x: (x["date"], x["id"]),
        reverse=True,
    )
    with open(cards_json_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    return updated_today

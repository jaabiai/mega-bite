/* MEGA BITE – tiny hash-router + renderer. No build step, no dependencies. */
(function () {
  "use strict";

  var DATA = window.MEGABITE;
  var state = { category: "All", query: "" };

  var $ = function (sel) { return document.querySelector(sel); };
  var views = {
    home: $("#view-home"),
    tools: $("#view-tools"),
    about: $("#view-about"),
    article: $("#view-article"),
    notfound: $("#view-404")
  };

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtDate(iso) {
    var d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  }

  function sortedArticles() {
    return DATA.articles.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; });
  }

  function matches(article) {
    if (state.category !== "All" && article.category !== state.category) return false;
    var q = state.query.trim().toLowerCase();
    if (!q) return true;
    var hay = [article.title, article.summary, article.category, article.body.join(" ")].join(" ").toLowerCase();
    return hay.indexOf(q) !== -1;
  }

  function metaHtml(a) {
    return '<div class="meta"><span class="tag">' + esc(a.category) + "</span>" +
      "<span>" + esc(fmtDate(a.date)) + "</span><span>·</span><span>" + esc(a.minutes) + " min read</span></div>";
  }

  /* ---------- Home ---------- */
  function renderChips() {
    var cats = ["All"].concat(DATA.categories);
    $("#chips").innerHTML = cats.map(function (c) {
      return '<button type="button" class="chip" data-cat="' + esc(c) + '" aria-pressed="' + (c === state.category) + '">' + esc(c) + "</button>";
    }).join("");
  }

  function renderList() {
    var list = sortedArticles().filter(matches);
    var featured = list[0];
    var rest = list.slice(1);

    $("#featured").innerHTML = featured
      ? '<a class="featured" href="#/post/' + esc(featured.id) + '">' + metaHtml(featured) +
        "<h2>" + esc(featured.title) + "</h2><p>" + esc(featured.summary) + "</p></a>"
      : "";

    $("#grid").innerHTML = rest.map(function (a) {
      return '<a class="card" href="#/post/' + esc(a.id) + '">' + metaHtml(a) +
        "<h3>" + esc(a.title) + "</h3><p>" + esc(a.summary) + "</p></a>";
    }).join("");

    $("#empty").hidden = list.length > 0;
  }

  /* ---------- Tools ---------- */
  function renderTools() {
    $("#tools-grid").innerHTML = DATA.tools.map(function (t) {
      return '<button type="button" class="card" data-query="' + esc(t.query) + '">' +
        '<span class="icon" aria-hidden="true">' + t.icon + "</span>" +
        "<h3>" + esc(t.name) + "</h3><p>" + esc(t.desc) + "</p></button>";
    }).join("");
  }

  /* ---------- Article ---------- */
  function renderArticle(id) {
    var a = DATA.articles.filter(function (x) { return x.id === id; })[0];
    if (!a) return false;
    views.article.innerHTML =
      '<a class="back" href="#/">← All articles</a>' +
      "<h1>" + esc(a.title) + "</h1>" +
      '<div class="article-meta">' + metaHtml(a) + "</div>" +
      '<p class="lead">' + esc(a.summary) + "</p>" +
      a.body.map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
    document.title = a.title + " – MEGA BITE";
    return true;
  }

  /* ---------- Router ---------- */
  function show(name) {
    Object.keys(views).forEach(function (k) { views[k].hidden = k !== name; });
    var navKey = name === "tools" ? "tools" : name === "about" ? "about" : (name === "home" || name === "article") ? "news" : "";
    document.querySelectorAll(".nav a").forEach(function (a) {
      if (a.dataset.nav === navKey) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  function route() {
    var hash = location.hash.replace(/^#/, "") || "/";
    var parts = hash.split("/").filter(Boolean);
    document.title = "MEGA BITE – Tech News, AI Tools & Technology Updates";

    if (parts.length === 0) {
      show("home");
      renderChips();
      renderList();
    } else if (parts[0] === "tools") {
      show("tools");
      document.title = "AI Tools – MEGA BITE";
    } else if (parts[0] === "about") {
      show("about");
      document.title = "About – MEGA BITE";
    } else if (parts[0] === "post" && parts[1] && renderArticle(decodeURIComponent(parts[1]))) {
      show("article");
    } else {
      show("notfound");
      document.title = "Not found – MEGA BITE";
    }
    window.scrollTo(0, 0);
  }

  /* ---------- Events ---------- */
  $("#chips").addEventListener("click", function (e) {
    var btn = e.target.closest("[data-cat]");
    if (!btn) return;
    state.category = btn.dataset.cat;
    renderChips();
    renderList();
  });

  $("#q").addEventListener("input", function (e) {
    state.query = e.target.value;
    renderList();
  });
  $("#search-form").addEventListener("submit", function (e) { e.preventDefault(); });

  $("#tools-grid").addEventListener("click", function (e) {
    var btn = e.target.closest("[data-query]");
    if (!btn) return;
    state.query = btn.dataset.query;
    state.category = "All";
    $("#q").value = state.query;
    if (location.hash === "#/" || location.hash === "") route();
    else location.hash = "#/";
  });

  $("#theme-toggle").addEventListener("click", function () {
    var root = document.documentElement;
    var current = root.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("mb-theme", next); } catch (err) { /* storage unavailable */ }
  });

  window.addEventListener("hashchange", route);

  $("#year").textContent = new Date().getFullYear();
  renderTools();
  route();
})();

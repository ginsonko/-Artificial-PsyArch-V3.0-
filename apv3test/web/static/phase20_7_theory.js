// APV3 理论读本：加载 md → 自包含渲染 → 构建目录 → 跟随高亮当前章节
// 设计原则：纯前端、无后端改动、断网可用、不依赖任何 CDN 的 API 形状。
// 历史教训：原版用 marked.js CDN + new marked.Renderer() + marked.use({renderer}),
//           marked v9+ 的 Renderer.link 入参变成 token 对象后调用 origLink(href,title,txt) 会抛，
//           try/catch 静默走 renderPlain 回退——用户看到纯文本。
//           现在改成内置迷你 markdown 渲染器，覆盖此 md 用到的全部语法，
//           行为对运行环境/网络状态完全确定。

(function () {
  "use strict";

  var articleEl = document.getElementById("theoryArticle");
  var tocNav = document.getElementById("theoryTocNav");
  var MD_URL = "/APV3_Theory_Reader_20260703.md";

  async function fetchMd() {
    var resp = await fetch(MD_URL, { cache: "no-cache" });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return await resp.text();
  }

  // 字符串转义：跨 Node/浏览器一致，无需 DOM（避免在 server 端 sandbox 测试时报错）
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&" + "#39;");
  }

  function slugify(text) {
    var v = String(text || "").trim()
      .replace(/\s+/g, "-")
      .replace(/[.,:;?!，。、（）()【】\[\]""'']+/g, "")
      .replace(/[^A-Za-z0-9\u4e00-\u9fff_-]/g, "")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60);
    return v || "section";
  }

  // 行内渲染：代码、加粗、斜体、链接、图片。顺序很重要：先吃代码段以保护内容。
  function renderInline(text) {
    var parts = [];
    var ph = []; // 代码段占位：先抽走，最后还原
    var idx = 0;
    // inline code
    text = text.replace(/`([^`]+)`/g, function (_, c) {
      var token = "\u0000CODE" + idx + "\u0000";
      ph.push('<code class="md-inline-code">' + escapeHtml(c) + "</code>");
      idx++;
      return token;
    });
    // 图片：![alt](src)
    text = text.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, function (_, alt, src) {
      var token = "\u0000IMG" + idx + "\u0000";
      ph.push('<img alt="' + escapeHtml(alt) + '" src="' + escapeHtml(src) + '" loading="lazy" />');
      idx++;
      return token;
    });
    // 链接：[text](href)
    text = text.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, function (_, t, href) {
      var token = "\u0000LINK" + idx + "\u0000";
      var safe = /^https?:\/\//.test(href) ? href : "#";
      ph.push('<a href="' + escapeHtml(safe) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(t) + "</a>");
      idx++;
      return token;
    });
    // 加粗 **x**
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // 斜体 *x* 或 _x_
    text = text.replace(/(^|[^\w*])\*([^*\s][^*]*)\*(?=[^\w*]|$)/g, "$1<em>$2</em>");
    text = text.replace(/(^|[^\w_])_([^_\s][^_]*)_(?=[^\w_]|$)/g, "$1<em>$2</em>");
    // 还原占位
    text = text.replace(/\u0000(CODE|IMG|LINK)(\d+)\u0000/g, function (_, kind, n) {
      return ph[parseInt(n, 10)] || "";
    });
    return text;
  }

  // 块级渲染：标题 / 列表 / 引用 / 代码块 / 表格 / hr / 段落
  function renderMarkdown(src) {
    var lines = String(src || "").replace(/\r\n/g, "\n").split("\n");
    var html = [];
    var i = 0;
    var inList = false;
    var listType = null; // "ul" / "ol"
    var blockquoteLines = [];
    var codeFence = null;
    var codeBuf = [];
    var tableRows = [];

    function closeList() {
      if (inList) { html.push("</" + listType + ">"); inList = false; listType = null; }
    }
    function flushBlockquote() {
      if (!blockquoteLines.length) return;
      // 递归解析引用块内部：把内部列表也跑起来。这里简化：内部行也走一次 block 解析。
      var innerHtml = renderMarkdown(blockquoteLines.join("\n"));
      html.push('<blockquote class="md-quote">' + innerHtml + "</blockquote>");
      blockquoteLines = [];
    }
    function flushTable() {
      if (!tableRows.length) return;
      var header = tableRows[0];
      var body = tableRows.slice(1);
      var h = '<table class="md-table"><thead><tr>';
      header.forEach(function (c) { h += "<th>" + renderInline(c) + "</th>"; });
      h += "</tr></thead><tbody>";
      body.forEach(function (row) {
        h += "<tr>";
        row.forEach(function (c) { h += "<td>" + renderInline(c) + "</td>"; });
        h += "</tr>";
      });
      h += "</tbody></table>";
      html.push(h);
      tableRows = [];
    }

    function parseTableRow(line) {
      // 简单：去首尾 |，按 | 分割
      var s = line.trim();
      if (s.charAt(0) === "|") s = s.slice(1);
      if (s.charAt(s.length - 1) === "|") s = s.slice(0, -1);
      return s.split("|").map(function (c) { return c.trim(); });
    }
    function isTableRow(line) {
      return /^\s*\|.*\|\s*$/.test(line);
    }
    function isTableSep(line) {
      return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(line);
    }

    for (; i < lines.length; i++) {
      var line = lines[i];

      // 代码围栏
      if (codeFence !== null) {
        if (line.trim() === codeFence) {
          html.push('<pre class="md-code"><code>' + escapeHtml(codeBuf.join("\n")) + "</code></pre>");
          codeBuf = [];
          codeFence = null;
        } else {
          codeBuf.push(line);
        }
        continue;
      }
      if (/^\s*```\s*([\w-]*)\s*$/.test(line)) {
        closeList(); flushBlockquote(); flushTable();
        codeFence = "```";
        codeBuf = [];
        continue;
      }

      // 表格：连续的 |...| 行（中间允许 1 行分隔 ---）
      if (isTableRow(line)) {
        closeList(); flushBlockquote();
        tableRows.push(parseTableRow(line));
        var nxt = lines[i + 1] || "";
        if (isTableSep(nxt)) i++; // 跳过分隔行
        var nxt2 = lines[i + 1] || "";
        if (!isTableRow(nxt2)) flushTable();
        continue;
      }
      flushTable();

      // 引用块
      if (/^\s*>\s?/.test(line)) {
        closeList();
        blockquoteLines.push(line.replace(/^\s*>\s?/, ""));
        continue;
      }
      flushBlockquote();

      // 标题
      var h = line.match(/^(#{1,6})\s+(.+?)\s*#*$/);
      if (h) {
        closeList();
        var level = h[1].length;
        var text = h[2];
        var id = slugify(text);
        html.push('<h' + level + ' id="' + escapeHtml(id) + '">' + renderInline(text) + "</h" + level + ">");
        continue;
      }

      // 水平线
      if (/^\s*([-*_])\1\1[-*_\s]*$/.test(line) && line.trim().length >= 3) {
        closeList();
        html.push('<hr class="md-hr" />');
        continue;
      }

      // 无序列表
      var ul = line.match(/^\s*[-*+]\s+(.+)$/);
      if (ul) {
        if (!inList || listType !== "ul") { closeList(); html.push("<ul>"); inList = true; listType = "ul"; }
        html.push("<li>" + renderInline(ul[1]) + "</li>");
        continue;
      }
      // 有序列表
      var ol = line.match(/^\s*\d+\.\s+(.+)$/);
      if (ol) {
        if (!inList || listType !== "ol") { closeList(); html.push("<ol>"); inList = true; listType = "ol"; }
        html.push("<li>" + renderInline(ol[1]) + "</li>");
        continue;
      }
      closeList();

      // 空行
      if (line.trim() === "") {
        continue;
      }

      // 段落：连续非空非块行合并
      var para = [line];
      while (i + 1 < lines.length) {
        var nx = lines[i + 1];
        if (nx.trim() === "") break;
        if (/^\s*#{1,6}\s+/.test(nx)) break;
        if (/^\s*[-*+]\s+/.test(nx)) break;
        if (/^\s*\d+\.\s+/.test(nx)) break;
        if (/^\s*>\s?/.test(nx)) break;
        if (isTableRow(nx)) break;
        if (/^\s*```/.test(nx.trim())) break;
        if (/^\s*([-*_])\1\1[-*_\s]*$/.test(nx) && nx.trim().length >= 3) break;
        para.push(nx);
        i++;
      }
      html.push("<p>" + renderInline(para.join(" ")) + "</p>");
    }

    closeList();
    flushBlockquote();
    flushTable();
    if (codeFence !== null && codeBuf.length) {
      html.push('<pre class="md-code"><code>' + escapeHtml(codeBuf.join("\n")) + "</code></pre>");
    }
    return html.join("\n");
  }

  function renderArticle(text) {
    try {
      articleEl.innerHTML = renderMarkdown(text);
    } catch (e) {
      console.error("[theory] 自包含渲染失败，回退纯文本:", e);
      var pre = document.createElement("pre");
      pre.className = "preview-plain";
      pre.textContent = text;
      articleEl.innerHTML = "";
      articleEl.appendChild(pre);
      tocNav.innerHTML = '<div style="color:var(--text-light);font-size:12px;padding:8px;">渲染异常，纯文本展示。</div>';
      return;
    }
    // 第一个 blockquote 提升为顶部 callout
    var firstQuote = articleEl.querySelector("blockquote");
    if (firstQuote) {
      var callout = document.createElement("div");
      callout.className = "theory-callout";
      while (firstQuote.firstChild) callout.appendChild(firstQuote.firstChild);
      firstQuote.replaceWith(callout);
    }
  }

  function buildToc() {
    var heads = Array.from(articleEl.querySelectorAll("h2, h3"));
    if (!heads.length) {
      tocNav.innerHTML = '<div style="color:var(--text-light);font-size:12px;padding:8px;">无章节目录。</div>';
      return;
    }
    var used = {};
    var entries = [];
    heads.forEach(function (h) {
      if (!h.id) h.id = slugify(h.textContent || "section");
      // 去重 id
      if (used[h.id]) {
        var n = 2;
        while (used[h.id + "-" + n]) n++;
        h.id = h.id + "-" + n;
      }
      used[h.id] = true;
      entries.push({ id: h.id, text: h.textContent || "", level: h.tagName === "H3" ? 3 : 2 });
    });
    tocNav.innerHTML = entries.map(function (e) {
      var cls = e.level === 3 ? "sub" : "";
      return '<a class="' + cls + '" href="#' + e.id + '" data-target="' + e.id + '">' + escapeHtml(e.text) + "</a>";
    }).join("");
  }

  function observeActiveSection() {
    var links = Array.from(tocNav.querySelectorAll("a[data-target]"));
    if (!links.length) return;
    var map = {};
    links.forEach(function (a) {
      var id = a.getAttribute("data-target");
      if (id) map[id] = a;
    });
    var headings = Object.keys(map)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    if (!("IntersectionObserver" in window) || !headings.length) return;
    var observer = new IntersectionObserver(
      function (entries) {
        var visible = entries.filter(function (e) { return e.isIntersecting; })
          .sort(function (a, b) { return a.boundingClientRect.top - b.boundingClientRect.top; })[0];
        if (!visible) return;
        var id = visible.target.id;
        links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("data-target") === id); });
      },
      { rootMargin: "-88px 0px -70% 0px", threshold: [0, 1] }
    );
    headings.forEach(function (h) { observer.observe(h); });

    links.forEach(function (a) {
      a.addEventListener("click", function (event) {
        var id = a.getAttribute("data-target");
        var target = id && document.getElementById(id);
        if (!target) return;
        event.preventDefault();
        var top = target.getBoundingClientRect().top + window.scrollY - 80;
        window.scrollTo({ top: top, behavior: "smooth" });
        history.replaceState(null, "", "#" + id);
        links.forEach(function (x) { x.classList.toggle("active", x === a); });
      });
    });
  }

  async function main() {
    var text;
    try {
      text = await fetchMd();
    } catch (e) {
      articleEl.innerHTML = "";
      var errDiv = document.createElement("div");
      errDiv.className = "theory-error";
      errDiv.textContent = "无法加载理论文本（" + String(e) + "）。请确认 apv3test/web/static/APV3_Theory_Reader_20260703.md 存在且服务在跑。";
      articleEl.appendChild(errDiv);
      return;
    }
    renderArticle(text);
    buildToc();
    observeActiveSection();
  }

  main();
})();

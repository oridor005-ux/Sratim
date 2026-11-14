// מסגרת משותפת לכל הסרטונים: ציר זמן, כתוביות, ופונקציות עזר.
// כל animation.html מגדיר window.drawScene(scene, p, t, info)
//   scene — הסצנה הנוכחית (id, start, end, speechStart, speechEnd...)
//   p     — התקדמות בתוך הסצנה, 0 עד 1
//   t     — זמן כולל בשניות
(function () {
  const H = (window.H = {
    clamp: (x, a = 0, b = 1) => Math.max(a, Math.min(b, x)),
    lerp: (a, b, k) => a + (b - a) * k,
    ease: (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2),
    // התקדמות 0..1 בין זמן a ל־b (שניות מתחילת הסצנה)
    span: (local, a, b) => H.clamp((local - a) / (b - a)),
    $: (id) => document.getElementById(id),
  });

  let TL = [], INFO = {}, capEl, chunksCache = {};

  function splitCaption(text, maxLine) {
    // מחלק לשורות קצרות, ואז לקבוצות של עד שתי שורות
    const words = text.split(/\s+/).filter(Boolean);
    const lines = [];
    let cur = "";
    for (const w of words) {
      if ((cur + " " + w).trim().length > maxLine && cur) {
        lines.push(cur);
        cur = w;
      } else cur = (cur + " " + w).trim();
    }
    if (cur) lines.push(cur);
    const chunks = [];
    for (let i = 0; i < lines.length; i += 2) chunks.push(lines.slice(i, i + 2).join("\n"));
    return chunks;
  }

  window.__setup = function (tl, info) {
    TL = tl;
    INFO = info;
    document.documentElement.lang = info.lang || "he";
    document.documentElement.dir = (info.lang || "he") === "he" ? "rtl" : "ltr";
    capEl = document.createElement("div");
    capEl.id = "caption";
    document.body.appendChild(capEl);
  };

  window.__seek = function (t) {
    let sc = TL[TL.length - 1];
    for (const s of TL) if (t >= s.start && t < s.end) { sc = s; break; }
    const p = H.clamp((t - sc.start) / (sc.end - sc.start));
    const local = t - sc.start;
    document.body.dataset.scene = sc.id;
    if (window.drawScene) window.drawScene(sc, p, t, INFO, local);

    // כתוביות
    if (!INFO.subtitles || !capEl) return;
    const text = sc.caption || "";
    if (!text || t < sc.speechStart - 0.15 || t > sc.speechEnd + 0.35) {
      capEl.style.opacity = 0;
      return;
    }
    const chunks = chunksCache[sc.i] || (chunksCache[sc.i] = splitCaption(text, 26));
    const total = chunks.reduce((a, c) => a + c.length, 0);
    const sp = H.clamp((t - sc.speechStart) / (sc.speechEnd - sc.speechStart)) * total;
    let acc = 0, idx = chunks.length - 1;
    for (let i = 0; i < chunks.length; i++) {
      acc += chunks[i].length;
      if (sp < acc) { idx = i; break; }
    }
    capEl.textContent = chunks[idx];
    capEl.style.opacity = 1;
  };

  window.addEventListener("DOMContentLoaded", () => {
    if (window.init) window.init();
    window.__ready = true;
  });
})();

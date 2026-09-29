(() => {
  "use strict";
  const DATA = JSON.parse(document.getElementById("kobun-data").textContent);
  const byNo = new Map(DATA.map((w) => [w.n, w]));
  const KEY = "kobun500:v1";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const wid = (n) => "w" + String(n).padStart(4, "0");

  // ---- 保存（この端末のブラウザだけ。使えない環境でも動く） ----
  let store = { chk: {}, st: {}, sheet: false };
  try { store = Object.assign(store, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) { /* 保存なしで続行 */ }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) { /* 無視 */ } };

  // ---- 3回チェック ----
  $$(".chk").forEach((b) => {
    if (store.chk[b.dataset.k]) b.classList.add("on");
    b.addEventListener("click", () => {
      const on = b.classList.toggle("on");
      if (on) store.chk[b.dataset.k] = 1; else delete store.chk[b.dataset.k];
      save();
    });
  });

  // ---- 赤シート ----
  const sheetBtn = $("#btn-sheet");
  const setSheet = (on) => {
    document.body.classList.toggle("sheet-on", on);
    sheetBtn.setAttribute("aria-pressed", String(on));
    $$(".sheet.peek").forEach((el) => el.classList.remove("peek"));
    store.sheet = on; save();
  };
  sheetBtn.addEventListener("click", () => setSheet(!document.body.classList.contains("sheet-on")));
  document.addEventListener("click", (ev) => {
    if (!document.body.classList.contains("sheet-on")) return;
    const s = ev.target.closest(".sheet");
    if (s) s.classList.toggle("peek");
  });
  if (store.sheet) setSheet(true);

  // ---- 確認テスト：4択と「答え」 ----
  $$(".test").forEach((t) => {
    const score = $("[data-score]", t);
    let got = 0, done = 0;
    const total = $$(".qa > li", t).length;
    $$(".qa > li", t).forEach((li) => {
      $$(".opt", li).forEach((o) => o.addEventListener("click", () => {
        const opts = $$(".opt", li);
        opts.forEach((x) => { x.disabled = true; if (x.dataset.ok === "1") x.classList.add("right"); });
        if (o.dataset.ok !== "1") o.classList.add("wrong"); else got++;
        done++;
        score.textContent = `${got} / ${done}` + (done === total ? `（A問題 ${total}問）` : "");
      }));
    });
  });
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest(".rv");
    if (!b) return;
    const a = b.nextElementSibling;
    a.hidden = !a.hidden;
    b.textContent = a.hidden ? b.dataset.label : "隠す";
  });
  $$(".rv").forEach((b) => { b.dataset.label = b.textContent; });

  // ---- 目次の進み具合（「覚えた」の割合） ----
  const paintProgress = () => {
    $$(".prog[data-day]").forEach((p) => {
      const d = +p.dataset.day;
      const ws = DATA.filter((w) => w.d === d);
      const ok = ws.filter((w) => store.st[w.n] === 2).length;
      p.firstElementChild.style.width = ws.length ? (100 * ok / ws.length) + "%" : "0";
      p.title = `覚えた ${ok} / ${ws.length}`;
    });
  };
  paintProgress();

  // ---- 検索 ----
  const q = $("#q"), results = $("#results");
  const norm = (s) => s.normalize("NFKC").replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
  q.addEventListener("input", () => {
    const v = norm(q.value.trim());
    if (!v) { results.hidden = true; return; }
    const hits = DATA.filter((w) => norm(w.h + w.k + w.y + w.m.join("")).includes(v)).slice(0, 14);
    results.innerHTML = hits.length
      ? hits.map((w) => `<a href="#${wid(w.n)}"><span class="n">${String(w.n).padStart(4, "0")}</span><span class="h">${esc(w.h)}</span><span class="m">${esc(w.m[0])}</span></a>`).join("")
      : "<p>見つかりません。ひらがな・漢字・現代語の意味で探せます。</p>";
    results.hidden = false;
  });
  results.addEventListener("click", (ev) => { if (ev.target.closest("a")) { results.hidden = true; q.value = ""; } });
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".bar")) results.hidden = true; });

  // ---- 暗記カード・4択クイズ ----
  const drill = $("#drill"), set = $("#drill-set");
  const fromSel = $("#d-from"), toSel = $("#d-to"), filt = $("#d-filter"), cnt = $("#d-count");
  const days = [...new Set(DATA.map((w) => w.d))];
  days.forEach((d) => {
    const o = `<option value="${d}">DAY ${String(d).padStart(2, "0")}</option>`;
    fromSel.insertAdjacentHTML("beforeend", o); toSel.insertAdjacentHTML("beforeend", o);
  });
  toSel.value = String(days[days.length - 1]);
  let mode = "flash", deck = [], pos = 0, right = 0, missed = [];
  const stages = ["flash", "quiz", "done"].map((id) => $("#" + id));
  const show = (id) => stages.forEach((s) => { s.hidden = s.id !== id; });
  const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const pickPool = () => {
    let a = +fromSel.value, b = +toSel.value;
    if (a > b) [a, b] = [b, a];
    let pool = DATA.filter((w) => w.d >= a && w.d <= b);
    if (filt.value === "weak") pool = pool.filter((w) => store.st[w.n] !== 2);
    if (filt.value === "new") pool = pool.filter((w) => store.st[w.n] === undefined);
    if (filt.value === "top") pool = pool.filter((w) => w.r === 3);
    return pool;
  };
  const summary = () => {
    const pool = pickPool();
    const c = [0, 0, 0];
    pool.forEach((w) => { const s = store.st[w.n]; if (s !== undefined) c[s]++; });
    $("#drill-sum").textContent = `対象 ${pool.length}語　覚えた ${c[2]}・あやしい ${c[1]}・まだ ${c[0]}・記録なし ${pool.length - c[0] - c[1] - c[2]}`;
  };
  [fromSel, toSel, filt].forEach((s) => s.addEventListener("change", summary));
  const open = (m) => {
    mode = m;
    drill.classList.toggle("flash-mode", m === "flash");
    $("#drill-title").textContent = m === "flash" ? "暗記カード" : "4択クイズ";
    stages.forEach((s) => { s.hidden = true; });
    drill.hidden = false; summary();
    $("#d-start").focus();
  };
  const close = () => { drill.hidden = true; paintProgress(); };
  $("#btn-flash").addEventListener("click", () => open("flash"));
  $("#btn-quiz").addEventListener("click", () => open("quiz"));
  $("#drill-close").addEventListener("click", close);
  drill.addEventListener("click", (ev) => { if (ev.target === drill) close(); });
  set.addEventListener("submit", (ev) => {
    ev.preventDefault();
    let pool = shuffle(pickPool());
    if (!pool.length) { $("#drill-sum").textContent = "この条件に当てはまる語はありません。範囲か出題を変えてください。"; return; }
    if (mode === "quiz") pool = pool.slice(0, +cnt.value);
    // 暗記カードは「まだ」→「あやしい」→記録なし→「覚えた」の順に出す
    if (mode === "flash") pool.sort((x, y) => rank(x) - rank(y));
    deck = pool; pos = 0; right = 0; missed = [];
    mode === "flash" ? flashShow() : quizShow();
  });
  const rank = (w) => ({ 0: 0, 1: 1, undefined: 2, 2: 3 })[store.st[w.n]];
  const stateName = (s) => s === 2 ? "覚えた" : s === 1 ? "あやしい" : s === 0 ? "まだ" : "記録なし";

  // 暗記カード
  const fCard = $("#f-card"), fHint = $(".f-hint"), fBack = $(".f-back");
  const flashShow = () => {
    if (pos >= deck.length) return finish();
    show("flash");
    const w = deck[pos];
    $("#f-pos").textContent = `${pos + 1} / ${deck.length}`;
    $("#f-state").textContent = "いまの記録：" + stateName(store.st[w.n]);
    $("#f-no").textContent = String(w.n).padStart(4, "0") + "　" + w.p;
    $("#f-hw").textContent = w.h;
    $("#f-kan").textContent = w.k || "";
    $("#f-mean").textContent = w.m.map((m, i) => "①②③④⑤⑥"[i] + m).join("　");
    $("#f-core").textContent = w.c || "";
    $("#f-core").hidden = !w.c;
    $("#f-ex").textContent = w.e;
    $("#f-tr").textContent = w.t;
    fHint.hidden = false; fBack.hidden = true;
  };
  const flip = () => { fHint.hidden = !fHint.hidden; fBack.hidden = !fBack.hidden; };
  fCard.addEventListener("click", flip);
  $$(".rate button").forEach((b) => b.addEventListener("click", () => rate(+b.dataset.rate)));
  const rate = (r) => {
    const w = deck[pos];
    store.st[w.n] = r; save();
    if (r === 2) right++; else missed.push(w);
    pos++; flashShow();
  };

  // 4択
  const quizShow = () => {
    if (pos >= deck.length) return finish();
    show("quiz");
    const w = deck[pos];
    $("#q-pos").textContent = `${pos + 1} / ${deck.length}`;
    $("#q-score").textContent = `正解 ${right}`;
    $("#q-hw").textContent = w.h;
    $("#q-kan").textContent = w.k || "";
    const used = new Set([w.m[0]]);
    const others = shuffle(DATA.filter((x) => x.n !== w.n && x.p.charAt(0) === w.p.charAt(0)));
    const opts = [w.m[0]];
    for (const x of others) { if (!used.has(x.m[0])) { used.add(x.m[0]); opts.push(x.m[0]); } if (opts.length === 4) break; }
    shuffle(opts);
    $("#q-opts").innerHTML = opts.map((o) => `<li><button type="button" data-ok="${o === w.m[0] ? 1 : 0}">${esc(o)}</button></li>`).join("");
    $("#q-next").hidden = true;
  };
  $("#q-opts").addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b || b.disabled) return;
    const w = deck[pos];
    $$("#q-opts button").forEach((x) => { x.disabled = true; if (x.dataset.ok === "1") x.classList.add("right"); });
    if (b.dataset.ok === "1") {
      right++;
      store.st[w.n] = store.st[w.n] === undefined || store.st[w.n] === 0 ? 1 : 2;
    } else {
      b.classList.add("wrong"); missed.push(w); store.st[w.n] = 0;
    }
    save();
    $("#q-score").textContent = `正解 ${right}`;
    $("#q-next").hidden = false; $("#q-next").focus();
  });
  $("#q-next").addEventListener("click", () => { pos++; quizShow(); });

  const finish = () => {
    show("done");
    $("#done-big").textContent = `${right} / ${deck.length}`;
    $("#done-msg").textContent = missed.length
      ? (mode === "flash" ? "「覚えた」以外の語。本文のカードで語構成とコアを確かめよう。" : "まちがえた語。本文のカードで例文を音読しよう。")
      : "全問クリア。範囲を広げてもう一度。";
    $("#done-list").innerHTML = missed.map((w) => `<li><a href="#${wid(w.n)}">${esc(w.h)}</a>${esc(w.m[0])}</li>`).join("");
    paintProgress();
  };
  $("#done-list").addEventListener("click", (ev) => { if (ev.target.closest("a")) close(); });
  $("#done-again").addEventListener("click", () => set.requestSubmit());

  document.addEventListener("keydown", (ev) => {
    if (drill.hidden) return;
    if (ev.key === "Escape") return close();
    if (!$("#flash").hidden) {
      if (ev.key === " " && ev.target === document.body) { ev.preventDefault(); flip(); }
      if (["1", "2", "3"].includes(ev.key)) rate(+ev.key - 1);
    }
    if (!$("#quiz").hidden && ["1", "2", "3", "4"].includes(ev.key)) {
      const b = $$("#q-opts button")[+ev.key - 1];
      if (b) b.click();
    }
  });
})();

/* 赤門ひろば — 画面側。
   利用者の文字列は必ず textContent で入れる（innerHTML は使わない）。 */
"use strict";

const state = {
  me: null,
  csrf: null,
  unreadDm: 0,
  boards: [],
  composerMedia: [],
  navOpen: false,
};

/* ---------- 小さな道具 ---------- */

function h(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "html") throw new Error("html は使わない");
    else if (key.startsWith("on")) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (value === true) node.setAttribute(key, "");
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function clear(node) { while (node.firstChild) node.firstChild.remove(); }

function toast(message, isError) {
  const box = document.getElementById("toast");
  box.textContent = message;
  box.hidden = false;
  box.classList.toggle("toast--error", Boolean(isError));
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { box.hidden = true; }, isError ? 6000 : 3000);
}

async function api(method, path, body, options) {
  const opts = options || {};
  const headers = {};
  if (state.csrf) headers["X-CSRF-Token"] = state.csrf;
  let payload = null;
  if (opts.raw) { payload = opts.raw; headers["Content-Type"] = opts.contentType || "application/octet-stream"; }
  else if (body !== undefined && body !== null) { payload = JSON.stringify(body); headers["Content-Type"] = "application/json"; }
  const res = await fetch(path, { method, headers, body: payload, credentials: "same-origin" });
  const type = res.headers.get("Content-Type") || "";
  const data = type.includes("application/json") ? await res.json() : null;
  if (!res.ok) {
    const error = new Error((data && data.error) || `通信に失敗しました（${res.status}）`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  if (data && data.csrf) state.csrf = data.csrf;
  return data;
}

function relativeTime(ms) {
  const diff = Date.now() - ms;
  if (diff < 60000) return "たった今";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}時間前`;
  if (diff < 7 * 86400000) return `${Math.floor(diff / 86400000)}日前`;
  const d = new Date(ms);
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
}

function boardName(slug) {
  const board = state.boards.find((b) => b.slug === slug);
  return board ? board.name : slug;
}

function requireLogin() {
  if (!state.me) { openAuthModal(); return false; }
  return true;
}

function requireAccount(action) {
  if (!requireLogin()) return false;
  if (state.me.is_guest) {
    toast(`${action}にはアカウント登録が必要です（ゲストは匿名の書き込みだけ）。`, true);
    return false;
  }
  return true;
}

/* ---------- 経路 ---------- */

function currentRoute() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, rest] = [raw.split("?")[0], raw.split("?").slice(1).join("?")];
  const parts = path.split("/").filter(Boolean);
  return { name: parts[0] || "public", args: parts.slice(1).map(decodeURIComponent), query: new URLSearchParams(rest) };
}

function go(hash) {
  if (location.hash === hash) render();
  else location.hash = hash;
}

/* ---------- 画面の骨格 ---------- */

function renderTopbar() {
  const box = document.getElementById("topbar-right");
  clear(box);
  if (state.me) {
    box.append(
      h("a", { class: "small", href: `#/user/${state.me.handle}` },
        state.me.display_name, state.me.is_guest ? "（ゲスト）" : ""),
      h("button", { class: "btn btn--small", onclick: logout }, "ログアウト"),
    );
  } else {
    box.append(
      h("button", { class: "btn btn--small", onclick: () => openAuthModal("login") }, "ログイン"),
      h("button", { class: "btn btn--small btn--primary", onclick: () => openAuthModal("register") }, "登録"),
    );
  }
}

function navLink(label, hash, options) {
  const opts = options || {};
  const active = location.hash === hash || (hash === "#/public" && !location.hash);
  return h("a", {
    class: `nav__link${active ? " is-active" : ""}`,
    href: hash,
    onclick: () => { state.navOpen = false; },
  }, label, opts.badge ? h("span", { class: "nav__badge", text: String(opts.badge) }) : null);
}

function renderNav() {
  const nav = document.getElementById("nav");
  clear(nav);
  nav.classList.toggle("is-open", state.navOpen);

  const main = h("div", { class: "nav__group" },
    navLink("みんなの投稿", "#/public"),
    state.me ? navLink("フォロー中", "#/home") : null,
    state.me ? navLink("DM", "#/dm", { badge: state.unreadDm || 0 }) : null,
    state.me ? navLink("設定", "#/settings") : null,
    state.me && state.me.is_admin ? navLink("管理", "#/admin") : null,
  );
  const boards = h("div", { class: "nav__group" },
    h("p", { class: "nav__title", text: "板" }),
    ...state.boards.map((b) => navLink(
      `${b.name}${b.verified_only ? "（認証）" : ""}`, `#/board/${b.slug}`)),
  );
  nav.append(main, boards);
}

function renderSide() {
  const side = document.getElementById("side");
  clear(side);

  const search = h("form", {
    class: "card card--tight",
    onsubmit: (ev) => {
      ev.preventDefault();
      const q = search.querySelector("input").value.trim();
      if (q.length >= 2) go(`#/search/${encodeURIComponent(q)}`);
      else toast("2文字以上で検索してください。", true);
    },
  }, h("input", { type: "text", placeholder: "投稿を検索", "aria-label": "投稿を検索" }));

  const rules = h("div", { class: "card small stack" },
    h("p", { class: "section-title", text: "このサイトの決まり" }),
    h("p", { class: "muted", text: "・R18 の画像は自動で止まります。すり抜けたものは通報してください。" }),
    h("p", { class: "muted", text: "・個人の特定につながる書き込み（実名・住所・晒し）は削除します。" }),
    h("p", { class: "muted", text: "・匿名の投稿でも、運営には投稿者が分かります。犯罪予告などは通報します。" }),
    h("p", { class: "muted", text: "・画像の位置情報（EXIF）は保存時に落としています。" }),
  );

  side.append(search, rules);
  if (!state.me) {
    side.append(h("div", { class: "card small stack" },
      h("p", { class: "section-title", text: "はじめてなら" }),
      h("p", { class: "muted", text: "登録せずに匿名で書くこともできます。フォロー・DM・いいねはアカウントが必要です。" }),
      h("button", { class: "btn btn--primary", onclick: () => openAuthModal("guest") }, "ゲストで書き込む"),
    ));
  }
}

/* ---------- 投稿の表示 ---------- */

function authorLine(post) {
  const author = post.author;
  const parts = [];
  if (author.anon) {
    parts.push(h("span", { class: "post__name", text: "匿名" }));
    if (author.anon_id) parts.push(h("span", { class: "badge badge--anon", text: `ID:${author.anon_id}` }));
    if (author.is_you) parts.push(h("span", { class: "badge", text: "あなた" }));
    if (author.verified) parts.push(h("span", { class: "badge badge--verified", text: "東大認証" }));
  } else {
    parts.push(h("a", { class: "post__name", href: `#/user/${author.handle}`, text: author.display_name }));
    parts.push(h("a", { class: "post__handle", href: `#/user/${author.handle}`, text: `@${author.handle}` }));
    if (author.verified) parts.push(h("span", { class: "badge badge--verified", text: "東大認証" }));
  }
  if (post.board) {
    parts.push(h("a", { class: "badge badge--board", href: `#/board/${post.board}`, text: boardName(post.board) }));
  }
  parts.push(h("a", { class: "post__time", href: `#/post/${post.id}`, text: relativeTime(post.created_at) }));
  return h("div", { class: "post__head" }, ...parts);
}

function mediaBlock(post) {
  if (!post.media || post.media.length === 0) return null;
  const grid = h("div", { class: `media${post.media.length === 1 ? " media--single" : ""}` });
  for (const item of post.media) {
    if (item.url) {
      grid.append(h("a", { href: item.url, target: "_blank", rel: "noopener" },
        h("img", { src: item.url, alt: "添付画像", loading: "lazy" })));
    } else if (item.status === "pending") {
      grid.append(h("div", { class: "media__hold", text: "画像を確認中です。公開されるまで表示されません。" }));
    } else {
      grid.append(h("div", { class: "media__hold", text: "この画像は公開されていません。" }));
    }
  }
  return grid;
}

function actionButton(label, kind, on, handler) {
  return h("button", {
    class: `action${on ? " is-on" : ""}`, dataset: { kind }, type: "button", onclick: handler,
  }, label);
}

function postCard(post, options) {
  const opts = options || {};
  const card = h("article", { class: `post${opts.focus ? " post--focus" : ""}` });

  if (post.reposted_by) {
    card.append(h("p", { class: "post__context", text: `${post.reposted_by.display_name} さんがリポスト` }));
  }
  card.append(authorLine(post));

  if (post.deleted) {
    card.append(h("p", { class: "post__body post--deleted", text: "この投稿は削除されました。" }));
    return card;
  }
  if (post.body) card.append(h("p", { class: "post__body", text: post.body }));
  const media = mediaBlock(post);
  if (media) card.append(media);

  const actions = h("div", { class: "post__actions" });
  actions.append(
    actionButton(`返信 ${post.counts.replies || ""}`.trim(), "reply", false, () => go(`#/post/${post.id}`)),
    actionButton(`リポスト ${post.counts.reposts || ""}`.trim(), "repost", post.viewer.reposted, async () => {
      if (!requireAccount("リポスト")) return;
      try {
        const next = !post.viewer.reposted;
        const data = await api("POST", `/api/posts/${post.id}/repost`, { on: next });
        post.viewer.reposted = next;
        post.counts.reposts = data.reposts;
        refreshCard(card, post, opts);
      } catch (err) { toast(err.message, true); }
    }),
    actionButton(`いいね ${post.counts.likes || ""}`.trim(), "like", post.viewer.liked, async () => {
      if (!requireAccount("いいね")) return;
      try {
        const next = !post.viewer.liked;
        const data = await api("POST", `/api/posts/${post.id}/like`, { on: next });
        post.viewer.liked = next;
        post.counts.likes = data.likes;
        refreshCard(card, post, opts);
      } catch (err) { toast(err.message, true); }
    }),
    actionButton("通報", "report", false, () => openReportModal(post)),
  );
  if (post.viewer.can_delete) {
    actions.append(actionButton("削除", "delete", false, async () => {
      if (!confirm("この投稿を削除します。よろしいですか？")) return;
      try {
        await api("DELETE", `/api/posts/${post.id}`);
        toast("削除しました。");
        render();
      } catch (err) { toast(err.message, true); }
    }));
  }
  card.append(actions);
  return card;
}

function refreshCard(card, post, opts) {
  const fresh = postCard(post, opts);
  card.replaceWith(fresh);
}

function postList(items, options) {
  if (!items.length) {
    return h("div", { class: "card center muted", text: "まだ投稿がありません。" });
  }
  const box = h("div", { class: "posts" });
  for (const post of items) box.append(postCard(post, options));
  return box;
}

/* ---------- 投稿フォーム ---------- */

function composer(options) {
  const opts = options || {};
  state.composerMedia = [];

  if (!state.me) {
    return h("div", { class: "card stack" },
      h("p", { class: "section-title", text: opts.parentId ? "返信するには" : "書き込むには" }),
      h("p", { class: "small muted", text: "ゲストのまま匿名で書けます。フォロー・DM・いいねを使うときは登録してください。" }),
      h("div", { class: "row" },
        h("button", { class: "btn btn--primary", onclick: () => openAuthModal("guest") }, "ゲストで書き込む"),
        h("button", { class: "btn", onclick: () => openAuthModal("register") }, "アカウント登録"),
        h("button", { class: "btn btn--ghost", onclick: () => openAuthModal("login") }, "ログイン"),
      ));
  }

  const body = h("textarea", {
    placeholder: opts.parentId ? "返信を書く" : "いま知りたいこと、伝えたいことを書く",
    maxlength: "600", "aria-label": "本文",
    oninput: () => { counter.textContent = `${body.value.length} / 600`; },
  });
  const counter = h("span", { class: "small muted", text: "0 / 600" });
  const thumbs = h("div", { class: "thumbs" });

  const anonymous = h("input", { type: "checkbox", checked: true, disabled: Boolean(state.me.is_guest) });
  const boardSelect = h("select", { "aria-label": "板を選ぶ" },
    ...state.boards.map((b) => h("option", {
      value: b.slug,
      selected: b.slug === (opts.board || "zenpan"),
      disabled: Boolean(b.verified_only && !state.me.verified),
    }, `${b.name}${b.verified_only ? "（東大認証が必要）" : ""}`)),
  );

  const fileInput = h("input", {
    type: "file", accept: "image/png,image/jpeg,image/webp,image/gif", multiple: true,
    onchange: async (ev) => {
      const files = Array.from(ev.target.files || []);
      ev.target.value = "";
      for (const file of files) {
        if (state.composerMedia.length >= 4) { toast("画像は4枚までです。", true); break; }
        await uploadFile(file, thumbs);
      }
    },
  });

  const submit = h("button", { class: "btn btn--primary", type: "submit" }, opts.parentId ? "返信する" : "投稿する");
  const errorBox = h("p", { class: "error", hidden: true });

  const form = h("form", {
    class: "card stack",
    onsubmit: async (ev) => {
      ev.preventDefault();
      errorBox.hidden = true;
      submit.disabled = true;
      try {
        const payload = {
          body: body.value,
          anonymous: anonymous.checked,
          media_ids: state.composerMedia.map((m) => m.id),
        };
        if (opts.parentId) payload.parent_id = opts.parentId;
        else payload.board = boardSelect.value;
        await api("POST", "/api/posts", payload);
        body.value = "";
        counter.textContent = "0 / 600";
        state.composerMedia = [];
        clear(thumbs);
        toast("投稿しました。");
        if (opts.onPosted) opts.onPosted();
        else render();
      } catch (err) {
        errorBox.textContent = err.message;
        errorBox.hidden = false;
      } finally {
        submit.disabled = false;
      }
    },
  },
    body,
    thumbs,
    h("div", { class: "row" },
      opts.parentId ? null : boardSelect,
      h("label", { class: "check" }, anonymous, "匿名で書く"),
      h("label", { class: "check" }, "画像", fileInput),
      h("span", { class: "spacer" }),
      counter,
      submit,
    ),
    errorBox,
    state.me.is_guest
      ? h("p", { class: "small muted", text: "ゲストの書き込みは常に匿名です。" })
      : null,
  );
  return form;
}

async function uploadFile(file, thumbs) {
  if (file.size > 8 * 1024 * 1024) { toast(`${file.name}: 8MB を超えています。`, true); return; }
  const placeholder = h("div", { class: "thumb" },
    h("span", { class: "thumb__status", text: "確認中…" }));
  thumbs.append(placeholder);
  try {
    const buffer = await file.arrayBuffer();
    const data = await api("POST", "/api/media", null, { raw: buffer, contentType: file.type || "image/jpeg" });
    const media = data.media;
    state.composerMedia.push(media);
    clear(placeholder);
    placeholder.append(
      h("img", { src: media.url, alt: file.name }),
      h("span", {
        class: "thumb__status",
        text: media.status === "approved" ? "添付できます" : "確認待ち",
      }),
      h("button", {
        class: "thumb__remove", type: "button", "aria-label": "取り消す",
        onclick: () => {
          state.composerMedia = state.composerMedia.filter((m) => m.id !== media.id);
          placeholder.remove();
        },
      }, "×"),
    );
    if (media.status === "pending") {
      toast(media.reason || "この画像は公開前に管理者が確認します。", true);
    }
  } catch (err) {
    placeholder.remove();
    toast(err.message, true);
  }
}

/* ---------- 各画面 ---------- */

async function viewTimeline(kind, options) {
  const opts = options || {};
  const main = document.getElementById("main");
  clear(main);

  if (opts.heading) {
    main.append(h("div", { class: "card card--tight" },
      h("p", { class: "section-title", text: opts.heading }),
      opts.description ? h("p", { class: "small muted", text: opts.description }) : null));
  }
  main.append(composer({ board: opts.board }));

  const listBox = h("div");
  main.append(listBox);
  const params = new URLSearchParams({ kind });
  if (opts.board) params.set("board", opts.board);
  if (opts.handle) params.set("handle", opts.handle);

  let cursor = null;
  const loadMore = h("button", { class: "btn", onclick: () => load() }, "もっと読む");
  const moreBox = h("div", { class: "center" });
  main.append(moreBox);

  async function load() {
    loadMore.disabled = true;
    try {
      if (cursor) params.set("cursor", cursor);
      const data = await api("GET", `/api/timeline?${params.toString()}`);
      const box = postList(data.items, {});
      if (cursor) listBox.append(box); else { clear(listBox); listBox.append(box); }
      cursor = data.next_cursor;
      clear(moreBox);
      if (cursor) moreBox.append(loadMore);
    } catch (err) {
      clear(listBox);
      listBox.append(h("div", { class: "card error", text: err.message }));
    } finally {
      loadMore.disabled = false;
    }
  }
  await load();
}

async function viewThread(postId) {
  const main = document.getElementById("main");
  clear(main);
  try {
    const data = await api("GET", `/api/posts/${postId}`);
    if (data.ancestors.length) main.append(postList(data.ancestors, {}));
    main.append(postList([data.post], { focus: true }));
    main.append(composer({ parentId: data.post.id, onPosted: () => viewThread(postId) }));
    main.append(h("p", { class: "section-title", text: `返信 ${data.replies.length} 件` }));
    main.append(postList(data.replies, {}));
  } catch (err) {
    main.append(h("div", { class: "card error", text: err.message }));
  }
}

async function viewProfile(handle) {
  const main = document.getElementById("main");
  clear(main);
  try {
    const { user } = await api("GET", `/api/users/${encodeURIComponent(handle)}`);
    const header = h("div", { class: "card stack" },
      h("div", { class: "row" },
        h("strong", { text: user.display_name }),
        user.verified ? h("span", { class: "badge badge--verified", text: "東大認証" }) : null,
        user.is_guest ? h("span", { class: "badge", text: "ゲスト" }) : null,
        h("span", { class: "muted small", text: `@${user.handle}` }),
      ),
      user.bio ? h("p", { text: user.bio }) : null,
      h("p", { class: "small muted" },
        `投稿 ${user.counts.posts}・フォロー ${user.counts.following}・フォロワー ${user.counts.followers}`,
        user.followed_by ? "・あなたをフォローしています" : ""),
    );
    if (state.me && !user.is_self) {
      header.append(h("div", { class: "row" },
        h("button", {
          class: `btn ${user.following ? "" : "btn--primary"}`,
          onclick: async () => {
            if (!requireAccount("フォロー")) return;
            try {
              const next = !user.following;
              await api("POST", `/api/users/${user.handle}/follow`, { on: next });
              toast(next ? "フォローしました。" : "フォローを外しました。");
              viewProfile(handle);
            } catch (err) { toast(err.message, true); }
          },
        }, user.following ? "フォロー中" : "フォローする"),
        h("button", {
          class: "btn",
          onclick: () => { if (requireAccount("DM")) openDmModal(user.handle); },
        }, "DM を送る"),
      ));
    }
    main.append(header);

    const data = await api("GET", `/api/timeline?kind=user&handle=${encodeURIComponent(handle)}`);
    if (user.is_self) {
      main.append(h("p", { class: "small muted", text: "自分の画面では匿名の投稿も表示されます（他の人には見えません）。" }));
    }
    main.append(postList(data.items, {}));
  } catch (err) {
    main.append(h("div", { class: "card error", text: err.message }));
  }
}

async function viewDm(threadId) {
  const main = document.getElementById("main");
  clear(main);
  if (!state.me || state.me.is_guest) {
    main.append(h("div", { class: "card stack" },
      h("p", { class: "section-title", text: "DM はアカウント登録が必要です" }),
      h("button", { class: "btn btn--primary", onclick: () => openAuthModal("register") }, "アカウント登録")));
    return;
  }
  const listBox = h("div", { class: "card dm__list stack" });
  const paneBox = h("div", { class: "card" }, h("p", { class: "muted", text: "左から会話を選んでください。" }));
  main.append(h("div", { class: "dm" }, listBox, paneBox));

  try {
    const { threads } = await api("GET", "/api/dm");
    clear(listBox);
    listBox.append(h("div", { class: "row" },
      h("p", { class: "section-title", text: "DM" }),
      h("span", { class: "spacer" }),
      h("button", { class: "btn btn--small", onclick: () => openDmModal("") }, "新規")));
    if (!threads.length) listBox.append(h("p", { class: "muted small", text: "まだ会話がありません。" }));
    for (const thread of threads) {
      listBox.append(h("div", {
        class: `dm__item${String(thread.id) === String(threadId) ? " is-active" : ""}`,
        onclick: () => go(`#/dm/${thread.id}`),
      },
        h("div", { class: "row" },
          h("strong", { text: thread.user.display_name }),
          thread.unread ? h("span", { class: "nav__badge", text: String(thread.unread) }) : null,
          thread.request ? h("span", { class: "badge", text: "リクエスト" }) : null),
        h("p", { class: "small muted", text: thread.last_message.body.slice(0, 40) })));
    }
    if (threadId) await renderDmThread(paneBox, threadId);
  } catch (err) {
    clear(listBox);
    listBox.append(h("p", { class: "error", text: err.message }));
  }
}

async function renderDmThread(paneBox, threadId) {
  clear(paneBox);
  try {
    const data = await api("GET", `/api/dm/${threadId}`);
    const messages = h("div", { class: "dm__messages" });
    for (const message of data.messages) {
      messages.append(h("div", { class: `bubble${message.mine ? " bubble--mine" : ""}` },
        h("span", { text: message.body }),
        h("span", { class: "bubble__time", text: relativeTime(message.created_at) })));
    }
    const input = h("input", { type: "text", placeholder: "メッセージを書く", maxlength: "2000" });
    const form = h("form", {
      class: "row",
      onsubmit: async (ev) => {
        ev.preventDefault();
        if (!input.value.trim()) return;
        try {
          await api("POST", "/api/dm", { handle: data.user.handle, body: input.value });
          input.value = "";
          await renderDmThread(paneBox, threadId);
          await loadMe();
        } catch (err) { toast(err.message, true); }
      },
    }, input, h("button", { class: "btn btn--primary", type: "submit" }, "送信"));

    paneBox.append(
      h("div", { class: "row" },
        h("strong", { text: data.user.display_name }),
        data.user.handle ? h("a", { class: "small muted", href: `#/user/${data.user.handle}`, text: `@${data.user.handle}` }) : null),
      messages, form);
    messages.scrollTop = messages.scrollHeight;
  } catch (err) {
    paneBox.append(h("p", { class: "error", text: err.message }));
  }
}

async function viewSettings() {
  const main = document.getElementById("main");
  clear(main);
  if (!state.me) { main.append(h("div", { class: "card", text: "ログインしてください。" })); return; }

  const name = h("input", { type: "text", value: state.me.display_name, maxlength: "40" });
  const bio = h("textarea", { maxlength: "300" });
  bio.value = state.me.bio || "";
  main.append(h("form", {
    class: "card stack",
    onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const data = await api("PATCH", "/api/me", { display_name: name.value, bio: bio.value });
        state.me = data.user;
        toast("保存しました。");
        renderTopbar();
      } catch (err) { toast(err.message, true); }
    },
  },
    h("p", { class: "section-title", text: "プロフィール" }),
    h("label", { class: "field" }, h("span", { text: "表示名" }), name),
    h("label", { class: "field" }, h("span", { text: "自己紹介" }), bio),
    h("button", { class: "btn btn--primary", type: "submit" }, "保存")));

  if (!state.me.is_guest) main.append(verificationCard());

  main.append(h("div", { class: "card stack small" },
    h("p", { class: "section-title", text: "匿名について" }),
    h("p", { class: "muted", text: "匿名の投稿では、名前とユーザ名は他の人に見えません。同じスレッドのあいだだけ、その日限りの ID が付きます（自演の見分け用）。" }),
    h("p", { class: "muted", text: "ただし運営は投稿者を特定できます。法令に反する書き込みは、記録とともに対応します。" })));
}

function verificationCard() {
  if (state.me.verified) {
    return h("div", { class: "card stack" },
      h("p", { class: "section-title", text: "東大メールの確認" }),
      h("p", { class: "small muted", text: "確認済みです。認証が必要な板にも書き込めます。" }));
  }
  const email = h("input", { type: "email", placeholder: "example@g.ecc.u-tokyo.ac.jp" });
  const code = h("input", { type: "text", placeholder: "6桁のコード", maxlength: "6" });
  const codeBox = h("div", { class: "stack", hidden: true },
    h("label", { class: "field" }, h("span", { text: "届いたコード" }), code),
    h("button", {
      class: "btn btn--primary", type: "button",
      onclick: async () => {
        try {
          const data = await api("POST", "/api/verify/confirm", { code: code.value });
          state.me = data.user;
          toast("東大メールの確認が終わりました。");
          viewSettings();
        } catch (err) { toast(err.message, true); }
      },
    }, "確認する"));

  return h("div", { class: "card stack" },
    h("p", { class: "section-title", text: "東大メールの確認（任意）" }),
    h("p", { class: "small muted", text: "u-tokyo.ac.jp のアドレスを確認すると認証バッジが付き、進学選択・研究室の板に書き込めます。アドレスは保存しません（照合用のハッシュだけ持ちます）。" }),
    h("label", { class: "field" }, h("span", { text: "メールアドレス" }), email),
    h("button", {
      class: "btn", type: "button",
      onclick: async () => {
        try {
          const data = await api("POST", "/api/verify/request", { email: email.value });
          codeBox.hidden = false;
          toast(data.dev_code
            ? `開発モードのためコードを表示します: ${data.dev_code}`
            : "確認コードを送りました。");
        } catch (err) { toast(err.message, true); }
      },
    }, "コードを送る"),
    codeBox);
}

async function viewAdmin() {
  const main = document.getElementById("main");
  clear(main);
  try {
    const data = await api("GET", "/api/admin/queue");
    main.append(h("div", { class: "card stack" },
      h("p", { class: "section-title", text: `確認待ちの画像 ${data.media.length} 件` }),
      data.media.length ? null : h("p", { class: "muted small", text: "ありません。" }),
      ...data.media.map((media) => h("div", { class: "row" },
        media.url ? h("img", { src: media.url, alt: "確認待ちの画像", class: "thumb__img", width: "96", height: "96" }) : null,
        h("span", { class: "small muted", text: `score ${media.score.toFixed(2)}／${media.reason || "理由なし"}` }),
        h("span", { class: "spacer" }),
        h("button", {
          class: "btn btn--small", onclick: () => moderateMedia(media.id, "approved"),
        }, "公開する"),
        h("button", {
          class: "btn btn--small btn--danger", onclick: () => moderateMedia(media.id, "blocked"),
        }, "ブロック")))));

    main.append(h("div", { class: "card stack" },
      h("p", { class: "section-title", text: `未対応の通報 ${data.reports.length} 件` }),
      data.reports.length ? null : h("p", { class: "muted small", text: "ありません。" }),
      ...data.reports.map((report) => h("div", { class: "stack" },
        h("p", { class: "small" },
          h("span", { class: "badge", text: report.reason_label }),
          ` ${report.target_type} #${report.target_id}`,
          report.note ? `／${report.note}` : ""),
        report.post ? postCard(report.post, {}) : null,
        h("div", { class: "row" },
          h("button", {
            class: "btn btn--small btn--danger",
            onclick: () => resolveReport(report.id, "delete_post"),
          }, "投稿を削除"),
          h("button", {
            class: "btn btn--small", onclick: () => resolveReport(report.id, "dismiss"),
          }, "問題なし"))))));
  } catch (err) {
    main.append(h("div", { class: "card error", text: err.message }));
  }
}

async function moderateMedia(mediaId, status) {
  try {
    await api("POST", `/api/admin/media/${mediaId}`, { status });
    toast(status === "approved" ? "公開しました。" : "ブロックしました。");
    viewAdmin();
  } catch (err) { toast(err.message, true); }
}

async function resolveReport(reportId, resolution) {
  try {
    await api("POST", `/api/admin/reports/${reportId}`, { resolution });
    toast("対応しました。");
    viewAdmin();
  } catch (err) { toast(err.message, true); }
}

async function viewSearch(q) {
  const main = document.getElementById("main");
  clear(main);
  main.append(h("p", { class: "section-title", text: `「${q}」の検索結果` }));
  try {
    const data = await api("GET", `/api/search?q=${encodeURIComponent(q)}`);
    main.append(postList(data.items, {}));
  } catch (err) {
    main.append(h("div", { class: "card error", text: err.message }));
  }
}

/* ---------- モーダル ---------- */

function openModal(builder) {
  const modal = document.getElementById("modal");
  const panel = document.getElementById("modal-panel");
  clear(panel);
  panel.append(builder(closeModal));
  modal.hidden = false;
  document.getElementById("modal-backdrop").onclick = closeModal;
}

function closeModal() {
  document.getElementById("modal").hidden = true;
}

function openAuthModal(mode) {
  let current = mode || "login";
  openModal((close) => {
    const wrap = h("div", { class: "stack" });
    const renderPanel = () => {
      clear(wrap);
      const tabs = h("div", { class: "tabs" },
        h("button", { class: `tab${current === "login" ? " is-active" : ""}`, onclick: () => { current = "login"; renderPanel(); } }, "ログイン"),
        h("button", { class: `tab${current === "register" ? " is-active" : ""}`, onclick: () => { current = "register"; renderPanel(); } }, "新規登録"),
        h("button", { class: `tab${current === "guest" ? " is-active" : ""}`, onclick: () => { current = "guest"; renderPanel(); } }, "ゲスト"),
      );
      wrap.append(tabs);

      if (current === "guest") {
        wrap.append(
          h("p", { class: "small muted", text: "登録せずに匿名で書き込めます。いいね・リポスト・フォロー・DM は使えません。" }),
          h("button", {
            class: "btn btn--primary",
            onclick: async () => {
              try {
                const data = await api("POST", "/api/guest");
                state.me = data.user;
                close();
                toast("ゲストとして書き込めます。");
                await loadMe();
                await render();
              } catch (err) { toast(err.message, true); }
            },
          }, "ゲストで始める"));
        return;
      }

      const handle = h("input", { type: "text", placeholder: "英数字3〜20文字", maxlength: "20" });
      const displayName = h("input", { type: "text", placeholder: "表示名", maxlength: "40" });
      const password = h("input", { type: "password", placeholder: "8文字以上" });
      const error = h("p", { class: "error", hidden: true });
      wrap.append(h("form", {
        class: "stack",
        onsubmit: async (ev) => {
          ev.preventDefault();
          error.hidden = true;
          try {
            const payload = { handle: handle.value, password: password.value };
            if (current === "register") payload.display_name = displayName.value || handle.value;
            const data = await api("POST", current === "register" ? "/api/register" : "/api/login", payload);
            state.me = data.user;
            close();
            toast(current === "register" ? "登録しました。" : "ログインしました。");
            await loadMe();
            await render();
          } catch (err) {
            error.textContent = err.message;
            error.hidden = false;
          }
        },
      },
        h("label", { class: "field" }, h("span", { text: "ユーザ名" }), handle),
        current === "register" ? h("label", { class: "field" }, h("span", { text: "表示名" }), displayName) : null,
        h("label", { class: "field" }, h("span", { text: "パスワード" }), password),
        h("button", { class: "btn btn--primary", type: "submit" },
          current === "register" ? "登録する" : "ログイン"),
        error,
        current === "register"
          ? h("p", { class: "small muted", text: "本名やメールアドレスは不要です。東大メールの確認は登録後に任意でできます。" })
          : null));
    };
    renderPanel();
    return wrap;
  });
}

function openReportModal(post) {
  if (!requireLogin()) return;
  openModal((close) => {
    const reason = h("select", { "aria-label": "通報の理由" },
      h("option", { value: "r18" }, "性的な画像・R18"),
      h("option", { value: "harassment" }, "誹謗中傷・晒し"),
      h("option", { value: "personal_info" }, "個人情報"),
      h("option", { value: "spam" }, "スパム・宣伝"),
      h("option", { value: "illegal" }, "違法・危険"),
      h("option", { value: "other" }, "その他"));
    const note = h("textarea", { placeholder: "補足（任意）", maxlength: "500" });
    return h("form", {
      class: "stack",
      onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          await api("POST", "/api/reports", {
            target_type: "post", target_id: String(post.id),
            reason: reason.value, note: note.value,
          });
          close();
          toast("通報しました。運営が確認します。");
        } catch (err) { toast(err.message, true); }
      },
    },
      h("p", { class: "section-title", text: "この投稿を通報する" }),
      h("label", { class: "field" }, h("span", { text: "理由" }), reason),
      note,
      h("div", { class: "row" },
        h("button", { class: "btn btn--primary", type: "submit" }, "通報する"),
        h("button", { class: "btn btn--ghost", type: "button", onclick: close }, "やめる")));
  });
}

function openDmModal(handle) {
  openModal((close) => {
    const to = h("input", { type: "text", value: handle || "", placeholder: "相手のユーザ名" });
    const body = h("textarea", { placeholder: "メッセージ", maxlength: "2000" });
    return h("form", {
      class: "stack",
      onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          const data = await api("POST", "/api/dm", { handle: to.value.replace(/^@/, ""), body: body.value });
          close();
          toast("送信しました。");
          go(`#/dm/${data.message.thread_id}`);
        } catch (err) { toast(err.message, true); }
      },
    },
      h("p", { class: "section-title", text: "DM を送る" }),
      h("label", { class: "field" }, h("span", { text: "宛先" }), to),
      body,
      h("button", { class: "btn btn--primary", type: "submit" }, "送信"));
  });
}

/* ---------- 起動 ---------- */

async function logout() {
  try { await api("POST", "/api/logout"); } catch (err) { /* すでに切れている場合は無視 */ }
  state.me = null;
  state.csrf = null;
  state.unreadDm = 0;
  toast("ログアウトしました。");
  location.hash = "#/public";
  await render();
}

async function loadMe() {
  try {
    const data = await api("GET", "/api/me");
    state.me = data.user;
    state.csrf = data.csrf || null;
    state.unreadDm = data.unread_dm || 0;
  } catch (err) {
    state.me = null;
  }
}

async function loadBoards() {
  try {
    const data = await api("GET", "/api/boards");
    state.boards = data.boards;
  } catch (err) {
    state.boards = [];
  }
}

function render_() {
  renderTopbar();
  renderNav();
  renderSide();
}

async function render() {
  render_();
  const route = currentRoute();
  switch (route.name) {
    case "home":
      if (!state.me) { openAuthModal(); go("#/public"); return; }
      await viewTimeline("home", { heading: "フォロー中", description: "フォローしている人の実名投稿とリポストが並びます。" });
      break;
    case "board": {
      const slug = route.args[0];
      const board = state.boards.find((b) => b.slug === slug);
      await viewTimeline("board", {
        board: slug,
        heading: board ? board.name : slug,
        description: board ? board.description : "",
      });
      break;
    }
    case "post":
      await viewThread(route.args[0]);
      break;
    case "user":
      await viewProfile(route.args[0]);
      break;
    case "dm":
      await viewDm(route.args[0]);
      break;
    case "settings":
      await viewSettings();
      break;
    case "admin":
      await viewAdmin();
      break;
    case "search":
      await viewSearch(route.args[0] || "");
      break;
    default:
      await viewTimeline("public", {
        heading: "みんなの投稿",
        description: "板をまたいだ新着。匿名でもそのまま読めます。",
      });
  }
  window.scrollTo({ top: 0 });
}

window.addEventListener("hashchange", render);
document.getElementById("menu-toggle").addEventListener("click", () => {
  state.navOpen = !state.navOpen;
  renderNav();
});

(async function start() {
  await Promise.all([loadMe(), loadBoards()]);
  await render();
})();

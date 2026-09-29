// Playwright の Chromium でページを開く共通処理。
// Google Fonts はプロキシ環境でブラウザから直接取れないことがあるので、
// curl（システムのCA設定を使う）で取得して .fontcache/ に保存し、そこから返す。
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");
const { execFileSync } = require("child_process");

function loadPlaywright() {
  const candidates = ["playwright", "/opt/node22/lib/node_modules/playwright"];
  for (const c of candidates) {
    try { return require(c); } catch (e) { /* 次へ */ }
  }
  throw new Error("playwright が見つかりません（npm i -g playwright）");
}

const CACHE = path.join(__dirname, "..", ".fontcache");
const UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36";

function cached(url) {
  fs.mkdirSync(CACHE, { recursive: true });
  const f = path.join(CACHE, crypto.createHash("sha1").update(url).digest("hex"));
  if (!fs.existsSync(f)) {
    const body = execFileSync("curl", ["-sSfL", "-A", UA, url], { maxBuffer: 64 * 1024 * 1024 });
    fs.writeFileSync(f, body);
  }
  return fs.readFileSync(f);
}

async function openPage({ file, width = 1280, height = 900, dark = false, media = "screen" }) {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width, height }, colorScheme: dark ? "dark" : "light" });
  page.on("pageerror", (e) => console.error("pageerror:", e.message));
  await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, async (route) => {
    const url = route.request().url();
    try {
      const body = cached(url);
      const type = url.includes("googleapis") ? "text/css; charset=utf-8" : "font/woff2";
      await route.fulfill({ status: 200, body, headers: { "content-type": type, "access-control-allow-origin": "*" } });
    } catch (e) {
      console.error("font fetch failed:", url);
      await route.abort();
    }
  });
  await page.emulateMedia({ media });
  await page.goto("file://" + path.resolve(file), { waitUntil: "networkidle", timeout: 180000 });
  await page.evaluate(() => document.fonts.ready);
  return { browser, page };
}

module.exports = { openPage };

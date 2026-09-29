#!/usr/bin/env node
// dist/kobun-tango-500.html を A4 の PDF にする。
//   node tools/make_pdf.cjs            → dist/kobun-tango-500.pdf
// 先に python3 build.py を実行しておくこと。
const path = require("path");
const { openPage } = require("./browser.cjs");

(async () => {
  const root = path.join(__dirname, "..");
  const src = path.join(root, "dist", "kobun-tango-500.html");
  const out = path.join(root, "dist", "kobun-tango-500.pdf");
  const { browser, page } = await openPage({ file: src, media: "print" });
  await page.pdf({ path: out, format: "A4", printBackground: true, preferCSSPageSize: true });
  await browser.close();
  console.log("wrote", path.relative(root, out));
})().catch((e) => { console.error(e); process.exit(1); });

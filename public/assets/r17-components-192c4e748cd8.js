/* Search/memo run only in this browser; no requests, cookies or storage. */
(() => {
  'use strict';
  const normalize = (s) => String(s || '').normalize('NFKC').toLocaleLowerCase('ja').trim();
  // カタカナをひらがなに寄せ、同じ語の表記ゆれで0件にならないようにする。
  const kana = (s) => normalize(s).replace(/[\u30a1-\u30f6]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
  // 入力された語に対して、記事側で使われやすい別の言い方（すべて部分一致で見る）。
  const SYNONYMS = {
    '要約': ['要約', 'summary', '短くまとめ'],
    '英作文': ['英作文', 'writing', '作文', 'ライティング'],
    '模試': ['模試', 'マーク模試', '判定'],
    '保護者': ['保護者', '親', '家庭'],
    '計画': ['計画', 'プラン', 'planner', '予定表'],
    '単語': ['単語', 'ボキャブラリー', 'vocabulary'],
    '長文': ['長文', '読解', 'reading'],
    '共通テスト': ['共通テスト', 'センター', 'kyotsu'],
    '東大': ['東大', '東京大学', 'todai'],
    '塾': ['塾', '予備校', 'juku'],
    'リスニング': ['リスニング', '聞き取り', 'listening'],
    '過去問': ['過去問', '赤本', 'kakomon'],
    '復習': ['復習', '解き直し', 'review'],
    '宿題': ['宿題', '課題', 'homework'],
    '不登校': ['不登校', '通信制', 'futoukou'],
    '浪人': ['浪人', '既卒', 'gap year'],
    '併願': ['併願', '受験校', '日程'],
    '面接': ['面接', '小論文', 'interview'],
  };
  // ひらがな・カタカナで打った読みから、記事側の漢字の語へ戻す。
  const READINGS = {
    'えいさくぶん': '英作文', 'ようやく': '要約', 'もぎ': '模試',
    'ほごしゃ': '保護者', 'けいかく': '計画', 'たんご': '単語', 'ちょうぶん': '長文',
    'きょうつうてすと': '共通テスト', 'とうだい': '東大', 'じゅく': '塾',
    'りすにんぐ': 'リスニング', 'かこもん': '過去問', 'ふくしゅう': '復習',
    'しゅくだい': '宿題', 'ふとうこう': '不登校', 'ろうにん': '浪人',
    'へいがん': '併願', 'めんせつ': '面接',
  };
  const candidates = (term) => {
    const key = kana(term);
    const canonical = READINGS[key];
    const extra = canonical || Object.keys(SYNONYMS).find((k) => kana(k) === key);
    const list = extra ? SYNONYMS[extra] : [term];
    const out = new Set([key]);
    for (const item of list) out.add(kana(item));
    return Array.from(out);
  };
  const finder = document.querySelector('[data-r17-finder]');
  if (finder) {
    const input = finder.querySelector('[data-r17-query]');
    const group = finder.querySelector('[data-r17-category]');
    const cards = Array.from(document.querySelectorAll('[data-r17-card]'));
    const status = finder.querySelector('[data-r17-status]');
    const empty = document.querySelector('[data-r17-empty]');
    const texts = cards.map((card) => kana(card.textContent));
    const update = () => {
      const terms = input.value.split(/[\s\u3000]+/).map(kana).filter(Boolean);
      const groups = terms.map(candidates);
      let count = 0;
      cards.forEach((card, i) => {
        const text = texts[i];
        const shown = (!group.value || card.dataset.category === group.value)
          && groups.every((alts) => alts.some((t) => text.includes(t)));
        card.hidden = !shown;
        if (shown) count++;
      });
      status.textContent = count === 0
        ? `${cards.length}件のうち、条件に合うガイドは見つかりませんでした。`
        : `${cards.length}件中${count}件を表示しています。`;
      if (empty) empty.hidden = count !== 0;
    };
    input.addEventListener('input', update);
    group.addEventListener('change', update);
    finder.querySelector('[data-r17-reset]').addEventListener('click', () => {
      input.value = ''; group.value = ''; update(); input.focus();
    });
    update();
  }
  for (const memo of document.querySelectorAll('[data-r17-memo]')) {
    const issue = memo.querySelector('[data-r17-issue]');
    const materials = memo.querySelector('[data-r17-materials]');
    const output = memo.querySelector('[data-r17-output]');
    const status = memo.querySelector('[data-r17-copy-status]');
    const title = document.querySelector('h1')?.textContent?.trim() || '学習ガイド';
    const canonical = document.querySelector('link[rel="canonical"]')?.href || location.origin + location.pathname;
    const update = () => {
      output.value = `黒田塾の無料相談について\n読んだページ：${title}\n${canonical}\n\n困っていること：${issue.value.trim() || '（ここに記入）'}\n現在の教材・授業：${materials.value.trim() || '（分かる範囲で記入）'}\n\n次に取り組む課題を相談したいです。`;
      status.textContent = '';
    };
    issue.addEventListener('input', update); materials.addEventListener('input', update); update();
    memo.querySelector('[data-r17-copy]').addEventListener('click', async () => {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
        await navigator.clipboard.writeText(output.value);
        status.textContent = 'コピーしました。内容を確認し、LINEにご自身で貼り付けて送信してください。';
      } catch (_) {
        output.focus(); output.select();
        status.textContent = '文章を選択しました。端末の「コピー」を使ってください。';
      }
    });
  }
})();

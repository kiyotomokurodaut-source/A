/* An optional visible topic selection, not visitor tracking. */
(() => {
  'use strict';
  const field = document.getElementById('consult-topic');
  if (!field) return;
  const topics = {english:'英語の読み方チェック6問',math:'数学の解説・方針の選び方',todai:'東大理系数学2026 第3問の解説',plan:'学習計画・学習管理',mock:'模試の復習シート',homework:'中学受験の宿題',pricing:'料金・プラン',cases:'指導事例'};
  const key = new URLSearchParams(location.search).get('topic');
  if (key && Object.hasOwn(topics,key)) field.value = topics[key];

  const planField=document.getElementById('consult-support');
  const plans={"interview-only":"面談のみ","lesson-only":"授業のみ（週1回）","interview-lesson-1":"面談＋授業（週1回）","interview-lesson-2":"面談＋授業（週2回）","interview-lesson-3":"面談＋授業（週3回）"};
  const planKey=new URLSearchParams(location.search).get('plan');
  if(planField&&planKey&&Object.hasOwn(plans,planKey))planField.value=plans[planKey];
})();

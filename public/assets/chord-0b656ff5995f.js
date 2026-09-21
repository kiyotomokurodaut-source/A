(()=>{'use strict';
const get=id=>document.getElementById(id), slider=get('chord-angle'),controls=get('chord-controls'),out=get('chord-readout');
if(!slider||!controls||!out)return;
const scale=46,ox=322,oy=292;const pos=(e,x,y)=>{e.setAttribute('cx',ox+x*scale);e.setAttribute('cy',oy-y*scale);};
const fmt=n=>Math.abs(n)<0.0005?'0.000':n.toFixed(3);
function update(){const deg=Number(slider.value);const rad=deg*Math.PI/180;const u=3-2*Math.cos(rad),v=-2*Math.sin(rad),r=Math.hypot(u,v),h=Math.sqrt(Math.max(0,25-r*r));const bad=Math.abs(deg-180)<1e-8;
const px=u-v*h/r,py=v+u*h/r,qx=u+v*h/r,qy=v-u*h/r;
pos(get('chord-m'),u,v);get('chord-om').setAttribute('x2',ox+u*scale);get('chord-om').setAttribute('y2',oy-v*scale);
get('chord-pq').setAttribute('x1',ox+px*scale);get('chord-pq').setAttribute('y1',oy-py*scale);get('chord-pq').setAttribute('x2',ox+qx*scale);get('chord-pq').setAttribute('y2',oy-qy*scale);
pos(get('chord-p'),px,py);pos(get('chord-q'),qx,qy);for(const id of ['chord-pq','chord-p','chord-q'])get(id).style.visibility=bad?'hidden':'visible';
get('chord-live-title').textContent=bad?'θ=180度ではPとQが一致するため不可':`θ=${deg}度の弦PQと中点M`;
out.classList.toggle('chord-warning',bad);out.textContent=bad?'θ = 180°\nM = (5.000, 0.000)\n弦の長さは0。PとQが一致するため、この配置は条件を満たしません。':`θ = ${deg}°\nM = (${fmt(u)}, ${fmt(v)})\nP = (${fmt(px)}, ${fmt(py)})\nQ = (${fmt(qx)}, ${fmt(qy)})\nR = (${fmt(4*Math.cos(rad))}, ${fmt(4*Math.sin(rad))}, 3.000)\n弦の長さ = ${fmt(2*h)}`;
get('chord-caption').textContent=bad?'背景の塗りつぶしが通過範囲。(5, 0) は除外点です。θ=180°の配置は不可のため、弦を表示していません。':`背景の塗りつぶしが通過範囲。(5, 0) は除外点です。現在の弦はθ=${deg}°。数式から描いた表示用の近似で、正確な条件は本文の不等式です。`;
}
slider.addEventListener('input',update);document.querySelectorAll('[data-angle]').forEach(b=>b.addEventListener('click',()=>{slider.value=b.dataset.angle;update();}));controls.hidden=false;update();
})();

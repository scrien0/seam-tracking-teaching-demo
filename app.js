const types = {
  butt: {name:'拼接焊', title:'拼接焊 · 轨迹跟踪', form:'1段直线', path:'M170 250 L630 250', plate:'<path d="M120 160H680V238H120Z"/><path d="M120 262H680V340H120Z"/>', laser:'M400 110L400 390', profile:'M25 72H112L140 94L168 72H255', fx:140, fy:94, feature:'拼接缝中心点'},
  arc: {name:'圆弧焊', title:'圆弧焊 · 曲线路径跟踪', form:'圆弧路径', path:'M205 315 A205 205 0 0 1 595 315', plate:'<path d="M130 325 A270 270 0 0 1 670 325 L670 390H130Z"/>', laser:'M400 110L400 390', profile:'M25 86H105Q112 86 112 79V58H168V79Q168 86 175 86H255', fx:140, fy:58, feature:'凸形焊道平顶中心特征点'},
  lap: {name:'搭接焊', title:'搭接焊 · 搭接边缘跟踪', form:'沿上板搭接边缘直线', path:'M240 270 L600 270', plate:'<path d="M120 180H680V350H120Z"/><path d="M240 130H600V270H240Z" fill="#d7d7d7"/>', laser:'M420 140L420 335', sensor:{x:420,y:263,angle:0}, profile:'M25 82H128V54H255', fx:128, fy:54, feature:'上板边缘形成的搭接拐点'},
  corner: {name:'直角焊', title:'直角焊 · T形接头角焊跟踪', form:'沿立板与底板交界线', path:'M250 308 L500 308', plate:'<polygon points="160,310 475,310 610,370 295,370" fill="#d0d0d0"/><polygon points="295,370 610,370 610,388 295,388" fill="#aaaaaa"/><polygon points="250,310 500,310 500,115 250,115" fill="#cccccc"/><polygon points="500,310 520,320 520,125 500,115" fill="#aaaaaa"/><path d="M250 307L500 307" stroke="#888888" stroke-width="8" stroke-linecap="round"/>', topPlate:'<path d="M150 155H650V335H150Z"/><path d="M150 238H650V262H150Z" fill="#d0d0d0"/>', topPath:'M180 250 L620 250', laser:'M400 130L400 340', sensor:{x:400,y:243,angle:0}, profile:'M25 94H140V25 M140 94H255', fx:140, fy:94, feature:'立板与底板交界处的角部特征点'}
};
let chosen = 'butt';
const el = id => document.getElementById(id);
function render() {
  const t=types[chosen], x=+el('x').value, y=+el('y').value, a=+el('a').value, dx=x*4, dy=y*4;
  const tr=`translate(${dx} ${dy}) rotate(${a} 400 250)`;
  const trackPath=t.topPath||t.path;
  el('plate').innerHTML=t.topPlate||t.plate; el('plate').setAttribute('transform',tr);
  el('ideal').setAttribute('d',trackPath); el('ideal').removeAttribute('transform');
  el('actual').setAttribute('d',trackPath); el('actual').removeAttribute('transform');
  el('laser').setAttribute('d',t.laser); el('laser').setAttribute('transform',tr);
  const p=trackPath.match(/M\s*([\d.]+)\s+([\d.]+)/);
  const sensor=t.sensor||{x:400,y:(+p[2])-7,angle:0};
  el('sensor').setAttribute('transform',`translate(${sensor.x+dx} ${sensor.y+dy}) rotate(${sensor.angle+a})`);
  el('dot').setAttribute('cx',+p[1]); el('dot').setAttribute('cy',+p[2]); el('dot').removeAttribute('transform');
  el('profile').setAttribute('d',t.profile); el('featureProfile').setAttribute('d',t.profile);
  el('featurePoint').setAttribute('cx',t.fx); el('featurePoint').setAttribute('cy',t.fy);
  el('featureCross').setAttribute('d',`M${t.fx-14} ${t.fy}H${t.fx+14}M${t.fx} ${t.fy-14}V${t.fy+14}`);
  el('featureDescription').textContent=`提取${t.feature}。`;
  el('sensorCoord').textContent=`( ${t.fx}, ${t.fy} ) px`;
  el('robotCoord').textContent=`( ${x}, ${y} ) mm`;
  el('title').textContent=t.title; el('kind').textContent=t.name; el('form').textContent=t.form;
  el('xv').textContent=`${x>0?'+':''}${x} mm`; el('yv').textContent=`${y>0?'+':''}${y} mm`; el('av').textContent=`${a>0?'+':''}${a}°`;
  el('delta').textContent=`ΔX ${x} mm　ΔY ${y} mm　θ ${a}°`;
}
document.querySelectorAll('[data-seam]').forEach(b=>b.onclick=()=>{
  document.querySelector('.active').classList.remove('active'); b.classList.add('active'); chosen=b.dataset.seam; render();
});
['x','y','a'].forEach(id=>el(id).oninput=()=>{
  el('scene').classList.remove('running','corrected');
  el('status').textContent='待运行'; el('status').style.color='';
  el('state').textContent='待运行'; el('state').style.color='';
  el('run').disabled=false; el('run').textContent='▶　运行一次跟踪演示';
  resetStages();
  render();
});
document.querySelectorAll('[data-seam]').forEach(b=>b.addEventListener('click',()=>{
  el('scene').classList.remove('running','corrected');
  el('status').textContent='待运行'; el('state').textContent='待运行';
  el('run').disabled=false; el('run').textContent='▶　运行一次跟踪演示';
  resetStages();
}));
el('run').onclick=()=>{
  const button=el('run'), scene=el('scene');
  button.disabled=true; button.textContent='跟踪运行中…';
  scene.classList.add('running');
  const start=tPathStart();
  const dx=+el('x').value*4, dy=+el('y').value*4, degrees=+el('a').value;
  const duration=1400;
  let began=0;
  function movePath(now){
    const progress=Math.min((now-began)/duration,1), eased=progress*progress*(3-2*progress);
    const rad=degrees*eased*Math.PI/180, c=Math.cos(rad), s=Math.sin(rad);
    const tx=400-c*400+s*250+dx*eased, ty=250-s*400-c*250+dy*eased;
    el('ideal').setAttribute('transform',`matrix(${c} ${s} ${-s} ${c} ${tx} ${ty})`);
    const targetX=c*start.x-s*start.y+tx, targetY=s*start.x+c*start.y+ty;
    el('dot').setAttribute('transform',`translate(${targetX-start.x} ${targetY-start.y})`);
    if(progress<1) requestAnimationFrame(movePath);
  }
  el('state').textContent='正在采集焊缝截面…'; el('state').style.color='#222222';
  el('stage1State').textContent='采集中'; el('stage1').classList.add('active');
  window.setTimeout(()=>{el('stage1State').textContent='已采集';el('stage1').classList.remove('active');el('stage1').classList.add('done');el('stage2State').textContent='提取中';el('stage2').classList.add('active');el('state').textContent='正在提取焊缝特征点…';},650);
  window.setTimeout(()=>{el('stage2State').textContent='已提取';el('stage2').classList.remove('active');el('stage2').classList.add('done');el('stage3State').textContent='转换中';el('stage3').classList.add('active');el('state').textContent='正在转换到机器人路径坐标…';},1400);
  window.setTimeout(()=>{
    el('stage3State').textContent='已转换';el('stage3').classList.remove('active');el('stage3').classList.add('done');
    el('stage4State').textContent='正在修正';el('stage4').classList.add('active');
    el('status').textContent='跟踪中';el('status').style.color='#222222';el('state').textContent='坐标转换完成，正在修正初始路径…';
    began=performance.now();requestAnimationFrame(movePath);
  },2200);
  window.setTimeout(()=>{
    scene.classList.remove('running'); scene.classList.add('corrected'); button.disabled=false; button.textContent='▶　再次运行跟踪演示';
    el('stage4State').textContent='已完成';el('stage4').classList.remove('active');el('stage4').classList.add('done');
    el('status').textContent='演示完成'; el('state').textContent='演示完成 · 已按偏差修正';
  },3900);
};
function resetStages(){
  ['stage1','stage2','stage3','stage4'].forEach(id=>el(id).classList.remove('active','done'));
  el('stage1State').textContent='待采集';el('stage2State').textContent='等待截面';el('stage3State').textContent='等待特征点';el('stage4State').textContent='等待坐标转换';
}
function tPathStart(){const t=types[chosen],match=(t.topPath||t.path).match(/M\s*([\d.]+)\s+([\d.]+)/);return{x:+match[1],y:+match[2]};}
render();
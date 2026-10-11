const colors = {'Regresión logística':'#527d91','Bosque aleatorio':'#d98b4e','SVM RBF':'#8e74a5'};
const shortNames = {'Regresión logística':'Regresión logística','Bosque aleatorio':'Bosque aleatorio','SVM RBF':'SVM RBF'};
let overviewData, performanceData, featureData;
const $ = id => document.getElementById(id);
const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.tab,.panel').forEach(el => el.classList.remove('active'));
  button.classList.add('active'); $(button.dataset.tab).classList.add('active');
}));

function horizontalBars(target, rows, max, colorFn) {
  $(target).innerHTML = rows.map(row => `<div class="bar-row"><span>${escapeHtml(row.name)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(1,row.value/max*100)}%;background:${colorFn(row.name)}"></div></div><b>${escapeHtml(row.display ?? row.value)}</b></div>`).join('');
}

function renderOverview() {
  const d=overviewData;
  $('stat-patients').textContent=d.patients; $('stat-images').textContent=d.images;
  $('stat-centers').textContent=d.centers; $('stat-regions').textContent=d.features[1].value.toLocaleString('es-GT');
  horizontalBars('class-chart', [{name:'CE',value:d.classes.CE},{name:'LAA',value:d.classes.LAA}],d.patients,n=>n==='CE'?'#527d91':'#d98b4e');
  const split=[['Entreno','entrenamiento'],['Validación','validacion'],['Prueba','prueba']].map(([name,key])=>({name,value:d.split[key]}));
  horizontalBars('split-chart',split,d.patients,()=> '#356b50'); renderCenters();
}

function renderCenters() {
  const filter=$('center-filter').value, rows=overviewData.by_center;
  const ids=[...new Set(rows.map(r=>r.center))].sort((a,b)=>Number(a)-Number(b));
  const totals=ids.map(id=>rows.filter(r=>r.center===id&& (filter==='all'||r.label===filter)).reduce((a,r)=>a+r.count,0));
  const max=Math.max(...totals);
  $('center-chart').innerHTML=ids.map((id,i)=>{
    const ce=filter==='LAA'?0:(rows.find(r=>r.center===id&&r.label==='CE')?.count||0);
    const laa=filter==='CE'?0:(rows.find(r=>r.center===id&&r.label==='LAA')?.count||0);
    return `<div class="center-item"><div class="center-stack"><div class="center-piece laa" style="height:${laa/max*145}px" title="Centro ${id}: ${laa} LAA"></div><div class="center-piece ce" style="height:${ce/max*145}px" title="Centro ${id}: ${ce} CE"></div></div><strong>${id}</strong><span>${totals[i]}</span></div>`;
  }).join('');
  const largest=totals.indexOf(max);
  $('center-insight').textContent=`Centro ${ids[largest]}: ${max} pacientes ${filter==='all'?'en total':'de clase '+filter}. La cantidad de pacientes varía entre centros; esa diferencia puede influir en lo que aprende el modelo.`;
}
$('center-filter').addEventListener('change',()=>overviewData&&renderCenters());

function featureLabel(name) {
  const prefix=name.startsWith('media_')?'Promedio':'Variación';
  const base=name.replace(/^(media|desv)_/,'');
  const descriptions={r_media:'intensidad roja',g_media:'intensidad verde',b_media:'intensidad azul',h_media:'tono',s_media:'saturación',v_media:'brillo',gris_desv:'variación de gris',gris_entropia:'entropía de gris',gradiente_media:'intensidad de bordes',gradiente_desv:'variación de bordes',laplaciano_var:'textura laplaciana'};
  return `${prefix} · ${descriptions[base]||base.replaceAll('_',' ')}`;
}
function formatValue(value) {return Math.abs(value)>=100?value.toFixed(1):Math.abs(value)>=1?value.toFixed(3):value.toFixed(4)}
function median(values) {const sorted=[...values].sort((a,b)=>a-b);return sorted.length?sorted[Math.floor((sorted.length-1)/2)]/2+sorted[Math.floor(sorted.length/2)]/2:null}
function renderFeatures() {
  if(!featureData)return;
  const column=$('feature-select').value, index=featureData.columns.indexOf(column);
  const split=$('feature-split').value, center=$('feature-center').value, selectedClass=$('feature-class').value;
  const rows=featureData.rows.filter(r=>(split==='all'||r.split===split)&&(center==='all'||r.center===center)&&(selectedClass==='all'||r.label===selectedClass));
  $('feature-description').textContent=column.startsWith('media_')?'Promedio de esta medida entre las regiones del paciente.':'Desviación de esta medida entre las regiones del paciente.';
  if(!rows.length){$('feature-chart').textContent='No hay pacientes para esta combinación de filtros.';$('feature-summary').textContent='';return}
  const values=rows.map(r=>r.values[index]), minimum=Math.min(...values), maximum=Math.max(...values);
  const low=minimum===maximum?minimum-.5:minimum, high=minimum===maximum?maximum+.5:maximum, bins=16;
  const groups={CE:[],LAA:[]};rows.forEach(r=>groups[r.label].push(r.values[index]));
  const counts={CE:Array(bins).fill(0),LAA:Array(bins).fill(0)};
  for(const label of ['CE','LAA'])for(const value of groups[label])counts[label][Math.min(bins-1,Math.floor((value-low)/(high-low)*bins))]++;
  const fractions={CE:counts.CE.map(x=>groups.CE.length?x/groups.CE.length:0),LAA:counts.LAA.map(x=>groups.LAA.length?x/groups.LAA.length:0)};
  const peak=Math.max(.01,...fractions.CE,...fractions.LAA), W=760,H=250,L=48,R=20,T=18,B=40,plotW=W-L-R,plotH=H-T-B,band=plotW/bins;
  const grid=[0,.25,.5,.75,1].map(v=>`<line class="grid" x1="${L}" x2="${W-R}" y1="${T+plotH*(1-v)}" y2="${T+plotH*(1-v)}"/><text x="${L-8}" y="${T+plotH*(1-v)+4}" text-anchor="end">${Math.round(v*peak*100)}%</text>`).join('');
  const bars=Array.from({length:bins},(_,i)=>['CE','LAA'].map((label,j)=>{const value=fractions[label][i],height=value/peak*plotH,x=L+i*band+j*band*.42+2,y=T+plotH-height;return `<rect x="${x}" y="${y}" width="${band*.39}" height="${height}" rx="2" fill="${label==='CE'?'#527d91':'#d98b4e'}"><title>${label}: ${counts[label][i]} pacientes (${Math.round(value*100)} % de la clase filtrada)</title></rect>`}).join('')).join('');
  $('feature-chart').innerHTML=`<svg class="chart-svg feature-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribución de ${featureLabel(column)} por clase">${grid}${bars}<line class="axis" x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}"/><text x="${L}" y="${H-14}">${formatValue(low)}</text><text x="${W-R}" y="${H-14}" text-anchor="end">${formatValue(high)}</text></svg>`;
  $('feature-summary').innerHTML=['CE','LAA'].map(label=>`<div><span class="swatch" style="background:${label==='CE'?'#527d91':'#d98b4e'}"></span><b>${label}</b> · ${groups[label].length} pacientes · mediana ${groups[label].length?formatValue(median(groups[label])):'—'}</div>`).join('');
}
['feature-select','feature-split','feature-center','feature-class'].forEach(id=>$(id).addEventListener('change',renderFeatures));

function visibleModels() {return Object.keys(colors).filter(name=>document.querySelector(`input[data-model="${name}"]`)?.checked)}
function metricLabel(key){return {roc_auc:'AUC ROC',balanced_accuracy:'Exactitud balanceada',average_precision:'Precisión promedio',recall_laa:'Sensibilidad LAA'}[key]}
function renderPerformance() {
  if(!performanceData)return;
  const names=visibleModels(), metric=$('metric-select').value, split=$('split-select').value;
  $('metric-name').textContent=metricLabel(metric);
  const rows=performanceData.metrics.filter(r=>r.particion===split&&names.includes(r.modelo));
  $('metric-chart').innerHTML=rows.length?rows.map(r=>`<div class="metric-row"><div class="metric-row-head"><span>${escapeHtml(r.modelo)}</span><b>${Number(r[metric]).toFixed(3)}</b></div><div class="bar-track"><div class="bar-fill" style="width:${r[metric]*100}%;background:${colors[r.modelo]}"></div></div></div>`).join(''):'Selecciona al menos un modelo.';
  const show=$('show-curves').checked;
  $('roc-chart').parentElement.style.display=show?'block':'none';
  if(show) drawRoc(names);
  renderConfusion();
}
$('show-performance').addEventListener('change',event=>{
  $('performance-content').hidden=!event.target.checked;
  $('performance-hidden').hidden=event.target.checked;
});
function drawRoc(names) {
  const W=500,H=255,L=48,R=16,T=17,B=37,sx=x=>L+x*(W-L-R),sy=y=>H-B-y*(H-T-B);
  const grid=[0,.25,.5,.75,1].map(v=>`<line class="grid" x1="${sx(v)}" x2="${sx(v)}" y1="${sy(0)}" y2="${sy(1)}"/><line class="grid" x1="${sx(0)}" x2="${sx(1)}" y1="${sy(v)}" y2="${sy(v)}"/><text x="${sx(v)}" y="${H-17}" text-anchor="middle">${v}</text><text x="${L-9}" y="${sy(v)+4}" text-anchor="end">${v}</text>`).join('');
  const lines=names.map(name=>{const points=performanceData.curves[name].roc.map(([x,y])=>`${sx(x)},${sy(y)}`).join(' ');return `<polyline fill="none" stroke="${colors[name]}" stroke-width="2.6" points="${points}"/>`}).join('');
  $('roc-chart').innerHTML=`<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Curvas ROC en pacientes de prueba">${grid}<line class="axis" x1="${L}" x2="${sx(1)}" y1="${sy(0)}" y2="${sy(0)}"/><line class="axis" x1="${L}" x2="${L}" y1="${sy(0)}" y2="${T}"/><line stroke="#b9c0b7" stroke-dasharray="5 5" x1="${sx(0)}" y1="${sy(0)}" x2="${sx(1)}" y2="${sy(1)}"/>${lines}<text x="${W/2}" y="${H-2}" text-anchor="middle">Falsos positivos</text><text x="12" y="${H/2}" transform="rotate(-90 12 ${H/2})" text-anchor="middle">Sensibilidad</text></svg>`;
}
function renderConfusion() {
  const model=$('confusion-select').value, split=$('split-select').value;
  const row=performanceData.metrics.find(r=>r.modelo===model&&r.particion===split);
  $('confusion-chart').innerHTML=`<div class="confusion-grid"><div></div><div>Pred. CE</div><div>Pred. LAA</div><div>Real CE</div><div class="confusion-cell">${row.tn}<small>correcto</small></div><div class="confusion-cell error">${row.fp}<small>falso LAA</small></div><div>Real LAA</div><div class="confusion-cell error">${row.fn}<small>falso CE</small></div><div class="confusion-cell">${row.tp}<small>correcto</small></div></div>`;
}
['metric-select','split-select','show-curves','confusion-select'].forEach(id=>$(id).addEventListener('change',renderPerformance));

$('image-input').addEventListener('change',event=>{
  const files=[...event.target.files];
  $('file-list').textContent=files.length?files.map(f=>f.name).join(' · '):'Todavía no seleccionaste archivos.';
});
$('predict-form').addEventListener('submit',async event=>{
  event.preventDefault(); const button=event.target.querySelector('button');button.disabled=true;
  $('prediction-result').innerHTML='<div class="empty-result">Procesando imágenes y regiones…</div>';
  try{
    const response=await fetch('/api/predict',{method:'POST',body:new FormData(event.target)});
    const data=await response.json(); if(!response.ok)throw new Error(data.error||'No se pudo clasificar.');
    $('prediction-result').innerHTML=`<div class="result-meta">${data.images_with_regions} de ${data.images_uploaded} imágenes con tejido · ${data.regions} regiones analizadas</div>`+data.predictions.map(p=>`<div class="prediction-item"><div><strong>${escapeHtml(p.model)}</strong><span class="pill ${p.class==='LAA'?'laa':''}">${p.class}</span></div><p>Salida LAA del modelo: ${(p.probability_laa*100).toFixed(1)} %</p><div class="bar-track"><div class="bar-fill" style="width:${p.probability_laa*100}%;background:${colors[p.model]}"></div></div></div>`).join('');
  }catch(error){$('prediction-result').innerHTML=`<div class="empty-result error-message">${escapeHtml(error.message)}</div>`}finally{button.disabled=false}
});

Promise.all([fetch('/api/overview').then(r=>r.json()),fetch('/api/performance').then(r=>r.json()),fetch('/api/features').then(r=>r.json())]).then(([o,p,f])=>{
  overviewData=o;performanceData=p;featureData=f;renderOverview();
  $('feature-select').innerHTML=f.columns.map(name=>`<option value="${name}">${featureLabel(name)}</option>`).join('');
  $('feature-select').value='media_gris_entropia';
  $('feature-center').innerHTML+=[...new Set(f.rows.map(r=>r.center))].sort((a,b)=>Number(a)-Number(b)).map(center=>`<option value="${center}">Centro ${center}</option>`).join('');
  renderFeatures();
  $('model-toggles').innerHTML=Object.keys(colors).map(name=>`<label><input type="checkbox" data-model="${name}" checked><span class="swatch" style="background:${colors[name]}"></span>${shortNames[name]}</label>`).join('');
  $('model-toggles').addEventListener('change',renderPerformance);renderPerformance();
}).catch(()=>{$('class-chart').textContent='No se pudieron cargar los resultados locales.'});

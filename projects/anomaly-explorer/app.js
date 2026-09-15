const metrics={flow_lpm:{name:'Flow',unit:'L/min',low:8,high:18},conductivity_us_cm:{name:'Conductivity',unit:'µS/cm',low:0,high:650},pressure_bar:{name:'Pressure',unit:'bar',low:0,high:4}};
const select=document.querySelector('#metric'),lowInput=document.querySelector('#low'),highInput=document.querySelector('#high');
let latest=null;
function draw(rows,metric,low,high){
 const svg=document.querySelector('#chart');svg.replaceChildren();
 const ns='http://www.w3.org/2000/svg';
 const add=(tag,attrs,text)=>{const el=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));if(text!==undefined)el.textContent=text;svg.append(el);return el;};
 const values=rows.map(row=>row[metric]);let min=Math.min(...values,low),max=Math.max(...values,high);const pad=(max-min)*.12||1;min-=pad;max+=pad;
 const x=i=>65+i/(rows.length-1)*780,y=v=>265-(v-min)/(max-min)*225;
 for(let i=0;i<5;i++){const v=min+(max-min)*i/4;add('line',{x1:65,x2:845,y1:y(v),y2:y(v),stroke:'#dae4e8'});add('text',{x:55,y:y(v)+5,'text-anchor':'end'},v.toFixed(metric==='conductivity_us_cm'?0:1));}
 for(const [v,name] of [[low,'Low'],[high,'High']]){add('line',{x1:65,x2:845,y1:y(v),y2:y(v),stroke:'#b64f27','stroke-dasharray':'6 5'});add('text',{x:850,y:y(v)+5},name);}
 add('polyline',{points:values.map((v,i)=>`${x(i)},${y(v)}`).join(' '),fill:'none',stroke:'#087361','stroke-width':2});
 rows.forEach((row,i)=>{if(row[metric]<low||row[metric]>high)add('circle',{cx:x(i),cy:y(row[metric]),r:4,fill:'#b64f27'});});
 for(const i of [0,36,72,108,143])add('text',{x:x(i),y:296,'text-anchor':'middle'},rows[i].timestamp.slice(11,16));
 add('text',{x:450,y:325,'text-anchor':'middle'},'Time (UTC)');
}
function render(){
 const error=document.querySelector('#error');
 try{
  if(lowInput.value.trim()===''||highInput.value.trim()==='')throw new Error('Enter both thresholds.');
  const metric=select.value,low=Number(lowInput.value),high=Number(highInput.value);
  latest={metric,low,high,...analyze(PILOT_REPORT.measurements,metric,low,high)};
  error.textContent='';document.querySelector('#results').hidden=false;document.querySelector('#download').disabled=false;
  document.querySelector('#count').textContent=latest.count;
  document.querySelector('#flagged').textContent=latest.flagged.length;
  document.querySelector('#mean').textContent=latest.mean.toFixed(2);
  document.querySelector('#mean-label').textContent=`Mean (${metrics[metric].unit})`;
  document.querySelector('#chart-title').textContent=metrics[metric].name+' · Synthetic demonstration';
  document.querySelector('#chart').setAttribute('aria-label',`${metrics[metric].name} over 24 hours; ${latest.flagged.length} readings outside thresholds. Values are also available in the table and CSV.`);
  draw(PILOT_REPORT.measurements,metric,low,high);
  const body=document.querySelector('tbody');body.replaceChildren();
  latest.flagged.forEach(row=>{const tr=document.createElement('tr');for(const value of [row.timestamp.slice(11,19)+' UTC',row.asset,row[metric]+' '+metrics[metric].unit,row[metric]<low?'Below lower threshold':'Above upper threshold']){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);});
  document.querySelector('#empty').hidden=latest.flagged.length>0;
 }catch(exc){error.textContent=exc.message;latest=null;document.querySelector('#results').hidden=true;document.querySelector('#download').disabled=true;}
}
function reset(){const m=metrics[select.value];lowInput.value=m.low;highInput.value=m.high;render();}
select.addEventListener('change',reset);lowInput.addEventListener('input',render);highInput.addEventListener('input',render);document.querySelector('#reset').addEventListener('click',reset);
document.querySelector('#download').addEventListener('click',()=>{if(!latest)return;const csv=['timestamp,asset,metric,value,low,high',...latest.flagged.map(row=>[row.timestamp,row.asset,latest.metric,row[latest.metric],latest.low,latest.high].join(','))].join('\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='flagged-readings.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});reset();

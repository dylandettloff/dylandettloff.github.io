const community = document.querySelector('#community');
const future = document.querySelector('#future');
const label = {RO:'Reverse osmosis', ED:'Electrodialysis', HDH:'Humidification–dehumidification', MSPD:'Multi-stage passive distillation'};
for (const value of [...new Set(RESEARCH_RESULTS.map(r=>r.community))]) community.add(new Option(value,value));
for (const value of [...new Set(RESEARCH_RESULTS.map(r=>r.future))]) future.add(new Option(value,value));
community.value='Navajo';
function render(){
  const rows=RESEARCH_RESULTS.filter(r=>r.community===community.value&&r.future===future.value).sort((a,b)=>b.win_rate-a.win_rate);
  document.querySelector('#winner').textContent=rows[0].tech;
  document.querySelector('#win-rate').textContent=(rows[0].win_rate*100).toFixed(1)+'%';
  document.querySelector('#feasible').textContent=rows.length;
  const bars=document.querySelector('#bars'); bars.replaceChildren();
  const body=document.querySelector('tbody'); body.replaceChildren();
  for(const row of rows){
    const item=document.createElement('div');item.className='bar-row';
    const name=document.createElement('strong');name.textContent=row.tech;
    const track=document.createElement('div');track.className='bar-track';
    const fill=document.createElement('div');fill.className='bar-fill';fill.style.width=(row.win_rate*100)+'%';track.append(fill);
    const value=document.createElement('span');value.className='bar-value';value.textContent=(row.win_rate*100).toFixed(1)+'%';
    item.append(name,track,value);bars.append(item);
    const tr=document.createElement('tr');
    for(const value of [label[row.tech],(row.win_rate*100).toFixed(2)+'%',row.avg_rank.toFixed(3)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);
  }
  document.querySelector('#context').textContent=`${community.value} · ${future.value} · Stored research results`;
}
community.addEventListener('change',render);future.addEventListener('change',render);render();

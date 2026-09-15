"use strict";
// Pure functions shared by the UI and Node tests.
function analyze(rows, metric, low, high){
  if(!Number.isFinite(low)||!Number.isFinite(high)||low>=high)throw new Error('Lower threshold must be less than upper threshold.');
  if(!rows.length)throw new Error('No measurements to analyze.');
  const values=rows.map(row=>row[metric]);
  if(values.some(value=>!Number.isFinite(value)))throw new Error('Measurements must be finite numbers.');
  const flagged=rows.filter(row=>row[metric]<low||row[metric]>high);
  return {flagged,mean:values.reduce((a,b)=>a+b,0)/values.length,min:Math.min(...values),max:Math.max(...values),count:rows.length};
}
if(typeof module!=='undefined')module.exports={analyze};

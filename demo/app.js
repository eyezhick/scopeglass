'use strict';
const $ = id => document.getElementById(id);
const make = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
const signed = value => (value >= 0 ? '+' : '') + value.toFixed(2);
const config = {
  garden_path: { hypothesis: 'Does a comma spare the model the cost of closing the wrong clause?', labels: {ambiguity:'Subordinate verb', boundary:'Boundary cue'} },
  np_s: { hypothesis: 'Does “that” help when the following noun could be an object or a new subject?', labels: {ambiguity:'Matrix verb', boundary:'Complementizer'} },
  agreement: { hypothesis: 'Which noun controls the verb: the subject, or the nearby distractor?', labels: {head:'Subject number', distractor:'Distractor number', verb:'Verb number'} },
  polarity: { hypothesis: 'Does “no” influence “ever” even from inside a relative clause?', labels: {location:'Negation location', negation:'Negation', target:'Critical word'} },
};
const names = {ambiguous:'Ambiguous verb',control:'Control',absent:'Absent',comma:'Comma',that:'Explicit “that”',sg:'Singular',pl:'Plural',matrix:'Matrix clause',embedded:'Relative clause',present:'Present',npi:'ever'};
let runs = {}, experiment = 'garden_path', factors = {};

function rowsForFrame() {
  return runs[$('model').value].rows.filter(row => row.experiment === experiment && row.item === $('frame').value);
}

function selectExperiment(preserve = false) {
  const previousFrame = $('frame').value;
  const previousFactors = {...factors};
  const rows = runs[$('model').value].rows.filter(row => row.experiment === experiment);
  $('frame').replaceChildren();
  for (const item of [...new Set(rows.map(row => row.item))]) {
    const example = rows.find(row => row.item === item);
    const option = make('option', item + ' · ' + example.context.split(' ').slice(0,4).join(' ') + '…');
    option.value = item;
    $('frame').append(option);
  }
  if (preserve && rows.some(row => row.item === previousFrame)) $('frame').value = previousFrame;
  selectFrame(preserve ? previousFactors : null);
}

function selectFrame(previous = null) {
  const rows = rowsForFrame();
  factors = {...rows[0].factors};
  $('factors').replaceChildren();
  for (const factor of Object.keys(factors)) {
    const label = make('label', config[experiment].labels[factor]);
    const select = make('select');
    select.name = factor;
    for (const value of [...new Set(rows.map(row => row.factors[factor]))]) {
      const text = factor === 'target' && value === 'control' ? 'often' : names[value] || value;
      const option = make('option', text); option.value = value; select.append(option);
    }
    if (previous && rows.some(row => row.factors[factor] === previous[factor])) {
      factors[factor] = previous[factor]; select.value = previous[factor];
    }
    select.addEventListener('change', () => {factors[factor] = select.value; renderSentence();});
    label.append(select); $('factors').append(label);
  }
  $('hypothesis').textContent = config[experiment].hypothesis;
  renderSentence();
}

function renderSentence() {
  const rows = rowsForFrame();
  const row = rows.find(row => Object.entries(factors).every(([key,value]) => row.factors[key] === value));
  $('sentence').replaceChildren(document.createTextNode(row.context + ' '), make('mark',row.target.trim()), make('span',row.spillover,'spillover'));
  $('score').textContent = row.surprisal_bits.toFixed(2);
  $('probability').textContent = 'P(scored region | context) ≈ ' + (100 * 2 ** -row.surprisal_bits).toPrecision(3) + '%';
  $('reading').textContent = 'Lower surprisal means this region was more expected in this context. A high value alone does not establish a syntactic effect.';
  $('tokens').replaceChildren(...row.tokens.map(token => make('span',JSON.stringify(token.text) + ' · ' + token.bits.toFixed(3) + ' bits','token')));
  $('conditions').replaceChildren();
  const maximum = Math.ceil(Math.max(...rows.map(row => row.surprisal_bits)));
  for (const condition of rows) {
    const container = make('div',undefined,'condition' + (condition.id === row.id ? ' selected' : ''));
    container.setAttribute('role','row');
    const description = Object.entries(condition.factors).map(([key,value]) => {
      if (key === 'target') return value === 'npi' ? 'ever' : 'often';
      return key + ': ' + (names[value] || value).toLowerCase();
    }).join(' / ');
    const label = make('span',description); label.setAttribute('role','cell');
    const track = make('div',undefined,'track'); track.setAttribute('aria-hidden','true');
    const bar = make('div',undefined,'bar'); bar.style.width = (100 * condition.surprisal_bits / Math.max(1,maximum)) + '%'; track.append(bar);
    const value = make('span',condition.surprisal_bits.toFixed(2) + ' b','value'); value.setAttribute('role','cell');
    container.append(label,track,value); $('conditions').append(container);
  }
  $('status').textContent = 'Measured run: ' + runs[$('model').value].metadata.model + ' · ' + row.item + ' · selected region: ' + row.surprisal_bits.toFixed(2) + ' bits · bar scale: 0–' + maximum + ' bits';
}

function plot(result) {
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox','0 0 300 82'); svg.setAttribute('role','img');
  svg.setAttribute('aria-label',result.title + ': ' + signed(result.estimate) + ' bits; 95% interval ' + result.ci95.map(signed).join(' to '));
  const extent = Math.max(1,...result.items.map(item => Math.abs(item.value)),...result.ci95.map(Math.abs));
  const x = value => 150 + value / extent * 128;
  const shape = (tag,attrs,text) => {const node = document.createElementNS(ns,tag); Object.entries(attrs).forEach(([key,value]) => node.setAttribute(key,value)); if (text !== undefined) node.textContent=text; svg.append(node); return node;};
  shape('line',{x1:22,y1:29,x2:278,y2:29,stroke:'#ced5c8'});
  shape('line',{x1:150,y1:5,x2:150,y2:58,stroke:'#9aa993','stroke-dasharray':'3 3'});
  result.items.forEach((item,index) => shape('circle',{cx:x(item.value),cy:15+(index%4)*8,r:3,fill:'#14634f',opacity:.7}));
  shape('line',{x1:x(result.ci95[0]),y1:53,x2:x(result.ci95[1]),y2:53,stroke:'#bd5133','stroke-width':3});
  shape('circle',{cx:x(result.estimate),cy:53,r:4,fill:'#bd5133'});
  [-extent,0,extent].forEach(value => shape('text',{x:x(value),y:76,'text-anchor':'middle',fill:'#61706a','font-size':10,'font-family':'monospace'},value.toFixed(1)));
  return svg;
}

function renderEffects() {
  const run = runs[$('model').value]; $('effect-cards').replaceChildren();
  for (const result of run.summary) {
    const card=make('article',undefined,'effect');
    const number=make('div',signed(result.estimate),'estimate'); number.append(make('span',' bits'));
    card.append(make('h3',result.title),number,make('div','95% CI ['+result.ci95.map(signed).join(', ')+']','ci'),plot(result),make('p',result.interpretation));
    $('effect-cards').append(card);
  }
  $('data-link').href='data/'+$('model').value+'.json'; $('report-link').href=$('model').value+'-report.html';
}

document.querySelectorAll('[data-experiment]').forEach(button => button.addEventListener('click', () => {
  experiment=button.dataset.experiment;
  document.querySelectorAll('[data-experiment]').forEach(tab => tab.setAttribute('aria-pressed',String(tab===button)));
  selectExperiment();
}));
$('model').addEventListener('change', () => {selectExperiment(true);renderEffects();});
$('frame').addEventListener('change', () => selectFrame());
$('bits').addEventListener('input', () => {
  const bits=Number($('bits').value); $('bits-value').textContent=bits+' bits';
  $('bits-probability').textContent='Probability: '+(100*2**-bits).toPrecision(3)+'% · 1 in '+(2**bits).toLocaleString();
});
document.querySelectorAll('button,select').forEach(control => {control.disabled=true;});
Promise.all(['distilgpt2','gpt2'].map(async key => {
  const response=await fetch('data/'+key+'.json');
  if(!response.ok) throw new Error('Unable to load '+key+' results');
  runs[key]=await response.json();
})).then(() => {
  selectExperiment();renderEffects();
  document.querySelectorAll('button,select').forEach(control => {control.disabled=false;});
}).catch(error => {
  $('status').textContent=error.message+'. Serve the demo over HTTP, or use the self-contained reports.';
  document.querySelectorAll('button,select').forEach(control => {control.disabled=true;});
});

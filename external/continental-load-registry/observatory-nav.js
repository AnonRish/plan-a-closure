(function(){
  const path=(location.pathname.split('/').pop()||'index.html').toLowerCase();
  const isIndex=path===''||path==='index.html';
  const isTrack3=path==='track3.html';
  const isResearch=path==='research.html';
  const isClosedCases=path==='closed-cases.html';
  const isAccounting=path==='global-accounting.html';
  const isCoverage=path==='track3-complete-coverage.html';
  const navItems=[
    {key:'overview',label:'Overview',href:'index.html#main',anchor:'main',page:'index'},
    {key:'map',label:'Map',href:'index.html#registryMap',anchor:'registryMap',page:'index'},
    {key:'evidence',label:'Evidence',href:'index.html#queueUniverse',anchor:'queueUniverse',page:'index'},
    {key:'data',label:'Data',href:'index.html#completeProjectLedger',anchor:'completeProjectLedger',page:'index'},
    {key:'track3',label:'Track 3',href:'track3.html',page:'track3'},
    {key:'closed',label:'Closed cases',href:'closed-cases.html',page:'closed'},
    {key:'accounting',label:'Global accounting',href:'global-accounting.html',page:'accounting'},
    {key:'coverage',label:'Full coverage',href:'track3-complete-coverage.html',page:'coverage'},
    {key:'research',label:'Research',href:'research.html',page:'research'},
    {key:'methods',label:'Methods',href:'index.html#methodology',anchor:'methodology',page:'index'}
  ];
  function activeClass(item){
    if(isTrack3&&item.page==='track3')return 'page';
    if(isClosedCases&&item.page==='closed')return 'page';
    if(isAccounting&&item.page==='accounting')return 'page';
    if(isCoverage&&item.page==='coverage')return 'page';
    if(isResearch&&item.page==='research')return 'page';
    if(isIndex&&item.page==='index'){
      if(location.hash && item.anchor===location.hash.slice(1))return 'location';
      if(!location.hash && item.key==='overview')return 'location';
    }
    return '';
  }
  function render(){
    const wrap=document.querySelector('[data-observatory-nav]');
    if(!wrap)return;
    const nav=wrap.querySelector('.obs-nav');
    nav.innerHTML='';
    navItems.forEach(function(item){
      const a=document.createElement('a');
      a.className='obs-tab';
      a.href=item.href;
      a.textContent=item.label;
      const ac=activeClass(item);
      if(ac)a.setAttribute('aria-current',ac==='page'?'page':'location');
      nav.appendChild(a);
    });
    const spacer=document.createElement('span');spacer.className='obs-nav-spacer';nav.appendChild(spacer);
    const rev=document.createElement('span');rev.className='obs-nav-rev';rev.textContent='OBSERVATORY · 2026';nav.appendChild(rev);
  }
  function progress(){
    let el=document.querySelector('.obs-progress');
    if(!el){el=document.createElement('div');el.className='obs-progress';el.innerHTML='<i></i>';document.body.prepend(el)}
    const i=el.firstElementChild;
    const max=document.documentElement.scrollHeight-window.innerHeight;
    i.style.width=(max>0?Math.min(100,Math.max(0,window.scrollY/max*100)):0)+'%';
  }
  function injectIndexCaseLink(){
    const actions=document.querySelector('.registry-deck-actions');
    if(!actions||document.getElementById('navClosedCasesLink'))return;
    const a=document.createElement('a');
    a.id='navClosedCasesLink';
    a.className='registry-mini-link';
    a.href='closed-cases.html';
    a.textContent='Closed cases';
    actions.appendChild(a);
  }
  function injectClosureFocus(){
    if(!isTrack3||document.getElementById('closureFocusBanner'))return;
    fetch('data/track3/ambiguous_case_studies.json?cb=20260927',{cache:'no-store'}).then(function(r){return r.ok?r.json():null}).then(function(d){
      if(!d||!d.cases)return;
      const el=document.createElement('section');
      el.id='closureFocusBanner';
      el.style.cssText='max-width:1180px;margin:12px auto 0;padding:0 16px';
      el.innerHTML='<div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;padding:14px 16px;border:1px solid var(--line);border-radius:14px;background:var(--panel);box-shadow:0 8px 24px rgba(22,35,58,.05)">'+
        '<div><div style="font:600 9px/1.2 IBM Plex Mono,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-faint)">CURRENT LEVER · CLOSED-CASE PILOT</div>'+
        '<div style="font-size:17px;font-weight:700;letter-spacing:-.02em;margin-top:5px">Three ambiguous cases are now the primary validation unit.</div>'+
        '<div style="font-size:11px;line-height:1.5;color:var(--ink-soft);margin-top:4px">'+d.cases.length+' cases · '+d.cases.filter(function(x){return String(x.adjudication).indexOf('CONFIRMED_')===0}).length+' confirmed outcomes · '+d.cases.filter(function(x){return x.adjudication==='INCONCLUSIVE_AFTER_SEARCH'}).length+' deliberately inconclusive. Epoch sites remain a reference cross-check.</div></div>'+
        '<a href="closed-cases.html" style="display:inline-flex;align-items:center;justify-content:center;padding:9px 12px;border-radius:9px;background:var(--ink);color:var(--panel);text-decoration:none;font:600 10px IBM Plex Mono,monospace;white-space:nowrap">OPEN CASE FILES →</a></div>';
      const nav=document.querySelector('[data-observatory-nav]');
      if(nav)nav.insertAdjacentElement('afterend',el);
    }).catch(function(){});
  }
  function init(){
    const old=document.querySelector('[data-observatory-nav]');
    if(old)old.remove();
    document.getElementById('closureFocusBanner')?.remove();
    document.getElementById('navClosedCasesLink')?.remove();
    progress();
    if(isIndex){injectIndexCaseLink();return;}
    const wrap=document.createElement('div');wrap.className='obs-nav-wrap';wrap.setAttribute('data-observatory-nav','');
    const nav=document.createElement('nav');nav.className='obs-nav';nav.setAttribute('aria-label','Registry sections');
    wrap.appendChild(nav);
    const insertAfter=document.querySelector('.visual-hero, header.hero, .hero, header');
    if(insertAfter)insertAfter.insertAdjacentElement('afterend',wrap);
    render();initSectionObserver();injectClosureFocus();
    document.querySelectorAll('.obs-tab[href*="#"]').forEach(function(a){
      a.addEventListener('click',function(){setTimeout(function(){render()},0)});
    });
  }
  function initSectionObserver(){
    if(!isIndex||typeof IntersectionObserver==='undefined')return;
    const map=new Map(navItems.filter(x=>x.anchor).map(x=>[x.anchor,x]));
    const obs=new IntersectionObserver(function(entries){
      entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top).forEach(function(e){
        const item=map.get(e.target.id);if(!item)return;
        document.querySelectorAll('.obs-tab[aria-current="location"]').forEach(function(a){a.removeAttribute('aria-current')});
        const link=document.querySelector('.obs-tab[href$="#'+item.anchor+'"]');
        if(link)link.setAttribute('aria-current','location');
      });
    },{rootMargin:'-18% 0px -68% 0px',threshold:0});
    navItems.filter(x=>x.anchor).forEach(function(x){const el=document.getElementById(x.anchor);if(el)obs.observe(el)});
  }
  window.addEventListener('scroll',progress,{passive:true});
  window.addEventListener('hashchange',render);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
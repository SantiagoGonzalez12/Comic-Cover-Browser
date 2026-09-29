#!/usr/bin/env python3
"""Comic Cover Browser (Comic Vine). Uses only the Python standard library."""
import json, os, re, urllib.parse, urllib.request, urllib.error, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
KEYFILE = os.path.join(HERE, "comicvine_key.txt")
BASE, UA, PORT = "https://comicvine.gamespot.com/api/", "ComicCoverBrowser/1.0", 8765
CACHE, KEY = {}, ""


def get_key():
    k = os.environ.get("COMICVINE_API_KEY", "").strip()
    if not k and os.path.exists(KEYFILE):
        k = open(KEYFILE).read().strip()
    if not k:
        k = input("Paste your Comic Vine API key (comicvine.gamespot.com/api): ").strip()
        open(KEYFILE, "w").write(k)
    return k


def cv(path, **params):
    params.update(api_key=KEY, format="json")
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    if url in CACHE:
        return CACHE[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        msg = "Rate limit reached, please wait a while." if e.code == 420 else f"HTTP error {e.code}"
        return {"status_code": e.code, "error": msg}
    except Exception as e:
        return {"status_code": 0, "error": f"Could not connect: {e}"}
    if data.get("status_code") == 1:
        CACHE[url] = data
    return data


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/":
            return self.send(PAGE, "text/html; charset=utf-8")
        if u.path == "/api/characters":
            return self.send(cv("search/", resources="character", query=q.get("q", ""), limit=30,
                                field_list="id,name,real_name,publisher,image,count_of_issue_appearances"))
        if u.path == "/api/charvols":
            return self.send(cv("character/4005-" + re.sub(r"\D", "", q.get("id", "")) + "/",
                                field_list="id,volume_credits"))
        if u.path == "/api/volumes":
            ids = "|".join(re.sub(r"\D", "", x) for x in q.get("ids", "").split(",") if x)
            return self.send(cv("volumes/", filter="id:" + ids, limit=100,
                                field_list="id,name,start_year,count_of_issues,publisher,image"))
        if u.path == "/api/people":
            return self.send(cv("search/", resources="person", query=q.get("q", ""), limit=30,
                                field_list="id,name,image,hometown,deck"))
        if u.path == "/api/personvols":
            return self.send(cv("person/4040-" + re.sub(r"\D", "", q.get("id", "")) + "/",
                                field_list="id,volume_credits"))
        if u.path == "/api/volsearch":
            return self.send(cv("search/", resources="volume", query=q.get("q", ""), limit=100,
                                page=int(q.get("page", 1)),
                                field_list="id,name,start_year,count_of_issues,publisher,image"))
        if u.path == "/api/search":
            return self.send(cv("search/", resources="volume", query=q.get("q", ""), limit=40,
                                field_list="id,name,start_year,count_of_issues,publisher,image"))
        if u.path == "/api/issues":
            return self.send(cv("issues/", filter="volume:" + re.sub(r"\D", "", q.get("volume", "")),
                                sort="cover_date:asc", offset=int(q.get("offset", 0)), limit=100,
                                field_list="id,issue_number,cover_date,image"))
        if u.path == "/api/variants":
            return self.send(cv("issue/4000-" + re.sub(r"\D", "", q.get("issue", "")) + "/",
                                field_list="id,associated_images"))
        if u.path == "/api/img":  # descarga con nombre de archivo
            src = q.get("u", "")
            host = urllib.parse.urlparse(src).hostname or ""
            if not (host.endswith("comicvine.gamespot.com") or host.endswith("comicvine.com")):
                self.send_error(400)
                return
            try:
                req = urllib.request.Request(src, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data, ctype = r.read(), r.headers.get("Content-Type", "image/jpeg")
            except Exception:
                self.send_error(502)
                return
            ext = os.path.splitext(urllib.parse.urlparse(src).path)[1] or ".jpg"
            name = re.sub(r"[^\w\-]+", "_", q.get("n", "cover")) + ext
            return self.send(data, ctype, {"Content-Disposition": f'attachment; filename="{name}"'})
        self.send_error(404)


PAGE = r"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Covers</title>
<style>
:root{--board:#d6dce0;--ink:#101828;--tape:#f2b705;--paper:#fafaf7;--mute:#5b6675}
*{box-sizing:border-box}body{margin:0;background:var(--board);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--ink);color:#fff;padding:12px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{margin:0;font:800 28px "Arial Narrow","Helvetica Neue",sans-serif;font-stretch:condensed;letter-spacing:.5px}
form{flex:1;display:flex;gap:8px;min-width:260px}
input,select{padding:9px 12px;border:0;border-radius:4px;font:inherit}form input{flex:1}
button,.btn{background:var(--tape);color:var(--ink);border:0;border-radius:4px;padding:9px 14px;font:600 14px system-ui;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
.mode{display:flex;border:1px solid #4a5568;border-radius:5px;overflow:hidden}
.mode button{background:none;color:#fff;border-radius:0}.mode button.on{background:var(--tape);color:var(--ink)}
main{padding:20px;max-width:1500px;margin:auto}
.msg{color:var(--mute);padding:30px 0;text-align:center}.err{color:#a4161a}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:16px}
.chars{grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
figure{margin:0;background:var(--paper);padding:8px;border-radius:3px;box-shadow:0 1px 0 rgba(0,0,0,.25);position:relative}
figure img{width:100%;aspect-ratio:2/3;object-fit:cover;display:block;background:#c3cad0}
figcaption{display:flex;justify-content:space-between;align-items:center;padding-top:6px;font-size:13px}
figcaption a{color:var(--ink);font-weight:600}
.var::before{content:"variant";position:absolute;top:14px;left:0;background:var(--tape);font:700 12px system-ui;padding:2px 8px}
.char{display:flex;gap:12px;cursor:pointer}.char img{width:60px;flex:none}
.char b{display:block}.char span,.sec span,.info{color:var(--mute);font-size:13px}
.tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px}.tools h2{margin:0;font-size:22px}
.tools input{width:220px}.sp{flex:1}
details.sec{background:var(--paper);border-radius:4px;margin-bottom:8px;box-shadow:0 1px 0 rgba(0,0,0,.25)}
summary{display:flex;gap:12px;align-items:center;padding:8px 12px;cursor:pointer;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸";transition:transform .15s;font-size:16px}details[open]>summary::before{transform:rotate(90deg)}
summary img{width:38px;aspect-ratio:2/3;object-fit:cover;background:#c3cad0}summary b{display:block}
.body{padding:4px 14px 16px;background:var(--board)}
.bar{display:flex;gap:12px;align-items:center;margin:10px 0}
</style>
<header><h1>COVERS</h1>
<div class="mode"><button type="button" data-m="char" class="on">Character</button><button type="button" data-m="comic">Comic</button><button type="button" data-m="artist">Artist</button></div>
<form id="f"><input id="q" placeholder="Character: Batman, Spider-Man, Catwoman…" autofocus><button>Search</button></form></header>
<main id="m"><p class="msg">Choose whether to search by character, comic or artist, type a name and press Search.</p></main>
<script>
const $=s=>document.querySelector(s),m=$('#m');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const base=u=>(u||'').split('/').pop();
async function api(p,q){const r=await fetch('/api/'+p+'?'+new URLSearchParams(q));const d=await r.json();
 if(d.status_code!==1)throw new Error(d.error||'Error '+d.status_code);return d}
let active=0;const Q=[];
function next(){while(active<3&&Q.length){active++;Q.shift()()}}
const enqueue=fn=>new Promise(res=>{Q.push(()=>fn().finally(()=>{active--;next();res()}));next()});

const PH={char:'Character: Batman, Spider-Man, Catwoman…',comic:'Comic: Absolute Batman, Detective Comics…',artist:'Artist: Peach Momoko, John Romita Jr.…'};
let mode='char',S=null;
document.querySelectorAll('.mode button').forEach(b=>b.onclick=()=>{mode=b.dataset.m;
 document.querySelectorAll('.mode button').forEach(x=>x.classList.toggle('on',x===b));
 $('#q').placeholder=PH[mode]});
$('#f').onsubmit=e=>{e.preventDefault();const q=$('#q').value.trim();if(!q)return;mode==='comic'?searchComics(q):searchChars(q,mode)};

async function searchChars(q,kind='char'){m.innerHTML='<p class="msg">Searching…</p>';
 try{const d=await api(kind==='char'?'characters':'people',{q});const r=d.results;
  if(!r.length){m.innerHTML='<p class="msg">No results for “'+esc(q)+'”.</p>';return}
  m.innerHTML='<p class="info">Choose the '+(kind==='char'?'character':'artist')+':</p><div class="grid chars">'+r.map((c,i)=>`<figure class="char" data-i="${i}">
   <img loading="lazy" src="${esc(c.image?.small_url)}"><div><b>${esc(c.name)}</b>
   <span>${kind==='char'?esc(c.real_name||'')+'<br>'+esc(c.publisher?.name||'')+' · '+(c.count_of_issue_appearances||0)+' appearances':esc(c.hometown||'')+'<br>'+esc((c.deck||'').slice(0,90))}</span></div></figure>`).join('')+'</div>';
  m.querySelectorAll('.char').forEach(el=>el.onclick=()=>openChar(r[el.dataset.i],()=>searchChars(q,kind),kind));
 }catch(e){m.innerHTML='<p class="msg err">'+esc(e.message)+'</p>'}}

async function openChar(c,back,kind='char'){window.scrollTo(0,0);m.innerHTML='<p class="msg">Finding series for '+esc(c.name)+'…</p>';
 try{const d=await api(kind==='char'?'charvols':'personvols',{id:c.id}).catch(e=>({results:{},err:e}));
  const byName=[];
  if(kind==='char'){const key=c.name.toLowerCase();
   for(let p=1;p<=10;p++){try{const r=await api('volsearch',{q:c.name,page:p});
    byName.push(...r.results.filter(v=>v.name.toLowerCase().includes(key)));if(r.results.length<100)break}catch(e){break}}}
  const have=new Set(byName.map(v=>v.id));
  const ids=(d.results.volume_credits||[]).map(v=>v.id).filter(i=>!have.has(i));
  if(!ids.length&&!byName.length){m.innerHTML='<p class="msg '+(d.err?'err':'')+'">'+esc(d.err?d.err.message:'No series found for this search.')+'</p>';return}
  const vols=[...byName];let done=0;
  const chunks=[];for(let i=0;i<ids.length;i+=100)chunks.push(ids.slice(i,i+100));
  await Promise.all(chunks.map(ch=>enqueue(async()=>{const r=await api('volumes',{ids:ch.join(',')});vols.push(...r.results);done+=ch.length;
   m.innerHTML=`<p class="msg">Loading series… ${done} of ${ids.length}</p>`})));
  showVolumes(c.name,vols,back);
 }catch(e){m.innerHTML='<p class="msg err">'+esc(e.message)+'</p>'}}

async function searchComics(q){m.innerHTML='<p class="msg">Searching…</p>';
 try{const d=await api('search',{q});if(!d.results.length){m.innerHTML='<p class="msg">No results for “'+esc(q)+'”.</p>';return}
  showVolumes('“'+q+'”',d.results,null)}catch(e){m.innerHTML='<p class="msg err">'+esc(e.message)+'</p>'}}

function groupVols(list){const g=new Map();
 list.filter(v=>v.count_of_issues>0).forEach(v=>{const k=v.name.trim().toLowerCase()+'|'+(v.start_year||''),pn=v.publisher?.name||'',x=g.get(k);
  if(!x)g.set(k,{...v,ids:[v.id],pubs:new Set([pn]),pubOf:{[v.id]:pn},top:v.count_of_issues});
  else{x.ids.push(v.id);x.pubs.add(pn);x.pubOf[v.id]=pn;x.count_of_issues+=v.count_of_issues;
   if(v.count_of_issues>x.top){x.top=v.count_of_issues;x.id=v.id;x.publisher=v.publisher;x.image=v.image}}});
 return [...g.values()].map(x=>({...x,multi:x.pubs.size>1}))}
const st=id=>S.st[id]??=({open:false,items:null,loading:false,err:'',busy:false});
function showVolumes(title,vols,back){
 S={title,vols:groupVols(vols),st:{},back,filter:'',sort:'new'};
 m.innerHTML=`<div class="tools">${back?'<button id="back">← Back</button>':''}<h2>${esc(title)}</h2><span class="info" id="cnt"></span><span class="sp"></span>
  <input id="flt" placeholder="Filter by title or publisher"><select id="srt"><option value="new">Newest</option><option value="num">Most issues</option><option value="az">A-Z</option></select>
  <button id="all">Open all</button></div><div id="list"></div>`;
 if(back)$('#back').onclick=back;
 $('#flt').oninput=e=>{S.filter=e.target.value.toLowerCase();renderList()};
 $('#srt').onchange=e=>{S.sort=e.target.value;renderList()};
 $('#all').onclick=toggleAll;renderList()}
const vis=()=>{const f=S.filter,a=S.vols.filter(v=>!f||(v.name+' '+(v.publisher?.name||'')).toLowerCase().includes(f));
 const k={new:(x,y)=>(y.start_year||0)-(x.start_year||0)||y.count_of_issues-x.count_of_issues,num:(x,y)=>y.count_of_issues-x.count_of_issues,az:(x,y)=>x.name.localeCompare(y.name)}[S.sort];
 return a.sort(k)};
function renderList(){const v=vis();$('#cnt').textContent=v.length+' series';
 $('#list').innerHTML=v.map(x=>`<details class="sec" data-id="${x.id}" ${st(x.id).open?'open':''}><summary>
  <img loading="lazy" src="${esc(x.image?.icon_url||x.image?.small_url)}"><div><b>${esc(x.name)}</b>
  <span>${esc(x.start_year||'?')} · ${esc(x.publisher?.name||'No publisher')} · ${x.count_of_issues} issues</span></div></summary>
  <div class="body">${st(x.id).open?body(x):''}</div></details>`).join('')||'<p class="msg">Nothing matches the filter.</p>'}
function toggleAll(){const v=vis(),opening=v.some(x=>!st(x.id).open);
 if(opening&&v.length>30&&!confirm(`That's ${v.length} series, and each uses at least one request. Comic Vine allows about 200 per hour. Open them all anyway?`))return;
 v.forEach(x=>st(x.id).open=opening);$('#all').textContent=opening?'Close all':'Open all';renderList()}
document.addEventListener('toggle',e=>{const el=e.target;if(!el.matches?.('details.sec'))return;
 const id=el.dataset.id,s=st(id);s.open=el.open;if(el.open){if(!s.items&&!s.loading)loadIssues(id);else refresh(id)}},true);
document.addEventListener('click',e=>{const b=e.target.closest('[data-act]');if(!b)return;
 if(b.dataset.act==='vars')loadVariants(b.dataset.id);
 if(b.dataset.act==='retry'){const s=st(b.dataset.id);s.items=null;s.err='';loadIssues(b.dataset.id)}});

const vol=id=>S.vols.find(v=>v.id==id);
function fig(v,it,img,isVar,n){const name=`${v.name}_${v.start_year||''}_${it.num}${isVar?'_var'+n:''}`;
 return `<figure class="${isVar?'var':''}"><img loading="lazy" src="${esc(img.medium_url||img.original_url)}">
 <figcaption><span>#${esc(it.num)}${it.pub?' · '+esc(it.pub):''}</span><a href="/api/img?u=${encodeURIComponent(img.original_url)}&n=${encodeURIComponent(name)}">Download</a></figcaption></figure>`}
function body(v){const s=st(v.id);
 if(!s.items)return s.err?`<p class="msg err">${esc(s.err)} <button data-act="retry" data-id="${v.id}">Retry</button></p>`:'<p class="msg">Loading covers…</p>';
 const nv=s.items.reduce((a,i)=>a+i.vars.length,0);
 return `<div class="bar"><span class="info">${s.items.length} covers${nv?' + '+nv+' variants':''}</span>
  <button data-act="vars" data-id="${v.id}" ${s.busy?'disabled':''}>${s.busy?'Finding variants…':'Load variants'}</button></div>
  ${s.err?`<p class="msg err">${esc(s.err)}</p>`:''}
  <div class="grid">${s.items.map(it=>fig(v,it,it.img,false)+it.vars.map((x,k)=>fig(v,it,x,true,k+1)).join('')).join('')}</div>`}
const pend={};
function refresh(id){if(pend[id])return;pend[id]=setTimeout(()=>{pend[id]=0;const el=document.querySelector(`details[data-id="${id}"] .body`);
 if(el&&st(id).open)el.innerHTML=body(vol(id))},250)}
function loadIssues(id){const s=st(id),g=vol(id);s.loading=true;refresh(id);
 return enqueue(async()=>{try{const items=[];
  for(const vid of g.ids){let off=0,total=1;
   while(off<total){const d=await api('issues',{volume:vid,offset:off});total=d.number_of_total_results;
    d.results.forEach(i=>{if(i.image?.original_url)items.push({id:i.id,num:i.issue_number,date:i.cover_date||'',pub:g.multi?g.pubOf[vid]:'',img:i.image,vars:[]})});off+=100}}
  if(g.ids.length>1)items.sort((a,b)=>(a.date>b.date)-(a.date<b.date)||parseFloat(a.num)-parseFloat(b.num));
  s.items=items;s.err=''}catch(e){s.err=e.message}s.loading=false;refresh(id)})}
async function loadVariants(id){const s=st(id);s.busy=true;s.err='';refresh(id);let stop='';
 await Promise.all(s.items.filter(i=>!i.done).map(it=>enqueue(async()=>{if(stop)return;
  try{const d=await api('variants',{issue:it.id}),k=base(it.img.original_url);
   it.vars=(d.results.associated_images||[]).filter(x=>x.original_url&&base(x.original_url)!==k)
    .map(x=>({original_url:x.original_url,medium_url:x.medium_url||x.original_url}));it.done=true;refresh(id)}
  catch(e){stop=e.message}})));
 s.busy=false;s.err=stop?stop+' Press “Load variants” again later to continue.':'';refresh(id)}
</script></html>"""

if __name__ == "__main__":
    KEY = get_key()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Running at http://127.0.0.1:{PORT}  (Ctrl+C to quit)")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

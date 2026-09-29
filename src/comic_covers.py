#!/usr/bin/env python3
"""Explorador de portadas de cómics (Comic Vine). Solo usa la librería estándar de Python."""
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
        k = input("Pega tu clave de Comic Vine (comicvine.gamespot.com/api): ").strip()
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
        msg = "Límite de peticiones alcanzado, espera un rato." if e.code == 420 else f"Error HTTP {e.code}"
        return {"status_code": e.code, "error": msg}
    except Exception as e:
        return {"status_code": 0, "error": f"No se pudo conectar: {e}"}
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
            name = re.sub(r"[^\w\-]+", "_", q.get("n", "portada")) + ext
            return self.send(data, ctype, {"Content-Disposition": f'attachment; filename="{name}"'})
        self.send_error(404)


PAGE = r"""<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Portadas</title>
<style>
:root{--board:#d6dce0;--ink:#101828;--tape:#f2b705;--paper:#fafaf7;--mute:#5b6675}
*{box-sizing:border-box}body{margin:0;background:var(--board);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--ink);color:#fff;padding:12px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{margin:0;font:800 28px "Arial Narrow","Helvetica Neue",sans-serif;font-stretch:condensed;letter-spacing:.5px}
form{flex:1;display:flex;gap:8px;min-width:240px}
input{flex:1;padding:10px 12px;border:0;border-radius:4px;font:inherit}
button,.btn{background:var(--tape);color:var(--ink);border:0;border-radius:4px;padding:9px 14px;font:600 14px system-ui;cursor:pointer;text-decoration:none}
button:disabled{opacity:.5;cursor:default}
main{padding:20px;max-width:1500px;margin:auto}
.msg{color:var(--mute);padding:40px 0;text-align:center}.err{color:#a4161a}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:18px}
.vols{grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
figure{margin:0;background:var(--paper);padding:8px;border-radius:3px;box-shadow:0 1px 0 rgba(0,0,0,.25);position:relative}
figure img{width:100%;aspect-ratio:2/3;object-fit:cover;display:block;background:#c3cad0}
figcaption{display:flex;justify-content:space-between;align-items:center;padding-top:6px;font-size:13px}
figcaption a{color:var(--ink);font-weight:600}
.var::before{content:"variante";position:absolute;top:14px;left:0;background:var(--tape);font:700 12px system-ui;padding:2px 8px}
.vol{display:flex;gap:12px;cursor:pointer;text-align:left}.vol img{width:70px;flex:none}
.vol b{display:block}.vol span{color:var(--mute);font-size:13px}
.bar{display:flex;gap:12px;align-items:center;margin-bottom:18px;flex-wrap:wrap}.bar h2{margin:0;font-size:22px}
.bar .info{color:var(--mute)}
</style>
<header><h1>PORTADAS</h1>
<form id="f"><input id="q" placeholder="Busca una serie o personaje: Batman, Absolute Batman, Spider-Man…" autofocus><button>Buscar</button></form></header>
<main id="m"><p class="msg">Escribe el nombre de una serie o personaje para ver sus portadas.</p></main>
<script>
const $=s=>document.querySelector(s),m=$('#m');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const base=u=>(u||'').split('/').pop();
async function api(p,q){const r=await fetch('/api/'+p+'?'+new URLSearchParams(q));const d=await r.json();
 if(d.status_code!==1)throw new Error(d.error||'Error '+d.status_code);return d}
$('#f').onsubmit=e=>{e.preventDefault();const q=$('#q').value.trim();if(q)search(q)};
let last='';
async function search(q){last=q;m.innerHTML='<p class="msg">Buscando…</p>';
 try{const d=await api('search',{q});
  const r=d.results.filter(v=>v.count_of_issues>0).sort((a,b)=>b.count_of_issues-a.count_of_issues);
  if(!r.length){m.innerHTML='<p class="msg">Sin resultados para «'+esc(q)+'».</p>';return}
  window.R=r;
  m.innerHTML='<div class="grid vols">'+r.map((v,i)=>`<figure class="vol" data-i="${i}">
   <img loading="lazy" src="${esc(v.image?.small_url)}"><div><b>${esc(v.name)}</b>
   <span>${esc(v.start_year||'?')} · ${esc(v.publisher?.name||'Sin editorial')}<br>${v.count_of_issues} números</span></div></figure>`).join('')+'</div>';
  m.querySelectorAll('.vol').forEach(el=>el.onclick=()=>openSeries(window.R[el.dataset.i]));
 }catch(e){m.innerHTML='<p class="msg err">'+esc(e.message)+'</p>'}}
let items=[],vol=null,busy=false;
async function openSeries(v){vol=v;items=[];window.scrollTo(0,0);draw('Cargando portadas…');
 try{let off=0,total=1;
  while(off<total){const d=await api('issues',{volume:v.id,offset:off});total=d.number_of_total_results;
   d.results.forEach(i=>{if(i.image?.original_url)items.push({id:i.id,num:i.issue_number,img:i.image,vars:[]})});
   off+=100;draw()}
  draw();
 }catch(e){draw(e.message,true)}}
function fig(it,img,isVar,n){const name=`${vol.name}_${it.num}${isVar?'_var'+n:''}`;
 return `<figure class="${isVar?'var':''}"><img loading="lazy" src="${esc(img.medium_url||img.original_url)}">
 <figcaption><span>#${esc(it.num)}</span><a href="/api/img?u=${encodeURIComponent(img.original_url)}&n=${encodeURIComponent(name)}">Descargar</a></figcaption></figure>`}
function draw(note,isErr){const nv=items.reduce((a,i)=>a+i.vars.length,0);
 m.innerHTML=`<div class="bar"><button id="back">← Resultados</button><h2>${esc(vol.name)} (${esc(vol.start_year||'?')})</h2>
  <span class="info">${items.length} portadas${nv?' + '+nv+' variantes':''}</span>
  <button id="vb" ${busy||!items.length?'disabled':''}>${busy?'Buscando variantes…':'Cargar variantes'}</button></div>
  ${note?`<p class="msg ${isErr?'err':''}">${esc(note)}</p>`:''}
  <div class="grid">${items.map(it=>fig(it,it.img,false)+it.vars.map((v,k)=>fig(it,v,true,k+1)).join('')).join('')}</div>`;
 $('#back').onclick=()=>last?search(last):location.reload();$('#vb').onclick=loadVariants}
async function loadVariants(){busy=true;draw();let idx=0,stop=null;
 const todo=items.filter(i=>!i.done);
 const worker=async()=>{while(idx<todo.length&&!stop){const it=todo[idx++];
  try{const d=await api('variants',{issue:it.id}),k=base(it.img.original_url);
   it.vars=(d.results.associated_images||[]).filter(x=>x.original_url&&base(x.original_url)!==k)
    .map(x=>({original_url:x.original_url,medium_url:x.medium_url||x.original_url}));it.done=true;draw()}
  catch(e){stop=e.message}}};
 await Promise.all([worker(),worker(),worker()]);busy=false;
 draw(stop?stop+' Vuelve a pulsar «Cargar variantes» más tarde para continuar.':'',!!stop)}
</script></html>"""

if __name__ == "__main__":
    KEY = get_key()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Abierto en http://127.0.0.1:{PORT}  (Ctrl+C para cerrar)")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

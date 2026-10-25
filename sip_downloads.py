"""Fixed SIP install routes and a bounded, cached public release feed."""
import json,threading,time,urllib.request
from pathlib import Path
_lock=threading.Lock();_cache=None;_until=0

def releases():
 global _cache,_until
 with _lock:
  if _cache is not None and time.monotonic()<_until:return _cache
  req=urllib.request.Request('https://api.github.com/repos/olamidebello/Sip/releases?per_page=10',headers={'Accept':'application/vnd.github+json','User-Agent':'AfricaAppsStore-SIP'})
  try:
   with urllib.request.urlopen(req,timeout=10) as response:raw=response.read(2000001)
   if len(raw)>2000000:raise ValueError('Release response too large')
   data=json.loads(raw)
   if not isinstance(data,list):raise ValueError('Invalid release list')
   result=[]
   for r in data[:10]:
    if r.get('draft'):continue
    assets=[]
    for a in r.get('assets',[])[:100]:
     url=a.get('browser_download_url','')
     if url.startswith('https://github.com/olamidebello/Sip/releases/download/'):
      assets.append({'name':a.get('name',''),'browser_download_url':url})
    result.append({'tag_name':r.get('tag_name',''),'draft':False,'assets':assets})
   _cache=result;_until=time.monotonic()+600;return result
  except Exception:
   if _cache is not None:return _cache
   raise

def serve_sip(handler,path):
 if handler.command not in ('GET','HEAD'):return False
 if path=='/api/sip-releases':
  try:handler.send(releases())
  except Exception:handler.send({'error':'Published download check unavailable'},503)
  return True
 files={'/install/sip':('index.html','text/html'),'/install/sip/':('index.html','text/html'),'/install/device-install.js':('device-install.js','text/javascript'),'/install/install.css':('install.css','text/css')}
 # /install/sip uses relative module URLs beneath /install/.
 files.update({'/install/sip/device-install.js':('device-install.js','text/javascript'),'/install/sip/install.css':('install.css','text/css')})
 if path not in files:return False
 name,kind=files[path];raw=(Path(__file__).parent/'static/sip'/name).read_bytes();handler.send_response(200);handler.headers_out(kind,len(raw));handler.end_headers()
 if handler.command!='HEAD':handler.wfile.write(raw)
 return True

def integrate_app(source):
 statement='from sip_downloads import serve_sip\n'
 if statement not in source:source=statement+source
 marker='        # SIP_DEVICE_INSTALL_V1'
 if marker not in source:
  anchor="        path=urlparse(self.path).path; query=parse_qs(urlparse(self.path).query)"
  if source.count(anchor)!=1:raise ValueError('Store router requires review')
  source=source.replace(anchor,anchor+'\n'+marker+'\n        if serve_sip(self,path):return')
 return source

def integrate_cards(source):
 source=source.replace("['media.africandroid.world','justisolve.com'].includes(a.domain)","['media.africandroid.world','justisolve.com','sip.dobhrap.com'].includes(a.domain)")
 marker="a.domain==='sip.dobhrap.com'?'<a class=\"button\" href=\"/install/sip\">Install / update for your device</a>':"
 if marker in source:return source
 anchor="a.domain==='media.africandroid.world'?'<a class=\"button\""
 if source.count(anchor)!=1:raise ValueError('Store listing renderer requires review')
 return source.replace(anchor,marker+anchor)

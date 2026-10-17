import unittest,tempfile,os,sys,threading,json,urllib.request,urllib.error,io,zipfile
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
tmp=tempfile.TemporaryDirectory();os.environ['STORE_DATA']=tmp.name
import app
class StoreTest(unittest.TestCase):
 def test_workflows(self):
  app.init();server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  def request(path,data=None,auth=None):
   headers={'Cookie':auth[0],'X-CSRF':auth[1]} if auth else {}
   if data is not None:
    headers['Content-Type']='application/octet-stream' if isinstance(data,bytes) else 'application/json';data=data if isinstance(data,bytes) else json.dumps(data).encode()
   try:
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/api'+path,data=data,headers=headers)) as r:return r.status,r.read(),r.headers
   except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
  try:
   status,_,h=request('/register',{'email':'owner@example.com','password':'long-test-password','name':'Owner'});self.assertEqual(status,200)
   cookie=h['Set-Cookie'].split(';')[0];s=json.loads(request('/me',auth=(cookie,''))[1]);auth=(cookie,s['csrf'])
   self.assertNotIn('token',s)
   self.assertNotIn('expires',s)
   self.assertEqual(request('/register',{'email':'blank@example.com','password':'long-test-password','name':'   '})[0],400)
   self.assertEqual(request('/register',[])[0],400)
   status,b,_=request('/apps',{'name':'Example','package':'org.example.app','kind':'Apps','category':'Tools','description':'Test','version':'1.0','privacy':'https://example.com/privacy'},auth);self.assertEqual(status,200);aid=json.loads(b)['id'];p=f'/apps/{aid}'
   self.assertEqual(request(p)[0],403)
   self.assertEqual(request(p+'/wishlist',{},(cookie,'wrong'))[0],403)
   self.assertEqual(request(p+'/moderate',{'status':'published'},auth)[0],403)
   buf=io.BytesIO()
   with zipfile.ZipFile(buf,'w') as z:z.writestr('AndroidManifest.xml','fixture')
   self.assertEqual(request(p+'/upload',b'PKbroken',auth)[0],400)
   self.assertEqual(request(p+'/upload',buf.getvalue(),auth)[0],200)
   self.assertEqual(request(p+'/submit',{},auth)[0],200)
   with app.db() as c:c.execute("UPDATE users SET role='admin' WHERE id=?",(s['user_id'],))
   self.assertEqual(request(p+'/moderate',{'status':'published'},auth)[0],200)
   self.assertNotIn('filename',json.loads(request(p,auth=auth)[1])['releases'][0])
   self.assertEqual(request(p+'/review',{'rating':5,'body':'Good'},auth)[0],403)
   self.assertEqual(request(p+'/download',auth=auth)[1],buf.getvalue())
   self.assertEqual(request(p+'/review',{'rating':5,'body':'Good'},auth)[0],200)
   self.assertEqual(request(p+'/review',{'rating':9,'body':'Bad'},auth)[0],409)
   self.assertEqual(request('/admin')[0],403)
   self.assertEqual(request('/settings',{'country':'Nigeria'},auth)[0],200)
   self.assertEqual(json.loads(request('/settings',auth=auth)[1])['country'],'Nigeria')
  finally:server.shutdown();server.server_close()
 def test_head(self):
  app.init();server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   base='http://127.0.0.1:'+str(server.server_port)
   for path in ('/','/static/app.js','/static/style.css'):
    with urllib.request.urlopen(base+path) as r: expected=len(r.read())
    with urllib.request.urlopen(urllib.request.Request(base+path,method='HEAD')) as r:
     self.assertEqual(r.status,200);self.assertEqual(int(r.headers['Content-Length']),expected);self.assertEqual(r.read(),b'')
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()

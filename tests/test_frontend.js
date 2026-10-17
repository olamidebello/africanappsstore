const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../static/app.js'),'utf8');
async function render(hash,user=null,preferences={}){
 const elements=new Map(),calls=[];
 const element=selector=>{
  if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',value:'',style:{},open:false,showModal(){this.open=true},close(){this.open=false},querySelector(){return {disabled:false}}});
  return elements.get(selector);
 };
 const context={document:{querySelector:element,querySelectorAll:()=>[],documentElement:{dataset:{}}},location:{hash,origin:'https://store.example'},window:{},navigator:{},URLSearchParams,AbortController,setTimeout,clearTimeout,fetch:async url=>{
  calls.push(url);
  let data=url==='/api/me'?user:url==='/api/settings'?preferences:url.startsWith('/api/apps?')?[]:{id:5,name:'Example',owner:1,package:'org.example.app',version:'1',age:3,status:'published',privacy:'https://example.com',releases:[],reviews:[]};
  return {ok:true,json:async()=>data};
 }};
 await vm.runInNewContext(source,context);
 return {elements,calls,context};
}
test('shared app links keep catalog context and open details after account load',async()=>{
 const {elements,calls}=await render('#app/5');
 assert.equal(elements.get('#title').textContent,'Apps');
 assert.ok(calls.indexOf('/api/me')<calls.indexOf('/api/apps/5'));
 assert.equal(elements.get('#modal').open,true);
 assert.match(elements.get('#detail').innerHTML,/Example/);
});
test('private views offer sign-in before querying protected APIs',async()=>{
 const {elements,calls}=await render('#Library');
 assert.match(elements.get('#content').innerHTML,/Sign in to access Library/);
 assert.equal(calls.some(x=>x.includes('mode=library')),false);
});
test('saved appearance and preference controls restore',async()=>{
 const {elements,context}=await render('#Settings',{user_id:1,name:'Owner',role:'user'},{theme:'Dark',personalization:'On',country:'Ghana'});
 assert.equal(context.document.documentElement.dataset.theme,'Dark');
 assert.equal(elements.get('#edit [name=theme]').value,'Dark');
 assert.equal(elements.get('#edit [name=personalization]').value,'On');
});

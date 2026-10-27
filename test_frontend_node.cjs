// Test de l'intégration JavaScript ↔ serveur API, sans navigateur graphique.
// Lancer avec `node test_frontend_node.cjs` après avoir démarré le serveur.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const script=fs.readFileSync(__dirname+'/shared.js','utf8');
let cookie='';
async function doFetch(path,options={}) {
  const headers={...(options.headers||{})};
  if(cookie)headers.Cookie=cookie;
  const result=await fetch('http://127.0.0.1:8896'+path,{...options,headers});
  const set=result.headers.get('set-cookie');
  if(set){const token=set.match(/dakhla_session=([^;]*)/);if(token)cookie=token[1]?`dakhla_session=${token[1]}`:'';}
  return result;
}
function page(name){
  const els={},navigations=[];
  const document={body:{dataset:{page:name}},getElementById(id){return els[id]??(els[id]={innerHTML:'',textContent:'',hidden:false,value:'',scrollIntoView(){},focus(){}})}};
  class FormDataFake{constructor(t){this.fields=t.fields;}get(k){return Object.hasOwn(this.fields,k)?this.fields[k]:null;}}
  const ctx={console,document,fetch:doFetch,FormData:FormDataFake,window:{location:{assign(x){navigations.push(x)},replace(x){navigations.push(x)}},scrollTo(){}},confirm:()=>true,alert(){}};
  vm.createContext(ctx);vm.runInContext(script,ctx);return {ctx,els,navigations};
}
const wait=()=>new Promise(resolve=>setTimeout(resolve,180));
(async()=>{
 const loginPage=page('login');await wait();
 assert(loginPage.els['auth-panel'].innerHTML.includes('Se connecter'));
 await loginPage.ctx.submitAuth({preventDefault(){},target:{fields:{email:'client@demo.test',password:'Demo2026!'}}});
 assert(loginPage.navigations.includes('/application.html'));
 const cl=page('app');await wait();
 assert(cl.els.workspace.innerHTML.includes('Publier une demande de service'));
 const code='V6-'+Date.now();
 await cl.ctx.createRequest({preventDefault(){},target:{fields:{service:'Plomberie',zone:code,budget:'240',when:'Cette semaine',details:'Test de synchronisation base de données depuis JavaScript.'}}});
 assert(cl.els.workspace.innerHTML.includes(code));
 await cl.ctx.logoutDemo();assert(cl.navigations.includes('/index.html'));
 const login2=page('login');await wait();
 await login2.ctx.submitAuth({preventDefault(){},target:{fields:{email:'pro@demo.test',password:'Demo2026!'}}});
 const pro=page('app');await wait();
 assert(pro.els.workspace.innerHTML.includes(code));
 const req=vm.runInContext('data',pro.ctx).requests.find(r=>r.zone===code);
 await pro.ctx.makeOffer(req.id,240,true);
 assert(vm.runInContext('data',pro.ctx).offers.some(o=>o.requestId===req.id&&o.price===240));
 await pro.ctx.logoutDemo();
 const login3=page('login');await wait();
 await login3.ctx.submitAuth({preventDefault(){},target:{fields:{email:'client@demo.test',password:'Demo2026!'}}});
 const cl2=page('app');await wait();
 const offer=vm.runInContext('data',cl2.ctx).offers.find(o=>o.requestId===req.id&&o.price===240);
 assert(offer);
 await cl2.ctx.selectOffer(req.id,offer.id);
 assert(vm.runInContext('data',cl2.ctx).requests.find(r=>r.id===req.id).status==='accepted');
 console.log('PASS: Frontend JavaScript → API → SQLite ; client / prestataire / contre-offre / sélection.');
 await cl2.ctx.logoutDemo();
})().catch(e=>{console.error(e);process.exit(1)});

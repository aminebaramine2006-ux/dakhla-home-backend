'use strict';
const CATEGORIES=['Plomberie','Électricité','Ménage','Climatisation','Peinture','Menuiserie','Électroménager','Déménagement','Jardinage','Serrurerie'];
const DEMO_PASS='Demo2026!';
const el=id=>document.getElementById(id);
const escapeHtml=(value)=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=x=>`${Number(x).toLocaleString('fr-FR')} DH`;
let data={requests:[],offers:[]}, PROS=[], currentAccount=null;
let role='client', activePro=null, highlightRequest=null,notification='';
let csrfToken='', authMode='login', selectedType='client',authFeedback='';
function icon(s){return ({'Plomberie':'🔧','Électricité':'⚡','Ménage':'🧹','Climatisation':'❄️','Peinture':'🎨','Menuiserie':'🪚','Électroménager':'🛠️','Déménagement':'📦','Jardinage':'🌿','Serrurerie':'🔑'})[s]||'🛠️';}
function proProfiles(){return PROS;}
async function api(url, method='GET',body){
 const opts={method,credentials:'same-origin',headers:{'Accept':'application/json'}};
 if(method!=='GET'){opts.headers['Content-Type']='application/json';opts.headers['X-CSRF-Token']=csrfToken;opts.body=JSON.stringify(body||{});}
 let res;
 try{res=await fetch(url,opts);}catch(_){throw new Error('Connexion à l’API impossible. Vérifiez que le serveur Python est en ligne et que Netlify est relié à ce serveur.');}
 const contentType=res.headers.get('content-type')||'';
 let payload={};
 if(contentType.includes('application/json'))payload=await res.json().catch(()=>({}));
 if(!res.ok){
   if(res.status===401&&document.body.dataset.page==='app')window.location.assign('/index.html');
   if(typeof payload.detail==='string')throw new Error(payload.detail);
   if(res.status===404)throw new Error('API introuvable (HTTP 404). Vérifiez le fichier _redirects sur Netlify et l’adresse de votre serveur Render.');
   if(res.status>=500)throw new Error(`Serveur API indisponible (HTTP ${res.status}). Vérifiez Render puis actualisez la page.`);
   throw new Error(`Échec de la requête API (HTTP ${res.status}).`);
 }
 if(!contentType.includes('application/json'))throw new Error('Réponse API incorrecte : le serveur renvoie une page HTML au lieu de JSON. Vérifiez la règle /api/* dans _redirects.');
 return payload;
}
async function loadData(){const result=await api('/api/state');data={requests:result.requests,offers:result.offers};PROS=result.pros;}
function authError(msg){authFeedback=`<div class="notice err auth-alert" role="alert">${escapeHtml(msg)}</div>`;renderAuth();}
function chooseType(kind){selectedType=kind;authFeedback='';renderAuth();}
function showAuth(mode='login'){authMode=mode;authFeedback='';renderAuth();window.scrollTo({top:0,behavior:'smooth'});}
function demoFill(email){authMode='login';authFeedback='';renderAuth();el('auth-email').value=email;el('auth-password').value=DEMO_PASS;el('auth-password').focus();}
function renderAuth(){
 const registration=authMode==='register', panel=el('auth-panel');
 panel.innerHTML=`<div class="auth-topline">🏠 Dakhla Home Services</div><h2>${registration?'Créer votre compte':'Bon retour parmi nous'}</h2><p class="auth-sub">${registration?'Choisissez votre profil pour commencer.':'Connectez-vous pour accéder à votre espace.'}</p>
 <div class="auth-switch"><button type="button" class="${!registration?'selected':''}" onclick="showAuth('login')">Se connecter</button><button type="button" class="${registration?'selected':''}" onclick="showAuth('register')">Créer un compte</button></div>
 ${authFeedback}
 <form id="auth-form" onsubmit="submitAuth(event)">
 ${registration?`<label class="auth-field" style="display:block">Je souhaite m'inscrire comme</label><div class="account-types"><button type="button" class="account-choice ${selectedType==='client'?'selected':''}" onclick="chooseType('client')"><span>🏡</span>Client<small>Demander des prestations et comparer les offres.</small></button><button type="button" class="account-choice ${selectedType==='pro'?'selected':''}" onclick="chooseType('pro')"><span>🛠️</span>Prestataire<small>Recevoir des demandes et proposer mes tarifs.</small></button></div><div class="auth-field"><label>Nom complet<input name="name" minlength="2" maxlength="70" autocomplete="name" required placeholder="Votre nom"></label></div>`:''}
 <div class="auth-field"><label>Adresse e-mail<input id="auth-email" name="email" type="email" required autocomplete="email" maxlength="120" placeholder="exemple@email.com"></label></div>
 <div class="auth-field"><label>Mot de passe<input id="auth-password" name="password" type="password" required minlength="${registration?10:1}" autocomplete="${registration?'new-password':'current-password'}" placeholder="${registration?'10 caractères minimum':'Votre mot de passe'}"></label></div>
 ${registration?`<div class="auth-field"><label>Confirmer le mot de passe<input name="confirm" type="password" minlength="10" autocomplete="new-password" required placeholder="Retapez votre mot de passe"></label></div>${selectedType==='pro'?`<div class="auth-field"><label>Votre spécialité<select name="service" required>${CATEGORIES.map(c=>`<option value="${escapeHtml(c)}">${icon(c)} ${escapeHtml(c)}</option>`).join('')}</select></label></div>`:''}<div class="auth-field"><label style="display:flex;align-items:flex-start;gap:7px;font-weight:500"><input type="checkbox" name="accept" required style="width:auto;margin:3px 0 0"> J’accepte de participer aux essais de cette plateforme pédagogique et de ne pas publier d’informations sensibles.</label></div>`:''}
 <button type="submit" class="auth-submit">${registration?`Créer mon compte ${selectedType==='pro'?'prestataire':'client'}`:'Se connecter'} →</button></form>
 ${!registration?`<div class="demo-access"><strong>🔑 Comptes d’essai (fictifs)</strong><div class="demo-links"><button type="button" onclick="demoFill('client@demo.test')">🏡 Client démo</button><button type="button" onclick="demoFill('pro@demo.test')">🛠️ Prestataire démo</button><button type="button" onclick="demoFill('admin@demo.test')">📊 Admin démo</button></div><div style="margin-top:8px">Mot de passe : <code>Demo2026!</code></div></div>`:''}
 <div class="auth-bottom"><b>ℹ Prototype académique uniquement.</b> Les comptes de démonstration sont enregistrés sur le serveur Python. Sur un hébergement gratuit sans stockage permanent, les données peuvent être réinitialisées. Ce prototype n’est pas un service public et ne doit pas recueillir d’informations sensibles.</div>`;
}
async function submitAuth(event){
 event.preventDefault();
 const f=new FormData(event.target),email=String(f.get('email')||'').trim().toLowerCase(),password=String(f.get('password')||'');
 try{
  if(authMode==='login'){
    const res=await api('/api/login','POST',{email,password});csrfToken=res.csrf;startAccount(res.account);return;
  }
  const name=String(f.get('name')||'').trim();
  if(password!==String(f.get('confirm')||''))throw new Error('Les mots de passe ne correspondent pas.');
  if(!f.get('accept'))throw new Error('Veuillez accepter les conditions des essais.');
  const service=selectedType==='pro'?String(f.get('service')||''):null;
  const res=await api('/api/register','POST',{name,email,password,role:selectedType,service});
  csrfToken=res.csrf;startAccount(res.account);
 }catch(e){authError(e.message);}
}
async function startAccount(account){
 currentAccount=account;role=account.role;activePro=account.role==='pro'?account.proId:activePro;
 if(document.body.dataset.page==='login'){window.location.assign('/application.html');return;}
 el('site-page').hidden=false;
 el('account-bar').hidden=false;el('top-welcome').hidden=true;
 el('account-label').textContent=account.name+' · '+({client:'Client',pro:'Prestataire',admin:'Administrateur'}[account.role]);
 const heroAction=el('hero-action');
 if(heroAction)heroAction.textContent=account.role==='client'?'Créer une demande →':account.role==='pro'?'Consulter les demandes →':'Voir les statistiques →';
 try{await loadData();alertMessage(`Bienvenue ${account.name}. Les modifications sont enregistrées sur le serveur.`);render();}
 catch(e){el('workspace').innerHTML=`<div class="notice err">${escapeHtml(e.message)}</div>`;}
}
async function logoutDemo(){
 try{await api('/api/logout','POST');}catch(e){alert(e.message);return;}
 currentAccount=null;window.location.assign('/index.html');
}
async function bootAuth(){
 try{
  const result=await api('/api/session');csrfToken=result.csrf;
  if(document.body.dataset.page==='login'){
    if(result.account)window.location.replace('/application.html');else renderAuth();
  }else if(result.account){await startAccount(result.account);}
  else window.location.replace('/index.html');
 }catch(e){if(document.body.dataset.page==='login'){authError(e.message);}else{el('workspace').innerHTML=`<div class="notice err">${escapeHtml(e.message)}</div>`;}}
}
const labelStatus={open:'En attente d’offres',accepted:'Professionnel choisi',done:'Intervention terminée',cancelled:'Annulée'};
function scrollToDemo(){el('demo')?.scrollIntoView({behavior:'smooth',block:'start'});}
async function resetDemo(){
 if(currentAccount?.role!=='admin'||!confirm('Réinitialiser toutes les demandes de la base de démonstration ?'))return;
 try{await api('/api/admin/reset','POST');await loadData();alertMessage('Les demandes fictives ont été réinitialisées.');render();}catch(e){alertMessage(e.message,'error');render();}
}
function switchRole(next){if(!currentAccount||next!==currentAccount.role)return;role=next;render();}
function alertMessage(msg,kind='ok'){notification=`<div class="notice ${kind==='error'?'err':''}" role="status">${escapeHtml(msg)}</div>`;}
function statusHTML(r){return `<span class="status ${r.status}">${escapeHtml(labelStatus[r.status]||r.status)}</span>`;}
function tabs(){const labels={client:'🏠 Espace client',pro:'🛠️ Espace prestataire',admin:'📊 Tableau de bord'};el('role-tabs').innerHTML=`<div class="role-identity"><span style="font-size:24px">${role==='pro'?'🛠️':role==='admin'?'📊':'🏡'}</span><div><strong>${escapeHtml(currentAccount?.name||'')}</strong><div class="muted">${labels[role]||''}</div></div></div>${role!=='admin'?`<button type="button" class="btn secondary" style="width:100%;margin-bottom:8px" onclick="${chatMode?'closeMessages()':'openMessages()'}">${chatMode?'← Mon espace':'💬 Ma messagerie'}<span id="chat-badge"></span></button>`:''}<button type="button" class="btn secondary" style="width:100%" onclick="logoutDemo()">Se déconnecter</button>`;}
function offerCards(r){const offers=data.offers.filter(o=>o.requestId===r.id);if(!offers.length)return `<div class="empty">Aucune offre pour le moment. Un professionnel peut proposer un tarif depuis son propre compte.</div>`;return `<div style="display:grid;gap:3px">${offers.map(o=>{const p=proProfiles().find(p=>p.id===o.proId)||{name:"Prestataire démo",id:o.proId};const selected=r.selectedOffer===o.id;return `<div class="offer"><div style="display:flex;align-items:center;gap:10px;min-width:0"><div class="avatar">${escapeHtml(p.name.slice(-1))}</div><div><b>${escapeHtml(p.name)}</b> <span class="tag">Prestataire</span><div class="offer-meta">🕒 ${escapeHtml(o.eta)} · ${escapeHtml(o.message)}</div></div></div><div style="text-align:right"><div class="offer-price">${money(o.price)}</div><button class="btn small outline" onclick="openMessages(${r.id},'${o.proId}')">💬 Discuter</button>${r.status==='open'?`<button class="btn small" onclick="selectOffer(${r.id},${o.id})">Choisir</button>`:selected?'<span class="pill">✓ Sélectionné</span>':''}</div></div>`;}).join('')}</div>`;}
function client(){const myRequests=data.requests.filter(r=>r.clientId===currentAccount?.id);return `<div class="panel"><h3>Publier une demande de service</h3><p class="sub">Expliquez votre besoin et indiquez le budget que vous souhaitez proposer.</p><form id="request-form" onsubmit="createRequest(event)"><div class="form-grid"><label>Type de service<select name="service" required>${CATEGORIES.map(c=>`<option value="${escapeHtml(c)}">${icon(c)} ${escapeHtml(c)}</option>`).join('')}</select></label><label>Zone à Dakhla<input name="zone" maxlength="80" placeholder="Ex. Centre-ville" required></label><label>Votre budget proposé (DH)<input name="budget" type="number" min="20" max="100000" step="1" placeholder="Ex. 150" required></label><label>Quand souhaitez-vous l'intervention ?<select name="when" required><option>Aujourd'hui</option><option>Demain matin</option><option>Demain après-midi</option><option>Cette semaine</option><option>À convenir</option></select></label><label class="full">Décrivez les travaux à réaliser<textarea name="details" maxlength="400" required placeholder="Ex. Réparation d'une fuite sous l'évier..." minlength="10"></textarea></label><label class="full" style="display:flex;align-items:center;gap:8px"><input type="checkbox" name="urgent" style="width:auto;margin:0"> Demande urgente (sous réserve de disponibilité)</label></div><div class="buttons" style="margin-top:17px"><button class="btn" type="submit">Publier la demande →</button><span class="muted">Aucun paiement n'est effectué.</span></div></form></div><div class="section-head"><div><h2>Mes demandes <span class="tag">${myRequests.length}</span></h2><p>Consultez les offres, comparez les prix et choisissez un professionnel.</p></div></div><div style="display:grid;gap:14px">${myRequests.slice().reverse().map(r=>`<article class="panel" id="request-${r.id}" style="margin:0;${highlightRequest===r.id?'border-color:#22bfa0':''}"><div class="request-top"><div><div class="muted">Demande #${r.id} · ${escapeHtml(r.zone)} ${r.urgent?'· 🚨 Urgent':''}</div><h3>${icon(r.service)} ${escapeHtml(r.service)}</h3></div>${statusHTML(r)}</div><p class="sub" style="margin:9px 0">${escapeHtml(r.details)}</p><div class="buttons" style="justify-content:space-between"><b>Budget proposé : ${money(r.budget)}</b><span class="tag">🗓 ${escapeHtml(r.when)}</span></div><hr class="thin"><h4 style="margin:0 0 10px">${r.status==='open'?'Propositions reçues':r.status==='accepted'?'Offre retenue':'Historique des offres'} (${data.offers.filter(o=>o.requestId===r.id).length})</h4>${offerCards(r)}${r.status==='accepted'?`<div class="buttons" style="margin-top:15px"><button class="btn" onclick="markDone(${r.id})">Confirmer l'intervention terminée</button><span class="muted">Après réalisation réelle uniquement ; ici, démonstration.</span></div>`:''}${r.status==='done'?(r.rating?`<div class="notice">⭐ Évaluation enregistrée : ${r.rating}/5 (démonstration).</div>`:`<div class="selector"><b>Évaluez le service (démonstration)</b><div class="buttons" style="margin-top:9px">${[1,2,3,4,5].map(n=>`<button class="btn small secondary" onclick="rateRequest(${r.id},${n})">${n} ★</button>`).join('')}</div></div>`):''}</article>`).join('')}</div>`;}
function pro(){const selected=proProfiles().find(p=>p.id===activePro);const requests=data.requests.filter(r=>r.status==='open'&&selected.services.includes(r.service));const myOffers=data.offers.filter(o=>o.proId===activePro);return `<div class="panel"><h3>Espace professionnel</h3><p class="sub">Consultez les demandes compatibles avec votre spécialité, acceptez le budget ou proposez un autre tarif.</p><div class="notice info">Compte : <b>${escapeHtml(currentAccount.name)}</b> · Spécialité(s) : ${selected.services.map(escapeHtml).join(", ")}. Prototype avec données de démonstration et comptes de test.</div></div><div class="section-head"><div><h2>Demandes disponibles</h2><p>Vous êtes libre de répondre ou d'ignorer une demande.</p></div><span class="pill">${requests.length} compatibles</span></div><div class="request-grid">${requests.length?requests.slice().reverse().map(r=>{const old=myOffers.find(o=>o.requestId===r.id);return `<article class="request"><div class="request-top"><span class="pill">${icon(r.service)} ${escapeHtml(r.service)}</span>${r.urgent?'<span class="status accepted">🚨 Urgent</span>':''}</div><h4>${escapeHtml(r.details)}</h4><p>📍 ${escapeHtml(r.zone)} · 🗓 ${escapeHtml(r.when)}</p><div class="muted">Budget proposé par le client</div><div class="money">${money(r.budget)}</div>${old?`<div class="notice">Vous avez déjà proposé <b>${money(old.price)}</b> pour cette demande.</div>`:`<div class="buttons" style="margin-top:14px"><button class="btn small" onclick="makeOffer(${r.id},${r.budget},true)">Accepter ${money(r.budget)}</button><button class="btn small outline" onclick="offerForm(${r.id})">Faire une contre-offre</button></div><div id="offerform-${r.id}" style="display:none;margin-top:13px"><label>Votre tarif proposé (DH)<input type="number" id="price-${r.id}" min="20" max="100000" value="${r.budget}"></label><label>Disponibilité<select id="eta-${r.id}"><option>Aujourd'hui</option><option>Demain matin</option><option>Demain après-midi</option><option>Cette semaine</option><option>À convenir</option></select></label><label>Précision éventuelle<input id="message-${r.id}" maxlength="130" placeholder="Ex. Déplacement inclus"></label><button style="margin-top:10px" class="btn" onclick="makeOffer(${r.id},null,false)">Envoyer ma proposition</button></div>`}</article>`;}).join(''):'<div class="empty" style="grid-column:1/-1">Aucune demande ouverte pour les spécialités de ce profil. Un compte client doit publier une demande.</div>'}</div><div class="panel" style="margin-top:16px"><h3>Mes offres envoyées</h3><p class="sub">Les offres de votre propre compte professionnel uniquement.</p>${myOffers.length?myOffers.slice().reverse().map(o=>{const r=data.requests.find(r=>r.id===o.requestId);return `<div class="offer"><div><b>Demande #${o.requestId} · ${escapeHtml(r?.service||'')}</b><div class="offer-meta">${escapeHtml(r?.zone||'')} · ${escapeHtml(r?.selectedOffer===o.id?'Offre retenue':r?.status==='open'?'En attente de décision':'Non retenue ou terminée')}</div></div><div class="pro-offer-actions"><b class="offer-price">${money(o.price)}</b><button class="btn small outline" onclick="openMessages(${o.requestId},'${o.proId}')">💬 Contacter le client</button></div></div>`;}).join(''):'<div class="empty">Aucune proposition envoyée.</div>'}</div>`;}

function admin(){const total=data.requests.length,offers=data.offers.length,chosen=data.requests.filter(r=>r.selectedOffer).length,done=data.requests.filter(r=>r.status==='done').length,ratings=data.requests.filter(r=>r.rating).map(r=>r.rating),satisfaction=ratings.length?(ratings.reduce((a,b)=>a+b,0)/ratings.length).toFixed(1):'—';return `<div class="panel"><h3>Tableau de bord — démonstration</h3><p class="sub">Indicateurs calculés à partir des demandes présentes dans la base SQLite. Ils ne constituent PAS des résultats de test réels.</p><div class="metricgrid"><div class="kpi"><b>${total}</b><span>Demandes simulées</span></div><div class="kpi"><b>${offers}</b><span>Propositions envoyées</span></div><div class="kpi"><b>${chosen}</b><span>Professionnels choisis</span></div><div class="kpi"><b>${done}</b><span>Interventions simulées terminées</span></div><div class="kpi"><b>${satisfaction}${ratings.length?' / 5':''}</b><span>Note moyenne (${ratings.length} avis)</span></div><div class="kpi"><b>${total?(100*chosen/total).toFixed(0):0}%</b><span>Taux de sélection</span></div></div><hr class="thin"><h3>Suivi du parcours</h3><p class="sub">Demandes ayant reçu au moins une proposition</p><div class="progress"><span style="width:${total?Math.round(data.requests.filter(r=>data.offers.some(o=>o.requestId===r.id)).length/total*100):0}%"></span></div><p class="muted" style="margin-top:9px">${data.requests.filter(r=>data.offers.some(o=>o.requestId===r.id)).length} / ${total} demandes</p><div class="notice info">Pour respecter les consignes du professeur, l'équipe devra encore recruter 20 testeurs extérieurs, faire tester pendant au moins deux semaines et consigner les mesures dans le tableau de suivi. Les données initiales de cet écran sont fictives ; les véritables tests doivent être documentés séparément.</div></div><div class="panel"><h3>Vue des demandes</h3>${data.requests.slice().reverse().map(r=>`<div class="offer"><div><b>#${r.id} · ${escapeHtml(r.service)}</b><div class="offer-meta">${escapeHtml(r.zone)} · ${data.offers.filter(o=>o.requestId===r.id).length} propositions</div></div>${statusHTML(r)}</div>`).join('')}</div>`;}
function render(){if(!currentAccount)return;role=currentAccount.role;tabs();const node=el('workspace');node.innerHTML=(notification||'')+(chatMode?renderInbox():role==='client'?client():role==='pro'?pro():admin());notification='';}
async function createRequest(event){
 event.preventDefault();if(currentAccount?.role!=='client')return;
 const f=new FormData(event.target);
 const values={service:String(f.get('service')||''),zone:String(f.get('zone')||'').trim(),budget:Number(f.get('budget')),
  details:String(f.get('details')||'').trim(),when:String(f.get('when')||''),urgent:f.get('urgent')!==null};
 try{
  const r=await api('/api/requests','POST',values);highlightRequest=r.id;await loadData();
  alertMessage(`Demande #${r.id} enregistrée dans la base. Un prestataire peut maintenant proposer un prix.`);render();
  el(`request-${r.id}`)?.scrollIntoView({behavior:'smooth',block:'center'});
 }catch(e){alertMessage(e.message,'error');render();}
}
async function selectOffer(requestId,offerId){
 if(currentAccount?.role!=='client')return;
 try{await api(`/api/requests/${requestId}/select`,'POST',{offerId});await loadData();highlightRequest=requestId;alertMessage('Proposition choisie et enregistrée dans la base de données.');render();}
 catch(e){alertMessage(e.message,'error');render();}
}
async function markDone(id){
 if(currentAccount?.role!=='client')return;
 try{await api(`/api/requests/${id}/done`,'POST');await loadData();highlightRequest=id;alertMessage('Intervention marquée comme terminée (démonstration).');render();}
 catch(e){alertMessage(e.message,'error');render();}
}
async function rateRequest(id,n){
 if(currentAccount?.role!=='client')return;
 try{await api(`/api/requests/${id}/rate`,'POST',{rating:n});await loadData();alertMessage('Votre évaluation est enregistrée.');render();}
 catch(e){alertMessage(e.message,'error');render();}
}
function offerForm(id){el(`offerform-${id}`).style.display='block';el(`price-${id}`).focus();}
async function makeOffer(requestId,price,accept){
 if(currentAccount?.role!=='pro')return;
 const found=data.requests.find(r=>r.id===requestId);if(!found)return;
 const amount=accept?found.budget:Number(el(`price-${requestId}`)?.value);
 const eta=accept?'À convenir':String(el(`eta-${requestId}`)?.value||'À convenir');
 const message=accept?'Budget accepté (démonstration)':String(el(`message-${requestId}`)?.value||'').trim();
 try{await api('/api/offers','POST',{requestId,price:amount,eta,message});await loadData();alertMessage(`Offre à ${money(amount)} enregistrée pour la demande #${requestId}.`);render();}
 catch(e){alertMessage(e.message,'error');render();}
}

// ——— Messagerie privée entre un client et un professionnel ayant proposé un prix ———
let chatMode=false;
let conversations=[],currentThread=null,threadMessages=[];
let chatNotice='', chatPolling=false;
const chatKey=(rid,pid)=>`${rid}:${pid}`;
const currentConversation=()=>conversations.find(c=>currentThread&&c.requestId===currentThread.requestId&&c.proId===currentThread.proId);
const routeChat=c=>`/api/conversations/${c.requestId}/${encodeURIComponent(c.proId)}`;
const chatTime=s=>s?String(s).slice(11,16):'';

async function openMessages(rid=null,pid=null){
 if(!currentAccount||currentAccount.role==='admin')return;
 chatMode=true; chatNotice='';
 try{
  conversations=(await api('/api/conversations')).conversations;
  let selected=rid!==null?conversations.find(c=>c.requestId===rid&&c.proId===pid):null;
  selected=selected||currentConversation()||conversations[0]||null;
  currentThread=selected?{requestId:selected.requestId,proId:selected.proId}:null;
  threadMessages=[];
  if(currentThread)await fetchThread(true);
  render();scrollToDemo();scrollChatToBottom();
 }catch(e){chatNotice=e.message;render();}
}
function closeMessages(){chatMode=false;chatNotice='';render();scrollToDemo();}
async function chooseConversation(rid,pid){
 if(!conversations.some(c=>c.requestId===rid&&c.proId===pid))return;
 currentThread={requestId:rid,proId:pid};chatNotice='';
 try{await fetchThread(true);render();scrollChatToBottom();}
 catch(e){chatNotice=e.message;render();}
}
async function fetchThread(markRead=false){
 const c=currentConversation();
 if(!c){threadMessages=[];return;}
 const result=await api(`${routeChat(c)}/messages`);
 threadMessages=result.messages;
 if(markRead&&threadMessages.some(m=>!m.mine&&!m.read)){
  await api(`${routeChat(c)}/read`,'POST');
  conversations=(await api('/api/conversations')).conversations;
 }
}
function refreshListHtml(){
 if(!conversations.length)return `<div class="chat-no-convos"><span>📭</span><strong>Aucune discussion</strong><p>La messagerie devient disponible après une première proposition de prix d'un prestataire.</p></div>`;
 return conversations.map(c=>`<button type="button" class="chat-contact ${currentThread&&chatKey(c.requestId,c.proId)===chatKey(currentThread.requestId,currentThread.proId)?'on':''}" onclick="chooseConversation(${c.requestId},'${c.proId}')">
   <span class="chat-avatar">${escapeHtml(c.correspondent.slice(0,1).toUpperCase())}</span>
   <span class="chat-contact-detail"><strong>${escapeHtml(c.correspondent)}</strong><small>${icon(c.service)} ${escapeHtml(c.service)} · #${c.requestId} · ${money(c.price)}</small><span>${escapeHtml(c.lastMessage||'Démarrer la discussion')}</span></span>
   ${c.unread?`<span class="chat-unread">${Math.min(c.unread,99)}</span>`:''}
  </button>`).join('');
}
function messagesHtml(){
 if(!threadMessages.length)return '<div class="chat-empty-thread"><span>👋</span><strong>Commencez la conversation</strong><p>Échangez sur les détails de la prestation, le prix et les disponibilités.</p></div>';
 return threadMessages.map(m=>`<div class="chat-line ${m.mine?'mine':'theirs'}"><div class="chat-bubble">${escapeHtml(m.body).replace(/\n/g,'<br>')}<span class="chat-meta">${chatTime(m.createdAt)} ${m.mine?(m.read?' · ✓✓ Lu':' · ✓ Envoyé'):''}</span></div></div>`).join('');
}
function renderInbox(){
 const c=currentConversation();
 return `<div class="chat-page">
   <div class="chat-title-row"><div><div class="chat-overline">MESSAGERIE INTÉGRÉE</div><h2>💬 Mes conversations</h2><p>Discutez du devis et de l'intervention sans quitter Dakhla Home Services.</p></div><button class="btn outline" onclick="closeMessages()">← Retour à mon espace</button></div>
   ${chatNotice?`<div class="notice err">${escapeHtml(chatNotice)}</div>`:''}
   <div class="chat-layout">
    <aside class="chat-sidebar"><div class="chat-sidebar-head"><strong>Discussions <span class="tag">${conversations.length}</span></strong><button class="chat-refresh" title="Actualiser" onclick="refreshMessages()">↻</button></div><div id="chat-contact-list">${refreshListHtml()}</div></aside>
    <section class="chat-thread">
      ${c?`<div class="chat-thread-head"><span class="chat-avatar large">${escapeHtml(c.correspondent.slice(0,1).toUpperCase())}</span><div><strong>${escapeHtml(c.correspondent)}</strong><small>${icon(c.service)} ${escapeHtml(c.service)} · Demande #${c.requestId} · Offre ${money(c.price)}</small></div><span class="chat-trust">🔒 Discussion privée</span></div>
       <div id="chat-scroll" class="chat-scroll" role="log" aria-live="polite" aria-label="Messages">${messagesHtml()}</div>
       ${c.canSend?`<form id="chat-form" class="chat-composer" onsubmit="sendChatMessage(event)"><label for="chat-input" class="sr-only">Votre message</label><textarea id="chat-input" name="body" maxlength="1000" rows="2" required placeholder="Écrivez votre message..." onkeydown="chatKeyDown(event)"></textarea><button class="btn chat-send" type="submit">Envoyer ➤</button></form>`:`<div class="chat-closed">🔒 Cette discussion est clôturée. Vous pouvez toujours consulter les messages précédents.</div>`}
       <p class="chat-hint">Ne partagez pas de mots de passe ni de données bancaires. Actualisation automatique toutes les 12 secondes.</p>`
       :`<div class="chat-thread-placeholder"><span>💬</span><h3>Vos messages en un seul endroit</h3><p>Lorsqu'un professionnel propose un prix, une conversation privée devient accessible ici.</p></div>`}
    </section>
   </div></div>`;
}
async function sendChatMessage(event){
 event.preventDefault();const c=currentConversation();if(!c||!c.canSend)return;
 const textArea=el('chat-input'),body=textArea.value.trim();if(!body)return;
 const btn=event.target.querySelector('button[type=submit]');if(btn)btn.disabled=true;
 try{
  await api(`${routeChat(c)}/messages`,'POST',{body});
  textArea.value='';chatNotice='';
  await refreshMessages();
 }catch(e){chatNotice=e.message;render();}
 finally{if(btn)btn.disabled=false;}
}
function chatKeyDown(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.currentTarget.form.requestSubmit();}}
function scrollChatToBottom(){const n=el('chat-scroll');if(n)n.scrollTop=n.scrollHeight;}
async function refreshMessages(){
 if(!chatMode||chatPolling)return;
 chatPolling=true;
 try{
  const before=JSON.stringify(threadMessages);
  conversations=(await api('/api/conversations')).conversations;
  if(!currentConversation())currentThread=conversations[0]?{requestId:conversations[0].requestId,proId:conversations[0].proId}:null;
  if(currentThread)await fetchThread(true);
  // Mettre à jour seulement les parties non éditables : ne pas effacer un message en cours de rédaction.
  const list=el('chat-contact-list');if(list)list.innerHTML=refreshListHtml();
  const thread=el('chat-scroll');if(thread&&before!==JSON.stringify(threadMessages)){thread.innerHTML=messagesHtml();scrollChatToBottom();}
  const badge=el('chat-badge');if(badge){const unread=conversations.reduce((a,c)=>a+c.unread,0);badge.textContent=unread?` · ${unread} nouveau${unread>1?'x':''}`:'';}
 }catch(e){chatNotice=e.message;const err=el('chat-error');if(err)err.textContent=e.message;}
 finally{chatPolling=false;}
}
if(typeof window!=='undefined'&&typeof window.setInterval==='function')window.setInterval(()=>{if(document.body.dataset.page==='app'&&chatMode)refreshMessages();},12000);

bootAuth();

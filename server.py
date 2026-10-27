"""Dakhla Home Services V6 — serveur de démonstration FastAPI + SQLite.
Démarrer: python -m uvicorn server:app --reload
Remarque : prototype pédagogique, non audité pour la production.
"""
import os
import re
import json
import uuid
import sqlite3
import hashlib
import secrets
import time
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('DAKHLA_DB_PATH', str(ROOT / 'dakhla_home.sqlite3')))
DEMO_MODE = os.environ.get('DEMO_MODE', '1') == '1'
SECURE_COOKIES = os.environ.get('COOKIE_SECURE', '0') == '1'  # HTTPS obligatoire en production
COOKIE_NAME = 'dakhla_session'
SESSION_AGE = 2 * 24 * 3600
SERVICES = ['Plomberie','Électricité','Ménage','Climatisation','Peinture','Menuiserie','Électroménager','Déménagement','Jardinage','Serrurerie']
DEMO_PASS = 'Demo2026!'
hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=2)
app = FastAPI(title='Dakhla Home Services - prototype avec messagerie SQLite', docs_url=None, redoc_url=None)

@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 10000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize():
    with database() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, name TEXT NOT NULL,
          email TEXT NOT NULL COLLATE NOCASE UNIQUE, password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK (role IN ('client','pro','admin')),
          pro_id TEXT UNIQUE, services TEXT NOT NULL DEFAULT '[]',
          demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          client_id TEXT NOT NULL REFERENCES users(id),
          service TEXT NOT NULL, zone TEXT NOT NULL, details TEXT NOT NULL,
          budget INTEGER NOT NULL CHECK(budget BETWEEN 20 AND 100000),
          when_label TEXT NOT NULL, urgent INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','accepted','done','cancelled')),
          selected_offer INTEGER, rating INTEGER CHECK(rating BETWEEN 1 AND 5),
          created TEXT NOT NULL DEFAULT CURRENT_DATE
        );
        CREATE TABLE IF NOT EXISTS offers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
          pro_id TEXT NOT NULL REFERENCES users(pro_id),
          price INTEGER NOT NULL CHECK(price BETWEEN 20 AND 100000),
          eta TEXT NOT NULL, message TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(request_id, pro_id)
        );
        CREATE INDEX IF NOT EXISTS idx_requests_client ON requests(client_id);
        CREATE INDEX IF NOT EXISTS idx_requests_service_status ON requests(service, status);
        CREATE INDEX IF NOT EXISTS idx_offers_request ON offers(request_id);
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
          pro_id TEXT NOT NULL REFERENCES users(pro_id),
          sender_id TEXT NOT NULL REFERENCES users(id),
          body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 1000),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          read_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(request_id,pro_id,id);
        CREATE INDEX IF NOT EXISTS idx_messages_unread ON messages(request_id,pro_id,read_at);
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
          csrf TEXT NOT NULL, expires INTEGER NOT NULL
        );
        ''')
        if DEMO_MODE:
            demos = [
              ('client-demo','Client Démo','client@demo.test','client',None,[]),
              ('pro-a','Artisan démo A','pro@demo.test','pro','p1',['Plomberie','Électricité','Climatisation']),
              ('pro-b','Artisan démo B','pro2@demo.test','pro','p2',['Plomberie','Peinture','Menuiserie']),
              ('pro-c','Artisan démo C','pro3@demo.test','pro','p3',['Ménage','Peinture','Déménagement']),
              ('admin-demo','Administrateur Démo','admin@demo.test','admin',None,[])
            ]
            for uid,name,email,role,pid,services in demos:
                if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():
                    c.execute('INSERT INTO users(id,name,email,password_hash,role,pro_id,services,demo) VALUES (?,?,?,?,?,?,?,1)',
                              (uid,name,email,hasher.hash(DEMO_PASS),role,pid,json.dumps(services,ensure_ascii=False)))
            if not c.execute('SELECT 1 FROM requests LIMIT 1').fetchone():
                seed_data(c)


def seed_data(c):
    r1 = c.execute('INSERT INTO requests(id,client_id,service,zone,details,budget,when_label,urgent) VALUES(1001,?,?,?,?,?,?,0)',
                    ('client-demo','Plomberie','Centre-ville','Réparer une fuite sous l’évier. Exemple fictif.',150,'Demain matin')).lastrowid
    c.execute('INSERT INTO requests(id,client_id,service,zone,details,budget,when_label,urgent) VALUES(1002,?,?,?,?,?,?,0)',
              ('client-demo','Ménage','Dakhla','Ménage d’un petit appartement. Exemple fictif.',130,'Cette semaine'))
    c.execute('INSERT INTO offers(request_id,pro_id,price,eta,message) VALUES(?,?,?,?,?)',(r1,'p1',150,'Demain matin','Je peux prendre en charge la petite fuite (simulation).'))
    c.execute('INSERT INTO offers(request_id,pro_id,price,eta,message) VALUES(?,?,?,?,?)',(r1,'p2',130,'Après-demain','Disponible sur rendez-vous (simulation).'))

initialize()


def fail(message, status=400):
    raise HTTPException(status_code=status, detail=message)


def user_public(row):
    if row is None: return None
    return {'id':row['id'], 'name':row['name'], 'email':row['email'], 'role':row['role'],
            'proId':row['pro_id'], 'service':(json.loads(row['services']) or [''])[0], 'demo':bool(row['demo'])}


def sid_hash(sid): return hashlib.sha256(sid.encode('utf-8')).hexdigest()


def get_session(c, req):
    sid = req.cookies.get(COOKIE_NAME, '')
    if not sid or not re.fullmatch(r'[A-Za-z0-9_-]{40,150}',sid): return None
    return c.execute('SELECT * FROM sessions WHERE token_hash=? AND expires>?',(sid_hash(sid),int(time.time()))).fetchone()


def start_session(c, user_id=None):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    c.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires) VALUES(?,?,?,?)',
              (sid_hash(token),user_id,csrf,int(time.time())+SESSION_AGE))
    return token, csrf


def set_session_cookie(response, token):
    response.set_cookie(COOKIE_NAME,token,httponly=True,secure=SECURE_COOKIES,
                        samesite='lax',max_age=SESSION_AGE,path='/')


def current_user(c, req, role=None):
    sess = get_session(c,req)
    if not sess or not sess['user_id']: fail('Veuillez vous connecter.',401)
    user = c.execute('SELECT * FROM users WHERE id=?',(sess['user_id'],)).fetchone()
    if not user: fail('Compte introuvable.',401)
    if role and user['role']!=role: fail('Accès refusé pour ce rôle.',403)
    return user


def check_csrf(c,req):
    sess=get_session(c,req)
    token=req.headers.get('x-csrf-token','')
    if not sess or not token or not secrets.compare_digest(token,sess['csrf']):
        fail('Jeton de sécurité invalide. Actualisez la page.',403)
    return sess


@app.middleware('http')
async def response_headers(req,call_next):
    if req.method in ('POST','PUT','PATCH','DELETE'):
        if req.headers.get('content-length') and int(req.headers['content-length']) > 20000:
            return JSONResponse({'detail':'Requête trop volumineuse.'},status_code=413)
    res=await call_next(req)
    res.headers['X-Content-Type-Options']='nosniff'
    res.headers['X-Frame-Options']='DENY'
    res.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    res.headers['Cache-Control']='no-store'
    return res


@app.get('/')
def home(): return RedirectResponse('/index.html')

@app.get('/index.html')
def auth_page(): return FileResponse(ROOT/'index.html',media_type='text/html')

@app.get('/application.html')
def app_page(): return FileResponse(ROOT/'application.html',media_type='text/html')

@app.get('/shared.js')
def app_js(): return FileResponse(ROOT/'shared.js',media_type='text/javascript')


@app.get('/api/session')
def session_info(req:Request):
    with database() as c:
        sess=get_session(c,req)
        if not sess:
            token,csrf=start_session(c)
            res=JSONResponse({'csrf':csrf,'account':None})
            set_session_cookie(res,token)
            return res
        account = c.execute('SELECT * FROM users WHERE id=?',(sess['user_id'],)).fetchone() if sess['user_id'] else None
        return {'csrf':sess['csrf'], 'account':user_public(account)}


async def json_body(req):
    try: payload=await req.json()
    except Exception: fail('Format JSON attendu.')
    if not isinstance(payload,dict): fail('Données incorrectes.')
    return payload


@app.post('/api/register')
async def register(req:Request):
    payload=await json_body(req)
    name=str(payload.get('name','')).strip()
    email=str(payload.get('email','')).strip().lower()
    password=str(payload.get('password',''))
    role=payload.get('role')
    service=payload.get('service') if role=='pro' else None
    if not (2 <= len(name) <= 70) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>120: fail('Vérifiez le nom et l’e-mail.')
    if not 10<=len(password)<=128: fail('Le mot de passe doit contenir au moins 10 caractères.')
    if role not in ('client','pro'): fail('Choisissez Client ou Prestataire.')
    if role=='pro' and service not in SERVICES: fail('Spécialité invalide.')
    with database() as c:
        previous=check_csrf(c,req)
        if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone(): fail('Adresse e-mail déjà utilisée.',409)
        uid='u-'+uuid.uuid4().hex
        pid='p-'+uid if role=='pro' else None
        c.execute('INSERT INTO users(id,name,email,password_hash,role,pro_id,services,demo) VALUES(?,?,?,?,?,?,?,0)',
                  (uid,name,email,hasher.hash(password),role,pid,json.dumps([service] if service else [],ensure_ascii=False)))
        c.execute('DELETE FROM sessions WHERE token_hash=?',(previous['token_hash'],))
        token,csrf=start_session(c,uid)
        res=JSONResponse({'account':user_public(c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()), 'csrf':csrf})
        set_session_cookie(res,token)
        return res


@app.post('/api/login')
async def login(req:Request):
    payload=await json_body(req)
    email=str(payload.get('email','')).strip().lower()[:120]
    password=str(payload.get('password',''))
    with database() as c:
        old_session=check_csrf(c,req)
        found=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        valid=False
        if found:
            try: valid=hasher.verify(found['password_hash'],password)
            except (VerifyMismatchError,VerificationError): pass
        if not valid: fail('Adresse e-mail ou mot de passe incorrect.',401)
        c.execute('DELETE FROM sessions WHERE token_hash=?',(old_session['token_hash'],))
        token,csrf=start_session(c,found['id'])
        res=JSONResponse({'account':user_public(found),'csrf':csrf})
        set_session_cookie(res,token)
        return res


@app.post('/api/logout')
async def logout(req:Request):
    with database() as c:
        sess=check_csrf(c,req)
        c.execute('DELETE FROM sessions WHERE token_hash=?',(sess['token_hash'],))
    res=JSONResponse({'ok':True})
    res.delete_cookie(COOKIE_NAME,path='/')
    return res


def allowed_request_ids(c,user):
    if user['role']=='admin':
        return [row['id'] for row in c.execute('SELECT id FROM requests').fetchall()]
    if user['role']=='client':
        return [row['id'] for row in c.execute('SELECT id FROM requests WHERE client_id=?',(user['id'],)).fetchall()]
    services=json.loads(user['services'])
    # Offres déjà soumises visibles même après attribution de la demande.
    return [row['id'] for row in c.execute('SELECT DISTINCT r.id FROM requests r LEFT JOIN offers o ON o.request_id=r.id AND o.pro_id=? WHERE o.id IS NOT NULL OR (r.status=\'open\' AND r.service IN ('+','.join('?' for _ in services)+'))',
                       (user['pro_id'],*services)).fetchall()] if services else []


@app.get('/api/state')
def state(req:Request):
    with database() as c:
        user=current_user(c,req)
        ids=allowed_request_ids(c,user)
        rows = c.execute('SELECT * FROM requests WHERE id IN ('+','.join('?' for _ in ids)+') ORDER BY id',ids).fetchall() if ids else []
        request_rows=[{'id':r['id'],'clientId':r['client_id'],'service':r['service'],'zone':r['zone'],
          'details':r['details'],'budget':r['budget'],'when':r['when_label'],'urgent':bool(r['urgent']),
          'status':r['status'],'selectedOffer':r['selected_offer'],'rating':r['rating'],'created':r['created']} for r in rows]
        # Les prestataires ne reçoivent que leurs propres offres ; les clients voient les offres faites à leurs demandes.
        if user['role']=='pro':
            offers=c.execute('SELECT * FROM offers WHERE pro_id=? ORDER BY id',(user['pro_id'],)).fetchall()
        elif ids:
            offers=c.execute('SELECT * FROM offers WHERE request_id IN ('+','.join('?' for _ in ids)+') ORDER BY id',ids).fetchall()
        else: offers=[]
        offer_rows=[{'id':o['id'],'requestId':o['request_id'],'proId':o['pro_id'],'price':o['price'],
                     'eta':o['eta'],'message':o['message']} for o in offers]
        profiles=[{'id':p['pro_id'],'name':p['name'],'services':json.loads(p['services']), 'zone':'Dakhla'}
          for p in c.execute("SELECT pro_id,name,services FROM users WHERE role='pro' ORDER BY created_at, name")]
        return {'requests':request_rows,'offers':offer_rows,'pros':profiles}


@app.post('/api/requests')
async def create_request(req:Request):
    b=await json_body(req)
    service=b.get('service');zone=str(b.get('zone','')).strip();details=str(b.get('details','')).strip()
    when=b.get('when');budget=b.get('budget');urgent=b.get('urgent') is True
    if service not in SERVICES or not (2<=len(zone)<=80) or not (10<=len(details)<=400): fail('Service, zone ou description invalide.')
    if not isinstance(budget,int) or isinstance(budget,bool) or not 20<=budget<=100000: fail('Budget invalide.')
    if when not in ['Aujourd\'hui','Demain matin','Demain après-midi','Cette semaine','À convenir']: fail('Créneau invalide.')
    with database() as c:
        check_csrf(c,req);user=current_user(c,req,'client')
        ident=c.execute('INSERT INTO requests(client_id,service,zone,details,budget,when_label,urgent) VALUES(?,?,?,?,?,?,?)',
                       (user['id'],service,zone,details,budget,when,int(urgent))).lastrowid
        return {'id':ident,'ok':True}


@app.post('/api/offers')
async def create_offer(req:Request):
    b=await json_body(req)
    request_id=b.get('requestId');price=b.get('price')
    eta=str(b.get('eta','')).strip();message=str(b.get('message','')).strip()
    if not isinstance(request_id,int) or not isinstance(price,int) or isinstance(price,bool) or not 20<=price<=100000 or not 1<=len(eta)<=60 or len(message)>130:
        fail('Offre invalide.')
    with database() as c:
        check_csrf(c,req);pro=current_user(c,req,'pro')
        r=c.execute('SELECT * FROM requests WHERE id=?',(request_id,)).fetchone()
        if not r: fail('Demande introuvable.',404)
        if r['status']!='open' or r['service'] not in json.loads(pro['services']): fail('Demande indisponible ou service non autorisé.',403)
        try:
            ident=c.execute('INSERT INTO offers(request_id,pro_id,price,eta,message) VALUES(?,?,?,?,?)',
                            (request_id,pro['pro_id'],price,eta,message)).lastrowid
        except sqlite3.IntegrityError: fail('Vous avez déjà fait une proposition.',409)
        return {'ok':True,'id':ident}


@app.post('/api/requests/{rid}/select')
async def choose_offer(rid:int,req:Request):
    b=await json_body(req)
    oid=b.get('offerId')
    if not isinstance(oid,int): fail('Offre invalide.')
    with database() as c:
        check_csrf(c,req);u=current_user(c,req,'client')
        offer=c.execute('SELECT id FROM offers WHERE id=? AND request_id=?',(oid,rid)).fetchone()
        if not offer: fail('Offre introuvable.',404)
        count=c.execute("UPDATE requests SET selected_offer=?,status='accepted' WHERE id=? AND client_id=? AND status='open'",(oid,rid,u['id'])).rowcount
        if not count: fail('Cette demande ne peut pas être attribuée.',409)
        return {'ok':True}


@app.post('/api/requests/{rid}/done')
async def done(rid:int,req:Request):
    with database() as c:
        check_csrf(c,req);u=current_user(c,req,'client')
        count=c.execute("UPDATE requests SET status='done' WHERE id=? AND client_id=? AND status='accepted'",(rid,u['id'])).rowcount
        if not count: fail('Vous ne pouvez pas terminer cette demande.',409)
        return {'ok':True}


@app.post('/api/requests/{rid}/rate')
async def rate(rid:int,req:Request):
    b=await json_body(req);rating=b.get('rating')
    if not isinstance(rating,int) or isinstance(rating,bool) or not 1<=rating<=5: fail('Note invalide.')
    with database() as c:
        check_csrf(c,req);u=current_user(c,req,'client')
        count=c.execute("UPDATE requests SET rating=? WHERE id=? AND client_id=? AND status='done' AND rating IS NULL",(rating,rid,u['id'])).rowcount
        if not count: fail('Évaluation déjà donnée ou demande non terminée.',409)
        return {'ok':True}



def chat_access(c, user, request_id, pro_id):
    """A conversation belongs exclusively to the request owner and a professional
    who has placed an offer. Once an offer is selected, only that professional
    can continue messaging; previous conversations stay readable.
    """
    if user['role'] not in ('client','pro'):
        fail('Messagerie réservée aux clients et professionnels.',403)
    if not re.fullmatch(r'[A-Za-z0-9-]{1,70}',pro_id):
        fail('Conversation introuvable.',404)
    row=c.execute('''SELECT r.id, r.client_id, r.status, r.selected_offer,
                            o.id AS offer_id, o.pro_id, pu.id AS professional_user_id
                     FROM requests r JOIN offers o ON o.request_id=r.id
                     JOIN users pu ON pu.pro_id=o.pro_id
                     WHERE r.id=? AND o.pro_id=?''',(request_id,pro_id)).fetchone()
    if not row:
        fail('Conversation introuvable.',404)
    if user['role']=='client' and row['client_id']!=user['id']:
        fail('Accès à cette conversation refusé.',403)
    if user['role']=='pro' and row['professional_user_id']!=user['id']:
        fail('Accès à cette conversation refusé.',403)
    allowed_to_send=row['status']=='open' or (
        row['status'] in ('accepted','done') and row['selected_offer']==row['offer_id'])
    return row, allowed_to_send


@app.get('/api/conversations')
def conversations(req:Request):
    with database() as c:
        user=current_user(c,req)
        if user['role']=='client':
            rows=c.execute('''SELECT r.id AS request_id, r.service, r.status, r.selected_offer,
                               o.id AS offer_id, o.pro_id, o.price,
                               u.name AS correspondent
                               FROM offers o JOIN requests r ON r.id=o.request_id
                               JOIN users u ON u.pro_id=o.pro_id
                               WHERE r.client_id=? ORDER BY o.id DESC LIMIT 100''',(user['id'],)).fetchall()
        elif user['role']=='pro':
            rows=c.execute('''SELECT r.id AS request_id, r.service, r.status, r.selected_offer,
                               o.id AS offer_id, o.pro_id, o.price,
                               u.name AS correspondent
                               FROM offers o JOIN requests r ON r.id=o.request_id
                               JOIN users u ON u.id=r.client_id
                               WHERE o.pro_id=? ORDER BY o.id DESC LIMIT 100''',(user['pro_id'],)).fetchall()
        else:
            fail('Accès réservé aux clients et prestataires.',403)
        result=[]
        for row in rows:
            last=c.execute('''SELECT body,created_at,sender_id FROM messages
                              WHERE request_id=? AND pro_id=?
                              ORDER BY id DESC LIMIT 1''',(row['request_id'],row['pro_id'])).fetchone()
            unread=c.execute('''SELECT COUNT(*) AS n FROM messages
                                WHERE request_id=? AND pro_id=? AND sender_id<>? AND read_at IS NULL''',
                             (row['request_id'],row['pro_id'],user['id'])).fetchone()['n']
            can_send=row['status']=='open' or (row['status'] in ('accepted','done') and row['selected_offer']==row['offer_id'])
            result.append({'requestId':row['request_id'],'proId':row['pro_id'],
                           'service':row['service'],'status':row['status'],
                           'price':row['price'],'correspondent':row['correspondent'],
                           'canSend':bool(can_send),'unread':unread,
                           'lastMessage':last['body'][:90] if last else '',
                           'lastAt':last['created_at'] if last else None})
        result.sort(key=lambda x:(x['unread']>0, x['lastAt'] or '',x['requestId']),reverse=True)
        return {'conversations':result}


@app.get('/api/conversations/{rid}/{pro_id}/messages')
def get_messages(rid:int,pro_id:str,req:Request):
    with database() as c:
        user=current_user(c,req)
        row,can_send=chat_access(c,user,rid,pro_id)
        rows=c.execute('''SELECT * FROM (SELECT m.id,m.sender_id,m.body,m.created_at,m.read_at
                          FROM messages m WHERE m.request_id=? AND m.pro_id=?
                          ORDER BY m.id DESC LIMIT 150) ORDER BY id''',(rid,pro_id)).fetchall()
        return {'requestId':rid,'proId':pro_id,'canSend':can_send,
                'messages':[{'id':m['id'],'mine':m['sender_id']==user['id'],
                             'body':m['body'],'createdAt':m['created_at'],
                             'read':m['read_at'] is not None} for m in rows]}


@app.post('/api/conversations/{rid}/{pro_id}/messages')
async def send_message(rid:int,pro_id:str,req:Request):
    b=await json_body(req)
    body=b.get('body')
    if not isinstance(body,str) or not 1<=len(body.strip())<=1000:
        fail('Le message doit contenir entre 1 et 1000 caractères.')
    body=body.strip()
    # refuse binary/control data apart from ordinary line breaks and tabs
    if any(ord(char)<32 and char not in '\\n\\r\\t' for char in body):
        fail('Le message contient des caractères interdits.')
    with database() as c:
        check_csrf(c,req)
        user=current_user(c,req)
        _,can_send=chat_access(c,user,rid,pro_id)
        if not can_send: fail('Cette discussion est clôturée.',409)
        sent=c.execute('''SELECT COUNT(*) AS n FROM messages
                          WHERE request_id=? AND pro_id=? AND sender_id=?
                          AND created_at>=datetime('now','-1 minute')''',
                       (rid,pro_id,user['id'])).fetchone()['n']
        if sent>=12: fail('Trop de messages. Réessayez dans une minute.',429)
        new_id=c.execute('INSERT INTO messages(request_id,pro_id,sender_id,body) VALUES(?,?,?,?)',
                         (rid,pro_id,user['id'],body)).lastrowid
        return {'ok':True,'id':new_id}


@app.post('/api/conversations/{rid}/{pro_id}/read')
def mark_messages_read(rid:int,pro_id:str,req:Request):
    with database() as c:
        check_csrf(c,req)
        user=current_user(c,req)
        chat_access(c,user,rid,pro_id)
        updated=c.execute('''UPDATE messages SET read_at=CURRENT_TIMESTAMP
                             WHERE request_id=? AND pro_id=?
                             AND sender_id<>? AND read_at IS NULL''',
                          (rid,pro_id,user['id'])).rowcount
        return {'ok':True,'readCount':updated}

@app.post('/api/admin/reset')
def admin_reset(req:Request):
    if not DEMO_MODE: fail('Réinitialisation désactivée.',403)
    with database() as c:
        check_csrf(c,req);current_user(c,req,'admin')
        c.execute('DELETE FROM messages');c.execute('DELETE FROM offers');c.execute('DELETE FROM requests')
        seed_data(c)
        return {'ok':True}


if __name__=='__main__':
    import uvicorn
    uvicorn.run('server:app',host='127.0.0.1',port=8000)

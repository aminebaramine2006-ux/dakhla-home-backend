"""Tests du flux complet et des droits d'accès avec une base temporaire."""
import os
import sys
import tempfile
import importlib
from pathlib import Path
from fastapi.testclient import TestClient

DIR = Path(__file__).resolve().parent


def make_app():
    d=tempfile.TemporaryDirectory()
    os.environ['DAKHLA_DB_PATH']=str(Path(d.name)/'tests.sqlite3')
    os.environ['DEMO_MODE']='1'
    sys.path.insert(0,str(DIR))
    if 'server' in sys.modules:
        del sys.modules['server']
    module=importlib.import_module('server')
    return d,module


def session_client(app):
    client=TestClient(app)
    r=client.get('/api/session');assert r.status_code==200
    return client,r.json()['csrf']


def login(app, email, password='Demo2026!'):
    client,csrf=session_client(app)
    r=client.post('/api/login',json={'email':email,'password':password},headers={'X-CSRF-Token':csrf})
    assert r.status_code==200, r.text
    return client,r.json()['csrf']


def post(client, csrf, path, body=None):
    return client.post(path,json=body or {},headers={'X-CSRF-Token':csrf})


def test_flow():
    temp,backend=make_app()
    try:
        assert backend.DB_PATH.exists()
        anonymous,csrf_anon=session_client(backend.app)
        assert anonymous.get('/api/state').status_code==401
        assert post(anonymous,csrf_anon,'/api/register',{'name':'Fake Admin','email':'fake@example.test','password':'secure-password-123','role':'admin'}).status_code==400
        assert post(anonymous,csrf_anon,'/api/login',{'email':'client@demo.test','password':'wrong'}).status_code==401
        client,csrf=login(backend.app,'client@demo.test')
        assert client.get('/api/state').status_code==200
        assert post(client,csrf,'/api/offers',{'requestId':1001,'price':90,'eta':'Aujourd’hui'}).status_code==403
        create=post(client,csrf,'/api/requests',{'service':'Plomberie','zone':'Quartier Test','details':'Une fuite à réparer dans la cuisine.','budget':200,'when':'Cette semaine','urgent':False})
        assert create.status_code==200,create.text
        rid=create.json()['id']
        assert rid>1002
        pro,csrf_pro=login(backend.app,'pro@demo.test')
        state=pro.get('/api/state').json()
        assert rid in [r['id'] for r in state['requests']]
        assert post(pro,csrf_pro,f'/api/requests/{rid}/done').status_code==403
        offer=post(pro,csrf_pro,'/api/offers',{'requestId':rid,'price':180,'eta':'Demain matin','message':'Déplacement compris'})
        assert offer.status_code==200,offer.text
        offer_id=offer.json()['id']
        assert post(pro,csrf_pro,'/api/offers',{'requestId':rid,'price':140,'eta':'Demain'}).status_code==409
        assert post(pro,csrf_pro,f'/api/requests/{rid}/select',{'offerId':offer_id}).status_code==403
        assert post(client,csrf,f'/api/requests/{rid}/select',{'offerId':offer_id}).status_code==200
        assert post(client,csrf,f'/api/requests/{rid}/select',{'offerId':offer_id}).status_code==409
        assert post(client,csrf,f'/api/requests/{rid}/done').status_code==200
        assert post(client,csrf,f'/api/requests/{rid}/rate',{'rating':5}).status_code==200
        assert post(client,csrf,f'/api/requests/{rid}/rate',{'rating':4}).status_code==409
        assert client.get('/api/state').json()['requests'][-1]['rating']==5
        assert post(pro,csrf_pro,'/api/admin/reset').status_code==403
        assert post(client,csrf,'/api/logout').status_code==200
        assert client.get('/api/state').status_code==401
        # Etat conservé dans SQLite, consultable avec une nouvelle connexion
        client2,csrf2=login(backend.app,'client@demo.test')
        assert any(r['id']==rid and r['rating']==5 for r in client2.get('/api/state').json()['requests'])
        # Inscription d'un nouveau pro; accès aux services compatibles seulement.
        visitor,sv=session_client(backend.app)
        newpro=post(visitor,sv,'/api/register',{'name':'Entreprise Test','email':'new-pro@example.test','password':'password-2026-secure','role':'pro','service':'Électricité'})
        assert newpro.status_code==200,newpro.text
        proinfo=newpro.json()['account']
        assert proinfo['role']=='pro' and proinfo['proId']
        # Aucune demande Plomberie visible au pro Électricité.
        visible=visitor.get('/api/state').json()['requests']
        assert all(r['service']=='Électricité' for r in visible)
        assert post(visitor,newpro.json()['csrf'],'/api/offers',{'requestId':rid,'price':180,'eta':'Demain'}).status_code==403
        admin,csrf_admin=login(backend.app,'admin@demo.test')
        assert len(admin.get('/api/state').json()['requests'])>=3
        assert post(admin,csrf_admin,'/api/admin/reset').status_code==200
        assert len(admin.get('/api/state').json()['requests'])==2
        print('OK: Inscription, connexion, demandes, offres, validation, évaluation, droits et persistance SQLite.')
    finally:
        temp.cleanup()

if __name__=='__main__':
    test_flow()

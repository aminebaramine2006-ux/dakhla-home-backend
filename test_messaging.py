"""Test fonctionnel et contrôle des accès de la messagerie."""
from test_backend import make_app,login,session_client,post
from fastapi.testclient import TestClient

def test_messages():
    temp,backend=make_app()
    try:
        app=backend.app
        client,c_csrf=login(app,'client@demo.test')
        pro,p_csrf=login(app,'pro@demo.test')
        pro2,p2_csrf=login(app,'pro2@demo.test')
        admin,a_csrf=login(app,'admin@demo.test')
        thread='/api/conversations/1001/p1'
        assert client.get('/api/conversations').status_code==200
        assert pro.get('/api/conversations').status_code==200
        assert admin.get('/api/conversations').status_code==403
        assert admin.get(thread+'/messages').status_code==403
        assert pro2.get(thread+'/messages').status_code==403  # cannot read another pro
        assert client.get('/api/conversations/1001/p3/messages').status_code==404
        assert client.get('/api/conversations/1002/p3/messages').status_code==404
        assert post(pro,p_csrf,thread+'/messages',{'body':'Bonjour avant de répondre au client.'},).status_code==200
        assert post(pro2,p2_csrf,thread+'/messages',{'body':'Intrusion!'}).status_code==403
        assert post(pro,p_csrf,'/api/conversations/1001/p2/messages',{'body':'Autre compte'}).status_code==403
        # CSRF protection for writes
        assert pro.post(thread+'/messages',json={'body':'CSRF'},headers={}).status_code==403
        # owner receives private reply and unread notification
        res=client.get('/api/conversations').json()['conversations']
        c=next(x for x in res if x['proId']=='p1')
        assert c['unread']==1 and c['lastMessage'].startswith('Bonjour')
        msg=client.get(thread+'/messages').json()['messages']
        assert len(msg)==1 and msg[0]['mine'] is False
        assert post(client,c_csrf,thread+'/read').json()['readCount']==1
        assert pro.get(thread+'/messages').json()['messages'][0]['read'] is True
        assert post(client,c_csrf,thread+'/messages',{'body':'Bonjour, quel est votre délai ?'}).status_code==200
        assert pro.get('/api/conversations').json()['conversations'][0]['unread']==1
        assert post(pro,p_csrf,thread+'/read').json()['readCount']==1
        assert post(client,c_csrf,thread+'/messages',{'body':'<script>alert(1)</script>'}).status_code==200
        assert post(client,c_csrf,thread+'/messages',{'body':'  '}).status_code==400
        assert post(client,c_csrf,thread+'/messages',{'body':'x'*1001}).status_code==400
        assert post(client,c_csrf,thread+'/messages',{'body':'\x00'}).status_code==400
        assert post(client,c_csrf,thread+'/messages',{'body':'a'}) .status_code==200
        for _ in range(9):
            assert post(client,c_csrf,thread+'/messages',{'body':'a'}).status_code==200
        assert post(client,c_csrf,thread+'/messages',{'body':'stop spam'}).status_code==429
        # The conversation remains in DB across reconnection
        client_again,csrf_again=login(app,'client@demo.test')
        assert len(client_again.get(thread+'/messages').json()['messages'])==13
        # Client from another account cannot access conversation
        anon,anon_csrf=session_client(app)
        registration=post(anon,anon_csrf,'/api/register',{'name':'Deuxième Client','email':'autre-client@example.test','password':'SuperSecret-2026','role':'client'})
        assert registration.status_code==200
        assert anon.get(thread+'/messages').status_code==403
        # Selecting another professional ends chat with non-selected, but history remains readable
        offers=client.get('/api/state').json()['offers']
        p1_offer=next(o['id'] for o in offers if o['proId']=='p1' and o['requestId']==1001)
        assert post(client,c_csrf,'/api/requests/1001/select',{'offerId':p1_offer}).status_code==200
        assert post(pro2,p2_csrf,'/api/conversations/1001/p2/messages',{'body':'Trop tard'}).status_code==409
        assert pro2.get('/api/conversations/1001/p2/messages').status_code==200
        assert post(pro,p_csrf,thread+'/messages',{'body':'Offre retenue !'}).status_code==200
        assert post(admin,a_csrf,'/api/admin/reset').status_code==200
        assert client.get(thread+'/messages').json()['messages']==[]
        print('OK V6 : messagerie client/pro, confidentialité, CSRF, limite, lecture, persist., choix et reset.')
    finally:
        temp.cleanup()

if __name__=='__main__':
    test_messages()

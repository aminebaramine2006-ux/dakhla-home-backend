DAKHLA HOME - DÉPLOIEMENT API PYTHON SUR RENDER
================================================
IMPORTANT : ce paquet contient du code serveur. Ne le déposez PAS sur Netlify.
Le site Netlify doit seulement contenir les fichiers du paquet DakhlaHome_NETLIFY_SITE.

1. Créez un dépôt GitHub, ajoutez le CONTENU de ce dossier à la racine du dépôt.
2. Sur https://dashboard.render.com, New > Web Service et connectez votre dépôt.
3. Runtime: Python 3 ; Build: pip install -r requirements.txt
   Start: uvicorn server:app --host 0.0.0.0 --port $PORT
4. Environment: DEMO_MODE=1 ; COOKIE_SECURE=1
5. Après déploiement, copiez l'URL HTTPS en .onrender.com.
6. Ouvrez https://VOTRE-SERVEUR.onrender.com/api/session. Vous devez voir du JSON avec csrf et account.
7. Remplacez le domaine d'exemple dans le _redirects du paquet Netlify.

ATTENTION : Render Free perd la base SQLite à la mise en veille, au redémarrage et au redéploiement.
Aucun message, compte ajouté ou demande ne sera conservé durablement. Pour un usage réel,
utilisez un stockage persistant et sécurisez la plateforme avant la mise en ligne publique.
Aucune vraie donnée personnelle pendant les essais.

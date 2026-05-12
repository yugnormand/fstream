# -*- coding: utf-8 -*-
# https://github.com/yugnormand/fstream

# Import enregistrement
import subprocess
import xbmcvfs
import xbmc

from datetime import datetime
from resources.lib.comaddon import addon, VSlog, VSPath, isMatrix, siteManager
from resources.lib.update import cUpdate


if isMatrix():
    # Import Serveur
    import threading
    from socketserver import ThreadingMixIn
    from http.server import HTTPServer, ThreadingHTTPServer


# === Configuration heartbeat fStream ===
HEARTBEAT_INTERVAL = 5 * 60   # secondes entre 2 heartbeats (5 min)
ABORT_TICK         = 10       # granularité de réactivité à la fermeture Kodi


def service():
    # mise à jour des setting si nécessaire
    cUpdate().getUpdateSetting()

    # les flux TV ne permettent plus d'être enregistrés
    return

    # gestion des enregistrements en cours
    ADDON = addon()
    recordIsActivate = ADDON.getSetting('enregistrement_activer')
    if recordIsActivate == 'false':
        return

    pathRecording = 'special://userdata/addon_data/plugin.video.fstream/Enregistrement'
#    pathRecording = ADDON.getSetting('path_enregistrement_programmation')
    path = ''.join([pathRecording])
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdir(path)

    # enregistrement TV
    recordList = xbmcvfs.listdir(path)
    interval = 55  # Vérifier toutes les minutes si un enregistrement est programmé
    ADDON.setSetting('path_enregistrement_programmation', path)
    recordInProgress = False
    monitor = xbmc.Monitor()

    del ADDON

    while not monitor.abortRequested() and recordInProgress is not True:
        if monitor.waitForAbort(int(interval)):
            break

        hour = datetime.now().strftime('%d-%H-%M') + '.py'
        if hour in str(recordList):
            hour = path + '/' + hour
            hour = VSPath(hour)
            recordInProgress = True
            VSlog('python ' + hour)
            command = 'python ' + hour
            proc = subprocess.Popen(command, stdout=subprocess.PIPE)
            p_status = proc.wait()

    # server_thread.join()


def try_auto_login(auth_module):
    """
    Tentative de connexion automatique au démarrage de Kodi.

    Cas couverts :
      - Premier lancement après installation : credentials saisis dans les settings
        mais pas encore de token → on se connecte
      - Token expiré ou révoqué : credentials toujours présents → on retente
      - Pas de credentials : on ne fait rien (l'user verra l'écran de login)

    On reste silencieux en cas d'échec : la modale serait gênante au démarrage.
    L'user verra le résultat au prochain ouverture du plugin.
    """
    # Déjà authentifié : rien à faire
    if auth_module.is_authenticated():
        VSlog('[fStream] Auto-login : déjà connecté')
        return

    settings = auth_module._settings()
    if not settings.get('username') or not settings.get('password'):
        VSlog('[fStream] Auto-login : pas de credentials sauvegardés')
        return

    if not settings.get('api_base'):
        VSlog('[fStream] Auto-login : URL API non configurée')
        return

    VSlog('[fStream] Auto-login : tentative de connexion...')
    try:
        success, message = auth_module.login()
        if success:
            VSlog('[fStream] Auto-login : OK')
        else:
            VSlog('[fStream] Auto-login échoué : ' + str(message))
    except Exception as e:
        VSlog('[fStream] Auto-login : exception ' + str(e))


def do_heartbeat(auth_module):
    """
    Envoie un heartbeat à l'API fStream et affiche les notifications reçues.
    Toute notification reçue est rendue en MODALE BLOQUANTE (OK) puis marquée lue.
    """
    try:
        ok, notifs = auth_module.heartbeat()
    except Exception as e:
        VSlog('[fStream] Erreur heartbeat : ' + str(e))
        return

    if not ok:
        return

    for n in (notifs or []):
        try:
            title   = 'fStream — ' + (n.get('title')   or 'Notification')
            message = n.get('message') or ''
            auth_module.modal(title, message)
            nid = n.get('id')
            if nid:
                auth_module.mark_notification_read(nid)
        except Exception as e:
            VSlog('[fStream] Erreur traitement notification : ' + str(e))


def start_proxy_if_needed():
    """
    Démarre le proxy HTTP local sur 127.0.0.1:2424 si Matrix + site actif.
    Retourne (httpd, server_thread) ou (None, None).
    """
    if not isMatrix():
        return None, None

    sitesManager = siteManager()
    if not (sitesManager.isActive('toonanime') or sitesManager.isActive('kaydo_ws')):
        return None, None

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """Handle requests in a separate thread."""

    try:
        from resources.lib.proxy.ProxyHTTPRequestHandler import ProxyHTTPRequestHandler

        server_address = ('127.0.0.1', 2424)
        httpd = ThreadingHTTPServer(server_address, ProxyHTTPRequestHandler)

        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True   # meurt avec Kodi
        server_thread.start()
        VSlog('[fStream] Proxy HTTP démarré sur 127.0.0.1:2424')
        return httpd, server_thread
    except Exception as e:
        VSlog('[fStream] Impossible de démarrer le proxy HTTP : ' + str(e))
        return None, None


def main_loop():
    """
    Boucle principale du service :
        - heartbeat fStream toutes les 5 min (notifs + détection session révoquée)
        - garde le proxy HTTP vivant en parallèle si actif
    """
    # Démarre le proxy HTTP en thread séparé (si pertinent)
    httpd, server_thread = start_proxy_if_needed()

    # Charge le module auth (en try/except : si non configuré, on ne plante pas)
    auth_module = None
    try:
        from resources.lib import auth as auth_module
        VSlog('[fStream] Module auth chargé, heartbeat actif')
    except Exception as e:
        VSlog('[fStream] Module auth indisponible, heartbeat inactif : ' + str(e))

    # Tentative de login auto au démarrage si credentials présents mais pas de token
    if auth_module is not None:
        try:
            try_auto_login(auth_module)
        except Exception as e:
            VSlog('[fStream] Auto-login global error : ' + str(e))

    monitor = xbmc.Monitor()
    elapsed = HEARTBEAT_INTERVAL  # premier heartbeat dès le 1er tour

    try:
        while not monitor.abortRequested():
            # Heartbeat fStream
            if auth_module is not None and elapsed >= HEARTBEAT_INTERVAL:
                elapsed = 0
                do_heartbeat(auth_module)

            # Attente courte : permet une fermeture rapide de Kodi
            if monitor.waitForAbort(ABORT_TICK):
                break
            elapsed += ABORT_TICK
    finally:
        # Arrêt propre du proxy HTTP
        if httpd is not None:
            try:
                VSlog('[fStream] Arrêt du proxy HTTP')
                httpd.shutdown()
            except Exception as e:
                VSlog('[fStream] Erreur arrêt proxy : ' + str(e))


if __name__ == '__main__':
    service()
    main_loop()
# -*- coding: utf-8 -*-
"""
fStream — Heartbeat opportuniste côté default.py

À chaque navigation utilisateur dans le plugin, on profite pour checker
les notifications. Throttle 30s pour éviter de spammer l'API à chaque clic.

Garantit que toute notif envoyée par l'admin Filament est vue rapidement,
sans dépendre uniquement du polling périodique de service.py (1 min).
"""

import os
import time

import xbmcvfs

try:
    from resources.lib.comaddon import VSlog
except Exception:
    import xbmc
    def VSlog(msg):
        xbmc.log(str(msg))


# Cooldown : ne pas re-ping plus d'une fois toutes les 30 secondes
COOLDOWN_SECONDS = 30

# Fichier marqueur pour partager le "dernier ping" entre les invocations
# (chaque exécution de default.py est un process Python séparé sous Kodi)
_MARKER = 'special://userdata/addon_data/plugin.video.fstream/last_heartbeat.txt'


def _marker_path():
    return xbmcvfs.translatePath(_MARKER)


def _read_last_ping():
    """Retourne le timestamp du dernier ping ou 0."""
    try:
        path = _marker_path()
        if not os.path.exists(path):
            return 0.0
        with open(path, 'r') as f:
            return float(f.read().strip() or 0)
    except Exception:
        return 0.0


def _write_last_ping():
    try:
        path = _marker_path()
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except Exception:
                pass
        with open(path, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass


def ping_if_due():
    """
    Déclenche un heartbeat si le cooldown est passé.
    Affiche les notifications reçues en modale.
    Silencieux en cas d'erreur (pas de blocage de la navigation).
    """
    now = time.time()
    last = _read_last_ping()

    if (now - last) < COOLDOWN_SECONDS:
        return  # trop tôt

    _write_last_ping()

    try:
        from resources.lib import auth
        if not auth.is_authenticated():
            return

        ok, notifs = auth.heartbeat()
        if not ok or not notifs:
            return

        for n in notifs:
            try:
                title   = 'fStream — ' + (n.get('title')   or 'Notification')
                message = n.get('message') or ''
                auth.modal(title, message)
                nid = n.get('id')
                if nid:
                    auth.mark_notification_read(nid)
            except Exception as e:
                VSlog('[fStream] Erreur affichage notif : ' + str(e))

    except Exception as e:
        VSlog('[fStream] Erreur ping_if_due : ' + str(e))

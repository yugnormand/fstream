import json
import re
import uuid
import platform
import xbmcaddon
import xbmcgui

try:
    from resources.lib.comaddon import VSlog
except Exception:
    def VSlog(msg):  # fallback si comaddon indisponible
        try:
            import xbmc
            xbmc.log(str(msg), level=xbmc.LOGINFO)
        except Exception:
            pass

ADDON = xbmcaddon.Addon()

SETTING_API_BASE  = "api_base_url"
SETTING_USER      = "auth_username"
SETTING_PASS      = "auth_password"
SETTING_TOKEN     = "auth_token"
SETTING_DEVICE_ID = "auth_device_id"
SETTING_AUTO      = "auth_autologin"

API_KEY = "14102209"

# Migrations de domaine (ancien → nouveau)
# Appliquées silencieusement au prochain appel de _settings().
DOMAIN_MIGRATIONS = {
    'dev.studitaf.com': 'fstream-api.studitaf.com',
}

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False
    import urllib.request as urlrequest


# ──────────────────────────────────────────────────────────────────
#  UI helpers
# ──────────────────────────────────────────────────────────────────

def notify(title, msg, duration=3000):
    try:
        xbmcgui.Dialog().notification(title, msg, duration)
    except Exception:
        pass


def modal(title, msg):
    """Fenêtre modale bloquante avec OK."""
    try:
        xbmcgui.Dialog().ok(title, msg)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
#  Device identity
# ──────────────────────────────────────────────────────────────────

def get_device_id():
    """UUID stable, généré une fois puis persisté dans les settings."""
    did = ADDON.getSetting(SETTING_DEVICE_ID)
    if not did:
        did = str(uuid.uuid4())
        ADDON.setSetting(SETTING_DEVICE_ID, did)
    return did


def get_device_name():
    try:
        return "Kodi - " + (platform.node() or "Inconnu")
    except Exception:
        return "Kodi"


# ──────────────────────────────────────────────────────────────────
#  Settings + normalisation URL
# ──────────────────────────────────────────────────────────────────

def _is_versioned(url):
    """True si l'URL se termine par /v<chiffre> (ex: /v1, /v2, /v12)."""
    return bool(re.search(r'/v\d+$', url))


def _migrate_domain(base):
    """
    Migre l'ancien domaine vers le nouveau.
    Retourne (nouvelle_url, a_change_bool).
    """
    changed = False
    for old, new in DOMAIN_MIGRATIONS.items():
        if old in base:
            base = base.replace(old, new)
            changed = True
            VSlog('[fStream] Migration API : %s -> %s' % (old, new))
    return base, changed


def _settings():
    raw = ADDON.getSetting(SETTING_API_BASE).rstrip('/')

    # 1) Migration du domaine (persistée)
    migrated, did_migrate = _migrate_domain(raw)
    if did_migrate:
        ADDON.setSetting(SETTING_API_BASE, migrated)

    # 2) Versioning (calculé à la volée, jamais persisté)
    final = migrated
    if final and not _is_versioned(final):
        final = final + '/v1'

    return {
        "api_base": final,
        "username": ADDON.getSetting(SETTING_USER),
        "password": ADDON.getSetting(SETTING_PASS),
        "token":    ADDON.getSetting(SETTING_TOKEN),
    }


# ──────────────────────────────────────────────────────────────────
#  Token storage
# ──────────────────────────────────────────────────────────────────

def set_token(token):
    ADDON.setSetting(SETTING_TOKEN, token or "")


def get_token():
    return ADDON.getSetting(SETTING_TOKEN)


def is_authenticated():
    return len(get_token()) > 0


# ──────────────────────────────────────────────────────────────────
#  HTTP helpers
# ──────────────────────────────────────────────────────────────────

def _headers(with_auth=False, content_type='application/json'):
    h = {
        'Accept':    'application/json',
        'X-API-KEY': API_KEY,
    }
    if content_type:
        h['Content-Type'] = content_type
    if with_auth:
        h['Authorization'] = 'Bearer ' + get_token()
    return h


def _post(url, payload, with_auth=False):
    try:
        if HAS_REQUESTS:
            r = requests.post(url, json=payload, headers=_headers(with_auth), timeout=15)
            return r.status_code, r.text

        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(url, data=data, headers=_headers(with_auth))
        resp = urlrequest.urlopen(req, timeout=15)
        return resp.getcode(), resp.read().decode()
    except Exception as e:
        VSlog('[fStream] HTTP POST error on %s : %s' % (url, e))
        return None, str(e)


def _get(url, with_auth=True):
    try:
        if HAS_REQUESTS:
            r = requests.get(url, headers=_headers(with_auth, content_type=None), timeout=15)
            return r.status_code, r.text

        req = urlrequest.Request(url, headers=_headers(with_auth, content_type=None))
        resp = urlrequest.urlopen(req, timeout=15)
        return resp.getcode(), resp.read().decode()
    except Exception as e:
        VSlog('[fStream] HTTP GET error on %s : %s' % (url, e))
        return None, str(e)


def _delete(url, with_auth=True):
    try:
        if HAS_REQUESTS:
            r = requests.delete(url, headers=_headers(with_auth, content_type=None), timeout=15)
            return r.status_code, r.text

        req = urlrequest.Request(url, headers=_headers(with_auth, content_type=None), method='DELETE')
        resp = urlrequest.urlopen(req, timeout=15)
        return resp.getcode(), resp.read().decode()
    except Exception as e:
        VSlog('[fStream] HTTP DELETE error on %s : %s' % (url, e))
        return None, str(e)


def api_headers(extra=None):
    """Helper rétro-compatible utilisé par d'autres modules (live_tv, scrapers...)."""
    h = _headers(with_auth=True, content_type=None)
    if extra:
        h.update(extra)
    return h


# ──────────────────────────────────────────────────────────────────
#  Auth flows
# ──────────────────────────────────────────────────────────────────

def login(username=None, password=None):
    s = _settings()
    username = username or s["username"]
    password = password or s["password"]

    if not username or not password:
        return False, "Identifiants manquants"

    if not s["api_base"]:
        return False, "URL API non configurée"

    payload = {
        "email":       username,
        "password":    password,
        "device_id":   get_device_id(),
        "device_name": get_device_name(),
        "platform":    "kodi",
    }

    code, text = _post(s["api_base"] + "/login", payload)

    if code == 200:
        try:
            obj = json.loads(text)
            token = obj.get("token") or obj.get("access_token")
            if not token:
                return False, "Token introuvable dans la réponse"
            set_token(token)
            notify("fStream", "Connexion réussie")
            return True, "OK"
        except Exception as e:
            return False, "Réponse invalide : %s" % e

    if code == 423:
        try:
            obj = json.loads(text)
            modal(
                "fStream — Limite atteinte",
                "%s\n\nAppareils connectés : %s / %s\nDéconnectez-en un depuis votre espace utilisateur." % (
                    obj.get("message", ""),
                    obj.get("devices_count", "?"),
                    obj.get("max_devices",   "?"),
                ),
            )
        except Exception:
            modal("fStream", "Nombre maximum d'appareils atteint.")
        return False, "Limite atteinte"

    if code == 403:
        try:
            obj = json.loads(text)
            modal("fStream — Compte bloqué", obj.get("message", "Accès refusé"))
        except Exception:
            modal("fStream", "Accès refusé")
        return False, "Compte bloqué"

    if code == 429:
        modal("fStream", "Trop de tentatives. Réessayez dans quelques minutes.")
        return False, "Throttle"

    if code == 422:
        try:
            obj = json.loads(text)
            return False, obj.get("message", "Identifiants invalides")
        except Exception:
            return False, "Identifiants invalides"

    return False, "Erreur (%s) : %s" % (code, text)


def logout(server_side=True):
    if server_side and is_authenticated():
        s = _settings()
        if s["api_base"]:
            try:
                _post(s["api_base"] + "/logout", {}, with_auth=True)
            except Exception:
                pass
    set_token("")
    notify("fStream", "Déconnecté")


# ──────────────────────────────────────────────────────────────────
#  Heartbeat & notifications
# ──────────────────────────────────────────────────────────────────

def heartbeat():
    """À appeler depuis service.py. Retourne (ok, notifications)."""
    if not is_authenticated():
        return False, []

    s = _settings()
    if not s["api_base"]:
        return False, []

    code, text = _post(s["api_base"] + "/heartbeat", {}, with_auth=True)

    if code == 401:
        # Session révoquée par l'admin
        set_token("")
        modal("fStream", "Votre session a été fermée par un administrateur.\nVeuillez vous reconnecter.")
        return False, []

    if code == 403:
        # Compte suspendu/banni
        set_token("")
        try:
            obj = json.loads(text)
            modal("fStream", obj.get("message", "Compte suspendu"))
        except Exception:
            modal("fStream", "Compte suspendu")
        return False, []

    if code == 200:
        try:
            obj = json.loads(text)
            return True, obj.get("notifications", [])
        except Exception:
            return False, []

    return False, []


def mark_notification_read(notif_id):
    s = _settings()
    if not s["api_base"]:
        return
    try:
        _post(s["api_base"] + "/notifications/" + str(notif_id) + "/read", {}, with_auth=True)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
#  "Mon compte" — endpoints self-service
# ──────────────────────────────────────────────────────────────────

def get_user_info():
    """
    Récupère les infos compte du user courant.
    Retourne le dict {id, firstname, lastname, email, role, status, max_devices,
    devices_count, banned_until, member_since} ou None en cas d'erreur.
    """
    if not is_authenticated():
        return None

    s = _settings()
    if not s["api_base"]:
        return None

    code, text = _get(s["api_base"] + "/me")

    if code == 200:
        try:
            return json.loads(text)
        except Exception:
            return None

    if code == 401:
        set_token("")
    return None


def list_devices():
    """
    Liste les appareils du user courant.
    Retourne le dict {max_devices, count, devices: [...]} ou None.
    Chaque device a un champ `current: true` pour l'appareil actuel.
    """
    if not is_authenticated():
        return None

    s = _settings()
    if not s["api_base"]:
        return None

    code, text = _get(s["api_base"] + "/me/devices")

    if code == 200:
        try:
            return json.loads(text)
        except Exception:
            return None

    return None


def revoke_device(device_id):
    """
    Révoque un appareil spécifique. Retourne (success, message).
    Ne peut PAS révoquer l'appareil courant (à faire via logout()).
    """
    if not is_authenticated():
        return False, "Non authentifié"

    s = _settings()
    if not s["api_base"]:
        return False, "URL API non configurée"

    code, text = _delete(s["api_base"] + "/me/devices/" + str(device_id))

    if code == 200:
        try:
            obj = json.loads(text)
            return True, obj.get("message", "Appareil déconnecté.")
        except Exception:
            return True, "Appareil déconnecté."

    if code == 422:
        try:
            obj = json.loads(text)
            return False, obj.get("message", "Action invalide")
        except Exception:
            return False, "Action invalide"

    if code == 404:
        return False, "Appareil introuvable"

    return False, "Erreur (%s)" % code


def revoke_other_devices():
    """
    Révoque tous les appareils sauf le courant. Retourne (success, message, count).
    """
    if not is_authenticated():
        return False, "Non authentifié", 0

    s = _settings()
    if not s["api_base"]:
        return False, "URL API non configurée", 0

    code, text = _post(s["api_base"] + "/me/devices/revoke-others", {}, with_auth=True)

    if code == 200:
        try:
            obj = json.loads(text)
            return True, obj.get("message", "OK"), int(obj.get("count", 0))
        except Exception:
            return True, "OK", 0

    return False, "Erreur (%s)" % code, 0

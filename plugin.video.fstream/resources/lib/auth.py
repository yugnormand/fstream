import json
import xbmcaddon
import xbmcgui
import xbmc
import time

ADDON = xbmcaddon.Addon()

SETTING_API_BASE = "api_base_url"
SETTING_USER = "auth_username"
SETTING_PASS = "auth_password"
SETTING_TOKEN = "auth_token"
SETTING_AUTO = "auth_autologin"

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False
    import urllib.request as urlrequest
    import urllib.parse as urlparse

def notify(title, msg, duration=3000):
    try:
        xbmcgui.Dialog().notification(title, msg, duration)
    except:
        pass

def get_settings():
    return {
        "api_base": ADDON.getSetting(SETTING_API_BASE).rstrip('/'),
        "username": ADDON.getSetting(SETTING_USER),
        "password": ADDON.getSetting(SETTING_PASS),
        "token": ADDON.getSetting(SETTING_TOKEN)
    }

def set_token(token):
    if not token:
        ADDON.setSetting(SETTING_TOKEN, "")
    else:
        ADDON.setSetting(SETTING_TOKEN, token)

def is_authenticated():
    return len(ADDON.getSetting(SETTING_TOKEN)) > 0

def get_token():
    return ADDON.getSetting(SETTING_TOKEN)

def login(username=None, password=None):
    s = get_settings()

    if username is None:
        username = s["username"]
    if password is None:
        password = s["password"]

    if not username or not password:
        return False, "Identifiants manquants"

    url = s["api_base"] + "/auth/login"
    payload = {"email": username, "password": password}

    try:
        if HAS_REQUESTS:
            r = requests.post(url, json=payload)
            code = r.status_code
            text = r.text
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urlrequest.Request(url, data=data, headers={'Content-Type': 'application/json'})
            resp = urlrequest.urlopen(req)
            code = resp.getcode()
            text = resp.read().decode()

        if code == 200:
            obj = json.loads(text)
            token = obj.get("token") or obj.get("access_token") or None

            if not token:
                return False, "Token introuvable"

            set_token(token)
            notify("Fstream", "Connexion réussie")
            return True, "OK"

        return False, "Erreur: %s" % text

    except Exception as e:
        return False, str(e)

def logout():
    set_token("")
    notify("Fstream", "Déconnecté")

def api_headers(extra=None):
    headers = {"Accept": "application/json"}
    token = get_token()
    if token:
        headers["Authorization"] = "Bearer " + token
    if extra:
        headers.update(extra)
    return headers

def api_get(path):
    s = get_settings()
    url = s["api_base"] + path

    try:
        if HAS_REQUESTS:
            r = requests.get(url, headers=api_headers())
            return r.status_code, r.text

        req = urlrequest.Request(url, headers=api_headers())
        resp = urlrequest.urlopen(req)
        return resp.getcode(), resp.read().decode()

    except Exception as e:
        return None, str(e)

# -*- coding: utf-8 -*-
"""
fStream — Client API pour /api/v1/channels

Fonctionnalités :
- Récupère le catalogue depuis l'API Laravel (avec X-API-KEY + Bearer)
- Cache local 24h (TTL court) + cache de secours illimité (fallback hors-ligne)
- Support ETag : on n'écrase pas le cache si le serveur répond 304
- Robuste : si l'API est down, on retourne le dernier cache même expiré
"""

import json
import os
import time

import xbmc
import xbmcvfs

from resources.lib import auth

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False
    import urllib.request as urlrequest
    import urllib.error as urlerror

try:
    from resources.lib.comaddon import VSlog
except Exception:
    def VSlog(msg):
        xbmc.log(str(msg), level=xbmc.LOGINFO)


CACHE_TTL_SECONDS  = 24 * 60 * 60     # 24h
CACHE_FILENAME     = 'channels_cache.json'
ETAG_FILENAME      = 'channels_etag.txt'
HTTP_TIMEOUT       = 15


# ──────────────────────────────────────────────────────────────────
#  Cache file paths
# ──────────────────────────────────────────────────────────────────

def _cache_dir():
    """Retourne le dossier de cache de l'addon."""
    path = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fstream/cache')
    if not xbmcvfs.exists(path):
        try:
            xbmcvfs.mkdirs(path)
        except Exception:
            pass
    return path


def _cache_path():
    return os.path.join(_cache_dir(), CACHE_FILENAME)


def _etag_path():
    return os.path.join(_cache_dir(), ETAG_FILENAME)


# ──────────────────────────────────────────────────────────────────
#  Cache I/O
# ──────────────────────────────────────────────────────────────────

def _read_cache():
    """Retourne (data, age_seconds) ou (None, None) si pas de cache."""
    path = _cache_path()
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = time.time() - os.path.getmtime(path)
        return data, age
    except Exception as e:
        VSlog('[live_tv] Erreur lecture cache : %s' % e)
        return None, None


def _write_cache(data):
    try:
        with open(_cache_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        VSlog('[live_tv] Erreur écriture cache : %s' % e)


def _read_etag():
    path = _etag_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None


def _write_etag(etag):
    if not etag:
        return
    try:
        with open(_etag_path(), 'w', encoding='utf-8') as f:
            f.write(etag)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
#  HTTP fetch
# ──────────────────────────────────────────────────────────────────

def _build_url():
    """Construit l'URL complète : base_api + /channels."""
    settings = auth._settings()    # bénéficie de la migration domaine + /v1
    base = settings.get('api_base') or ''
    if not base:
        return None
    return base.rstrip('/') + '/channels'


def _do_request(url, etag=None):
    """
    Effectue un GET avec headers complets.
    Retourne (status_code, body_text, response_etag) ou (None, error_str, None).
    """
    headers = {
        'Accept':        'application/json',
        'X-API-KEY':     auth.API_KEY,
        'Authorization': 'Bearer ' + auth.get_token(),
    }
    if etag:
        headers['If-None-Match'] = etag

    try:
        if HAS_REQUESTS:
            r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            return r.status_code, r.text, r.headers.get('ETag')

        req = urlrequest.Request(url, headers=headers)
        try:
            resp = urlrequest.urlopen(req, timeout=HTTP_TIMEOUT)
            return resp.getcode(), resp.read().decode('utf-8'), resp.headers.get('ETag')
        except urlerror.HTTPError as e:
            # 304 arrive ici avec urllib
            if e.code == 304:
                return 304, '', etag
            return e.code, str(e), None
    except Exception as e:
        VSlog('[live_tv] HTTP error : %s' % e)
        return None, str(e), None


# ──────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────

def get_catalog(force_refresh=False):
    """
    Retourne le catalogue (dict) ou None si impossible (pas auth, API down ET pas de cache).

    Stratégie :
      1. Cache frais (<24h) ET pas force_refresh → retourne direct.
      2. Sinon : tente fetch avec ETag.
         - 200 → maj cache, maj etag, retourne nouvelle data
         - 304 → cache toujours bon, on rafraîchit son mtime, retourne cache
         - autre → fallback sur le cache même expiré
      3. Si pas de cache et fetch KO → None.
    """
    if not auth.is_authenticated():
        VSlog('[live_tv] Non authentifié, impossible de charger le catalogue')
        return None

    # 1) Cache frais ?
    cached, age = _read_cache()
    if cached is not None and not force_refresh and age is not None and age < CACHE_TTL_SECONDS:
        VSlog('[live_tv] Catalogue depuis cache (age=%ds)' % int(age))
        return cached

    # 2) Fetch
    url = _build_url()
    if not url:
        VSlog('[live_tv] URL API non configurée')
        return cached  # mieux que rien

    etag = _read_etag()
    status, body, new_etag = _do_request(url, etag=etag)

    if status == 200:
        try:
            data = json.loads(body)
            _write_cache(data)
            _write_etag(new_etag)
            VSlog('[live_tv] Catalogue rafraîchi (%d categories)' %
                  len(data.get('categories', [])))
            return data
        except Exception as e:
            VSlog('[live_tv] JSON invalide : %s' % e)
            return cached

    if status == 304:
        VSlog('[live_tv] Catalogue inchangé (304), on garde le cache')
        # On touch le mtime pour décaler la prochaine vérif
        try:
            os.utime(_cache_path(), None)
        except Exception:
            pass
        return cached

    # Autre erreur → fallback sur cache (même expiré)
    if cached is not None:
        VSlog('[live_tv] API KO (status=%s), fallback sur cache expiré' % status)
        return cached

    VSlog('[live_tv] API KO et aucun cache disponible')
    return None


def find_channel(catalog, channel_id):
    """Cherche une chaîne par son canonical_id dans le catalogue."""
    if not catalog:
        return None
    for cat in catalog.get('categories', []):
        for ch in cat.get('channels', []):
            if ch.get('id') == channel_id:
                return ch
    return None


def find_category(catalog, category_id):
    """Cherche une catégorie par son id."""
    if not catalog:
        return None
    for cat in catalog.get('categories', []):
        if cat.get('id') == category_id:
            return cat
    return None

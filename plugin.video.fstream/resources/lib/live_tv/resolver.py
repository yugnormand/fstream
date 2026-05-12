# -*- coding: utf-8 -*-
"""
fStream — Résolveur de sources pour chaînes Live TV

Quand l'user clique sur "BeIN Sport 1", on a une liste de sources triées par priorité :
  [{site: 'witv', ref: 'bein-sport-1-fr', ...},
   {site: 'elitegol', ref: 'bein-1', ...},
   {site: 'daddyhd', ref: 'bein_1_fr', ...}]

Le résolveur essaie chaque source dans l'ordre jusqu'à en trouver une qui fournit une URL valide.

Pour chaque scraper, on définit un HANDLER qui sait extraire l'URL depuis la ref.
Si un scraper ne dispose pas de handler dédié, on essaie le pattern générique
'getMediaUrl(ref)' qui est la convention fStream la plus courante.
"""

import xbmc
import xbmcgui

try:
    from resources.lib.comaddon import VSlog
except Exception:
    def VSlog(msg):
        xbmc.log(str(msg), level=xbmc.LOGINFO)


# ──────────────────────────────────────────────────────────────────
#  Handlers : un par scraper
#
#  Chaque handler reçoit (ref, meta) et doit retourner une URL jouable
#  (str) ou None si la source ne peut pas fournir le flux.
#
#  Si tu ajoutes un nouveau scraper TV côté Kodi, déclare-le ici.
# ──────────────────────────────────────────────────────────────────

def _handler_generic(scraper_module, ref, meta):
    """
    Handler générique : appelle scraper_module.getMediaUrl(ref) si la fonction existe.
    Convention fStream la plus répandue.
    """
    fn = getattr(scraper_module, 'getMediaUrl', None)
    if callable(fn):
        try:
            return fn(ref)
        except Exception as e:
            VSlog('[live_tv resolver] %s.getMediaUrl failed: %s' % (scraper_module.__name__, e))
    return None


def _handler_witv(scraper_module, ref, meta):
    """WiTV : ref = slug de chaîne sur witv.org."""
    return _handler_generic(scraper_module, ref, meta)


def _handler_elitegol(scraper_module, ref, meta):
    """EliteGol : ref = slug ou URL relative."""
    return _handler_generic(scraper_module, ref, meta)


def _handler_daddyhd(scraper_module, ref, meta):
    """DaddyHD : ref = identifiant de chaîne."""
    return _handler_generic(scraper_module, ref, meta)


# Mapping scraper → handler
HANDLERS = {
    'witv':          _handler_witv,
    'elitegol':      _handler_elitegol,
    'daddyhd':       _handler_daddyhd,
    'fullmatchtv':   _handler_generic,
    'neymartv':      _handler_generic,
    'livetv':        _handler_generic,
    'channelstream': _handler_generic,
    'freebox':       _handler_generic,
    'pluto_tv':      _handler_generic,
    'direct_stream': _handler_generic,
    'directfr':      _handler_generic,
}


def _load_scraper(site_name):
    """Importe dynamiquement resources.sites.<site_name>."""
    try:
        mod = __import__('resources.sites.%s' % site_name, fromlist=[site_name])
        return mod
    except Exception as e:
        VSlog('[live_tv resolver] Impossible de charger le scraper %s : %s' % (site_name, e))
        return None


def _try_source(source):
    """
    Tente d'extraire une URL jouable depuis une source.
    Retourne l'URL (str) ou None.
    """
    site = source.get('site')
    ref  = source.get('ref')
    meta = source.get('meta') or {}

    if not site or not ref:
        return None

    handler = HANDLERS.get(site, _handler_generic)
    scraper = _load_scraper(site)
    if scraper is None:
        return None

    VSlog('[live_tv resolver] Essai source : %s / %s' % (site, ref))
    try:
        url = handler(scraper, ref, meta)
        if url:
            VSlog('[live_tv resolver] ✓ Source OK : %s' % site)
            return url
        VSlog('[live_tv resolver] ✗ Source vide : %s' % site)
    except Exception as e:
        VSlog('[live_tv resolver] ✗ Exception %s : %s' % (site, e))

    return None


# ──────────────────────────────────────────────────────────────────
#  Point d'entrée public
# ──────────────────────────────────────────────────────────────────

def resolve_channel(channel):
    """
    Essaie chaque source dans l'ordre de priorité.

    `channel` est un dict comme retourné par l'API Laravel :
        {
            'id': 'bein_sport_1',
            'label': 'BeIN Sport 1',
            'logo': '...',
            'sources': [ {site, ref, meta, priority}, ... ]
        }

    Retourne (url, source_used) ou (None, None) si tout a échoué.
    L'utilisateur ne voit AUCUN message tant qu'on a encore des sources à essayer.
    """
    sources = channel.get('sources', []) or []
    if not sources:
        return None, None

    # Affichage subtil pendant l'essai (les sources peuvent prendre quelques secondes)
    progress = xbmcgui.DialogProgressBG()
    try:
        progress.create('fStream', channel.get('label', '') + ' — recherche...')
    except Exception:
        progress = None

    total = len(sources)

    try:
        for idx, source in enumerate(sources, start=1):
            if progress:
                try:
                    pct = int((idx / total) * 100)
                    progress.update(pct, 'fStream', '%s — source %d/%d' %
                                    (channel.get('label', ''), idx, total))
                except Exception:
                    pass

            url = _try_source(source)
            if url:
                return url, source
    finally:
        if progress:
            try:
                progress.close()
            except Exception:
                pass

    return None, None

# -*- coding: utf-8 -*-
"""
fStream — Résolveur de sources pour chaînes Live TV

Approche pragmatique : on utilise UNIQUEMENT les scrapers qui exposent
un accès unitaire par identifiant. Aujourd'hui ça concerne daddyhd
(table channels indexée par numéro).

Pour les autres sources non-unitaires (witv, freebox, livetv, etc.),
elles ne sont pas adaptées à un système "auto-essai par ref" — l'user
y accède via la "Bibliothèque IPTV" du menu principal (inchangée).
"""

import xbmc
import xbmcgui

try:
    from resources.lib.comaddon import VSlog
except Exception:
    def VSlog(msg):
        xbmc.log(str(msg), level=xbmc.LOGINFO)


# ──────────────────────────────────────────────────────────────────
#  Handlers — un par scraper supporté
# ──────────────────────────────────────────────────────────────────

def _handler_daddyhd(ref, meta):
    """
    DaddyHD : ref = numéro de chaîne (ex: "116" = BeIN Sport 1).

    On utilise directement la table `channels` et `URL_LINK` du module
    daddyhd. Si le scraper met à jour ses URLs, le resolver suit
    automatiquement sans modification.

    Si la chaîne n'est pas dans la table (numéro inconnu), on construit
    quand même une URL fallback avec ddh1 comme préfixe par défaut.
    """
    try:
        channel_id = int(ref)
    except (TypeError, ValueError):
        VSlog('[resolver daddyhd] ref invalide : %s' % ref)
        return None

    try:
        from resources.sites import daddyhd as scraper
    except Exception as e:
        VSlog('[resolver daddyhd] Import scraper échoué : %s' % e)
        return None

    url_link = getattr(scraper, 'URL_LINK', 'https://ddh1.mizhls.ru/')
    channels = getattr(scraper, 'channels', {})

    channel = channels.get(channel_id)

    if channel:
        # channel = [label, relative_path, thumb_url]
        path = channel[1]
    else:
        # Fallback si le numéro n'est pas dans la table : on suppose ddh1
        path = 'ddh1/premium%d/tracks-v1a1/mono.m3u8' % channel_id
        VSlog('[resolver daddyhd] Chaîne %d absente de la table, fallback ddh1' % channel_id)

    referer = (meta or {}).get('referer') or 'https://weblivehdplay.ru/'
    url = url_link.rstrip('/') + '/' + path.lstrip('/') + '|referer=' + referer

    return url


def _handler_direct_url(ref, meta):
    """
    URL m3u8 directe : ref = URL complète, on la passe telle quelle.
    Pratique pour stocker n'importe quelle URL en DB.

    Si meta contient referer/user_agent, on les concatène au format Kodi.
    """
    if not ref or not str(ref).startswith('http'):
        return None

    url = str(ref)
    meta = meta or {}

    extras = []
    if meta.get('referer'):
        extras.append('referer=' + meta['referer'])
    if meta.get('user_agent'):
        extras.append('User-Agent=' + meta['user_agent'])

    if extras and '|' not in url:
        url = url + '|' + '&'.join(extras)

    return url


# Mapping : scraper → handler
HANDLERS = {
    'daddyhd':    _handler_daddyhd,
    'direct_url': _handler_direct_url,
}


# ──────────────────────────────────────────────────────────────────
#  Résolution
# ──────────────────────────────────────────────────────────────────

def _try_source(source):
    """Tente d'extraire une URL jouable depuis une source. Retourne l'URL ou None."""
    site = source.get('site')
    ref  = source.get('ref')
    meta = source.get('meta') or {}

    if not site or not ref:
        return None

    handler = HANDLERS.get(site)
    if handler is None:
        VSlog('[resolver] Site non supporté : %s (utilisez daddyhd ou direct_url)' % site)
        return None

    VSlog('[resolver] Essai source : %s / %s' % (site, ref))

    try:
        url = handler(ref, meta)
        if url:
            VSlog('[resolver] ✓ Source OK : %s' % site)
            return url
        VSlog('[resolver] ✗ Source vide : %s' % site)
    except Exception as e:
        VSlog('[resolver] ✗ Exception %s : %s' % (site, e))

    return None


def resolve_channel(channel):
    """
    Essaie chaque source dans l'ordre de priorité jusqu'à en trouver une qui marche.
    Retourne (url, source_used) ou (None, None).

    Silencieux côté UI tant qu'il reste des sources à essayer.
    """
    sources = channel.get('sources', []) or []
    if not sources:
        return None, None

    # Petite barre de progression discrète pendant les essais
    progress = None
    try:
        progress = xbmcgui.DialogProgressBG()
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

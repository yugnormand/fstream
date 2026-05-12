# -*- coding: utf-8 -*-
"""
fStream — UI Live TV (Sport / Divertissement)

Point d'entrée appelable depuis default.py via :
  site=cLiveTV, function=showRoot / showCategory / playChannel
"""

import xbmc
import xbmcgui

from resources.lib.gui.gui import cGui
from resources.lib.gui.hoster import cHosterGui
from resources.lib.handler.inputParameterHandler  import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.live_tv import api, resolver

try:
    from resources.lib.comaddon import VSlog
except Exception:
    def VSlog(msg):
        xbmc.log(str(msg), level=xbmc.LOGINFO)


SITE_IDENTIFIER = 'cLiveTV'
SITE_NAME       = 'Live TV'

# Icônes par catégorie (utilisent les fichiers déjà présents dans l'addon, JAMAIS modifiés)
CATEGORY_ICONS = {
    'sport':          'sport.png',
    'divertissement': 'vod.png',
}


class cLiveTV:
    """Classe exposée à default.py pour gérer les menus Live TV."""

    # ─────────────────────────────────────────────────────────────
    #  Racine : 2 entrées (Sport / Divertissement)
    # ─────────────────────────────────────────────────────────────

    def showRoot(self):
        oGui = cGui()

        catalog = api.get_catalog()
        if catalog is None:
            self._showApiError(oGui)
            oGui.setEndOfDirectory()
            return

        for cat in catalog.get('categories', []):
            cat_id    = cat.get('id', '')
            cat_label = cat.get('label', cat_id.capitalize())
            cat_icon  = cat.get('icon') or CATEGORY_ICONS.get(cat_id, 'tv.png')
            count     = len(cat.get('channels', []))

            if count == 0:
                continue

            oOut = cOutputParameterHandler()
            oOut.addParameter('category_id', cat_id)

            oGui.addDir(
                SITE_IDENTIFIER,
                'showCategory',
                '%s (%d)' % (cat_label, count),
                cat_icon,
                oOut,
            )

        oGui.setEndOfDirectory()

    # ─────────────────────────────────────────────────────────────
    #  Une catégorie : liste les chaînes
    # ─────────────────────────────────────────────────────────────

    def showCategory(self):
        oGui  = cGui()
        oIn   = cInputParameterHandler()
        cat_id = oIn.getValue('category_id')

        catalog  = api.get_catalog()
        category = api.find_category(catalog, cat_id)

        if not category:
            self._showApiError(oGui, 'Catégorie introuvable.')
            oGui.setEndOfDirectory()
            return

        for ch in category.get('channels', []):
            ch_id    = ch.get('id', '')
            ch_label = ch.get('label', ch_id)
            ch_logo  = ch.get('logo') or 'tv.png'
            nb_src   = len(ch.get('sources', []))

            # On ajoute un indicateur subtil du nombre de sources disponibles
            label = ch_label
            if nb_src > 1:
                label = '%s  [COLOR gray](%d sources)[/COLOR]' % (ch_label, nb_src)

            oOut = cOutputParameterHandler()
            oOut.addParameter('channel_id', ch_id)

            # addLink (et non addDir) car cliquer DOIT lancer la lecture, pas afficher un sous-menu
            oGui.addLink(
                SITE_IDENTIFIER,
                'playChannel',
                label,
                ch_logo,
                '',
                oOut,
            )

        oGui.setEndOfDirectory()

    # ─────────────────────────────────────────────────────────────
    #  Lecture : auto-essai des sources
    # ─────────────────────────────────────────────────────────────

    def playChannel(self):
        oIn = cInputParameterHandler()
        ch_id = oIn.getValue('channel_id')

        catalog = api.get_catalog()
        channel = api.find_channel(catalog, ch_id)

        if not channel:
            xbmcgui.Dialog().notification(
                'fStream', 'Chaîne introuvable', xbmcgui.NOTIFICATION_WARNING, 3000)
            return

        url, source_used = resolver.resolve_channel(channel)

        if not url:
            xbmcgui.Dialog().ok(
                'fStream — ' + channel.get('label', ''),
                "Aucune source n'est disponible actuellement.\n"
                "Réessayez dans quelques minutes."
            )
            return

        # Lecture via le système de hosters fStream
        oHoster = cHosterGui().checkHoster(url)
        if oHoster:
            oHoster.setDisplayName(channel.get('label', ''))
            oHoster.setFileName(channel.get('label', ''))
            cHosterGui().showHoster(cGui(), oHoster, url, '')
            return

        # Fallback : lecture directe via Kodi player
        VSlog('[live_tv ui] Pas de hoster, lecture directe : %s' % url)
        li = xbmcgui.ListItem(channel.get('label', 'fStream'))
        try:
            li.setArt({'thumb': channel.get('logo', 'tv.png')})
        except Exception:
            pass
        xbmc.Player().play(url, li)

    # ─────────────────────────────────────────────────────────────
    #  Erreurs (helper)
    # ─────────────────────────────────────────────────────────────

    def _showApiError(self, oGui, msg=None):
        """Affiche un message d'erreur dans le listing (pas une popup)."""
        oGui.addText(
            SITE_IDENTIFIER,
            msg or "Impossible de charger le catalogue TV.\nVérifie ta connexion et réessaie."
        )

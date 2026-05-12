# -*- coding: utf-8 -*-
"""
fStream — Mon compte

Menu utilisateur self-service :
- Affichage du statut du compte (actif, suspendu, banni)
- Affichage du quota d'appareils (X/Y avec couleur si proche du max)
- Liste des appareils connectés (current marqué visuellement)
- Déconnexion d'un appareil spécifique
- Déconnexion de tous les autres appareils (en 1 clic)
- Modification du mot de passe via les settings de l'addon
- Déconnexion globale (logout)
"""

import xbmc
import xbmcgui

from resources.lib import auth
from resources.lib.gui.gui import cGui
from resources.lib.handler.inputParameterHandler  import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler

try:
    from resources.lib.comaddon import VSlog, addon
except Exception:
    def VSlog(msg):
        xbmc.log(str(msg), level=xbmc.LOGINFO)
    def addon():
        import xbmcaddon
        return xbmcaddon.Addon()


SITE_IDENTIFIER = 'cAccount'
SITE_NAME       = 'Mon compte'


# ──────────────────────────────────────────────────────────────────
#  Helpers d'affichage
# ──────────────────────────────────────────────────────────────────

def _format_status(status):
    """Retourne (label_humain, couleur_kodi)."""
    mapping = {
        'active':    ('Actif',     'green'),
        'inactive':  ('Inactif',   'orange'),
        'suspended': ('Suspendu',  'red'),
    }
    return mapping.get(status, (status or 'Inconnu', 'gray'))


def _format_devices_badge(count, maxd):
    """
    Badge coloré X/Y :
    - vert si <50%
    - jaune si 50-80%
    - rouge si >80%
    """
    try:
        ratio = (count / maxd) if maxd > 0 else 0
    except Exception:
        ratio = 0

    if ratio < 0.5:
        color = 'green'
    elif ratio < 0.8:
        color = 'yellow'
    else:
        color = 'red'

    return '[COLOR %s]%d/%d[/COLOR]' % (color, count, maxd)


def _truncate_ip(ip):
    """Masque partiellement une IPv4 pour la lisibilité (192.168.x.x)."""
    if not ip:
        return '—'
    parts = ip.split('.')
    if len(parts) == 4:
        return '%s.%s.x.x' % (parts[0], parts[1])
    return ip


# ──────────────────────────────────────────────────────────────────
#  Classe principale
# ──────────────────────────────────────────────────────────────────

class cAccount:
    """Point d'entrée appelé depuis default.py (site=cAccount)."""

    addons = addon()

    # ─────────────────────────────────────────────────────────────
    #  Vue principale : tableau de bord du compte
    # ─────────────────────────────────────────────────────────────

    def showAccount(self):
        oGui = cGui()

        info = auth.get_user_info()

        if info is None:
            xbmcgui.Dialog().ok('fStream', "Impossible de récupérer vos informations.\nVérifiez votre connexion.")
            return

        fullname = ('%s %s' % (info.get('firstname', ''), info.get('lastname', ''))).strip() or info.get('email', '')
        email    = info.get('email', '')
        status   = info.get('status', '')
        max_dev  = int(info.get('max_devices', 0))
        count    = int(info.get('devices_count', 0))

        status_label, status_color = _format_status(status)

        # En-tête : nom + email (en lecture seule)
        oGui.addText(SITE_IDENTIFIER,
                     '[B]%s[/B]' % fullname)
        oGui.addText(SITE_IDENTIFIER,
                     '[COLOR gray]%s[/COLOR]' % email)

        # Statut
        oGui.addText(SITE_IDENTIFIER,
                     'Statut : [COLOR %s]%s[/COLOR]' % (status_color, status_label))

        # Quota d'appareils
        badge = _format_devices_badge(count, max_dev)
        oGui.addText(SITE_IDENTIFIER,
                     'Appareils : %s' % badge)

        # Séparateur
        oGui.addText(SITE_IDENTIFIER, '──────────────────────')

        # Action : voir les appareils
        oOut = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            'showDevices',
            'Mes appareils connectes',
            'host.png',
            oOut,
        )

        # Action : déconnecter tous les autres (visible uniquement si >1 appareil)
        if count > 1:
            oOut = cOutputParameterHandler()
            oGui.addDir(
                SITE_IDENTIFIER,
                'revokeOthers',
                "Deconnecter les autres appareils (%d)" % (count - 1),
                'host.png',
                oOut,
            )

        # Action : modifier identifiants (ouvre les settings de l'addon)
        oOut = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            'openSettings',
            'Modifier mes identifiants',
            'parametres.png',
            oOut,
        )

        # Action : déconnexion globale
        oOut = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            'doLogout',
            '[COLOR red]Se deconnecter[/COLOR]',
            'logout.png',
            oOut,
        )

        oGui.setEndOfDirectory()

    # ─────────────────────────────────────────────────────────────
    #  Liste des appareils
    # ─────────────────────────────────────────────────────────────

    def showDevices(self):
        oGui = cGui()

        data = auth.list_devices()

        if data is None:
            xbmcgui.Dialog().ok('fStream', 'Impossible de récupérer vos appareils.')
            return

        devices = data.get('devices', [])
        max_dev = int(data.get('max_devices', 0))
        count   = int(data.get('count', 0))

        # Bandeau récap
        badge = _format_devices_badge(count, max_dev)
        oGui.addText(SITE_IDENTIFIER, 'Quota : %s' % badge)
        oGui.addText(SITE_IDENTIFIER, '──────────────────────')

        if not devices:
            oGui.addText(SITE_IDENTIFIER, 'Aucun appareil connecté.')
            oGui.setEndOfDirectory()
            return

        for d in devices:
            name      = d.get('device_name') or 'Appareil sans nom'
            platform  = d.get('platform') or 'unknown'
            ip        = _truncate_ip(d.get('ip'))
            is_current = bool(d.get('current'))
            device_id  = d.get('id')

            # Label coloré
            if is_current:
                label = '[COLOR green][B]✓ %s[/B][/COLOR]  [COLOR gray](%s — cet appareil)[/COLOR]' % (name, platform)
            else:
                label = '%s  [COLOR gray](%s — %s)[/COLOR]' % (name, platform, ip)

            oOut = cOutputParameterHandler()
            oOut.addParameter('device_id', str(device_id))
            oOut.addParameter('device_name', name)
            oOut.addParameter('is_current', '1' if is_current else '0')

            # On utilise addDir pour permettre le clic (qui déclenche révocation)
            # L'appareil courant n'est pas révocable -> on appelle revokeCurrent qui affiche un message
            oGui.addDir(
                SITE_IDENTIFIER,
                'revokeDevice' if not is_current else 'revokeCurrent',
                label,
                'host.png',
                oOut,
            )

        oGui.setEndOfDirectory()

    # ─────────────────────────────────────────────────────────────
    #  Actions : révocation
    # ─────────────────────────────────────────────────────────────

    def revokeDevice(self):
        oIn = cInputParameterHandler()
        device_id   = oIn.getValue('device_id')
        device_name = oIn.getValue('device_name')

        if not device_id:
            return

        # Confirmation
        confirm = xbmcgui.Dialog().yesno(
            'fStream',
            'Déconnecter cet appareil ?\n\n[B]%s[/B]\n\nIl devra se reconnecter pour utiliser fStream.' % device_name,
            nolabel='Annuler',
            yeslabel='Déconnecter',
        )

        if not confirm:
            return

        ok, message = auth.revoke_device(device_id)
        if ok:
            xbmcgui.Dialog().notification('fStream', message, xbmcgui.NOTIFICATION_INFO, 3000)
            # Rafraîchir la liste
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().ok('fStream', message)

    def revokeCurrent(self):
        """Appelé si l'user clique sur SON appareil. On lui explique."""
        xbmcgui.Dialog().ok(
            'fStream',
            "Vous ne pouvez pas déconnecter votre appareil actuel depuis cet écran.\n\n"
            "Utilisez le bouton [B]Se déconnecter[/B] dans le menu Mon compte."
        )

    def revokeOthers(self):
        confirm = xbmcgui.Dialog().yesno(
            'fStream',
            "Déconnecter tous vos autres appareils ?\n\n"
            "Cet appareil restera connecté.\n"
            "Les autres devront se reconnecter manuellement.",
            nolabel='Annuler',
            yeslabel='Tout déconnecter',
        )

        if not confirm:
            return

        ok, message, count = auth.revoke_other_devices()
        if ok:
            xbmcgui.Dialog().notification(
                'fStream',
                '%d appareil(s) déconnecté(s)' % count,
                xbmcgui.NOTIFICATION_INFO,
                3000,
            )
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().ok('fStream', message)

    # ─────────────────────────────────────────────────────────────
    #  Actions : compte
    # ─────────────────────────────────────────────────────────────

    def openSettings(self):
        """Ouvre les paramètres Kodi de l'addon pour éditer email/password."""
        self.addons.openSettings()

    def doLogout(self):
        confirm = xbmcgui.Dialog().yesno(
            'fStream',
            'Confirmer la déconnexion ?',
            nolabel='Annuler',
            yeslabel='Se déconnecter',
        )

        if not confirm:
            return

        auth.logout()

        # Rebascule sur l'écran de login
        from resources.lib.home import cHome
        cHome().loginScreen()

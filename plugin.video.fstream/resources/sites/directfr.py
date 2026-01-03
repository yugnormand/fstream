# -*- coding: utf-8 -*-
# fStream - DirectFR
# Source: https://directfr.sbs

from resources.lib.gui.hoster import cHosterGui
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.parser import cParser
from resources.lib.comaddon import siteManager
from resources.lib.comaddon import VSlog
import re

SITE_IDENTIFIER = 'directfr'
SITE_NAME = 'Favoris Chaines TV Françaises'
SITE_DESC = 'Chaines TV en directs'

URL_MAIN = siteManager().getUrlMain(SITE_IDENTIFIER)

# Pour apparaître dans Live TV
SPORT_SPORTS = (True, 'load')
SPORT_TV = ('generaliste', 'showChannels')

# MAPPING complet NOM → URL
CHANNEL_MAPPING = {
    'TF1': 'generaliste/6-tf1.html',
    'France 2': 'chaines-tv/49-france-2.html',
    'FRANCE 2': 'chaines-tv/49-france-2.html',
    'France 3': 'chaines-tv/50-france-3.html',
    'FRANCE 3': 'chaines-tv/50-france-3.html',
    'M6': 'chaines-tv/44-m6.html',
    'CANAL+': 'chaines-tv/45-canal.html',
    'W9': 'chaines-tv/24-w9.html',
    'TMC': 'chaines-tv/52-tmc.html',
    'TFX': 'chaines-tv/53-tfx.html',
    'RMC Découverte': 'chaines-tv/26-rmc-decouverte.html',
    'RMC Story': 'chaines-tv/59-rmc-story.html',
    'beIN SPORT 1 FR': 'chaines-tv/13-bein-sport-1-fr.html',
    'beIN SPORT 2 FR': 'chaines-tv/14-bein-sport-2-fr.html',
    'beIN SPORT 3 FR': 'chaines-tv/15-bein-sport-3-fr.html',
    'EUROSPORT 1': 'chaines-tv/14-eurosport-1.html',
    'EUROSPORT 2': 'chaines-tv/21-eurosport-2.html',
    'RMC SPORT 1': 'chaines-tv/7-rmc-sport-1.html',
    'CANAL + Sport': 'chaines-tv/16-canal-sport.html',
    'CANAL + Sport HD': 'chaines-tv/17-canal-sport-360.html',
    'Dazn 1': 'chaines-tv/52-dazn-1.html',
    'Dazn 2': 'chaines-tv/54-dazn-2.html',
    'NOVELAS TV': 'chaines-tv/10-novelas-tv.html',
    'Mangas': 'chaines-tv/11-mangas.html',
}

def load():
    oGui = cGui()

    categories = [
        ('generaliste', 'Chaînes Généralistes', 'tv.png'),
        ('sport', 'Chaînes Sport', 'sport.png'),
        ('cinema', 'Chaînes Cinéma', 'films.png'),
        ('jeunesse', 'Chaînes Jeunesse', 'kids.png'),
        ('musique', 'Chaînes Musique', 'music.png'),
    ]

    for cat_url, cat_title, cat_thumb in categories:
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', cat_url)
        oGui.addDir(SITE_IDENTIFIER, 'showChannels', cat_title, cat_thumb, oOutputParameterHandler)

    oGui.setEndOfDirectory()

def showChannels():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sCategory = oInputParameterHandler.getValue('siteUrl')

    if not sCategory:
        oGui.addText(SITE_IDENTIFIER, 'Catégorie manquante')
        oGui.setEndOfDirectory()
        return

    sUrl = URL_MAIN + sCategory + '/'
    VSlog('DirectFR - Chargement: ' + sUrl)

    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)

    try:
        sHtmlContent = oRequestHandler.request()
        if not sHtmlContent:
            oGui.addText(SITE_IDENTIFIER, 'Page inaccessible')
            oGui.setEndOfDirectory()
            return

        oParser = cParser()
        aResult = oParser.parse(sHtmlContent, r'En Direct\s*</[^>]*>\s*\n\s*([^\n<>]+?)\s*\n')

        channels_found = []
        if aResult[0]:
            for sChannelName in aResult[1]:
                sChannelName = sChannelName.strip()

                if sChannelName in CHANNEL_MAPPING:
                    sChannelUrl = CHANNEL_MAPPING[sChannelName]
                    channels_found.append((sChannelName, sChannelUrl))
                    VSlog(f'DirectFR - Trouvé: {sChannelName}')
                else:
                    sSafeName = sChannelName.lower().replace(' ', '-').replace("'", '').replace('+', '')
                    sSafeName = re.sub(r'[^a-z0-9-]', '', sSafeName)
                    sChannelUrl = f'chaines-tv/{sSafeName}.html'
                    channels_found.append((sChannelName, sChannelUrl))

        if not channels_found:
            VSlog('DirectFR - Fallback hardcoded')
            if sCategory == 'generaliste':
                channels_found = [
                    ('TF1', 'generaliste/6-tf1.html'),
                    ('M6', 'chaines-tv/44-m6.html'),
                    ('France 2', 'chaines-tv/49-france-2.html'),
                    ('France 3', 'chaines-tv/50-france-3.html'),
                    ('CANAL+', 'chaines-tv/45-canal.html'),
                    ('W9', 'chaines-tv/24-w9.html'),
                    ('TMC', 'chaines-tv/52-tmc.html'),
                    ('TFX', 'chaines-tv/53-tfx.html'),
                    ('beIN SPORT 1 FR', 'chaines-tv/13-bein-sport-1-fr.html'),
                    ('beIN SPORT 2 FR', 'chaines-tv/14-bein-sport-2-fr.html'),
                    ('beIN SPORT 3 FR', 'chaines-tv/15-bein-sport-3-fr.html'),
                    ('EUROSPORT 1', 'chaines-tv/14-eurosport-1.html'),
                    ('EUROSPORT 2', 'chaines-tv/21-eurosport-2.html'),
                    ('RMC SPORT 1', 'chaines-tv/7-rmc-sport-1.html'),
                    ('CANAL + Sport', 'chaines-tv/16-canal-sport.html'),
                    ('CANAL + Sport HD', 'chaines-tv/17-canal-sport-360.html'),
                    ('Dazn 1', 'chaines-tv/52-dazn-1.html'),
                    ('Dazn 2', 'chaines-tv/54-dazn-2.html'),
                    ('NOVELAS TV', 'chaines-tv/10-novelas-tv.html'),
                    ('Mangas', 'chaines-tv/11-mangas.html'),
                ]
            elif sCategory == 'sport':
                channels_found = [
                    ('beIN SPORT 1 FR', 'sport/1-bein-sports-1.html'),
                    ('beIN SPORT 2 FR', 'sport/2-bein-sports-2.html'),
                    ('EUROSPORT 1', 'sport/14-eurosport-1.html'),
                    ('CANAL + Sport', 'chaines-tv/16-canal-sport.html'),
                ]

        oOutputParameterHandler = cOutputParameterHandler()
        for sTitle, sChannelUrl in channels_found[:25]:
            sThumb = 'tv.png'

            oOutputParameterHandler.addParameter('siteUrl', sChannelUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)

            oGui.addLink(SITE_IDENTIFIER, 'showLink', sTitle, sThumb, '', oOutputParameterHandler)

        VSlog(f'DirectFR - {len(channels_found)} chaînes affichées')

    except Exception as e:
        VSlog('DirectFR - Erreur: ' + str(e))
        import traceback
        VSlog(traceback.format_exc())
        oGui.addText(SITE_IDENTIFIER, 'Erreur chargement')

    oGui.setEndOfDirectory()

def showLink():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrlPath = oInputParameterHandler.getValue('siteUrl')
    sTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')

    sUrl = URL_MAIN.rstrip('/') + '/' + sUrlPath.lstrip('/')
    VSlog('DirectFR - STREAM pour ' + sTitle + ': ' + sUrl)

    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)

    try:
        sHtmlContent = oRequestHandler.request()
        if not sHtmlContent:
            oGui.addText(SITE_IDENTIFIER, 'Page inaccessible')
            oGui.setEndOfDirectory()
            return

        oParser = cParser()
        stream_patterns = [
            r'<iframe[^>]+src\s*=\s*["\']([^"\']+)["\']',
            r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"file"\s*:\s*["\']([^"\']+)["\']',
            r'src\s*=\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]

        sHosterUrl = None
        for pattern in stream_patterns:
            aResult = oParser.parse(sHtmlContent, pattern)
            if aResult[0]:
                sHosterUrl = aResult[1][0].strip()
                VSlog(f'DirectFR - Stream trouvé: {sHosterUrl}')
                break

        if sHosterUrl:
            # Nettoyer URL
            if sHosterUrl.startswith('//'):
                sHosterUrl = 'https:' + sHosterUrl
            elif sHosterUrl.startswith('/'):
                sHosterUrl = URL_MAIN.rstrip('/') + sHosterUrl

            VSlog('DirectFR - URL intermédiaire: ' + sHosterUrl)

            # Si c'est player.php, récupérer le VRAI stream
            if 'player.php' in sHosterUrl:
                VSlog('DirectFR - Résolution player.php...')
                oRequestHandler2 = cRequestHandler(sHosterUrl)
                oRequestHandler2.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                oRequestHandler2.addHeaderEntry('Referer', sUrl)

                try:
                    sPlayerContent = oRequestHandler2.request()
                    if sPlayerContent:
                        # Chercher le vrai stream M3U8 dans player.php
                        real_stream_patterns = [
                            r'"?file"?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                            r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                            r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                            r'https?://[^"\'\s<>]+\.m3u8[^"\'\s<>]*',
                        ]

                        for pattern in real_stream_patterns:
                            aResult2 = oParser.parse(sPlayerContent, pattern)
                            if aResult2[0]:
                                sRealStream = aResult2[1][0].strip()
                                VSlog(f'DirectFR - VRAI stream M3U8: {sRealStream}')
                                sHosterUrl = sRealStream
                                break
                except Exception as e:
                    VSlog(f'DirectFR - Erreur résolution player.php: {str(e)}')

            # Nettoyer URL finale
            if sHosterUrl.startswith('//'):
                sHosterUrl = 'https:' + sHosterUrl

            # Ajouter headers
            if '|' not in sHosterUrl:
                sHosterUrl += f'|Referer={URL_MAIN}&User-Agent=Mozilla/5.0'

            VSlog('DirectFR - URL FINALE: ' + sHosterUrl)

            # Test hoster
            oHoster = cHosterGui().checkHoster(sHosterUrl)
            if oHoster:
                oHoster.setDisplayName(sTitle)
                oHoster.setFileName(sTitle)
                cHosterGui().showHoster(oGui, oHoster, sHosterUrl, sThumb)
            else:
                # Lecture directe SIMPLIFIÉE (méthode fStream standard)
                VSlog('DirectFR - Lecture directe via player')

                oGuiElement = cGuiElement()
                oGuiElement.setSiteName(SITE_IDENTIFIER)
                oGuiElement.setTitle(sTitle)
                oGuiElement.setFileName(sTitle)
                oGuiElement.setMediaUrl(sHosterUrl)
                oGuiElement.setThumbnail(sThumb)
                oGuiElement.setIcon(sThumb)

                from resources.lib.player import cPlayer
                oPlayer = cPlayer()
                oPlayer.clearPlayList()
                oPlayer.addItemToPlaylist(oGuiElement)
                oPlayer.startPlayer()

                VSlog('DirectFR - Lecture lancée')
        else:
            VSlog('DirectFR - AUCUN stream détecté')
            oGui.addText(SITE_IDENTIFIER, f'Stream introuvable: {sTitle}')

    except Exception as e:
        VSlog('DirectFR - Erreur stream: ' + str(e))
        import traceback
        VSlog(traceback.format_exc())
        oGui.addText(SITE_IDENTIFIER, 'Erreur lecture')

    oGui.setEndOfDirectory()
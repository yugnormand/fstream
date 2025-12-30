# -*- coding: utf-8 -*-
# fStream - DirectFR
# Source: https://directfr.sbs

from resources.lib.gui.hoster import cHosterGui
from resources.lib.gui.gui import cGui
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.parser import cParser
from resources.lib.comaddon import VSlog
import re

SITE_IDENTIFIER = 'directfr_sbs'
SITE_NAME = 'DirectFR'
SITE_DESC = 'TV en direct - Toutes les chaînes françaises'

URL_MAIN = 'https://directfr.sbs/'

# Catégories
SPORT_SPORTS = (True, 'load')


# Liste des chaînes avec leurs catégories
channels = {
    'Généraliste': [
        ['TF1', 'generaliste/6-tf1.html', 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Logo_TF1_2013.svg/320px-Logo_TF1_2013.svg.png'],
        ['France 2', 'chaines-tv/49-france-2.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/c/c5/France_2_2018.svg/320px-France_2_2018.svg.png'],
        ['France 3', 'chaines-tv/50-france-3.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/2/28/France_3_2018.svg/320px-France_3_2018.svg.png'],
        ['France 5', 'chaines-tv/51-france-5.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/c/c3/France_5_2018.svg/320px-France_5_2018.svg.png'],
        ['M6', 'chaines-tv/44-m6.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/f/f6/M6_2009.svg/320px-M6_2009.svg.png'],
        ['CANAL+', 'chaines-tv/45-canal.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/1/1a/Canal%2B_2013.svg/320px-Canal%2B_2013.svg.png'],
        ['W9', 'chaines-tv/24-w9.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/b/b5/W9_-_2009_logo.svg/320px-W9_-_2009_logo.svg.png'],
        ['TMC', 'chaines-tv/52-tmc.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/6/63/TMC_logo_2016.svg/320px-TMC_logo_2016.svg.png'],
        ['TFX', 'chaines-tv/53-tfx.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/2/2d/TFX_logo_2018.svg/320px-TFX_logo_2018.svg.png'],
        ['NRJ 12', 'chaines-tv/54-nrj-12.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/e/e4/NRJ12_logo_2015.svg/320px-NRJ12_logo_2015.svg.png'],
        ['C8', 'chaines-tv/55-c8.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/e/e8/C8_logo_2016.svg/320px-C8_logo_2016.svg.png'],
        ['CStar', 'chaines-tv/56-cstar.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/5/52/CStar_logo_2017.svg/320px-CStar_logo_2017.svg.png'],
        ['6ter', 'chaines-tv/57-6ter.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/5/5b/6ter_logo_2018.svg/320px-6ter_logo_2018.svg.png'],
        ['Chérie 25', 'chaines-tv/58-cherie-25.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/f/f0/Ch%C3%A9rie_25_logo_2015.svg/320px-Ch%C3%A9rie_25_logo_2015.svg.png'],
        ['RMC Découverte', 'chaines-tv/26-rmc-decouverte.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/c/c7/RMC_D%C3%A9couverte_logo_2012.svg/320px-RMC_D%C3%A9couverte_logo_2012.svg.png'],
        ['RMC Story', 'chaines-tv/59-rmc-story.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/8/85/RMC_Story_logo_2017.svg/320px-RMC_Story_logo_2017.svg.png'],
    ],
    'Sport': [
        ['beIN Sports 1', 'sport/1-bein-sports-1.html', 'https://r2.thesportsdb.com/images/media/channel/logo/BeIn_Sports_1_Australia.png'],
        ['beIN Sports 2', 'sport/2-bein-sports-2.html', 'https://r2.thesportsdb.com/images/media/channel/logo/BeIn_Sports_2_Australia.png'],
        ['beIN Sports 3', 'sport/3-bein-sports-3.html', 'https://r2.thesportsdb.com/images/media/channel/logo/BeIn_Sports_3_Australia.png'],
        ['Eurosport 1', 'sport/14-eurosport-1.html', 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Eurosport_1_logo.svg/320px-Eurosport_1_logo.svg.png'],
        ['Eurosport 2', 'sport/15-eurosport-2.html', 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Eurosport_2_logo.svg/320px-Eurosport_2_logo.svg.png'],
        ['RMC Sport 1', 'sport/60-rmc-sport-1.html', 'https://i0.wp.com/www.planetecsat.com/wp-content/uploads/2018/07/RMC_SPORT1_PNG_500x500px.png'],
        ['L\'Equipe', 'sport/61-lequipe.html', 'https://www.cse.fr/wp-content/uploads/2016/02/LEquipe_logo-300x200-300x150.png'],
        ['CANAL+ Sport', 'sport/62-canal-sport.html', 'https://upload.wikimedia.org/wikipedia/fr/2/2c/C%2B_Sport_%282023%29.png'],
    ],
    'Cinéma': [
        ['CANAL+ Cinéma', 'cinema/63-canal-cinema.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/a/a5/Canal%2B_Cin%C3%A9ma_logo_2018.svg/320px-Canal%2B_Cin%C3%A9ma_logo_2018.svg.png'],
        ['OCS Max', 'cinema/64-ocs-max.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/2/27/OCS_Max_logo_2018.svg/320px-OCS_Max_logo_2018.svg.png'],
        ['Paramount Channel', 'cinema/65-paramount-channel.html', 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Paramount_Channel_2020.svg/320px-Paramount_Channel_2020.svg.png'],
    ],
    'Séries': [
        ['TF1 Séries Films', 'fiction-serie/66-tf1-series-films.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/4/48/TF1_S%C3%A9ries_Films_logo_2018.svg/320px-TF1_S%C3%A9ries_Films_logo_2018.svg.png'],
        ['Série Club', 'fiction-serie/67-serie-club.html', 'https://upload.wikimedia.org/wikipedia/fr/thumb/8/8f/S%C3%A9rie_Club_logo_2018.svg/320px-S%C3%A9rie_Club_logo_2018.svg.png'],
    ],
}


def load():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    for sCategory in channels.keys():
        oOutputParameterHandler.addParameter('siteUrl', sCategory)
        oGui.addDir(SITE_IDENTIFIER, 'showCategory', sCategory, 'tv.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showCategory():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sCategory = oInputParameterHandler.getValue('siteUrl')
    
    if sCategory not in channels:
        oGui.addText(SITE_IDENTIFIER, 'Catégorie introuvable')
        oGui.setEndOfDirectory()
        return
    
    oOutputParameterHandler = cOutputParameterHandler()
    for channel in channels[sCategory]:
        sTitle = channel[0]
        sUrl = channel[1]
        sThumb = channel[2]
        
        oOutputParameterHandler.addParameter('siteUrl', sUrl)
        oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
        oOutputParameterHandler.addParameter('sThumb', sThumb)
        
        oGui.addTV(SITE_IDENTIFIER, 'showLink', sTitle, '', sThumb, '', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showLink():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = URL_MAIN + oInputParameterHandler.getValue('siteUrl')
    sTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    
    VSlog('DirectFR - Récupération du lien pour: ' + sTitle)
    VSlog('DirectFR - URL: ' + sUrl)
    
    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)
    
    try:
        sHtmlContent = oRequestHandler.request()
        
        if not sHtmlContent:
            oGui.addText(SITE_IDENTIFIER, 'Impossible de charger la page')
            oGui.setEndOfDirectory()
            return
        
        # Patterns pour trouver le stream
        oParser = cParser()
        patterns = [
            '<iframe[^>]+src=["\']([^"\']+)["\']',
            'file:["\']([^"\']+)["\']',
            'source:["\']([^"\']+)["\']',
            '"file":["\']([^"\']+)["\']',
            'src:["\']([^"\']+\.m3u8[^"\']*)["\']',
            'hlsManifestUrl["\']?:["\']([^"\']+)["\']',
        ]
        
        sHosterUrl = None
        for pattern in patterns:
            aResult = oParser.parse(sHtmlContent, pattern)
            if aResult[0]:
                sHosterUrl = aResult[1][0]
                VSlog('DirectFR - Lien trouvé avec pattern: ' + pattern)
                VSlog('DirectFR - Lien: ' + sHosterUrl)
                break
        
        if not sHosterUrl:
            # Chercher dans le JavaScript
            aResult = oParser.parse(sHtmlContent, 'source.*?src.*?["\']([^"\']+)["\']')
            if aResult[0]:
                sHosterUrl = aResult[1][0]
                VSlog('DirectFR - Lien trouvé dans JavaScript')
        
        if sHosterUrl:
            # Nettoyer l'URL
            if sHosterUrl.startswith('//'):
                sHosterUrl = 'https:' + sHosterUrl
            elif sHosterUrl.startswith('/'):
                sHosterUrl = URL_MAIN.rstrip('/') + sHosterUrl
            
            VSlog('DirectFR - URL finale: ' + sHosterUrl)
            
            # Vérifier si c'est un hoster connu
            oHoster = cHosterGui().checkHoster(sHosterUrl)
            if oHoster:
                # Ajouter le referer
                if '|' not in sHosterUrl:
                    sHosterUrl += '|Referer=' + URL_MAIN.rstrip('/')
                    sHosterUrl += '&User-Agent=Mozilla/5.0'
                
                oHoster.setDisplayName(sTitle)
                oHoster.setFileName(sTitle)
                cHosterGui().showHoster(oGui, oHoster, sHosterUrl, sThumb)
            else:
                VSlog('DirectFR - Hoster non reconnu, lecture directe')
                # Lecture directe
                from resources.lib.player import cPlayer
                oPlayer = cPlayer()
                
                # Ajouter les headers pour la lecture
                if '|' not in sHosterUrl:
                    sHosterUrl += '|Referer=' + URL_MAIN.rstrip('/')
                    sHosterUrl += '&User-Agent=Mozilla/5.0'
                
                oPlayer.clearPlayList()
                oPlayer.addItemToPlaylist(sHosterUrl, sTitle, sThumb)
                oPlayer.startPlayer()
        else:
            VSlog('DirectFR - Aucun lien trouvé dans la page')
            oGui.addText(SITE_IDENTIFIER, 'Impossible de trouver le lien de streaming')
    
    except Exception as e:
        VSlog('DirectFR - Erreur: ' + str(e))
        import traceback
        VSlog('DirectFR - Traceback: ' + traceback.format_exc())
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors de la récupération du lien')
    
    oGui.setEndOfDirectory()

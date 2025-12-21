# -*- coding: utf-8 -*-
# fStream - Frembed
# Source: https://frembed.life

from resources.lib.gui.hoster import cHosterGui
from resources.lib.gui.gui import cGui
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.comaddon import progress, VSlog, addon
from resources.lib.parser import cParser
from resources.lib.util import cUtil
import re

SITE_IDENTIFIER = 'frembed_life'
SITE_NAME = 'Frembed'
SITE_DESC = 'Films & Séries via Frembed'

# URL de base
URL_MAIN = 'https://frembed.life'

# Intégration dans fStream
def getCategoryList():
    liste = []
    liste.append(['Films', URL_MAIN, 'films.png', 'showMovies'])
    liste.append(['Séries', URL_MAIN, 'series.png', 'showSeries'])
    return liste


def load():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'movies')
    oGui.addDir(SITE_IDENTIFIER, 'showMovies', 'Films', 'films.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'series')
    oGui.addDir(SITE_IDENTIFIER, 'showSeries', 'Séries', 'series.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showMovies():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', URL_MAIN)
    oGui.addDir(SITE_IDENTIFIER, 'showSearchMovie', 'Recherche par TMDB ID', 'search.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showSeries():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', URL_MAIN)
    oGui.addDir(SITE_IDENTIFIER, 'showSearchSerie', 'Recherche par TMDB ID', 'search.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showSearchMovie():
    """Recherche de film par TMDB ID"""
    oGui = cGui()
    
    sSearchText = oGui.showKeyBoard('', 'Entrez le TMDB ID du film')
    if not sSearchText:
        oGui.setEndOfDirectory()
        return
    
    VSlog('Frembed - Recherche film TMDB ID: ' + sSearchText)
    
    # URL de l'API film
    sUrl = URL_MAIN + '/api/film.php?id=' + sSearchText
    
    VSlog('Frembed - URL: ' + sUrl)
    
    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)
    
    try:
        sHtmlContent = oRequestHandler.request()
        VSlog('Frembed - Réponse reçue: ' + str(len(sHtmlContent) if sHtmlContent else 0) + ' caractères')
        
        if sHtmlContent:
            # Essayer de parser comme JSON
            try:
                import json
                data = json.loads(sHtmlContent)
                VSlog('Frembed - JSON parsé avec succès')
                
                if 'title' in data:
                    sTitle = data.get('title', 'Film')
                    sPoster = data.get('poster', '')
                    
                    oOutputParameterHandler = cOutputParameterHandler()
                    oOutputParameterHandler.addParameter('siteUrl', sUrl)
                    oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
                    oOutputParameterHandler.addParameter('sThumb', sPoster)
                    oOutputParameterHandler.addParameter('sTmdbId', sSearchText)
                    
                    oGui.addMovie(SITE_IDENTIFIER, 'showHosters', sTitle, 'films.png', sPoster, '', oOutputParameterHandler)
                else:
                    VSlog('Frembed - Pas de titre dans la réponse JSON')
                    oGui.addText(SITE_IDENTIFIER, 'Film non trouvé')
            except Exception as e:
                VSlog('Frembed - Erreur parsing JSON: ' + str(e))
                VSlog('Frembed - Contenu brut: ' + sHtmlContent[:200])
                # Ce n'est peut-être pas du JSON, essayons de récupérer le lecteur iframe
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('siteUrl', sUrl)
                oOutputParameterHandler.addParameter('sMovieTitle', 'Film TMDB ID: ' + sSearchText)
                oOutputParameterHandler.addParameter('sTmdbId', sSearchText)
                
                oGui.addMovie(SITE_IDENTIFIER, 'showHosters', 'Film TMDB ID: ' + sSearchText, 'films.png', '', '', oOutputParameterHandler)
        else:
            VSlog('Frembed - Aucune réponse reçue')
            oGui.addText(SITE_IDENTIFIER, 'Aucune réponse du serveur')
    
    except Exception as e:
        VSlog('Frembed - Erreur requête: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur de connexion: ' + str(e))
    
    oGui.setEndOfDirectory()


def showSearchSerie():
    """Recherche de série par TMDB ID"""
    oGui = cGui()
    
    sSearchText = oGui.showKeyBoard('', 'Entrez le TMDB ID de la série')
    if not sSearchText:
        oGui.setEndOfDirectory()
        return
    
    VSlog('Frembed - Recherche série TMDB ID: ' + sSearchText)
    
    # Demander la saison
    sSeason = oGui.showKeyBoard('1', 'Numéro de saison')
    if not sSeason:
        sSeason = '1'
    
    # Demander l'épisode
    sEpisode = oGui.showKeyBoard('1', 'Numéro d\'épisode')
    if not sEpisode:
        sEpisode = '1'
    
    # URL de l'API série
    sUrl = URL_MAIN + '/api/serie.php?id=' + sSearchText + '&sa=' + sSeason + '&epi=' + sEpisode
    
    VSlog('Frembed - URL: ' + sUrl)
    
    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)
    
    try:
        sHtmlContent = oRequestHandler.request()
        VSlog('Frembed - Réponse reçue: ' + str(len(sHtmlContent) if sHtmlContent else 0) + ' caractères')
        
        if sHtmlContent:
            sTitle = 'S' + sSeason.zfill(2) + 'E' + sEpisode.zfill(2) + ' - TMDB ID: ' + sSearchText
            
            oOutputParameterHandler = cOutputParameterHandler()
            oOutputParameterHandler.addParameter('siteUrl', sUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sTmdbId', sSearchText)
            oOutputParameterHandler.addParameter('sSeason', sSeason)
            oOutputParameterHandler.addParameter('sEpisode', sEpisode)
            
            oGui.addEpisode(SITE_IDENTIFIER, 'showHosters', sTitle, 'series.png', '', '', oOutputParameterHandler)
        else:
            VSlog('Frembed - Aucune réponse reçue')
            oGui.addText(SITE_IDENTIFIER, 'Aucune réponse du serveur')
    
    except Exception as e:
        VSlog('Frembed - Erreur requête: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur de connexion: ' + str(e))
    
    oGui.setEndOfDirectory()


def showHosters():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    
    VSlog('Frembed - showHosters URL: ' + sUrl)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', sUrl)
    oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
    oOutputParameterHandler.addParameter('sThumb', sThumb)
    
    oGui.addLink(SITE_IDENTIFIER, 'playVideo', sMovieTitle + ' [Frembed]', sThumb, '', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def playVideo():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    
    VSlog('Frembed - Lecture: ' + sUrl)
    
    # Frembed retourne une page HTML avec un iframe embed
    # On récupère le contenu et on cherche le lecteur
    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)
    
    try:
        sHtmlContent = oRequestHandler.request()
        
        if not sHtmlContent:
            oGui.addText(SITE_IDENTIFIER, 'Impossible de charger la vidéo')
            oGui.setEndOfDirectory()
            return
        
        VSlog('Frembed - Contenu HTML reçu: ' + str(len(sHtmlContent)) + ' caractères')
        
        # Chercher l'iframe ou le lien de streaming
        oParser = cParser()
        
        # Patterns à chercher
        patterns = [
            '<iframe[^>]+src=["\']([^"\']+)["\']',
            'file:["\']([^"\']+)["\']',
            'source:["\']([^"\']+)["\']',
            'src=["\']([^"\']+\.m3u8[^"\']*)["\']',
            'src=["\']([^"\']+\.mp4[^"\']*)["\']',
            'player_src=["\']([^"\']+)["\']'
        ]
        
        stream_url = None
        for pattern in patterns:
            aResult = oParser.parse(sHtmlContent, pattern)
            if aResult[0]:
                stream_url = aResult[1][0]
                VSlog('Frembed - Lien trouvé avec pattern: ' + pattern)
                break
        
        if stream_url:
            # Nettoyer l'URL
            if stream_url.startswith('//'):
                stream_url = 'https:' + stream_url
            elif stream_url.startswith('/'):
                stream_url = URL_MAIN + stream_url
            
            VSlog('Frembed - Stream URL finale: ' + stream_url)
            
            # Vérifier si c'est un hoster connu
            oHoster = cHosterGui().checkHoster(stream_url)
            if oHoster:
                oHoster.setDisplayName(sMovieTitle)
                oHoster.setFileName(sMovieTitle)
                cHosterGui().showHoster(oGui, oHoster, stream_url, sThumb)
            else:
                # Essayer de lire directement
                VSlog('Frembed - Tentative de lecture directe')
                from resources.lib.player import cPlayer
                oPlayer = cPlayer()
                oPlayer.clearPlayList()
                oPlayer.addItemToPlaylist(stream_url, sMovieTitle, sThumb)
                oPlayer.startPlayer()
        else:
            # Si aucun lien trouvé, on affiche l'URL de l'API comme iframe
            VSlog('Frembed - Aucun lien extrait, tentative avec l\'URL directe')
            
            # On peut essayer de charger l'URL de Frembed directement dans le lecteur
            from resources.lib.player import cPlayer
            oPlayer = cPlayer()
            oPlayer.clearPlayList()
            oPlayer.addItemToPlaylist(sUrl, sMovieTitle, sThumb)
            oPlayer.startPlayer()
    
    except Exception as e:
        VSlog('Frembed - Erreur lecture: ' + str(e))
        import traceback
        VSlog('Frembed - Traceback: ' + traceback.format_exc())
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors de la lecture')
    
    oGui.setEndOfDirectory()

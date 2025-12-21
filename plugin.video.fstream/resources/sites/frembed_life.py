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
from resources.lib.tmdb import cTMDb
import re

SITE_IDENTIFIER = 'frembed_life'
SITE_NAME = 'Frembed'
SITE_DESC = 'Films & Séries via Frembed'

# URL de base
URL_MAIN = 'https://frembed.life'

# Menu GLOBALE HOME
MOVIE_MOVIE = (True, 'showMenuMovies')
SERIE_SERIES = (True, 'showMenuSeries')

# Recherche
MY_SEARCH_MOVIES = (True, 'showSearchMovie')
MY_SEARCH_SERIES = (True, 'showSearchSerie')

# Intégration dans fStream
def getCategoryList():
    liste = []
    liste.append(['Films', URL_MAIN, 'films.png', 'showMenuMovies'])
    liste.append(['Séries', URL_MAIN, 'series.png', 'showMenuSeries'])
    return liste


def load():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', MOVIE_MOVIE[0])
    oGui.addDir(SITE_IDENTIFIER, MOVIE_MOVIE[1], 'Films', 'films.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', SERIE_SERIES[0])
    oGui.addDir(SITE_IDENTIFIER, SERIE_SERIES[1], 'Séries', 'series.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showMenuMovies():
    oGui = cGui()
    addons = addon()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', MY_SEARCH_MOVIES[0])
    oGui.addDir(SITE_IDENTIFIER, MY_SEARCH_MOVIES[1], addons.VSlang(30076), 'search.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'tmdb_popular')
    oGui.addDir(SITE_IDENTIFIER, 'showMoviesFromTMDB', addons.VSlang(30102), 'popular.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'tmdb_top')
    oGui.addDir(SITE_IDENTIFIER, 'showMoviesFromTMDB', addons.VSlang(30421), 'notes.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'tmdb_upcoming')
    oGui.addDir(SITE_IDENTIFIER, 'showMoviesFromTMDB', 'Films à venir', 'news.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showMenuSeries():
    oGui = cGui()
    addons = addon()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', MY_SEARCH_SERIES[0])
    oGui.addDir(SITE_IDENTIFIER, MY_SEARCH_SERIES[1], addons.VSlang(30076), 'search.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'tmdb_popular')
    oGui.addDir(SITE_IDENTIFIER, 'showSeriesFromTMDB', addons.VSlang(30102), 'popular.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'tmdb_top')
    oGui.addDir(SITE_IDENTIFIER, 'showSeriesFromTMDB', addons.VSlang(30421), 'notes.png', oOutputParameterHandler)
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'tmdb_airing')
    oGui.addDir(SITE_IDENTIFIER, 'showSeriesFromTMDB', 'Séries en cours', 'news.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showSearchMovie():
    """Recherche de film"""
    oGui = cGui()
    
    sSearchText = oGui.showKeyBoard()
    if not sSearchText:
        oGui.setEndOfDirectory()
        return
    
    # Recherche via TMDB
    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    aResult = oTmdb.searchMovie(sSearchText)
    
    if aResult:
        oOutputParameterHandler = cOutputParameterHandler()
        for aMovie in aResult:
            sTitle = aMovie['title']
            sYear = aMovie['year']
            sId = aMovie['tmdb_id']
            sPoster = aMovie['cover_url']
            sDesc = aMovie['overview']
            
            sDisplayTitle = '%s (%s)' % (sTitle, sYear)
            
            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/film.php?id=' + str(sId))
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sPoster)
            oOutputParameterHandler.addParameter('sTmdbId', str(sId))
            oOutputParameterHandler.addParameter('sYear', sYear)
            
            oGui.addMovie(SITE_IDENTIFIER, 'showHosters', sDisplayTitle, '', sPoster, sDesc, oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucun résultat')
    
    oGui.setEndOfDirectory()


def showSearchSerie():
    """Recherche de série"""
    oGui = cGui()
    
    sSearchText = oGui.showKeyBoard()
    if not sSearchText:
        oGui.setEndOfDirectory()
        return
    
    # Recherche via TMDB
    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    aResult = oTmdb.searchTVShow(sSearchText)
    
    if aResult:
        oOutputParameterHandler = cOutputParameterHandler()
        for aSerie in aResult:
            sTitle = aSerie['title']
            sYear = aSerie['year']
            sId = aSerie['tmdb_id']
            sPoster = aSerie['cover_url']
            sDesc = aSerie['overview']
            
            sDisplayTitle = '%s (%s)' % (sTitle, sYear)
            
            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/serie.php?id=' + str(sId))
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sPoster)
            oOutputParameterHandler.addParameter('sTmdbId', str(sId))
            oOutputParameterHandler.addParameter('sYear', sYear)
            
            oGui.addTV(SITE_IDENTIFIER, 'showSeasons', sDisplayTitle, '', sPoster, sDesc, oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucun résultat')
    
    oGui.setEndOfDirectory()


def showMoviesFromTMDB():
    """Affiche les films depuis TMDB"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sType = oInputParameterHandler.getValue('siteUrl')
    
    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    
    if sType == 'tmdb_popular':
        aResult = oTmdb.getPopularMovies()
    elif sType == 'tmdb_top':
        aResult = oTmdb.getTopRatedMovies()
    elif sType == 'tmdb_upcoming':
        aResult = oTmdb.getUpcomingMovies()
    else:
        aResult = []
    
    if aResult:
        oOutputParameterHandler = cOutputParameterHandler()
        for aMovie in aResult:
            sTitle = aMovie['title']
            sYear = aMovie['year']
            sId = aMovie['tmdb_id']
            sPoster = aMovie['cover_url']
            sDesc = aMovie['overview']
            
            sDisplayTitle = '%s (%s)' % (sTitle, sYear)
            
            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/film.php?id=' + str(sId))
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sPoster)
            oOutputParameterHandler.addParameter('sTmdbId', str(sId))
            oOutputParameterHandler.addParameter('sYear', sYear)
            
            oGui.addMovie(SITE_IDENTIFIER, 'showHosters', sDisplayTitle, '', sPoster, sDesc, oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showSeriesFromTMDB():
    """Affiche les séries depuis TMDB"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sType = oInputParameterHandler.getValue('siteUrl')
    
    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    
    if sType == 'tmdb_popular':
        aResult = oTmdb.getPopularTVShows()
    elif sType == 'tmdb_top':
        aResult = oTmdb.getTopRatedTVShows()
    elif sType == 'tmdb_airing':
        aResult = oTmdb.getOnTheAirTVShows()
    else:
        aResult = []
    
    if aResult:
        oOutputParameterHandler = cOutputParameterHandler()
        for aSerie in aResult:
            sTitle = aSerie['title']
            sYear = aSerie['year']
            sId = aSerie['tmdb_id']
            sPoster = aSerie['cover_url']
            sDesc = aSerie['overview']
            
            sDisplayTitle = '%s (%s)' % (sTitle, sYear)
            
            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/serie.php?id=' + str(sId))
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sPoster)
            oOutputParameterHandler.addParameter('sTmdbId', str(sId))
            oOutputParameterHandler.addParameter('sYear', sYear)
            
            oGui.addTV(SITE_IDENTIFIER, 'showSeasons', sDisplayTitle, '', sPoster, sDesc, oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showSeasons():
    """Affiche les saisons d'une série"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    sTmdbId = oInputParameterHandler.getValue('sTmdbId')
    
    # Récupérer les infos de la série via TMDB
    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    aSeasons = oTmdb.getSeasons(sTmdbId)
    
    if aSeasons:
        oOutputParameterHandler = cOutputParameterHandler()
        for aSeason in aSeasons:
            sSeasonNum = str(aSeason['season'])
            sSeasonTitle = '%s - Saison %s' % (sMovieTitle, sSeasonNum)
            
            oOutputParameterHandler.addParameter('siteUrl', sUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
            oOutputParameterHandler.addParameter('sSeason', sSeasonNum)
            
            oGui.addSeason(SITE_IDENTIFIER, 'showEpisodes', sSeasonTitle, '', sThumb, '', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showEpisodes():
    """Affiche les épisodes d'une saison"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    sTmdbId = oInputParameterHandler.getValue('sTmdbId')
    sSeason = oInputParameterHandler.getValue('sSeason')
    
    # Récupérer les épisodes via TMDB
    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    aEpisodes = oTmdb.getEpisodes(sTmdbId, sSeason)
    
    if aEpisodes:
        oOutputParameterHandler = cOutputParameterHandler()
        for aEpisode in aEpisodes:
            sEpisodeNum = str(aEpisode['episode'])
            sEpisodeTitle = aEpisode.get('title', 'Episode ' + sEpisodeNum)
            
            sTitle = '%s S%sE%s' % (sMovieTitle, sSeason.zfill(2), sEpisodeNum.zfill(2))
            sDisplayTitle = '%s - %s' % (sTitle, sEpisodeTitle)
            
            # URL de l'API Frembed avec saison et épisode
            sEpisodeUrl = sUrl.replace('serie.php?id=', 'serie.php?id=') + '&sa=' + sSeason + '&epi=' + sEpisodeNum
            
            oOutputParameterHandler.addParameter('siteUrl', sEpisodeUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
            oOutputParameterHandler.addParameter('sSeason', sSeason)
            oOutputParameterHandler.addParameter('sEpisode', sEpisodeNum)
            
            oGui.addEpisode(SITE_IDENTIFIER, 'showHosters', sDisplayTitle, '', sThumb, '', oOutputParameterHandler)
    
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

# -*- coding: utf-8 -*-
# fStream - Frembed
# Source: https://frembed.life

from resources.lib.gui.hoster import cHosterGui
from resources.lib.gui.gui import cGui
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.comaddon import progress, VSlog, addon, siteManager
from resources.lib.parser import cParser
from resources.lib.util import cUtil
from resources.lib.tmdb import cTMDb
import re

SITE_IDENTIFIER = 'frembed_life'
SITE_NAME = 'Frembed'
SITE_DESC = 'Films & Séries via Frembed'

# URL de base
URL_MAIN = siteManager().getUrlMain(SITE_IDENTIFIER)

# Menu GLOBALE HOME
MOVIE_MOVIE = (True, 'showMenuMovies')
SERIE_SERIES = (True, 'showMenuSeries')

# Recherche
MY_SEARCH_MOVIES = (True, 'showSearchMovie')
MY_SEARCH_SERIES = (True, 'showSearchSerie')

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
    aResult = oTmdb.getMovieSearch(sSearchText)

    if aResult:
        oOutputParameterHandler = cOutputParameterHandler()
        for aMovie in aResult:
            sTitle = aMovie['title']
            sYear = aMovie['year']
            sId = aMovie['tmdb_id']
            sPoster = aMovie['cover_url']
            sDesc = aMovie['overview']

            sDisplayTitle = '%s (%s)' % (sTitle, sYear)

            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/film.php?tmdb_id=' + str(sId))
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
    aResult = oTmdb.getTvSearch(sSearchText)

    if aResult:
        oOutputParameterHandler = cOutputParameterHandler()
        for aSerie in aResult:
            sTitle = aSerie['title']
            sYear = aSerie['year']
            sId = aSerie['tmdb_id']
            sPoster = aSerie['cover_url']
            sDesc = aSerie['overview']

            sDisplayTitle = '%s (%s)' % (sTitle, sYear)

            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/serie.php?tmdb_id=' + str(sId))
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
        aResult = oTmdb.getMoviePopular()
    elif sType == 'tmdb_top':
        aResult = oTmdb.getMovieTopRated()
    elif sType == 'tmdb_upcoming':
        aResult = oTmdb.getMovieUpcoming()
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

            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/film.php?tmdb_id=' + str(sId))
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sPoster)
            oOutputParameterHandler.addParameter('sTmdbId', str(sId))
            oOutputParameterHandler.addParameter('sYear', sYear)

            oGui.addMovie(SITE_IDENTIFIER, 'showHosters', sDisplayTitle, '', sPoster, sDesc, oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucun résultat')

    oGui.setEndOfDirectory()


def showSeriesFromTMDB():
    """Affiche les séries depuis TMDB"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sType = oInputParameterHandler.getValue('siteUrl')

    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)

    if sType == 'tmdb_popular':
        aResult = oTmdb.getTvPopular()
    elif sType == 'tmdb_top':
        aResult = oTmdb.getTvTopRated()
    elif sType == 'tmdb_airing':
        aResult = oTmdb.getTvAiringToday()
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

            oOutputParameterHandler.addParameter('siteUrl', URL_MAIN + '/api/serie.php?tmdb_id=' + str(sId))
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sPoster)
            oOutputParameterHandler.addParameter('sTmdbId', str(sId))
            oOutputParameterHandler.addParameter('sYear', sYear)

            oGui.addTV(SITE_IDENTIFIER, 'showSeasons', sDisplayTitle, '', sPoster, sDesc, oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucun résultat')

    oGui.setEndOfDirectory()


def showSeasons():
    """Affiche les saisons d'une série"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    sTmdbId = oInputParameterHandler.getValue('sTmdbId')

    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    # Récupérer les infos de la série pour avoir le nombre de saisons
    aSerieInfo = oTmdb.getTvInfo(int(sTmdbId))

    if aSerieInfo and 'seasons' in aSerieInfo:
        nbSeasons = aSerieInfo['seasons']
        oOutputParameterHandler = cOutputParameterHandler()

        for iSeason in range(1, nbSeasons + 1):
            sSeasonTitle = '%s - Saison %d' % (sMovieTitle, iSeason)
            oOutputParameterHandler.addParameter('siteUrl', sUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oOutputParameterHandler.addParameter('sSeason', str(iSeason))
            oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
            oGui.addSeason(SITE_IDENTIFIER, 'showEpisodes', sSeasonTitle, '', sThumb, '', oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucune saison trouvée')

    oGui.setEndOfDirectory()


def showEpisodes():
    """Affiche les épisodes d'une saison"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    sSeason = oInputParameterHandler.getValue('sSeason')
    sTmdbId = oInputParameterHandler.getValue('sTmdbId')

    oTmdb = cTMDb(SITE_IDENTIFIER, SITE_NAME)
    aEpisodes = oTmdb.getTvEpisodes(int(sTmdbId), int(sSeason))

    if aEpisodes:
        oOutputParameterHandler = cOutputParameterHandler()
        for aEpisode in aEpisodes:
            iEpNumber = aEpisode.get('episode_number', 0)
            sEpName = aEpisode.get('name', '')

            sEpisodeTitle = '%s S%02dE%02d' % (sMovieTitle, int(sSeason), iEpNumber)
            if sEpName:
                sEpisodeTitle += ' - ' + sEpName

            oOutputParameterHandler.addParameter('siteUrl', sUrl + '&season=%s&episode=%d' % (sSeason, iEpNumber))
            oOutputParameterHandler.addParameter('sMovieTitle', sEpisodeTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oGui.addEpisode(SITE_IDENTIFIER, 'showHosters', sEpisodeTitle, '', sThumb, '', oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucun épisode trouvé')

    oGui.setEndOfDirectory()


def showHosters():
    """Récupère les liens Frembed"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')

    VSlog('Frembed - showHosters URL: ' + sUrl)

    oRequestHandler = cRequestHandler(sUrl)
    oRequestHandler.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    oRequestHandler.addHeaderEntry('Referer', URL_MAIN)

    try:
        sHtmlContent = oRequestHandler.request()
    except Exception as e:
        VSlog('Frembed - Erreur requête: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors de la récupération du lien')
        oGui.setEndOfDirectory()
        return

    if not sHtmlContent:
        oGui.addText(SITE_IDENTIFIER, 'Lien Frembed non disponible')
        oGui.setEndOfDirectory()
        return

    VSlog('Frembed - Contenu HTML reçu: ' + str(len(sHtmlContent)) + ' caractères')

    oParser = cParser()
    patterns = [
        '<iframe[^>]+src=[\'"]([^\'"]+)[\'"]',
        '"file":"([^"]+)"',
        '"url":"([^"]+)"',
        'file:[\'"]([^\'"]+)[\'"]',
        'source:[\'"]([^\'"]+)[\'"]'
    ]

    sHosterUrl = None
    for pattern in patterns:
        aResult = oParser.parse(sHtmlContent, pattern)
        if aResult[0] and aResult[1]:
            sHosterUrl = aResult[1][0]
            # Nettoyer l'URL
            sHosterUrl = sHosterUrl.replace('\\/', '/')
            VSlog('Frembed - URL trouvée: ' + sHosterUrl)
            break

    if sHosterUrl:
        # Vérifier si c'est un hoster connu
        oHoster = cHosterGui().checkHoster(sHosterUrl)
        if oHoster:
            oHoster.setDisplayName(sMovieTitle)
            oHoster.setFileName(sMovieTitle)
            cHosterGui().showHoster(oGui, oHoster, sHosterUrl, sThumb)
        else:
            # Lien direct
            oOutputParameterHandler = cOutputParameterHandler()
            oOutputParameterHandler.addParameter('siteUrl', sHosterUrl)
            oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oGui.addLink(SITE_IDENTIFIER, 'playVideo', sMovieTitle + ' [Frembed]', sThumb, '', oOutputParameterHandler)
    else:
        oGui.addText(SITE_IDENTIFIER, 'Aucun lien vidéo trouvé')

    oGui.setEndOfDirectory()


def playVideo():
    """Lance la lecture"""
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')

    VSlog('Frembed - Lecture: ' + sUrl)

    if sUrl.startswith('http'):
        # Vérifier à nouveau si c'est un hoster
        oHoster = cHosterGui().checkHoster(sUrl)
        if oHoster:
            oHoster.setDisplayName(sMovieTitle)
            oHoster.setFileName(sMovieTitle)
            cHosterGui().showHoster(oGui, oHoster, sUrl, sThumb)
        else:
            # Lecture directe
            from resources.lib.player import cPlayer
            oPlayer = cPlayer()
            oPlayer.run(sUrl, sMovieTitle, sThumb)
    else:
        oGui.addText(SITE_IDENTIFIER, 'URL invalide')

    oGui.setEndOfDirectory()
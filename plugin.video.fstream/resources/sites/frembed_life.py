# -*- coding: utf-8 -*-
# fStream - Frembed.life
# Source: https://frembed.life / https://frembed.fun

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
SITE_DESC = 'Films & Séries en Streaming'

# API Frembed
API_URL = 'https://frembed.life'
MOVIE_API = API_URL + '/api/film.php?id='  # + tmdb_id
SERIE_API = API_URL + '/api/serie.php?id='  # + tmdb_id&sa=season&epi=episode


def load():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', 'movies')
    oGui.addDir(SITE_IDENTIFIER, 'showMovies', 'Films', 'films.png', oOutputParameterHandler)
    
    oOutputParameterHandler.addParameter('siteUrl', 'series')
    oGui.addDir(SITE_IDENTIFIER, 'showSeries', 'Séries', 'series.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showMovies():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', API_URL + '/api/movies?order=latest&limit=50')
    oGui.addDir(SITE_IDENTIFIER, 'showMoviesList', 'Derniers Films Ajoutés', 'news.png', oOutputParameterHandler)
    
    oOutputParameterHandler.addParameter('siteUrl', API_URL + '/api/movies?order=update&limit=50')
    oGui.addDir(SITE_IDENTIFIER, 'showMoviesList', 'Dernières MAJ Films', 'update.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showSeries():
    oGui = cGui()
    
    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', API_URL + '/api/tv?order=latest&limit=50')
    oGui.addDir(SITE_IDENTIFIER, 'showSeriesList', 'Dernières Séries Ajoutées', 'news.png', oOutputParameterHandler)
    
    oOutputParameterHandler.addParameter('siteUrl', API_URL + '/api/tv?order=update&limit=50')
    oGui.addDir(SITE_IDENTIFIER, 'showSeriesList', 'Dernières MAJ Séries', 'update.png', oOutputParameterHandler)
    
    oGui.setEndOfDirectory()


def showMoviesList(sSearch=''):
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    
    if sSearch:
        # Recherche par TMDB ID ou titre
        sUrl = API_URL + '/api/movies?search=' + sSearch
    
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()
    
    if not sHtmlContent:
        oGui.addText(SITE_IDENTIFIER, 'Aucun résultat')
        oGui.setEndOfDirectory()
        return
    
    # Parser la réponse JSON
    try:
        import json
        data = json.loads(sHtmlContent)
        
        if 'data' in data and data['data']:
            movies = data['data']
            
            for movie in movies:
                sTitle = movie.get('title', 'Film')
                sTmdbId = str(movie.get('tmdb_id', ''))
                sYear = str(movie.get('year', ''))
                sPoster = movie.get('poster', '')
                sDesc = movie.get('overview', '')
                
                if not sTmdbId:
                    continue
                
                # Construire le titre avec l'année
                if sYear:
                    sDisplayTitle = sTitle + ' (' + sYear + ')'
                else:
                    sDisplayTitle = sTitle
                
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('siteUrl', MOVIE_API + sTmdbId)
                oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
                oOutputParameterHandler.addParameter('sThumb', sPoster)
                oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
                oOutputParameterHandler.addParameter('sYear', sYear)
                
                oGui.addMovie(SITE_IDENTIFIER, 'showHosters', sDisplayTitle, 'films.png', sPoster, sDesc, oOutputParameterHandler)
        
        # Pagination
        if 'current_page' in data and 'last_page' in data:
            current = int(data['current_page'])
            last = int(data['last_page'])
            
            if current < last:
                oOutputParameterHandler = cOutputParameterHandler()
                next_url = sUrl.split('&page=')[0] + '&page=' + str(current + 1)
                oOutputParameterHandler.addParameter('siteUrl', next_url)
                oGui.addNext(SITE_IDENTIFIER, 'showMoviesList', 'Page ' + str(current + 1), oOutputParameterHandler)
    
    except Exception as e:
        VSlog('Frembed - Erreur parsing JSON: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors du chargement')
    
    oGui.setEndOfDirectory()


def showSeriesList(sSearch=''):
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    
    if sSearch:
        sUrl = API_URL + '/api/tv?search=' + sSearch
    
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()
    
    if not sHtmlContent:
        oGui.addText(SITE_IDENTIFIER, 'Aucun résultat')
        oGui.setEndOfDirectory()
        return
    
    try:
        import json
        data = json.loads(sHtmlContent)
        
        if 'data' in data and data['data']:
            series = data['data']
            
            for serie in series:
                sTitle = serie.get('title', 'Série')
                sTmdbId = str(serie.get('tmdb_id', ''))
                sYear = str(serie.get('year', ''))
                sPoster = serie.get('poster', '')
                sDesc = serie.get('overview', '')
                
                if not sTmdbId:
                    continue
                
                if sYear:
                    sDisplayTitle = sTitle + ' (' + sYear + ')'
                else:
                    sDisplayTitle = sTitle
                
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('siteUrl', API_URL + '/api/tv/' + sTmdbId)
                oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
                oOutputParameterHandler.addParameter('sThumb', sPoster)
                oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
                oOutputParameterHandler.addParameter('sYear', sYear)
                
                oGui.addTV(SITE_IDENTIFIER, 'showSeasons', sDisplayTitle, 'series.png', sPoster, sDesc, oOutputParameterHandler)
        
        # Pagination
        if 'current_page' in data and 'last_page' in data:
            current = int(data['current_page'])
            last = int(data['last_page'])
            
            if current < last:
                oOutputParameterHandler = cOutputParameterHandler()
                next_url = sUrl.split('&page=')[0] + '&page=' + str(current + 1)
                oOutputParameterHandler.addParameter('siteUrl', next_url)
                oGui.addNext(SITE_IDENTIFIER, 'showSeriesList', 'Page ' + str(current + 1), oOutputParameterHandler)
    
    except Exception as e:
        VSlog('Frembed - Erreur parsing JSON: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors du chargement')
    
    oGui.setEndOfDirectory()


def showSeasons():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sTmdbId = oInputParameterHandler.getValue('sTmdbId')
    sThumb = oInputParameterHandler.getValue('sThumb')
    
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()
    
    if not sHtmlContent:
        oGui.addText(SITE_IDENTIFIER, 'Aucune saison trouvée')
        oGui.setEndOfDirectory()
        return
    
    try:
        import json
        data = json.loads(sHtmlContent)
        
        if 'seasons' in data:
            seasons = data['seasons']
            
            for season in seasons:
                season_num = season.get('season_number', 0)
                episode_count = season.get('episode_count', 0)
                
                if season_num == 0:  # Ignorer les "Specials"
                    continue
                
                sTitle = 'Saison ' + str(season_num) + ' (' + str(episode_count) + ' épisodes)'
                
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('siteUrl', API_URL + '/api/tv/' + sTmdbId + '/season/' + str(season_num))
                oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle)
                oOutputParameterHandler.addParameter('sThumb', sThumb)
                oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
                oOutputParameterHandler.addParameter('sSeason', str(season_num))
                
                oGui.addSeason(SITE_IDENTIFIER, 'showEpisodes', sTitle, 'series.png', sThumb, '', oOutputParameterHandler)
    
    except Exception as e:
        VSlog('Frembed - Erreur parsing saisons: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors du chargement des saisons')
    
    oGui.setEndOfDirectory()


def showEpisodes():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sTmdbId = oInputParameterHandler.getValue('sTmdbId')
    sSeason = oInputParameterHandler.getValue('sSeason')
    sThumb = oInputParameterHandler.getValue('sThumb')
    
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()
    
    if not sHtmlContent:
        oGui.addText(SITE_IDENTIFIER, 'Aucun épisode trouvé')
        oGui.setEndOfDirectory()
        return
    
    try:
        import json
        data = json.loads(sHtmlContent)
        
        if 'episodes' in data:
            episodes = data['episodes']
            
            for episode in episodes:
                ep_num = episode.get('episode_number', 0)
                ep_title = episode.get('name', 'Episode ' + str(ep_num))
                
                sTitle = 'S' + sSeason.zfill(2) + 'E' + str(ep_num).zfill(2) + ' - ' + ep_title
                
                # URL de l'API pour cet épisode
                sEpisodeUrl = SERIE_API + sTmdbId + '&sa=' + sSeason + '&epi=' + str(ep_num)
                
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('siteUrl', sEpisodeUrl)
                oOutputParameterHandler.addParameter('sMovieTitle', sMovieTitle + ' ' + sTitle)
                oOutputParameterHandler.addParameter('sThumb', sThumb)
                oOutputParameterHandler.addParameter('sTmdbId', sTmdbId)
                oOutputParameterHandler.addParameter('sSeason', sSeason)
                oOutputParameterHandler.addParameter('sEpisode', str(ep_num))
                
                oGui.addEpisode(SITE_IDENTIFIER, 'showHosters', sTitle, 'series.png', sThumb, '', oOutputParameterHandler)
    
    except Exception as e:
        VSlog('Frembed - Erreur parsing épisodes: ' + str(e))
        oGui.addText(SITE_IDENTIFIER, 'Erreur lors du chargement des épisodes')
    
    oGui.setEndOfDirectory()


def showHosters():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    
    # L'URL de l'API Frembed retourne directement un lecteur embed
    # On peut essayer de récupérer le lien direct ou utiliser l'iframe
    
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
    
    # L'API Frembed retourne une page avec un player embed
    # On doit extraire le vrai lien de streaming
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()
    
    if not sHtmlContent:
        oGui.addText(SITE_IDENTIFIER, 'Impossible de charger la vidéo')
        oGui.setEndOfDirectory()
        return
    
    # Extraire l'iframe ou le lien direct
    oParser = cParser()
    
    # Chercher les patterns communs de liens de streaming
    patterns = [
        '<iframe[^>]+src=["\']([^"\']+)["\']',
        'file:["\']([^"\']+)["\']',
        'source:["\']([^"\']+)["\']',
        'src=["\']([^"\']+\.m3u8[^"\']*)["\']',
        'src=["\']([^"\']+\.mp4[^"\']*)["\']'
    ]
    
    aResult = None
    for pattern in patterns:
        aResult = oParser.parse(sHtmlContent, pattern)
        if aResult[0]:
            break
    
    if aResult and aResult[0]:
        stream_url = aResult[1][0]
        
        # Si c'est un lien relatif, le compléter
        if stream_url.startswith('//'):
            stream_url = 'https:' + stream_url
        elif stream_url.startswith('/'):
            stream_url = API_URL + stream_url
        
        VSlog('Frembed - Stream URL: ' + stream_url)
        
        # Vérifier si c'est un hoster connu
        oHoster = cHosterGui().checkHoster(stream_url)
        if oHoster:
            oHoster.setDisplayName(sMovieTitle)
            oHoster.setFileName(sMovieTitle)
            cHosterGui().showHoster(oGui, oHoster, stream_url, sThumb)
        else:
            # Essayer de lire directement
            from resources.lib.player import cPlayer
            oPlayer = cPlayer()
            oPlayer.clearPlayList()
            oPlayer.addItemToPlaylist(stream_url, sMovieTitle, sThumb)
            oPlayer.startPlayer()
    else:
        # Si on ne trouve pas de lien, on peut essayer de charger l'iframe directement
        VSlog('Frembed - Aucun lien trouvé, utilisation de l\'iframe')
        oGui.addText(SITE_IDENTIFIER, 'Lien de streaming non disponible')
    
    oGui.setEndOfDirectory()

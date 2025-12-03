# -*- coding: utf-8 -*-
# fStream https://github.com/Kodi-fStream/lomixx-xbmc-addons
# Venom.
import xbmcaddon
import xbmcgui
import requests
import os
import xbmc
from resources.lib import auth

#addon = xbmcaddon.Addon()

from resources.lib.gui.hoster import cHosterGui
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.search import cSearch
from resources.lib.handler.pluginHandler import cPluginHandler
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.comaddon import addon
from resources.sites.themoviedb_org import SITE_IDENTIFIER as SITE_TMDB
from resources.lib.trakt import SITE_IDENTIFIER as SITE_TRAKT


SITE_IDENTIFIER = 'cHome'
SITE_NAME = 'Home'
IPTV_COUNTRIES = {
    'FR': 'France',
    'US': 'United States',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'IT': 'Italy',
    'ES': 'Spain',
    'CA': 'Canada',
    'AU': 'Australia',
    'BR': 'Brazil',
    'IN': 'India',
    'JP': 'Japan',
    'KR': 'South Korea',
    'CN': 'China',
    'RU': 'Russia',
    'TR': 'Turkey',
    'EG': 'Egypt',
    'SA': 'Saudi Arabia',
    'AE': 'United Arab Emirates',
    'MX': 'Mexico',
    'AR': 'Argentina',
    'CM': 'Cameroon',
    'NG': 'Nigeria',
    'ZA': 'South Africa',
    'CIV': 'Ivory Coast'
}

# ✅ CLASSE DE CACHE SIMPLE
class IPTVCache:
    """Classe simple pour gérer le cache des fichiers M3U"""
    
    @staticmethod
    def get_cache_dir():
        """Retourne le répertoire de cache"""
        cache_dir = xbmc.translatePath('special://temp/fstream_iptv_cache')
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
            except:
                pass
        return cache_dir
    
    @staticmethod
    def get_cached(cache_name):
        """Récupère le contenu du cache s'il existe"""
        try:
            cache_file = os.path.join(IPTVCache.get_cache_dir(), cache_name)
            if os.path.exists(cache_file):
                # Vérifier si le cache a moins de 24h
                import time
                file_time = os.path.getmtime(cache_file)
                current_time = time.time()
                
                # Cache valide pendant 24h (86400 secondes)
                if (current_time - file_time) < 86400:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return f.read()
            return None
        except Exception as e:
            from resources.lib.comaddon import VSlog
            VSlog(f"[CACHE] Erreur lecture cache: {str(e)}")
            return None
    
    @staticmethod
    def save_cache(cache_name, data):
        """Sauvegarde le contenu dans le cache"""
        try:
            cache_file = os.path.join(IPTVCache.get_cache_dir(), cache_name)
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(data)
            from resources.lib.comaddon import VSlog
            VSlog(f"[CACHE] Cache sauvegardé: {cache_name}")
        except Exception as e:
            from resources.lib.comaddon import VSlog
            VSlog(f"[CACHE] Erreur sauvegarde cache: {str(e)}")


# ✅ Fonctions utilitaires
def getCountryM3U(country_code):
    """Retourne l'URL du fichier M3U pour un pays donné"""
    return [f"https://iptv-org.github.io/iptv/countries/{country_code.lower()}.m3u"]


def loadM3U(urls, cache_name):
    """Charge le contenu M3U depuis les URLs ou le cache"""
    from resources.lib.comaddon import VSlog
    
    # Essayer de charger depuis le cache
    data = IPTVCache.get_cached(cache_name)
    
    if data is not None:
        VSlog(f"[M3U] Chargé depuis le cache: {cache_name}")
        return data

    # Sinon télécharger
    VSlog(f"[M3U] Téléchargement depuis les URLs...")
    data = ""
    for url in urls:
        try:
            VSlog(f"[M3U] Téléchargement: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data += response.text + "\n"
            VSlog(f"[M3U] Téléchargé: {len(response.text)} caractères")
        except Exception as e:
            VSlog(f"[M3U] Erreur téléchargement {url}: {str(e)}")
            continue

    # Sauvegarder dans le cache si on a des données
    if data:
        IPTVCache.save_cache(cache_name, data)
    
    return data


def extractCountriesFromAPI():
    """Récupère la liste de tous les pays disponibles sur iptv-org"""
    from resources.lib.comaddon import VSlog
    import requests
    
    try:
        # L'API iptv-org fournit un index des pays
        url = "https://iptv-org.github.io/iptv/countries.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        countries_data = response.json()
        VSlog(f"[IPTV] {len(countries_data)} pays trouvés")
        
        # Retourner un dictionnaire {code: name}
        countries = {}
        for country in countries_data:
            code = country.get('code', '').upper()
            name = country.get('name', '')
            if code and name:
                countries[code] = name
        
        return countries
        
    except Exception as e:
        VSlog(f"[IPTV] Erreur récupération pays: {str(e)}")
        # Fallback sur la liste statique
        return IPTV_COUNTRIES


def parseAndShowM3U(oGui, data, show_categories=True, show_by='category'):
    """
    Parse le contenu M3U et affiche selon le mode choisi
    show_by: 'category' ou 'country'
    """
    import re
    from resources.lib.comaddon import VSlog
    
    if not data:
        VSlog("[M3U] Aucune donnée à parser")
        oGui.addText('fStream', 'Aucune chaîne trouvée')
        return

    VSlog(f"[M3U] Parsing de {len(data)} caractères, mode: {show_by}")
    
    # Dictionnaires pour regrouper
    categories = {}
    countries = {}
    all_channels = []
    
    # Parser ligne par ligne
    lines = data.split('\n')
    i = 0
    total_parsed = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            try:
                # ===== EXTRACTION DU TITRE =====
                # Méthode 1: Chercher tvg-name
                name_match = re.search(r'tvg-name="([^"]+)"', line)
                title = name_match.group(1) if name_match else None
                
                # Méthode 2: Texte après la virgule (le plus courant)
                if not title or len(title.strip()) == 0:
                    comma_parts = line.split(',', 1)
                    if len(comma_parts) > 1:
                        # Nettoyer le titre (enlever les attributs avant)
                        potential_title = comma_parts[1].strip()
                        # Enlever les éventuels attributs qui traînent
                        potential_title = re.sub(r'^.*?\s+([A-Za-z0-9])', r'\1', potential_title)
                        if potential_title and len(potential_title) > 0:
                            title = potential_title
                
                # Méthode 3: tvg-id peut parfois donner un indice
                if not title or len(title.strip()) == 0:
                    id_match = re.search(r'tvg-id="([^"]+)"', line)
                    if id_match:
                        title = id_match.group(1).replace('.', ' ').replace('-', ' ')
                
                # Si vraiment rien trouvé
                if not title or len(title.strip()) == 0:
                    title = "Chaîne"
                
                # ===== EXTRACTION DES AUTRES INFOS =====
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                group_match = re.search(r'group-title="([^"]*)"', line)
                country_match = re.search(r'tvg-country="([^"]*)"', line)
                
                # Chercher l'URL dans les lignes suivantes
                stream_url = None
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#'):
                        if next_line.startswith('http'):
                            stream_url = next_line
                            break
                    j += 1
                
                if stream_url and title:
                    logo = logo_match.group(1) if logo_match else "tv.png"
                    category = group_match.group(1) if group_match else "Général"
                    country = country_match.group(1) if country_match else "International"
                    
                    # Nettoyer le titre
                    title = title.replace('[', '').replace(']', '').strip()
                    # Enlever les balises HTML éventuelles
                    title = re.sub(r'<[^>]+>', '', title)
                    # Limiter la longueur si trop long
                    if len(title) > 60:
                        title = title[:57] + "..."
                    
                    # Créer l'objet chaîne
                    channel = {
                        'title': title,
                        'url': stream_url,
                        'logo': logo,
                        'category': category,
                        'country': country
                    }
                    
                    # Grouper par catégorie
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(channel)
                    
                    # Grouper par pays
                    if country not in countries:
                        countries[country] = []
                    countries[country].append(channel)

                    # Liste globale
                    all_channels.append(channel)
                    
                    total_parsed += 1
                    
                    if total_parsed <= 5:  # Debug: afficher les 5 premières
                        VSlog(f"[M3U] Chaîne: '{title}' | Catégorie: {category} | Pays: {country}")
                    
            except Exception as e:
                VSlog(f"[M3U] Erreur parsing ligne {i}: {str(e)}")
        
        i += 1
    
    VSlog(f"[M3U] Total parsé: {total_parsed} chaînes")
    VSlog(f"[M3U] {len(categories)} catégories, {len(countries)} pays")
    
    # Affichage selon le mode
    if show_by == 'category':
        if categories:
            sorted_categories = sorted(categories.keys())
            for category in sorted_categories:
                channel_count = len(categories[category])
                
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('filter_type', 'category')
                oOutputParameterHandler.addParameter('filter_value', category)
                oOutputParameterHandler.addParameter('m3u_data', data)
                
                icon = get_category_icon(category)
                
                oGui.addDir(
                    SITE_IDENTIFIER, 
                    'showIPTV_Filtered', 
                    f"{category} ({channel_count})", 
                    icon, 
                    oOutputParameterHandler
                )
        else:
            oGui.addText('fStream', 'Aucune catégorie trouvée')
            
    elif show_by == 'country':
        if countries:
            sorted_countries = sorted(countries.keys())
            for country in sorted_countries:
                channel_count = len(countries[country])
                
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('filter_type', 'country')
                oOutputParameterHandler.addParameter('filter_value', country)
                oOutputParameterHandler.addParameter('m3u_data', data)
                
                # Essayer de trouver le code pays pour l'icône
                country_code = get_country_code(country)
                icon = f"{country_code.lower()}.png" if country_code else "tv.png"
                
                oGui.addDir(
                    SITE_IDENTIFIER, 
                    'showIPTV_Filtered', 
                    f"{country} ({channel_count})", 
                    icon, 
                    oOutputParameterHandler
                )
        else:
            oGui.addText('fStream', 'Aucun pays trouvé')
    elif show_by == 'all':
        # Afficher toutes les chaînes
        for channel in all_channels:
            oOutputParameterHandler = cOutputParameterHandler()
            oOutputParameterHandler.addParameter('siteUrl', channel['url'])
            oOutputParameterHandler.addParameter('sMovieTitle', channel['title'])
            oOutputParameterHandler.addParameter('sThumb', channel['logo'])
            
            oGui.addLink(
                SITE_IDENTIFIER, 
                'playIPTV', 
                channel['title'], 
                channel['logo'], 
                '', 
                oOutputParameterHandler
            )
        
        if len(all_channels) == 0:
            oGui.addText('fStream', 'Aucune chaîne trouvée')
            

def parseAndShowChannels(oGui, data, filter_type, filter_value):
    """Affiche les chaînes filtrées par catégorie ou pays"""
    import re
    from resources.lib.comaddon import VSlog
    
    if not data:
        VSlog("[M3U] Aucune donnée à parser")
        oGui.addText('fStream', 'Aucune chaîne trouvée')
        return
    
    VSlog(f"[M3U] Filtrage par {filter_type}: {filter_value}")
    
    lines = data.split('\n')
    i = 0
    count = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF'):
            try:
                # Extraire les métadonnées
                group_match = re.search(r'group-title="([^"]*)"', line)
                country_match = re.search(r'tvg-country="([^"]*)"', line)
                
                category = group_match.group(1) if group_match else "Général"
                country = country_match.group(1) if country_match else "International"
                
                # Vérifier si correspond au filtre
                match = False
                if filter_type == 'category' and category == filter_value:
                    match = True
                elif filter_type == 'country' and country == filter_value:
                    match = True
                
                if match:
                    # Extraire le titre (même logique améliorée)
                    name_match = re.search(r'tvg-name="([^"]+)"', line)
                    title = name_match.group(1) if name_match else None
                    
                    if not title or len(title.strip()) == 0:
                        comma_parts = line.split(',', 1)
                        if len(comma_parts) > 1:
                            title = comma_parts[1].strip()
                            title = re.sub(r'^.*?\s+([A-Za-z0-9])', r'\1', title)
                    
                    if not title or len(title.strip()) == 0:
                        id_match = re.search(r'tvg-id="([^"]+)"', line)
                        if id_match:
                            title = id_match.group(1).replace('.', ' ').replace('-', ' ')
                    
                    if not title or len(title.strip()) == 0:
                        title = f"Chaîne {count + 1}"
                    
                    # Extraire logo et URL
                    logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                    
                    stream_url = None
                    j = i + 1
                    while j < len(lines) and j < i + 5:
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith('#'):
                            if next_line.startswith('http'):
                                stream_url = next_line
                                break
                        j += 1
                    
                    if stream_url:
                        logo = logo_match.group(1) if logo_match else "tv.png"
                        title = title.replace('[', '').replace(']', '').strip()
                        title = re.sub(r'<[^>]+>', '', title)
                        
                        if len(title) > 60:
                            title = title[:57] + "..."
                        
                        oOutputParameterHandler = cOutputParameterHandler()
                        oOutputParameterHandler.addParameter('siteUrl', stream_url)
                        oOutputParameterHandler.addParameter('sMovieTitle', title)
                        oOutputParameterHandler.addParameter('sThumb', logo)
                        
                        oGui.addLink(
                            SITE_IDENTIFIER, 
                            'playIPTV', 
                            title, 
                            logo, 
                            '', 
                            oOutputParameterHandler
                        )
                        count += 1
                        
            except Exception as e:
                VSlog(f"[M3U] Erreur parsing: {str(e)}")
        
        i += 1
    
    VSlog(f"[M3U] {count} chaînes affichées")
    
    if count == 0:
        oGui.addText('fStream', f'Aucune chaîne trouvée')


def get_country_code(country_name):
    """Essaie de trouver le code pays depuis le nom"""
    # Mapping inversé
    for code, name in IPTV_COUNTRIES.items():
        if name.lower() == country_name.lower():
            return code
    
    # Codes courants
    common_codes = {
        'france': 'FR', 'united states': 'US', 'usa': 'US',
        'united kingdom': 'GB', 'uk': 'GB', 'germany': 'DE',
        'italy': 'IT', 'spain': 'ES', 'canada': 'CA',
        'international': 'WORLD'
    }
    
    return common_codes.get(country_name.lower(), None)


def get_category_icon(category):
    """Retourne une icône appropriée selon la catégorie"""
    category_lower = category.lower()
    
    icon_map = {
        'news': 'news.png',
        'sport': 'sport.png',
        'entertainment': 'vod.png',
        'movies': 'films.png',
        'films': 'films.png',
        'series': 'series.png',
        'documentary': 'doc.png',
        'kids': 'enfants.png',
        'music': 'genres.png',
        'general': 'tv.png',
        'information': 'news.png',
        'divertissement': 'vod.png',
        'enfants': 'enfants.png',
        'musique': 'genres.png',
    }
    
    for key, icon in icon_map.items():
        if key in category_lower:
            return icon
    
    return 'tv.png'


class cHome:

    addons = addon()

    def loginScreen(self):
        oGui = cGui()

        oGui.addText('Fstream', 'Veuillez vous connecter')

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('function', 'doLogin')

        oGui.addDir(SITE_IDENTIFIER, 'doLogin', 'Se connecter', 'login.png', oOutputParameterHandler)
        oGui.setEndOfDirectory()
   
    def doLogin(self):
        """
        Tente une connexion avec les identifiants sauvegardés dans les paramètres
        """
        from resources.lib.comaddon import VSlog
    
        VSlog("[HOME] Fonction doLogin() appelée")
    
        # Récupération des identifiants depuis settings.xml
        email = self.addons.getSetting("auth_username")
        password = self.addons.getSetting("auth_password")
    
        VSlog(f"[HOME] Email récupéré : {email}")
        VSlog(f"[HOME] Password présent : {bool(password)}")
    
        # Vérification que les champs ne sont pas vides
        if not email or not password:
            VSlog("[HOME] Identifiants manquants")
            xbmcgui.Dialog().ok("Fstream", "Veuillez entrer votre email et mot de passe dans les paramètres")
            self.addons.openSettings()
            return
    
        # Tentative de connexion (login retourne un tuple: success, message)
        VSlog("[HOME] Appel de auth.login()...")
        success, message = auth.login(email, password)
    
        VSlog(f"[HOME] Résultat login : success={success}, message={message}")
    
        if success:
            VSlog("[HOME] Login réussi, rechargement de l'interface")
            xbmcgui.Dialog().ok("Fstream", "Connexion réussie !")
            # Rafraîchir l'interface
            self.load()
        else:
            VSlog(f"[HOME] Login échoué : {message}")
            # Afficher l'erreur retournée par l'API
            xbmcgui.Dialog().ok("Fstream", f"Erreur de connexion :\n{message}")
            

    def doLogout(self):
        auth.logout()
        xbmcgui.Dialog().ok("Fstream", "Déconnecté")
        self.loginScreen()

    def load(self):
        oGui = cGui()
        token = auth.get_token()

        if not token:
            self.loginScreen()
            return
        
        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(SITE_IDENTIFIER, 'doLogout', '[Déconnexion]', 'logout.png', oOutputParameterHandler)
        oGui.addDir(SITE_IDENTIFIER, 'showVOD', self.addons.VSlang(30131), 'vod.png')
        oGui.addDir(SITE_IDENTIFIER, 'showDirect', self.addons.VSlang(30132), 'direct.png')
        oGui.addDir(SITE_IDENTIFIER, 'showReplay', self.addons.VSlang(30350), 'replay.png')
        oGui.addDir(SITE_IDENTIFIER, 'showMyVideos', self.addons.VSlang(30130), 'profile.png')
        oGui.addDir(SITE_IDENTIFIER, 'showTools', self.addons.VSlang(30033), 'tools.png')

        view = False
        if self.addons.getSetting('active-view') == 'true':
            view = self.addons.getSetting('accueil-view')

        oGui.setEndOfDirectory(view)

    def showVOD(self):
        oGui = cGui()
        oGui.addDir(SITE_IDENTIFIER, 'showMovies', self.addons.VSlang(30120), 'films.png')
        oGui.addDir(SITE_IDENTIFIER, 'showSeries', self.addons.VSlang(30121), 'series.png')
        oGui.addDir(SITE_IDENTIFIER, 'showAnimes', self.addons.VSlang(30122), 'animes.png')
        oGui.addDir(SITE_IDENTIFIER, 'showDocs', self.addons.VSlang(30112), 'doc.png')
        oGui.addDir(SITE_IDENTIFIER, 'showDramas', self.addons.VSlang(30124), 'dramas.png')
        oGui.addDir(SITE_TMDB, 'showMenuActeur', self.addons.VSlang(30466), 'actor.png')
        oGui.addDir(SITE_IDENTIFIER, 'showMenuSearch', self.addons.VSlang(30135), 'search_direct.png')

        # ininteressant
        # oOutputParameterHandler.addParameter('siteUrl', 'http://lomixx')
        # oGui.addDir(SITE_IDENTIFIER, 'showNets', self.addons.VSlang(30114), 'buzz.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showMyVideos(self):
        oGui = cGui()
        oGui.addDir('cFav', 'getBookmarks', self.addons.VSlang(30207), 'mark.png')
        oGui.addDir('cViewing', 'showMenu', self.addons.VSlang(30125), 'vod.png')
        oGui.addDir('cWatched', 'showMenu', self.addons.VSlang(30321), 'annees.png')
        oGui.addDir(SITE_IDENTIFIER, 'showUsers', self.addons.VSlang(30455), 'profile.png')
        oGui.addDir('cDownload', 'getDownloadList', self.addons.VSlang(30229), 'download.png')

        # les enregistrements de chaines TV ne sont plus opérationnelles
        # folder = self.addons.getSetting('path_enregistrement')
        # if not folder:
        #     folder = 'special://userdata/addon_data/plugin.video.fstream/Enregistrement"/>'
        # oOutputParameterHandler.addParameter('siteUrl', folder)
        # oGui.addDir('cLibrary', 'openLibrary', self.addons.VSlang(30225), 'download.png', oOutputParameterHandler)

        oGui.addDir('globalSources', 'activeSources', self.addons.VSlang(30362), 'host.png')
        oGui.setEndOfDirectory()

    def showMenuSearch(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()

        # oOutputParameterHandler.addParameter('siteUrl', 'http://lomixx')
        # oGui.addDir('themoviedb_org', 'load', self.addons.VSlang(30088), 'searchtmdb.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('sCat', '1')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30120), 'search-films.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('sCat', '2')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30121), 'search-series.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('sCat', '3')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30122), 'search-animes.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('sCat', '9')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30124), 'search-dramas.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('sCat', '5')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30112), 'search-divers.png', oOutputParameterHandler)

        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('siteUrl', 'http://Lomixxx')
            oGui.addDir('cHome', 'showHistory', self.addons.VSlang(30308), 'history.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showMovieSearch(self):
        oGui = cGui()
        addons = self.addons
    
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', 'search/movie')
        oGui.addDir(SITE_TMDB, 'showSearchMovie', addons.VSlang(30120), 'search-films.png', oOutputParameterHandler)
    
        oOutputParameterHandler.addParameter('siteUrl', 'search/movie')
        oGui.addDir(SITE_TMDB, 'showSearchSaga', addons.VSlang(30139), 'search-sagas.png', oOutputParameterHandler)
    
        # Chercher une liste Trakt
        oOutputParameterHandler.addParameter('sCat', '1')
        oGui.addDir(SITE_TRAKT, 'showSearchList', addons.VSlang(30123), 'search-list.png', oOutputParameterHandler)

        # recherche acteurs
        oOutputParameterHandler.addParameter('siteUrl', 'search/person')
        oGui.addDir(SITE_TMDB, 'showSearchActor', addons.VSlang(30466), 'search-actor.png', oOutputParameterHandler)

        if addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('sCat', '1')
            oGui.addDir(SITE_IDENTIFIER, 'showHistory', addons.VSlang(30308), 'history.png', oOutputParameterHandler)
    
        oGui.setEndOfDirectory()


    def showSeriesSearch(self):
        oGui = cGui()
        addons = self.addons
    
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', 'search/tv')
        oGui.addDir(SITE_TMDB, 'showSearchSerie', addons.VSlang(30121), 'search-series.png', oOutputParameterHandler)
    
            # Chercher une liste
        oOutputParameterHandler.addParameter('sCat', '2')
        oGui.addDir(SITE_TRAKT, 'showSearchList', addons.VSlang(30123), 'search-list.png', oOutputParameterHandler)
        
        if addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('sCat', '2')
            oGui.addDir(SITE_IDENTIFIER, 'showHistory', addons.VSlang(30308), 'history.png', oOutputParameterHandler)
    
        oGui.setEndOfDirectory()


    def showAnimesSearch(self):
        oGui = cGui()
        oOutputParameterHandler = cOutputParameterHandler()

        # recherche directe
        oOutputParameterHandler.addParameter('sCat', '3')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search-animes.png', oOutputParameterHandler)
    
        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('sCat', '3')
            oGui.addDir(SITE_IDENTIFIER, 'showHistory', self.addons.VSlang(30308), 'history.png', oOutputParameterHandler)
    
    
        oGui.setEndOfDirectory()

    def showDramasSearch(self):
        oGui = cGui()
        oOutputParameterHandler = cOutputParameterHandler()

        # recherche directe
        oOutputParameterHandler.addParameter('sCat', '9')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search-dramas.png', oOutputParameterHandler)
    
        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('sCat', '9')
            oGui.addDir(SITE_IDENTIFIER, 'showHistory', self.addons.VSlang(30308), 'history.png', oOutputParameterHandler)
    
        oGui.setEndOfDirectory()

    def showDocsSearch(self):
        oGui = cGui()
        oOutputParameterHandler = cOutputParameterHandler()

        # recherche directe
        oOutputParameterHandler.addParameter('sCat', '5')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search-divers.png', oOutputParameterHandler)
    
        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('sCat', '5')
            oGui.addDir(SITE_IDENTIFIER, 'showHistory', self.addons.VSlang(30308), 'history.png', oOutputParameterHandler)
    
        oGui.setEndOfDirectory()


    def showSearchText(self):
        oGui = cGui()
        oInputParameterHandler = cInputParameterHandler()
        sSearchText = oGui.showKeyBoard(heading=self.addons.VSlang(30076))
        if not sSearchText:
            return False

        oSearch = cSearch()
        sCat = oInputParameterHandler.getValue('sCat')
        oSearch.searchGlobal(sSearchText, sCat)
        oGui.setEndOfDirectory()

    def showMovies(self):
        oGui = cGui()
        addons = self.addons

        oOutputParameterHandler = cOutputParameterHandler()

        # oOutputParameterHandler.addParameter('sCat', '1')
        # oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30120), 'search.png', oOutputParameterHandler)

#        oOutputParameterHandler.addParameter('siteUrl', 'search/movie')
        oGui.addDir(SITE_IDENTIFIER, 'showMovieSearch', addons.VSlang(30076), 'search.png', oOutputParameterHandler)

        # Nouveautés
        oOutputParameterHandler.addParameter('siteUrl', 'discover/movie')
        oGui.addDir(SITE_TMDB, 'showMoviesNews', addons.VSlang(30101), 'news.png', oOutputParameterHandler)

        # Populaires
        oOutputParameterHandler.addParameter('siteUrl', 'discover/movie')
        oGui.addDir(SITE_TMDB, 'showMovies', addons.VSlang(30102), 'popular.png', oOutputParameterHandler)
        
        # Box office
        oOutputParameterHandler.addParameter('siteUrl', 'movies/boxoffice')
        oOutputParameterHandler.addParameter('sCat', '1')
        oGui.addDir(SITE_TRAKT, 'getTrakt', addons.VSlang(30314), 'boxoffice.png', oOutputParameterHandler)
        
        # Genres
        oOutputParameterHandler.addParameter('siteUrl', 'genre/movie/list')
        oGui.addDir(SITE_TMDB, 'showGenreMovie', addons.VSlang(30105), 'genres.png', oOutputParameterHandler)
        
        # Années
        oOutputParameterHandler.addParameter('siteUrl', 'discover/movie')
        oGui.addDir(SITE_TMDB, 'showMoviesYears', self.addons.VSlang(30106), 'annees.png', oOutputParameterHandler)

        # # Top films TMDB
        # oOutputParameterHandler.addParameter('siteUrl', 'discover/movie')
        # oGui.addDir(SITE_TMDB, 'showMoviesTop', addons.VSlang(30104), 'notes.png', oOutputParameterHandler)

        # Top films TRAKT
        oOutputParameterHandler.addParameter('siteUrl', 'movies/popular')
        oOutputParameterHandler.addParameter('sCat', '1')
        oGui.addDir(SITE_TRAKT, 'getTrakt', self.addons.VSlang(30104), 'notes.png', oOutputParameterHandler)


        oOutputParameterHandler.addParameter('siteUrl', 'ANIM_ENFANTS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30109), 'enfants.png', oOutputParameterHandler)

        # oOutputParameterHandler.addParameter('siteUrl', 'MOVIE_VF')
        # oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30120), self.addons.VSlang(30107)), 'vf.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'MOVIE_VOSTFR')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30108), 'vostfr.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'MOVIE_MOVIE')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showSeries(self):
        oGui = cGui()
        addons=self.addons

        oOutputParameterHandler = cOutputParameterHandler()

        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('siteUrl', 'search/tv')
            oGui.addDir(SITE_IDENTIFIER, 'showSeriesSearch', addons.VSlang(30076), 'search.png', oOutputParameterHandler)
        else:
            oOutputParameterHandler.addParameter('siteUrl', 'search/tv')
            oGui.addDir(SITE_TMDB, 'showSearchSerie', addons.VSlang(30121), 'search-series.png', oOutputParameterHandler)
    
        # Nouveautés
        oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        oGui.addDir(SITE_TMDB, 'showSeriesNews', addons.VSlang(30101), 'news.png', oOutputParameterHandler)

        # Populaires TMDB
        # oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        # oGui.addDir(SITE_TMDB, 'showSeriesViews', addons.VSlang(30102), 'popular.png', oOutputParameterHandler)

        # Populaires trakt
        oOutputParameterHandler.addParameter('siteUrl', 'shows/trending')
        oOutputParameterHandler.addParameter('sCat', '2')
        oGui.addDir(SITE_TRAKT, 'getTrakt', addons.VSlang(30102), 'popular.png', oOutputParameterHandler)

    
        # Par diffuseurs
        oOutputParameterHandler.addParameter('siteUrl', 'genre/tv/list')
        oGui.addDir(SITE_TMDB, 'showSeriesNetworks', addons.VSlang(30467), 'diffuseur.png', oOutputParameterHandler)
    
        # Par genres
        oOutputParameterHandler.addParameter('siteUrl', 'genre/tv/list')
        oGui.addDir(SITE_TMDB, 'showGenreTV', addons.VSlang(30105), 'genres.png', oOutputParameterHandler)
    
        # Les mieux notés TMDB
        oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        oGui.addDir(SITE_TMDB, 'showSeriesTop', addons.VSlang(30104), 'notes.png', oOutputParameterHandler)

        # Les mieux notés TRAKT
        # oOutputParameterHandler.addParameter('siteUrl', 'shows/popular')
        # oOutputParameterHandler.addParameter('sCat', '2')
        # oGui.addDir(SITE_TRAKT, 'getTrakt', addons.VSlang(30104), 'notes.png', oOutputParameterHandler)

        # Par années
        oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        oGui.addDir(SITE_TMDB, 'showSeriesYears', self.addons.VSlang(30106), 'annees.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'SERIE_LIST')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30111), 'az.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'SERIE_VOSTFRS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30108), 'vostfr.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'SERIE_SERIES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showAnimes(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()

        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('siteUrl', 'search/tv')
            oGui.addDir(SITE_IDENTIFIER, 'showAnimesSearch', self.addons.VSlang(30076), 'search.png', oOutputParameterHandler)
        else:
            oOutputParameterHandler.addParameter('sCat', '3')
            oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search-animes.png', oOutputParameterHandler)

        # Nouveautés
        oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        oGui.addDir(SITE_TMDB, 'showAnimesNews', self.addons.VSlang(30101), 'news.png', oOutputParameterHandler)

        # Populaires
        oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        oGui.addDir(SITE_TMDB, 'showAnimes', self.addons.VSlang(30102), 'popular.png', oOutputParameterHandler)

        # TOP
        oOutputParameterHandler.addParameter('siteUrl', 'discover/tv')
        oGui.addDir(SITE_TMDB, 'showAnimesTop', self.addons.VSlang(30104), 'notes.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'ANIM_GENRES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30105), 'genres.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'ANIM_LIST')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30111), 'az.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'ANIM_VOSTFRS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30108), 'vf.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'ANIM_ANIMS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showDramas(self):
        oGui = cGui()

        # Affiche les Nouveautés Dramas
        oOutputParameterHandler = cOutputParameterHandler()
        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('siteUrl', 'search/tv')
            oGui.addDir(SITE_IDENTIFIER, 'showDramasSearch', self.addons.VSlang(30076), 'search.png', oOutputParameterHandler)
        else:
            oOutputParameterHandler.addParameter('sCat', '9')
            oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search-dramas.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'DRAMA_NEWS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30101), 'news.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'DRAMA_VIEWS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30102), 'popular.png', oOutputParameterHandler)

        # Affiche les Genres Dramas
        oOutputParameterHandler.addParameter('siteUrl', 'DRAMA_GENRES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30105), 'genres.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'DRAMA_ANNEES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30106), 'annees.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'DRAMA_LIST')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30111), 'az.png', oOutputParameterHandler)

        # Affiche les Sources Dramas
        oOutputParameterHandler.addParameter('siteUrl', 'DRAMA_DRAMAS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showDocs(self):
        oGui = cGui()

        # Affiche les Nouveautés Documentaires
        oOutputParameterHandler = cOutputParameterHandler()
        if self.addons.getSetting('history-view') == 'true':
            oOutputParameterHandler.addParameter('siteUrl', 'search/tv')
            oGui.addDir(SITE_IDENTIFIER, 'showDocsSearch', self.addons.VSlang(30076), 'search.png', oOutputParameterHandler)
        else:
            oOutputParameterHandler.addParameter('sCat', '5')
            oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search-divers.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'DOC_NEWS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30101), 'news.png', oOutputParameterHandler)

        # Affiche les Genres Documentaires
        oOutputParameterHandler.addParameter('siteUrl', 'DOC_GENRES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30105), 'genres.png', oOutputParameterHandler)

        # Affiche les Sources Documentaires
        oOutputParameterHandler.addParameter('siteUrl', 'DOC_DOCS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showSports(self):
        oGui = cGui()

        # Affiche les live Sportifs
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', 'SPORT_LIVE')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30119), 'replay.png', oOutputParameterHandler)

        # Affiche les Genres Sportifs
        oOutputParameterHandler.addParameter('siteUrl', 'SPORT_GENRES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30105), 'genre_sport.png', oOutputParameterHandler)

        # Chaines
        oOutputParameterHandler.addParameter('siteUrl', 'SPORT_TV')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30200), 'tv.png', oOutputParameterHandler)

        # Affiche les Sources Sportives
        oOutputParameterHandler.addParameter('siteUrl', 'SPORT_SPORTS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showDirect(self):
        oGui = cGui()
        oGui.addText('fStream', 'Choisissez un pays')

        for code, name in IPTV_COUNTRIES.items():
            oOutput = cOutputParameterHandler()
            oOutput.addParameter('country_code', code)
            oOutput.addParameter('country_name', name)

            oGui.addDir(SITE_IDENTIFIER, 'showIPTV_ByCountry', f"{name}", f"{code.lower()}.png", oOutput)

        oGui.setEndOfDirectory()

    def showMenuTV(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()

        # SI plusieurs sources proposent la TNT
        # oOutputParameterHandler.addParameter('siteUrl', 'CHAINE_TV')
        # oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30332), 'host.png', oOutputParameterHandler)
        # SINON accès direct à la seule source
        oOutputParameterHandler.addParameter('siteUrl', 'TV')
        oGui.addDir('freebox', 'showWeb', self.addons.VSlang(30332), 'tv.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'CHAINE_CINE')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30200), self.addons.VSlang(30133)), 'films.png', oOutputParameterHandler)
        # oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30138), self.addons.VSlang(30113)), 'host.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'TV_TV')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30138), self.addons.VSlang(30200)), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showReplay(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('sCat', '6')
        oGui.addDir(SITE_IDENTIFIER, 'showSearchText', self.addons.VSlang(30076), 'search.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'REPLAYTV_NEWS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30101), 'news.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'REPLAYTV_GENRES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30105), 'genres.png', oOutputParameterHandler)

        # oOutputParameterHandler.addParameter('siteUrl', 'SPORT_REPLAY')
        # oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30113), 'sport.png', oOutputParameterHandler)

        oOutputParameterHandler.addParameter('siteUrl', 'REPLAYTV_REPLAYTV')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', self.addons.VSlang(30138), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showNets(self):
        oGui = cGui()

        # Affiche les Nouveautés Vidéos
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', 'NETS_NEWS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30114), self.addons.VSlang(30101)), 'news.png', oOutputParameterHandler)

        # Affiche les Genres Vidéos
        oOutputParameterHandler.addParameter('siteUrl', 'NETS_GENRES')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30114), self.addons.VSlang(30105)), 'genres.png', oOutputParameterHandler)

        # Affiche les Sources Vidéos
        oOutputParameterHandler.addParameter('siteUrl', 'NETS_NETS')
        oGui.addDir(SITE_IDENTIFIER, 'callpluging', '%s (%s)' % (self.addons.VSlang(30138), self.addons.VSlang(30114)), 'host.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()

    def showUsers(self):
        oGui = cGui()
        oGui.addDir('siteonefichier', 'load', self.addons.VSlang(30327), 'sites/siteonefichier.png')
        oGui.addDir('alldebrid', 'load', 'AllDebrid', 'sites/alldebrid.png')
        oGui.addDir('sitedarkibox', 'load', 'DarkiBox', 'sites/sitedarkibox.png')
        oGui.addDir('themoviedb_org', 'showMyTmdb', 'TMDB', 'tmdb.png')
        oGui.addDir('cTrakt', 'getLoad', self.addons.VSlang(30214), 'trakt.png')
        # oGui.addDir('siteuptobox', 'load', 'Uptobox', 'sites/siteuptobox.png')
        oGui.setEndOfDirectory()

    def showTools(self):
        oGui = cGui()
        oGui.addDir(SITE_IDENTIFIER, 'opensetting', self.addons.VSlang(30227), 'parametres.png')
        oGui.addDir('cDownload', 'getDownload', self.addons.VSlang(30224), 'download.png')
        oGui.addDir('cLibrary', 'getLibrary', self.addons.VSlang(30303), 'library.png')
        oGui.addDir(SITE_IDENTIFIER, 'showHostDirect', self.addons.VSlang(30469), 'web.png')
        oGui.addDir(SITE_IDENTIFIER, 'showDonation', self.addons.VSlang(30143), 'paypal.png')
        oGui.addDir('globalSources', 'globalSources', self.addons.VSlang(30449), 'host.png')
        oGui.setEndOfDirectory()

    def showHistory(self):
        oGui = cGui()

        oInputParameterHandler = cInputParameterHandler()
        sCat = oInputParameterHandler.getValue('sCat')

        from resources.lib.db import cDb
        with cDb() as db:
            row = db.get_history(sCat)

        if row:
            oGui.addText(SITE_IDENTIFIER, self.addons.VSlang(30416), '')
        else:
            oGui.addText(SITE_IDENTIFIER)
        oOutputParameterHandler = cOutputParameterHandler()
        for match in row:
            sTitle = match['title']
            sCat = match['disp']

            # on ne propose l'historique que pour les films, séries, animes, doc, drama
            if int(sCat) not in (1, 2, 3, 5, 9):
                continue 

            oOutputParameterHandler.addParameter('siteUrl', 'http://lomixx')
            oOutputParameterHandler.addParameter('searchtext', sTitle)

            oGuiElement = cGuiElement()
            oGuiElement.setSiteName('globalSearch')
            oGuiElement.setFunction('globalSearch')

            try:
                oGuiElement.setTitle('- ' + sTitle)
            except:
                oGuiElement.setTitle('- ' + str(sTitle, 'utf-8'))

            oGuiElement.setFileName(sTitle)
            oGuiElement.setCat(sCat)
            oGuiElement.setIcon('search.png')
            oGui.createSimpleMenu(oGuiElement, oOutputParameterHandler, SITE_IDENTIFIER, 'cHome', 'delSearch', self.addons.VSlang(30412))
            oGui.addFolder(oGuiElement, oOutputParameterHandler)

        if row:
            oOutputParameterHandler.addParameter('siteUrl', 'http://lomixx')
            oGui.addDir(SITE_IDENTIFIER, 'delSearch', self.addons.VSlang(30413), 'trash.png', oOutputParameterHandler)

        oGui.setEndOfDirectory()


    def showDonation(self):
        from resources.lib.librecaptcha.gui import cInputWindowYesNo
        inputText = 'Merci pour votre soutien, il permet de maintenir ce projet.\r\nScanner ce code ou rendez vous sur :\r\nhttps://www.paypal.com/paypalme/kodivstream'
        oSolver = cInputWindowYesNo(captcha='special://home/addons/plugin.video.fstream/paypal.jpg', msg=inputText, roundnum=1, okDialog=True)
        oSolver.get()


    def showHostDirect(self):  # fonction de recherche
        oGui = cGui()
        sUrl = oGui.showKeyBoard(heading=self.addons.VSlang(30045))
        if sUrl:

            oHoster = cHosterGui().checkHoster(sUrl)
            if oHoster:
                oHoster.setDisplayName(self.addons.VSlang(30046))
                oHoster.setFileName(self.addons.VSlang(30046))
                cHosterGui().showHoster(oGui, oHoster, sUrl, '')

        oGui.setEndOfDirectory()

    def opensetting(self):
        self.addons.openSettings()

    def delSearch(self):
        from resources.lib.db import cDb
        with cDb() as db:
            db.del_history()
        return True

    def callpluging(self):
        oGui = cGui()

        oInputParameterHandler = cInputParameterHandler()
        sSiteUrl = oInputParameterHandler.getValue('siteUrl')

        oPluginHandler = cPluginHandler()
        aPlugins = oPluginHandler.getAvailablePlugins(sSiteUrl)
        oOutputParameterHandler = cOutputParameterHandler()
        for aPlugin in aPlugins:
            try:
                icon = 'sites/%s.png' % (aPlugin[2])
                oOutputParameterHandler.addParameter('siteUrl', aPlugin[0])
                oGui.addDir(aPlugin[2], aPlugin[3], aPlugin[1], icon, oOutputParameterHandler)
            except:
                pass

        oGui.setEndOfDirectory()


    
    def showDirect(self):
        """Menu principal IPTV avec choix de navigation"""
        oGui = cGui()
        oGui.addText('fStream', 'Chaînes TV en direct')

        # Option 1: Navigation par catégorie
        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER, 
            'showIPTV_ByCategory', 
            '📂 Par catégorie (Sport, News, etc.)', 
            'genres.png', 
            oOutputParameterHandler
        )
        
        # Option 2: Navigation par pays
        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER, 
            'showIPTV_ByCountry', 
            '🌍 Par pays', 
            'flags.png', 
            oOutputParameterHandler
        )

        oGui.setEndOfDirectory()
    
    def showIPTV_ByCategory(self):
        """Affiche toutes les catégories de toutes les chaînes"""
        oGui = cGui()
        from resources.lib.comaddon import VSlog
        
        VSlog("[HOME] Chargement de toutes les catégories")
        
        try:
            # Charger les M3U de tous les pays (ou un index global)
            # Pour l'instant, on charge un pays principal ou global
            url = "https://iptv-org.github.io/iptv/index.m3u"
            
            oOutputParameterHandler = cOutputParameterHandler()
            oOutputParameterHandler.addParameter('m3u_url', url)
            oGui.addDir(
                SITE_IDENTIFIER,
                'showIPTV_LoadAndShowCategories',
                'Toutes les catégories',
                'genres.png',
                oOutputParameterHandler
            )
            
        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            oGui.addText('fStream', f'Erreur: {str(e)}')
        
        oGui.setEndOfDirectory()
    
    def showIPTV_ByCountry(self):
        """Affiche tous les pays disponibles"""
        oGui = cGui()
        from resources.lib.comaddon import VSlog
        
        VSlog("[HOME] Chargement de la liste des pays")
        
        try:
            # Récupérer la liste dynamique des pays
            countries = extractCountriesFromAPI()
            
            for code, name in sorted(countries.items(), key=lambda x: x[1]):
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter('country_code', code)
                oOutputParameterHandler.addParameter('country_name', name)
                
                icon = f"{code.lower()}.png"
                oGui.addDir(
                    SITE_IDENTIFIER, 
                    'showIPTV_CountryMenu', 
                    name, 
                    icon, 
                    oOutputParameterHandler
                )
            
        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            oGui.addText('fStream', f'Erreur: {str(e)}')
        
        oGui.setEndOfDirectory()
    
    def showIPTV_CountryMenu(self):
        """Menu pour un pays: catégories ou toutes les chaînes"""
        oGui = cGui()
        oInput = cInputParameterHandler()
        
        code = oInput.getValue('country_code')
        name = oInput.getValue('country_name')
        
        from resources.lib.comaddon import VSlog
        VSlog(f"[HOME] Menu pour {name}")
        
        # Par catégories
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('country_code', code)
        oOutputParameterHandler.addParameter('show_by', 'category')
        oGui.addDir(
            SITE_IDENTIFIER,
            'showIPTV_Load',
            '📂 Par catégorie',
            'genres.png',
            oOutputParameterHandler
        )
        
        # Toutes les chaînes
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('country_code', code)
        oOutputParameterHandler.addParameter('show_by', 'all')
        oGui.addDir(
            SITE_IDENTIFIER,
            'showIPTV_Load',
            '📺 Toutes les chaînes',
            'tv.png',
            oOutputParameterHandler
        )
        
        oGui.setEndOfDirectory()
    
    def showIPTV_Load(self):
        """Charge et affiche les chaînes d'un pays"""
        oGui = cGui()
        oInput = cInputParameterHandler()
        
        code = oInput.getValue('country_code')
        show_by = oInput.getValue('show_by')
        
        from resources.lib.comaddon import VSlog
        VSlog(f"[HOME] Chargement {code}, mode: {show_by}")
        
        try:
            urls = getCountryM3U(code)
            data = loadM3U(urls, f"{code.lower()}_cache.m3u")
            
            if show_by == 'category':
                parseAndShowM3U(oGui, data, show_by='category')
            else:
                parseAndShowM3U(oGui, data, show_by='all')
                
        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            import traceback
            VSlog(traceback.format_exc())
            oGui.addText('fStream', f'Erreur: {str(e)}')
        
        oGui.setEndOfDirectory()
    
    def showIPTV_Filtered(self):
        """Affiche les chaînes filtrées"""
        oGui = cGui()
        oInput = cInputParameterHandler()
        
        filter_type = oInput.getValue('filter_type')
        filter_value = oInput.getValue('filter_value')
        data = oInput.getValue('m3u_data')
        
        from resources.lib.comaddon import VSlog
        VSlog(f"[HOME] Filtrage: {filter_type}={filter_value}")
        
        try:
            parseAndShowChannels(oGui, data, filter_type, filter_value)
        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            oGui.addText('fStream', f'Erreur: {str(e)}')
        
        oGui.setEndOfDirectory()
    
    def playIPTV(self):
        """Joue un flux IPTV"""
        oGui = cGui()
        oInputParameterHandler = cInputParameterHandler()
        sUrl = oInputParameterHandler.getValue('siteUrl')
        sTitle = oInputParameterHandler.getValue('sMovieTitle')
        
        from resources.lib.comaddon import VSlog
        VSlog(f"[HOME] Lecture: {sTitle}")
        
        oHoster = cHosterGui().checkHoster(sUrl)
        if oHoster:
            oHoster.setDisplayName(sTitle)
            oHoster.setFileName(sTitle)
            cHosterGui().showHoster(oGui, oHoster, sUrl, '')
        else:
            VSlog(f"[HOME] Pas de hoster pour: {sUrl}")
            xbmcgui.Dialog().ok("Erreur", "Impossible de lire ce flux")
        
        oGui.setEndOfDirectory()
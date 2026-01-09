# -*- coding: utf-8 -*-
# fStream https://github.com/Kodi-fStream/lomixx-xbmc-addons
# Venom.
import xbmcaddon
import xbmcgui
import requests
import os
import xbmc
from resources.lib import auth

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


SITE_IDENTIFIER = "cHome"
SITE_NAME = "Home"
IPTV_COUNTRIES = {
    "FR": "France",
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "IT": "Italy",
    "ES": "Spain",
    "CA": "Canada",
    "AU": "Australia",
    "BR": "Brazil",
    "IN": "India",
    "JP": "Japan",
    "KR": "South Korea",
    "CN": "China",
    "RU": "Russia",
    "TR": "Turkey",
    "EG": "Egypt",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "MX": "Mexico",
    "AR": "Argentina",
    "CM": "Cameroon",
    "NG": "Nigeria",
    "ZA": "South Africa",
    "CIV": "Ivory Coast",
}


# ===== CLASSE DE CACHE =====
class IPTVCache:
    """Classe simple pour gérer le cache des fichiers M3U"""

    @staticmethod
    def get_cache_dir():
        """Retourne le répertoire de cache"""
        cache_dir = xbmc.translatePath("special://temp/fstream_iptv_cache")
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
                import time

                file_time = os.path.getmtime(cache_file)
                current_time = time.time()

                # Cache valide pendant 24h (86400 secondes)
                if (current_time - file_time) < 86400:
                    with open(cache_file, "r", encoding="utf-8") as f:
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
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(data)
            from resources.lib.comaddon import VSlog

            VSlog(f"[CACHE] Cache sauvegarde: {cache_name}")
        except Exception as e:
            from resources.lib.comaddon import VSlog

            VSlog(f"[CACHE] Erreur sauvegarde cache: {str(e)}")


# ===== FONCTIONS UTILITAIRES IPTV =====


def extractCountriesFromAPI():
    """Récupère la liste de tous les pays disponibles sur iptv-org"""
    from resources.lib.comaddon import VSlog

    try:
        # L'API iptv-org fournit un index des pays
        url = "https://iptv-org.github.io/iptv/countries.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        countries_data = response.json()
        VSlog(f"[IPTV] {len(countries_data)} pays trouves via API")

        # Retourner un dictionnaire {code: name}
        countries = {}
        for country in countries_data:
            code = country.get("code", "").upper()
            name = country.get("name", "")
            if code and name:
                countries[code] = name

        return countries

    except Exception as e:
        VSlog(f"[IPTV] Erreur recuperation pays API: {str(e)}")
        # Fallback sur la liste statique
        return IPTV_COUNTRIES


def getCountryM3U(country_code):
    """Retourne l'URL du fichier M3U pour un pays donné"""
    return [f"https://iptv-org.github.io/iptv/countries/{country_code.lower()}.m3u"]


def loadM3U(urls, cache_name):
    """Charge le contenu M3U depuis les URLs ou le cache"""
    from resources.lib.comaddon import VSlog

    # Essayer de charger depuis le cache
    data = IPTVCache.get_cached(cache_name)

    if data is not None:
        VSlog(f"[M3U] Charge depuis le cache: {cache_name}")
        return data

    # Sinon télécharger
    VSlog(f"[M3U] Telechargement depuis les URLs...")
    data = ""
    for url in urls:
        try:
            VSlog(f"[M3U] Telechargement: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data += response.text + "\n"
            VSlog(f"[M3U] Telecharge: {len(response.text)} caracteres")
        except Exception as e:
            VSlog(f"[M3U] Erreur telechargement {url}: {str(e)}")
            continue

    # Sauvegarder dans le cache si on a des données
    if data:
        IPTVCache.save_cache(cache_name, data)

    return data


def parseAndShowM3U(oGui, data, show_by="category", max_channels=50):
    """
    Parse le contenu M3U et affiche selon le mode choisi
    show_by: 'category' ou 'all'
    max_channels: nombre maximum de chaînes à afficher (0 = illimité)
    """
    import re
    from resources.lib.comaddon import VSlog

    if not data:
        VSlog("[M3U] Aucune donnee a parser")
        oGui.addText("fStream", "Aucune chaine trouvee")
        return

    VSlog(f"[M3U] Parsing de {len(data)} caracteres, mode: {show_by}, max: {max_channels}")

    # Dictionnaires pour regrouper
    categories = {}
    all_channels = []

    # Parser ligne par ligne
    lines = data.split("\n")
    i = 0
    total_parsed = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF"):
            try:
                # ===== EXTRACTION DU TITRE (AMÉLI0RÉ) =====
                title = None

                # Méthode 1: tvg-name
                name_match = re.search(r'tvg-name="([^"]+)"', line)
                if name_match:
                    title = name_match.group(1).strip()

                # Méthode 2: Texte après la dernière virgule (le plus courant dans M3U)
                if not title or len(title) == 0:
                    comma_parts = line.split(",")
                    if len(comma_parts) > 1:
                        potential_title = comma_parts[-1].strip()
                        # Nettoyer des attributs qui traînent
                        potential_title = re.sub(
                            r'^\s*[\w-]+="[^"]*"\s*', "", potential_title
                        )
                        if potential_title and len(potential_title) > 0:
                            title = potential_title

                # Méthode 3: tvg-id
                if not title or len(title) == 0:
                    id_match = re.search(r'tvg-id="([^"]+)"', line)
                    if id_match:
                        title = (
                            id_match.group(1)
                            .replace(".", " ")
                            .replace("-", " ")
                            .strip()
                        )

                # Dernière chance: utiliser un compteur
                if not title or len(title) == 0:
                    title = f"Chaine {total_parsed + 1}"

                # ===== EXTRACTION DES AUTRES INFOS =====
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                group_match = re.search(r'group-title="([^"]*)"', line)

                # Chercher l'URL dans les lignes suivantes
                stream_url = None
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith("#"):
                        if next_line.startswith("http"):
                            stream_url = next_line
                            break
                    j += 1

                if stream_url and title:
                    logo = logo_match.group(1) if logo_match else "tv.png"
                    category = (
                        group_match.group(1).strip() if group_match else "General"
                    )

                    # Nettoyer le titre
                    title = title.replace("[", "").replace("]", "").strip()
                    title = re.sub(r"<[^>]+>", "", title)  # Enlever HTML
                    title = re.sub(r"\s+", " ", title)  # Normaliser espaces

                    # Limiter longueur
                    if len(title) > 60:
                        title = title[:57] + "..."

                    # Créer l'objet chaîne
                    channel = {
                        "title": title,
                        "url": stream_url,
                        "logo": logo,
                        "category": category,
                    }

                    # Grouper par catégorie
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(channel)

                    # Liste globale
                    all_channels.append(channel)

                    total_parsed += 1

                    if total_parsed <= 5:
                        VSlog(f"[M3U] '{title}' | Cat: {category}")

                    # Limiter le nombre de chaînes si demandé
                    if max_channels > 0 and total_parsed >= max_channels:
                        VSlog(f"[M3U] Limite de {max_channels} chaines atteinte")
                        break

            except Exception as e:
                VSlog(f"[M3U] Erreur parsing ligne {i}: {str(e)}")

        i += 1

        # Vérifier la limite après chaque ligne
        if max_channels > 0 and total_parsed >= max_channels:
            break

    VSlog(
        f"[M3U] Total: {total_parsed} chaines, {len(categories)} categories"
    )

    # ===== AFFICHAGE SELON LE MODE =====
    if show_by == "category":
        if categories:
            # Catégorie Sport en premier
            sport_categories = ["Sport", "Sports"]
            other_categories = []

            for category in sorted(categories.keys()):
                if category in sport_categories or "sport" in category.lower():
                    channel_count = len(categories[category])
                    oOutputParameterHandler = cOutputParameterHandler()
                    oOutputParameterHandler.addParameter("filter_type", "category")
                    oOutputParameterHandler.addParameter("filter_value", category)
                    oOutputParameterHandler.addParameter("m3u_data", data)

                    oGui.addDir(
                        SITE_IDENTIFIER,
                        "showIPTV_Filtered",
                        f"Sport ({channel_count})",
                        "sport.png",
                        oOutputParameterHandler,
                    )
                else:
                    other_categories.append(category)

            # Puis les autres catégories regroupées sous "Autres"
            if other_categories:
                total_other = sum(len(categories[cat]) for cat in other_categories)
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter("filter_type", "all")
                oOutputParameterHandler.addParameter("m3u_data", data)
                oOutputParameterHandler.addParameter("categories", ",".join(other_categories))

                oGui.addDir(
                    SITE_IDENTIFIER,
                    "showIPTV_Filtered",
                    f"Autres ({total_other})",
                    "tv.png",
                    oOutputParameterHandler,
                )
        else:
            oGui.addText("fStream", "Aucune categorie trouvee")

    elif show_by == "all":
        # Afficher toutes les chaînes
        for channel in all_channels:
            oOutputParameterHandler = cOutputParameterHandler()
            oOutputParameterHandler.addParameter("siteUrl", channel["url"])
            oOutputParameterHandler.addParameter("sMovieTitle", channel["title"])
            oOutputParameterHandler.addParameter("sThumb", channel["logo"])

            oGui.addLink(
                SITE_IDENTIFIER,
                "playIPTV",
                channel["title"],
                channel["logo"],
                "",
                oOutputParameterHandler,
            )

        if len(all_channels) == 0:
            oGui.addText("fStream", "Aucune chaine trouvee")


def parseAndShowChannels(oGui, data, filter_type, filter_value):
    """Affiche les chaînes filtrées par catégorie ou toutes"""
    import re
    from resources.lib.comaddon import VSlog

    if not data:
        VSlog("[M3U] Aucune donnee a parser")
        oGui.addText("fStream", "Aucune chaine trouvee")
        return

    VSlog(f"[M3U] Filtrage par {filter_type}: {filter_value}")

    lines = data.split("\n")
    i = 0
    count = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF"):
            try:
                # Extraire les métadonnées
                group_match = re.search(r'group-title="([^"]*)"', line)
                category = group_match.group(1).strip() if group_match else "General"

                # Vérifier si correspond au filtre
                match = False
                if filter_type == "category" and category == filter_value:
                    match = True
                elif filter_type == "all":
                    match = True

                if match:
                    # Extraire le titre (même logique améliorée)
                    title = None

                    name_match = re.search(r'tvg-name="([^"]+)"', line)
                    if name_match:
                        title = name_match.group(1).strip()

                    if not title or len(title) == 0:
                        comma_parts = line.split(",")
                        if len(comma_parts) > 1:
                            title = comma_parts[-1].strip()
                            title = re.sub(r'^\s*[\w-]+="[^"]*"\s*', "", title)

                    if not title or len(title) == 0:
                        id_match = re.search(r'tvg-id="([^"]+)"', line)
                        if id_match:
                            title = (
                                id_match.group(1)
                                .replace(".", " ")
                                .replace("-", " ")
                                .strip()
                            )

                    if not title or len(title) == 0:
                        title = f"Chaine {count + 1}"

                    # Extraire logo et URL
                    logo_match = re.search(r'tvg-logo="([^"]*)"', line)

                    stream_url = None
                    j = i + 1
                    while j < len(lines) and j < i + 5:
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith("#"):
                            if next_line.startswith("http"):
                                stream_url = next_line
                                break
                        j += 1

                    if stream_url:
                        logo = logo_match.group(1) if logo_match else "tv.png"
                        title = title.replace("[", "").replace("]", "").strip()
                        title = re.sub(r"<[^>]+>", "", title)
                        title = re.sub(r"\s+", " ", title)

                        if len(title) > 60:
                            title = title[:57] + "..."

                        oOutputParameterHandler = cOutputParameterHandler()
                        oOutputParameterHandler.addParameter("siteUrl", stream_url)
                        oOutputParameterHandler.addParameter("sMovieTitle", title)
                        oOutputParameterHandler.addParameter("sThumb", logo)

                        oGui.addLink(
                            SITE_IDENTIFIER,
                            "playIPTV",
                            title,
                            logo,
                            "",
                            oOutputParameterHandler,
                        )
                        count += 1

            except Exception as e:
                VSlog(f"[M3U] Erreur parsing: {str(e)}")

        i += 1

    VSlog(f"[M3U] {count} chaines affichees pour {filter_value}")

    if count == 0:
        oGui.addText("fStream", f"Aucune chaine trouvee")


def get_country_code(country_name):
    """Essaie de trouver le code pays depuis le nom"""
    # Mapping inversé
    for code, name in IPTV_COUNTRIES.items():
        if name.lower() == country_name.lower():
            return code

    # Codes courants
    common_codes = {
        "france": "FR",
        "united states": "US",
        "usa": "US",
        "united kingdom": "GB",
        "uk": "GB",
        "germany": "DE",
        "italy": "IT",
        "spain": "ES",
        "canada": "CA",
        "international": "WORLD",
        "brasil": "BR",
        "brazil": "BR",
    }

    return common_codes.get(country_name.lower(), None)


def get_category_icon(category):
    """Retourne une icône appropriée selon la catégorie"""
    category_lower = category.lower()

    icon_map = {
        "news": "news.png",
        "sport": "sport.png",
        "entertainment": "vod.png",
        "movies": "films.png",
        "films": "films.png",
        "series": "series.png",
        "documentary": "doc.png",
        "docs": "doc.png",
        "kids": "enfants.png",
        "music": "genres.png",
        "general": "tv.png",
        "information": "news.png",
        "divertissement": "vod.png",
        "enfants": "enfants.png",
        "musique": "genres.png",
    }

    for key, icon in icon_map.items():
        if key in category_lower:
            return icon

    return "tv.png"

def get_iptv_sources():
    """Retourne un dictionnaire de sources IPTV vérifiées et fonctionnelles"""
    return {
        # === IPTV-ORG PAR CATÉGORIE ===
        "IPTV-ORG-SPORT": {
            "name": "Sport (Mondial)",
            "url": "https://iptv-org.github.io/iptv/categories/sports.m3u",
            "type": "category",
            "icon": "sport.png",
            "description": "Chaînes sportives du monde entier"
        },
        "IPTV-ORG-NEWS": {
            "name": "News (Mondial)",
            "url": "https://iptv-org.github.io/iptv/categories/news.m3u",
            "type": "category",
            "icon": "news.png",
            "description": "Chaînes d'information"
        },
        "IPTV-ORG-MOVIES": {
            "name": "Films (Mondial)",
            "url": "https://iptv-org.github.io/iptv/categories/movies.m3u",
            "type": "category",
            "icon": "films.png",
            "description": "Chaînes de films"
        },
        "IPTV-ORG-SERIES": {
            "name": "Series (Mondial)",
            "url": "https://iptv-org.github.io/iptv/categories/series.m3u",
            "type": "category",
            "icon": "series.png",
            "description": "Chaînes de séries TV"
        },
        "IPTV-ORG-ENTERTAINMENT": {
            "name": "Divertissement",
            "url": "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
            "type": "category",
            "icon": "vod.png",
            "description": "Chaînes de divertissement"
        },
        "IPTV-ORG-MUSIC": {
            "name": "Musique",
            "url": "https://iptv-org.github.io/iptv/categories/music.m3u",
            "type": "category",
            "icon": "genres.png",
            "description": "Chaînes musicales"
        },
        "IPTV-ORG-KIDS": {
            "name": "Enfants",
            "url": "https://iptv-org.github.io/iptv/categories/kids.m3u",
            "type": "category",
            "icon": "enfants.png",
            "description": "Chaînes pour enfants"
        },
        "IPTV-ORG-DOCUMENTARY": {
            "name": "Documentaires",
            "url": "https://iptv-org.github.io/iptv/categories/documentary.m3u",
            "type": "category",
            "icon": "doc.png",
            "description": "Chaînes documentaires"
        },
        "IPTV-ORG-COOKING": {
            "name": "Cuisine",
            "url": "https://iptv-org.github.io/iptv/categories/cooking.m3u",
            "type": "category",
            "icon": "vod.png",
            "description": "Chaînes de cuisine"
        },
        "IPTV-ORG-TRAVEL": {
            "name": "Voyage",
            "url": "https://iptv-org.github.io/iptv/categories/travel.m3u",
            "type": "category",
            "icon": "vod.png",
            "description": "Chaînes de voyage"
        },
        "IPTV-ORG-WEATHER": {
            "name": "Meteo",
            "url": "https://iptv-org.github.io/iptv/categories/weather.m3u",
            "type": "category",
            "icon": "tv.png",
            "description": "Chaînes météo"
        },
        "IPTV-ORG-RELIGIOUS": {
            "name": "Religion",
            "url": "https://iptv-org.github.io/iptv/categories/religious.m3u",
            "type": "category",
            "icon": "tv.png",
            "description": "Chaînes religieuses"
        },
        "IPTV-ORG-EDUCATION": {
            "name": "Education",
            "url": "https://iptv-org.github.io/iptv/categories/education.m3u",
            "type": "category",
            "icon": "doc.png",
            "description": "Chaînes éducatives"
        },
        "IPTV-ORG-SCIENCE": {
            "name": "Science",
            "url": "https://iptv-org.github.io/iptv/categories/science.m3u",
            "type": "category",
            "icon": "doc.png",
            "description": "Chaînes scientifiques"
        },
        "IPTV-ORG-ANIMATION": {
            "name": "Animation",
            "url": "https://iptv-org.github.io/iptv/categories/animation.m3u",
            "type": "category",
            "icon": "animes.png",
            "description": "Chaînes d'animation"
        },
        "IPTV-ORG-CLASSIC": {
            "name": "Classique",
            "url": "https://iptv-org.github.io/iptv/categories/classic.m3u",
            "type": "category",
            "icon": "films.png",
            "description": "Chaînes classiques"
        },
        "IPTV-ORG-COMEDY": {
            "name": "Comedie",
            "url": "https://iptv-org.github.io/iptv/categories/comedy.m3u",
            "type": "category",
            "icon": "vod.png",
            "description": "Chaînes de comédie"
        },
        "IPTV-ORG-BUSINESS": {
            "name": "Business",
            "url": "https://iptv-org.github.io/iptv/categories/business.m3u",
            "type": "category",
            "icon": "news.png",
            "description": "Chaînes business"
        },
        "IPTV-ORG-LIFESTYLE": {
            "name": "Lifestyle",
            "url": "https://iptv-org.github.io/iptv/categories/lifestyle.m3u",
            "type": "category",
            "icon": "vod.png",
            "description": "Chaînes lifestyle"
        },
        "IPTV-ORG-AUTO": {
            "name": "Auto",
            "url": "https://iptv-org.github.io/iptv/categories/auto.m3u",
            "type": "category",
            "icon": "vod.png",
            "description": "Chaînes automobile"
        },

        # === IPTV-ORG PAR LANGUE ===
        "IPTV-ORG-FRENCH": {
            "name": "Chaines francophones",
            "url": "https://iptv-org.github.io/iptv/languages/fra.m3u",
            "type": "language",
            "icon": "fr.png",
            "description": "Toutes les chaînes en français"
        },
        "IPTV-ORG-ENGLISH": {
            "name": "Chaines anglophones",
            "url": "https://iptv-org.github.io/iptv/languages/eng.m3u",
            "type": "language",
            "icon": "gb.png",
            "description": "Toutes les chaînes en anglais"
        },
        "IPTV-ORG-SPANISH": {
            "name": "Chaines hispanophones",
            "url": "https://iptv-org.github.io/iptv/languages/spa.m3u",
            "type": "language",
            "icon": "es.png",
            "description": "Toutes les chaînes en espagnol"
        },
        "IPTV-ORG-ARABIC": {
            "name": "Chaines arabophones",
            "url": "https://iptv-org.github.io/iptv/languages/ara.m3u",
            "type": "language",
            "icon": "sa.png",
            "description": "Toutes les chaînes en arabe"
        },
        "IPTV-ORG-PORTUGUESE": {
            "name": "Chaines lusophones",
            "url": "https://iptv-org.github.io/iptv/languages/por.m3u",
            "type": "language",
            "icon": "br.png",
            "description": "Toutes les chaînes en portugais"
        },

        # === FREE-TV (Sources légales) ===
        "FREE-TV-FRANCE": {
            "name": "Free-TV France (Legal)",
            "url": "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_france_full.m3u8",
            "type": "country",
            "icon": "fr.png",
            "description": "Chaînes françaises légales uniquement"
        },
        "FREE-TV-USA": {
            "name": "Free-TV USA (Legal)",
            "url": "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_usa_full.m3u8",
            "type": "country",
            "icon": "us.png",
            "description": "Chaînes américaines légales uniquement"
        },
        "FREE-TV-UK": {
            "name": "Free-TV UK (Legal)",
            "url": "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_uk_full.m3u8",
            "type": "country",
            "icon": "gb.png",
            "description": "Chaînes britanniques légales uniquement"
        },

        # === INDEX GLOBAL ===
        "IPTV-ORG-GLOBAL": {
            "name": "Toutes les chaines (Mondial)",
            "url": "https://iptv-org.github.io/iptv/index.m3u",
            "type": "global",
            "icon": "tv.png",
            "description": "Index complet de toutes les chaînes IPTV-ORG"
        }
    }

# ===== CLASSE PRINCIPALE =====


class cHome:

    addons = addon()

    def loginScreen(self):
        oGui = cGui()

        oGui.addText("Fstream", "Veuillez vous connecter")

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("function", "doLogin")

        oGui.addDir(
            SITE_IDENTIFIER,
            "doLogin",
            "Se connecter",
            "login.png",
            oOutputParameterHandler,
        )
        oGui.setEndOfDirectory()

    def doLogin(self):
        """
        Tente une connexion avec les identifiants sauvegardés dans les paramètres
        """
        from resources.lib.comaddon import VSlog

        VSlog("[HOME] Fonction doLogin() appelee")

        # Récupération des identifiants depuis settings.xml
        email = self.addons.getSetting("auth_username")
        password = self.addons.getSetting("auth_password")

        VSlog(f"[HOME] Email recupere : {email}")
        VSlog(f"[HOME] Password present : {bool(password)}")

        # Vérification que les champs ne sont pas vides
        if not email or not password:
            VSlog("[HOME] Identifiants manquants")
            xbmcgui.Dialog().ok(
                "Fstream",
                "Veuillez entrer votre email et mot de passe dans les parametres",
            )
            self.addons.openSettings()
            return

        # Tentative de connexion (login retourne un tuple: success, message)
        VSlog("[HOME] Appel de auth.login()...")
        success, message = auth.login(email, password)

        VSlog(f"[HOME] Resultat login : success={success}, message={message}")

        if success:
            VSlog("[HOME] Login reussi, rechargement de l'interface")
            xbmcgui.Dialog().ok("Fstream", "Connexion reussie !")
            # Rafraîchir l'interface
            self.load()
        else:
            VSlog(f"[HOME] Login echoue : {message}")
            # Afficher l'erreur retournée par l'API
            xbmcgui.Dialog().ok("Fstream", f"Erreur de connexion :\n{message}")

    def doLogout(self):
        auth.logout()
        xbmcgui.Dialog().ok("Fstream", "Deconnecte")
        self.loginScreen()

    def load(self):
        oGui = cGui()
        token = auth.get_token()

        if not token:
            self.loginScreen()
            return

        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            "doLogout",
            "[Deconnexion]",
            "logout.png",
            oOutputParameterHandler,
        )
        oGui.addDir(SITE_IDENTIFIER, "showVOD", self.addons.VSlang(30131), "vod.png")
        oGui.addDir(
            SITE_IDENTIFIER, "showDirect", self.addons.VSlang(30132), "direct.png"
        )
        oGui.addDir(
            SITE_IDENTIFIER, "showReplay", self.addons.VSlang(30350), "replay.png"
        )
        oGui.addDir(
            SITE_IDENTIFIER, "showMyVideos", self.addons.VSlang(30130), "profile.png"
        )
        oGui.addDir(
            SITE_IDENTIFIER, "showTools", self.addons.VSlang(30033), "tools.png"
        )

        view = False
        if self.addons.getSetting("active-view") == "true":
            view = self.addons.getSetting("accueil-view")

        oGui.setEndOfDirectory(view)

    def showVOD(self):
        oGui = cGui()
        oGui.addDir(
            SITE_IDENTIFIER, "showMovies", self.addons.VSlang(30120), "films.png"
        )
        oGui.addDir(
            SITE_IDENTIFIER, "showSeries", self.addons.VSlang(30121), "series.png"
        )
        oGui.addDir(
            SITE_IDENTIFIER, "showAnimes", self.addons.VSlang(30122), "animes.png"
        )
        oGui.addDir(SITE_IDENTIFIER, "showDocs", self.addons.VSlang(30112), "doc.png")
        oGui.addDir(
            SITE_IDENTIFIER, "showDramas", self.addons.VSlang(30124), "dramas.png"
        )
        # Diffuseurs au menu principal VOD
        oGui.addDir(
            "themoviedb_org", "showSeriesNetworks", "Diffuseurs", "diffuseur.png"
        )
        oGui.addDir(SITE_TMDB, "showMenuActeur", self.addons.VSlang(30466), "actor.png")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showMenuSearch",
            self.addons.VSlang(30135),
            "search_direct.png",
        )

        oGui.setEndOfDirectory()

    def showMyVideos(self):
        oGui = cGui()
        oGui.addDir("cFav", "getBookmarks", self.addons.VSlang(30207), "mark.png")
        oGui.addDir("cViewing", "showMenu", self.addons.VSlang(30125), "vod.png")
        oGui.addDir("cWatched", "showMenu", self.addons.VSlang(30321), "annees.png")
        oGui.addDir(
            SITE_IDENTIFIER, "showUsers", self.addons.VSlang(30455), "profile.png"
        )
        oGui.addDir(
            "cDownload", "getDownloadList", self.addons.VSlang(30229), "download.png"
        )
        oGui.addDir(
            "globalSources", "activeSources", self.addons.VSlang(30362), "host.png"
        )
        oGui.setEndOfDirectory()

    def showMenuSearch(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()

        oOutputParameterHandler.addParameter("sCat", "1")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30120),
            "search-films.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("sCat", "2")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30121),
            "search-series.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("sCat", "3")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30122),
            "search-animes.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("sCat", "9")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30124),
            "search-dramas.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("sCat", "5")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30112),
            "search-divers.png",
            oOutputParameterHandler,
        )

        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("siteUrl", "http://Lomixxx")
            oGui.addDir(
                "cHome",
                "showHistory",
                self.addons.VSlang(30308),
                "history.png",
                oOutputParameterHandler,
            )

        oGui.setEndOfDirectory()

    def showMovieSearch(self):
        oGui = cGui()
        addons = self.addons

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "search/movie")
        oGui.addDir(
            SITE_TMDB,
            "showSearchMovie",
            addons.VSlang(30120),
            "search-films.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "search/movie")
        oGui.addDir(
            SITE_TMDB,
            "showSearchSaga",
            addons.VSlang(30139),
            "search-sagas.png",
            oOutputParameterHandler,
        )

        # Chercher une liste Trakt
        oOutputParameterHandler.addParameter("sCat", "1")
        oGui.addDir(
            SITE_TRAKT,
            "showSearchList",
            addons.VSlang(30123),
            "search-list.png",
            oOutputParameterHandler,
        )

        # recherche acteurs
        oOutputParameterHandler.addParameter("siteUrl", "search/person")
        oGui.addDir(
            SITE_TMDB,
            "showSearchActor",
            addons.VSlang(30466),
            "search-actor.png",
            oOutputParameterHandler,
        )

        if addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("sCat", "1")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showHistory",
                addons.VSlang(30308),
                "history.png",
                oOutputParameterHandler,
            )

        oGui.setEndOfDirectory()

    def showSeriesSearch(self):
        oGui = cGui()
        addons = self.addons

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "search/tv")
        oGui.addDir(
            SITE_TMDB,
            "showSearchSerie",
            addons.VSlang(30121),
            "search-series.png",
            oOutputParameterHandler,
        )

        # Chercher une liste
        oOutputParameterHandler.addParameter("sCat", "2")
        oGui.addDir(
            SITE_TRAKT,
            "showSearchList",
            addons.VSlang(30123),
            "search-list.png",
            oOutputParameterHandler,
        )

        if addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("sCat", "2")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showHistory",
                addons.VSlang(30308),
                "history.png",
                oOutputParameterHandler,
            )

        oGui.setEndOfDirectory()

    def showAnimesSearch(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()
        # recherche directe
        oOutputParameterHandler.addParameter("sCat", "3")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30076),
            "search-animes.png",
            oOutputParameterHandler,
        )

        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("sCat", "3")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showHistory",
                self.addons.VSlang(30308),
                "history.png",
                oOutputParameterHandler,
            )

        oGui.setEndOfDirectory()

    def showDramasSearch(self):
        oGui = cGui()
        oOutputParameterHandler = cOutputParameterHandler()

        # recherche directe
        oOutputParameterHandler.addParameter("sCat", "9")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30076),
            "search-dramas.png",
            oOutputParameterHandler,
        )

        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("sCat", "9")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showHistory",
                self.addons.VSlang(30308),
                "history.png",
                oOutputParameterHandler,
            )

        oGui.setEndOfDirectory()

    def showSearchText(self):
        oGui = cGui()
        oInputParameterHandler = cInputParameterHandler()
        sSearchText = oGui.showKeyBoard(heading=self.addons.VSlang(30076))
        if not sSearchText:
            return False

        oSearch = cSearch()
        sCat = oInputParameterHandler.getValue("sCat")
        oSearch.searchGlobal(sSearchText, sCat)
        oGui.setEndOfDirectory()

    def showMovies(self):
        oGui = cGui()
        addons = self.addons

        oOutputParameterHandler = cOutputParameterHandler()

        oGui.addDir(
            SITE_IDENTIFIER,
            "showMovieSearch",
            addons.VSlang(30076),
            "search.png",
            oOutputParameterHandler,
        )

        # Nouveautés
        oOutputParameterHandler.addParameter("siteUrl", "discover/movie")
        oGui.addDir(
            SITE_TMDB,
            "showMoviesNews",
            addons.VSlang(30101),
            "news.png",
            oOutputParameterHandler,
        )

        # Populaires
        oOutputParameterHandler.addParameter("siteUrl", "discover/movie")
        oGui.addDir(
            SITE_TMDB,
            "showMovies",
            addons.VSlang(30102),
            "popular.png",
            oOutputParameterHandler,
        )

        # Box office
        oOutputParameterHandler.addParameter("siteUrl", "movies/boxoffice")
        oOutputParameterHandler.addParameter("sCat", "1")
        oGui.addDir(
            SITE_TRAKT,
            "getTrakt",
            addons.VSlang(30314),
            "boxoffice.png",
            oOutputParameterHandler,
        )

        # Genres
        oOutputParameterHandler.addParameter("siteUrl", "genre/movie/list")
        oGui.addDir(
            SITE_TMDB,
            "showGenreMovie",
            addons.VSlang(30105),
            "genres.png",
            oOutputParameterHandler,
        )

        # Années
        oOutputParameterHandler.addParameter("siteUrl", "discover/movie")
        oGui.addDir(
            SITE_TMDB,
            "showMoviesYears",
            self.addons.VSlang(30106),
            "annees.png",
            oOutputParameterHandler,
        )

        # Top films TRAKT
        oOutputParameterHandler.addParameter("siteUrl", "movies/popular")
        oOutputParameterHandler.addParameter("sCat", "1")
        oGui.addDir(
            SITE_TRAKT,
            "getTrakt",
            self.addons.VSlang(30104),
            "notes.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "ANIM_ENFANTS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30109),
            "enfants.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "MOVIE_VOSTFR")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30108),
            "vostfr.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "MOVIE_MOVIE")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showSeries(self):
        oGui = cGui()
        addons = self.addons

        oOutputParameterHandler = cOutputParameterHandler()

        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("siteUrl", "search/tv")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showSeriesSearch",
                addons.VSlang(30076),
                "search.png",
                oOutputParameterHandler,
            )
        else:
            oOutputParameterHandler.addParameter("siteUrl", "search/tv")
            oGui.addDir(
                SITE_TMDB,
                "showSearchSerie",
                addons.VSlang(30121),
                "search-series.png",
                oOutputParameterHandler,
            )

        # Nouveautés
        oOutputParameterHandler.addParameter("siteUrl", "discover/tv")
        oGui.addDir(
            SITE_TMDB,
            "showSeriesNews",
            addons.VSlang(30101),
            "news.png",
            oOutputParameterHandler,
        )

        # Populaires trakt
        oOutputParameterHandler.addParameter("siteUrl", "shows/trending")
        oOutputParameterHandler.addParameter("sCat", "2")
        oGui.addDir(
            SITE_TRAKT,
            "getTrakt",
            addons.VSlang(30102),
            "popular.png",
            oOutputParameterHandler,
        )

        # Par diffuseurs
        oOutputParameterHandler.addParameter("siteUrl", "genre/tv/list")
        oGui.addDir(
            SITE_TMDB,
            "showSeriesNetworks",
            addons.VSlang(30467),
            "diffuseur.png",
            oOutputParameterHandler,
        )

        # Par genres
        oOutputParameterHandler.addParameter("siteUrl", "genre/tv/list")
        oGui.addDir(
            SITE_TMDB,
            "showGenreTV",
            addons.VSlang(30105),
            "genres.png",
            oOutputParameterHandler,
        )

        # Les mieux notés TMDB
        oOutputParameterHandler.addParameter("siteUrl", "discover/tv")
        oGui.addDir(
            SITE_TMDB,
            "showSeriesTop",
            addons.VSlang(30104),
            "notes.png",
            oOutputParameterHandler,
        )

        # Par années
        oOutputParameterHandler.addParameter("siteUrl", "discover/tv")
        oGui.addDir(
            SITE_TMDB,
            "showSeriesYears",
            self.addons.VSlang(30106),
            "annees.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "SERIE_LIST")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30111),
            "az.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "SERIE_VOSTFRS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30108),
            "vostfr.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "SERIE_SERIES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showAnimes(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()

        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("siteUrl", "search/tv")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showAnimesSearch",
                self.addons.VSlang(30076),
                "search.png",
                oOutputParameterHandler,
            )
        else:
            oOutputParameterHandler.addParameter("sCat", "3")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showSearchText",
                self.addons.VSlang(30076),
                "search-animes.png",
                oOutputParameterHandler,
            )

        # Nouveautés
        oOutputParameterHandler.addParameter("siteUrl", "discover/tv")
        oGui.addDir(
            SITE_TMDB,
            "showAnimesNews",
            self.addons.VSlang(30101),
            "news.png",
            oOutputParameterHandler,
        )

        # Populaires
        oOutputParameterHandler.addParameter("siteUrl", "discover/tv")
        oGui.addDir(
            SITE_TMDB,
            "showAnimes",
            self.addons.VSlang(30102),
            "popular.png",
            oOutputParameterHandler,
        )

        # TOP
        oOutputParameterHandler.addParameter("siteUrl", "discover/tv")
        oGui.addDir(
            SITE_TMDB,
            "showAnimesTop",
            self.addons.VSlang(30104),
            "notes.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "ANIM_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30105),
            "genres.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "ANIM_LIST")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30111),
            "az.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "ANIM_VOSTFRS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30108),
            "vf.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "ANIM_ANIMS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showDramas(self):
        oGui = cGui()

        # Affiche les Nouveautés Dramas
        oOutputParameterHandler = cOutputParameterHandler()
        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("siteUrl", "search/tv")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showDramasSearch",
                self.addons.VSlang(30076),
                "search.png",
                oOutputParameterHandler,
            )
        else:
            oOutputParameterHandler.addParameter("sCat", "9")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showSearchText",
                self.addons.VSlang(30076),
                "search-dramas.png",
                oOutputParameterHandler,
            )

        oOutputParameterHandler.addParameter("siteUrl", "DRAMA_NEWS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30101),
            "news.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "DRAMA_VIEWS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30102),
            "popular.png",
            oOutputParameterHandler,
        )

        # Affiche les Genres Dramas
        oOutputParameterHandler.addParameter("siteUrl", "DRAMA_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30105),
            "genres.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "DRAMA_ANNEES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30106),
            "annees.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "DRAMA_LIST")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30111),
            "az.png",
            oOutputParameterHandler,
        )

        # Affiche les Sources Dramas
        oOutputParameterHandler.addParameter("siteUrl", "DRAMA_DRAMAS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showDocs(self):
        oGui = cGui()

        # Affiche les Nouveautés Documentaires
        oOutputParameterHandler = cOutputParameterHandler()
        if self.addons.getSetting("history-view") == "true":
            oOutputParameterHandler.addParameter("siteUrl", "search/tv")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showDocsSearch",
                self.addons.VSlang(30076),
                "search.png",
                oOutputParameterHandler,
            )
        else:
            oOutputParameterHandler.addParameter("sCat", "5")
            oGui.addDir(
                SITE_IDENTIFIER,
                "showSearchText",
                self.addons.VSlang(30076),
                "search-divers.png",
                oOutputParameterHandler,
            )

        oOutputParameterHandler.addParameter("siteUrl", "DOC_NEWS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30101),
            "news.png",
            oOutputParameterHandler,
        )

        # Affiche les Genres Documentaires
        oOutputParameterHandler.addParameter("siteUrl", "DOC_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30105),
            "genres.png",
            oOutputParameterHandler,
        )

        # Affiche les Sources Documentaires
        oOutputParameterHandler.addParameter("siteUrl", "DOC_DOCS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showSports(self):
        oGui = cGui()

        # Affiche les live Sportifs
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_LIVE")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30119),
            "replay.png",
            oOutputParameterHandler,
        )

        # Affiche les Genres Sportifs
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30105),
            "genre_sport.png",
            oOutputParameterHandler,
        )

        # Chaines
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_TV")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30200),
            "tv.png",
            oOutputParameterHandler,
        )

        # Affiche les Sources Sportives
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_SPORTS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    # ===== MÉTHODES IPTV =====

    def showDirect(self):
        """Menu principal IPTV avec toutes les sources"""
        oGui = cGui()

        from resources.lib.comaddon import VSlog
        VSlog("[HOME] showDirect() appelee")

        oOutputParameterHandler = cOutputParameterHandler()

        # Option 1: Live TV (menu complet avec sous-menus)
        oGui.addDir(
            SITE_IDENTIFIER,
            'showMenuLiveTV',
            'Live TV (Evenements sportifs)',
            'tv.png',
            oOutputParameterHandler
        )

        # Option 2: Par pays (IPTV-org avec limite 50)
        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_AllCountries",
            "Par Pays (50 chaines max)",
            "tv.png",
            oOutputParameterHandler,
        )

        # Séparateur
        oGui.addText("fStream", "=== Categories ===")

        # Charger toutes les sources depuis get_iptv_sources()
        sources = get_iptv_sources()

        # Filtrer et afficher uniquement les catégories principales
        main_categories = [
            "IPTV-ORG-SPORT",
            "IPTV-ORG-NEWS",
            "IPTV-ORG-MOVIES",
            "IPTV-ORG-SERIES",
            "IPTV-ORG-ENTERTAINMENT",
            "IPTV-ORG-MUSIC",
            "IPTV-ORG-KIDS",
            "IPTV-ORG-DOCUMENTARY"
        ]

        for source_id in main_categories:
            if source_id in sources:
                source = sources[source_id]
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter("source_url", source["url"])
                oOutputParameterHandler.addParameter("source_name", source["name"])
                oGui.addDir(
                    SITE_IDENTIFIER,
                    "showIPTV_FromURL",
                    source["name"],
                    source["icon"],
                    oOutputParameterHandler,
                )

        # Séparateur
        oGui.addText("fStream", "=== Langues ===")

        # Afficher les sources par langue
        language_sources = [
            "IPTV-ORG-FRENCH",
            "IPTV-ORG-ENGLISH",
            "IPTV-ORG-SPANISH",
            "IPTV-ORG-ARABIC"
        ]

        for source_id in language_sources:
            if source_id in sources:
                source = sources[source_id]
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter("source_url", source["url"])
                oOutputParameterHandler.addParameter("source_name", source["name"])
                oGui.addDir(
                    SITE_IDENTIFIER,
                    "showIPTV_FromURL",
                    source["name"],
                    source["icon"],
                    oOutputParameterHandler,
                )

        # Séparateur
        oGui.addText("fStream", "=== Sources legales ===")

        # Afficher Free-TV
        legal_sources = [
            "FREE-TV-FRANCE",
            "FREE-TV-USA",
            "FREE-TV-UK"
        ]

        for source_id in legal_sources:
            if source_id in sources:
                source = sources[source_id]
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter("source_url", source["url"])
                oOutputParameterHandler.addParameter("source_name", source["name"])
                oGui.addDir(
                    SITE_IDENTIFIER,
                    "showIPTV_FromURL",
                    source["name"],
                    source["icon"],
                    oOutputParameterHandler,
                )

        # Option avancée: Toutes les sources
        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_AllSources",
            "--- Toutes les sources ---",
            "tv.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()
        """Menu principal IPTV avec plusieurs sources vérifiées"""
        oGui = cGui()

        from resources.lib.comaddon import VSlog
        VSlog("[HOME] showDirect() appelee")

        oOutputParameterHandler = cOutputParameterHandler()

        # Option 1: Live TV (source existante livetv.py)
        oGui.addDir(
            'livetv',
            'load',
            'Live TV (Evenements sportifs)',
            'tv.png',
            oOutputParameterHandler
        )

        # Option 2: Par pays (IPTV-org)
        oOutputParameterHandler = cOutputParameterHandler()
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_AllCountries",
            "Par pays (Toutes chaines)",
            "flags.png",
            oOutputParameterHandler,
        )

        # Option 3: Chaînes Sport uniquement
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/categories/sports.m3u")
        oOutputParameterHandler.addParameter("source_name", "Sport")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Sport (Mondial)",
            "sport.png",
            oOutputParameterHandler,
        )

        # Option 4: Chaînes News uniquement
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/categories/news.m3u")
        oOutputParameterHandler.addParameter("source_name", "News")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "News (Mondial)",
            "news.png",
            oOutputParameterHandler,
        )

        # Option 5: Chaînes Movies
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/categories/movies.m3u")
        oOutputParameterHandler.addParameter("source_name", "Movies")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Films (Mondial)",
            "films.png",
            oOutputParameterHandler,
        )

        # Option 6: Chaînes Entertainment
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/categories/entertainment.m3u")
        oOutputParameterHandler.addParameter("source_name", "Entertainment")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Divertissement",
            "vod.png",
            oOutputParameterHandler,
        )

        # Option 7: Chaînes Music
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/categories/music.m3u")
        oOutputParameterHandler.addParameter("source_name", "Music")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Musique",
            "genres.png",
            oOutputParameterHandler,
        )

        # Option 8: Chaînes Kids
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/categories/kids.m3u")
        oOutputParameterHandler.addParameter("source_name", "Kids")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Enfants",
            "enfants.png",
            oOutputParameterHandler,
        )

        # Option 9: France (langue française)
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://iptv-org.github.io/iptv/languages/fra.m3u")
        oOutputParameterHandler.addParameter("source_name", "Francais")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Chaines francophones",
            "fr.png",
            oOutputParameterHandler,
        )

        # Option 10: Free-TV (Chaînes légales uniquement)
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("source_url", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_france_full.m3u8")
        oOutputParameterHandler.addParameter("source_name", "Free-TV France")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showIPTV_FromURL",
            "Free-TV France (Legal)",
            "tv.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showIPTV_FromURL(self):
        """Charge et affiche les chaînes depuis une URL spécifique"""
        oGui = cGui()
        oInput = cInputParameterHandler()

        source_url = oInput.getValue("source_url")
        source_name = oInput.getValue("source_name")

        from resources.lib.comaddon import VSlog
        VSlog(f"[HOME] Chargement depuis: {source_url}")

        try:
            # Télécharger le M3U
            VSlog(f"[HOME] Telechargement de {source_name}...")
            response = requests.get(source_url, timeout=20)
            response.raise_for_status()
            data = response.text

            VSlog(f"[HOME] {len(data)} caracteres charges depuis {source_name}")

            # Afficher toutes les chaînes (pas de limite pour les catégories)
            parseAndShowM3U(oGui, data, show_by="all", max_channels=0)

        except requests.exceptions.HTTPError as e:
            VSlog(f"[HOME] Erreur HTTP {e.response.status_code}: {source_url}")
            oGui.addText("fStream", f"Source non disponible (Erreur {e.response.status_code})")
        except requests.exceptions.Timeout:
            VSlog(f"[HOME] Timeout pour: {source_url}")
            oGui.addText("fStream", "Delai d'attente depasse")
        except requests.exceptions.RequestException as e:
            VSlog(f"[HOME] Erreur reseau: {str(e)}")
            oGui.addText("fStream", f"Erreur reseau: {str(e)}")
        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            import traceback
            VSlog(traceback.format_exc())
            oGui.addText("fStream", f"Erreur: {str(e)}")

        oGui.setEndOfDirectory()

    def showIPTV_AllCountries(self):
        """Affiche tous les pays disponibles"""
        oGui = cGui()
        from resources.lib.comaddon import VSlog

        VSlog("[HOME] Chargement liste des pays")

        try:
            # Récupérer la liste dynamique des pays
            countries = extractCountriesFromAPI()
            VSlog(f"[HOME] {len(countries)} pays trouves")

            for code, name in sorted(countries.items(), key=lambda x: x[1]):
                oOutputParameterHandler = cOutputParameterHandler()
                oOutputParameterHandler.addParameter("country_code", code)
                oOutputParameterHandler.addParameter("country_name", name)

                icon = f"{code.lower()}.png"
                oGui.addDir(
                    SITE_IDENTIFIER,
                    "showIPTV_CountryChannels",
                    name,
                    icon,
                    oOutputParameterHandler,
                )

        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            oGui.addText("fStream", f"Erreur: {str(e)}")

        oGui.setEndOfDirectory()
    
    def showMenuLiveTV(self):
        """Sous-menu Live TV avec Genres, Chaines, Sources"""
        oGui = cGui()
        oOutputParameterHandler = cOutputParameterHandler()

        # En cours (événements en direct)
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_LIVE")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30119),  # "En cours"
            "replay.png",
            oOutputParameterHandler,
        )

        # Genres sportifs
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30105),  # "Genres"
            "genre_sport.png",
            oOutputParameterHandler,
        )

        # Chaînes TV sportives
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_TV")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30200),  # "Chaines"
            "tv.png",
            oOutputParameterHandler,
        )

        # Sources sportives
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "SPORT_SPORTS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),  # "Sources"
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showIPTV_AllSources(self):
        """Affiche toutes les sources disponibles organisées"""
        oGui = cGui()

        sources = get_iptv_sources()

        # Grouper par type
        categories = {}
        for source_id, source_data in sources.items():
            source_type = source_data["type"]
            if source_type not in categories:
                categories[source_type] = []
            categories[source_type].append((source_id, source_data))

        # Afficher par type
        type_names = {
            "category": "=== Par categorie ===",
            "language": "=== Par langue ===",
            "country": "=== Par pays ===",
            "global": "=== Index global ==="
        }

        for source_type in ["category", "language", "country", "global"]:
            if source_type in categories:
                oGui.addText("fStream", type_names.get(source_type, f"=== {source_type} ==="))

                for source_id, source_data in sorted(categories[source_type], key=lambda x: x[1]["name"]):
                    oOutputParameterHandler = cOutputParameterHandler()
                    oOutputParameterHandler.addParameter("source_url", source_data["url"])
                    oOutputParameterHandler.addParameter("source_name", source_data["name"])
                    oGui.addDir(
                        SITE_IDENTIFIER,
                        "showIPTV_FromURL",
                        source_data["name"],
                        source_data["icon"],
                        oOutputParameterHandler,
                    )

        oGui.setEndOfDirectory()

    def showIPTV_CountryChannels(self):
        """Charge et affiche les chaînes d'un pays (max 50) avec catégories Sport et Autres"""
        oGui = cGui()
        oInput = cInputParameterHandler()

        code = oInput.getValue("country_code")
        name = oInput.getValue("country_name")

        from resources.lib.comaddon import VSlog

        VSlog(f"[HOME] Chargement chaines pour {name} ({code})")

        try:
            urls = getCountryM3U(code)
            data = loadM3U(urls, f"{code.lower()}_cache.m3u")

            # Afficher par catégories (Sport / Autres) avec max 50 chaînes
            parseAndShowM3U(oGui, data, show_by="category", max_channels=50)

        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            import traceback

            VSlog(traceback.format_exc())
            oGui.addText("fStream", f"Erreur: {str(e)}")

        oGui.setEndOfDirectory()

    def showIPTV_Filtered(self):
        """Affiche les chaînes filtrées"""
        oGui = cGui()
        oInput = cInputParameterHandler()

        filter_type = oInput.getValue("filter_type")
        filter_value = oInput.getValue("filter_value")
        data = oInput.getValue("m3u_data")

        from resources.lib.comaddon import VSlog

        VSlog(f"[HOME] Filtrage: {filter_type}={filter_value}")

        try:
            parseAndShowChannels(oGui, data, filter_type, filter_value)
        except Exception as e:
            VSlog(f"[HOME] Erreur: {str(e)}")
            import traceback

            VSlog(traceback.format_exc())
            oGui.addText("fStream", f"Erreur: {str(e)}")

        oGui.setEndOfDirectory()

    def playIPTV(self):
        """Joue un flux IPTV"""
        oGui = cGui()
        oInputParameterHandler = cInputParameterHandler()
        sUrl = oInputParameterHandler.getValue("siteUrl")
        sTitle = oInputParameterHandler.getValue("sMovieTitle")

        from resources.lib.comaddon import VSlog

        VSlog(f"[HOME] Lecture: {sTitle}")

        oHoster = cHosterGui().checkHoster(sUrl)
        if oHoster:
            oHoster.setDisplayName(sTitle)
            oHoster.setFileName(sTitle)
            cHosterGui().showHoster(oGui, oHoster, sUrl, "")
        else:
            VSlog(f"[HOME] Pas de hoster pour: {sUrl}")
            xbmcgui.Dialog().ok("Erreur", "Impossible de lire ce flux")

        oGui.setEndOfDirectory()

    # ===== AUTRES MÉTHODES =====

    def showMenuTV(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()

        oOutputParameterHandler.addParameter("siteUrl", "TV")
        oGui.addDir(
            "freebox",
            "showWeb",
            self.addons.VSlang(30332),
            "tv.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "CHAINE_CINE")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            "%s (%s)" % (self.addons.VSlang(30200), self.addons.VSlang(30133)),
            "films.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "TV_TV")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            "%s (%s)" % (self.addons.VSlang(30138), self.addons.VSlang(30200)),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showReplay(self):
        oGui = cGui()

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("sCat", "6")
        oGui.addDir(
            SITE_IDENTIFIER,
            "showSearchText",
            self.addons.VSlang(30076),
            "search.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "REPLAYTV_NEWS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30101),
            "news.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "REPLAYTV_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30105),
            "genres.png",
            oOutputParameterHandler,
        )

        oOutputParameterHandler.addParameter("siteUrl", "REPLAYTV_REPLAYTV")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            self.addons.VSlang(30138),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showNets(self):
        oGui = cGui()

        # Affiche les Nouveautés Vidéos
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter("siteUrl", "NETS_NEWS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            "%s (%s)" % (self.addons.VSlang(30114), self.addons.VSlang(30101)),
            "news.png",
            oOutputParameterHandler,
        )

        # Affiche les Genres Vidéos
        oOutputParameterHandler.addParameter("siteUrl", "NETS_GENRES")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            "%s (%s)" % (self.addons.VSlang(30114), self.addons.VSlang(30105)),
            "genres.png",
            oOutputParameterHandler,
        )

        # Affiche les Sources Vidéos
        oOutputParameterHandler.addParameter("siteUrl", "NETS_NETS")
        oGui.addDir(
            SITE_IDENTIFIER,
            "callpluging",
            "%s (%s)" % (self.addons.VSlang(30138), self.addons.VSlang(30114)),
            "host.png",
            oOutputParameterHandler,
        )

        oGui.setEndOfDirectory()

    def showUsers(self):
        oGui = cGui()
        oGui.addDir(
            "siteonefichier", "load", self.addons.VSlang(30327), "sites/siteonefichier.png"
        )
        oGui.addDir("alldebrid", "load", "AllDebrid", "sites/alldebrid.png")
        oGui.addDir("sitedarkibox", "load", "DarkiBox", "sites/sitedarkibox.png")
        oGui.addDir("themoviedb_org", "showMyTmdb", "TMDB", "tmdb.png")
        oGui.addDir("cTrakt", "getLoad", self.addons.VSlang(30214), "trakt.png")
        oGui.setEndOfDirectory()

    def showTools(self):
        oGui = cGui()
        oGui.addDir(
            SITE_IDENTIFIER, "opensetting", self.addons.VSlang(30227), "parametres.png"
        )
        oGui.addDir("cDownload", "getDownload", self.addons.VSlang(30224), "download.png")
        oGui.addDir("cLibrary", "getLibrary", self.addons.VSlang(30303), "library.png")
        oGui.addDir(SITE_IDENTIFIER, "showHostDirect", self.addons.VSlang(30469), "web.png")
        oGui.addDir(
            SITE_IDENTIFIER, "showDonation", self.addons.VSlang(30143), "paypal.png"
        )
        oGui.addDir("globalSources", "globalSources", self.addons.VSlang(30449), "host.png")
        oGui.setEndOfDirectory()

    def showHistory(self):
        oGui = cGui()

        oInputParameterHandler = cInputParameterHandler()
        sCat = oInputParameterHandler.getValue("sCat")

        from resources.lib.db import cDb

        with cDb() as db:
            row = db.get_history(sCat)

        if row:
            oGui.addText(SITE_IDENTIFIER, self.addons.VSlang(30416), "")
        else:
            oGui.addText(SITE_IDENTIFIER)
        oOutputParameterHandler = cOutputParameterHandler()
        for match in row:
            sTitle = match["title"]
            sCat = match["disp"]

            # on ne propose l'historique que pour les films, séries, animes, doc, drama
            if int(sCat) not in (1, 2, 3, 5, 9):
                continue

            oOutputParameterHandler.addParameter("siteUrl", "http://lomixx")
            oOutputParameterHandler.addParameter("searchtext", sTitle)

            oGuiElement = cGuiElement()
            oGuiElement.setSiteName("globalSearch")
            oGuiElement.setFunction("globalSearch")

            try:
                oGuiElement.setTitle("- " + sTitle)
            except:
                oGuiElement.setTitle("- " + str(sTitle, "utf-8"))

            oGuiElement.setFileName(sTitle)
            oGuiElement.setCat(sCat)
            oGuiElement.setIcon("search.png")
            oGui.createSimpleMenu(
                oGuiElement,
                oOutputParameterHandler,
                SITE_IDENTIFIER,
                "cHome",
                "delSearch",
                self.addons.VSlang(30412),
            )
            oGui.addFolder(oGuiElement, oOutputParameterHandler)

        if row:
            oOutputParameterHandler.addParameter("siteUrl", "http://lomixx")
            oGui.addDir(
                SITE_IDENTIFIER,
                "delSearch",
                self.addons.VSlang(30413),
                "trash.png",
                oOutputParameterHandler,
            )

        oGui.setEndOfDirectory()

    def showDonation(self):
        from resources.lib.librecaptcha.gui import cInputWindowYesNo

        inputText = "Merci pour votre soutien, il permet de maintenir ce projet.\r\nScanner ce code ou rendez vous sur :\r\nhttps://www.paypal.com/paypalme/kodifstream"
        oSolver = cInputWindowYesNo(
            captcha="special://home/addons/plugin.video.fstream/paypal.jpg",
            msg=inputText,
            roundnum=1,
            okDialog=True,
        )
        oSolver.get()

    def showHostDirect(self):
        oGui = cGui()
        sUrl = oGui.showKeyBoard(heading=self.addons.VSlang(30045))
        if sUrl:
            oHoster = cHosterGui().checkHoster(sUrl)
            if oHoster:
                oHoster.setDisplayName(self.addons.VSlang(30046))
                oHoster.setFileName(self.addons.VSlang(30046))
                cHosterGui().showHoster(oGui, oHoster, sUrl, "")

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
        sSiteUrl = oInputParameterHandler.getValue("siteUrl")

        oPluginHandler = cPluginHandler()
        aPlugins = oPluginHandler.getAvailablePlugins(sSiteUrl)
        oOutputParameterHandler = cOutputParameterHandler()
        for aPlugin in aPlugins:
            try:
                icon = "sites/%s.png" % (aPlugin[2])
                oOutputParameterHandler.addParameter("siteUrl", aPlugin[0])
                oGui.addDir(
                    aPlugin[2], aPlugin[3], aPlugin[1], icon, oOutputParameterHandler
                )
            except:
                pass

        oGui.setEndOfDirectory()
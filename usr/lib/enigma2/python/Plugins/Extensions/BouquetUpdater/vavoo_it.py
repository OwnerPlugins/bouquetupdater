# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import logging
import os
from datetime import datetime

from . import _

try:
    from io import open
except ImportError:
    pass
try:
    from urllib.request import urlopen, Request
    # from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, Request

VAVOO_BOUQUET_NAME = _("Vavoo Italia")
VAVOO_BOUQUET_FILE = "userbouquet.vavooitalia.tv"
VAVOO_RESOLVED_BOUQUET_NAME = _("Vavoo Italia (Resolved)")
VAVOO_RESOLVED_BOUQUET_FILE = "userbouquet.vavooitaliares.tv"
VAVOO_HOST = "vavoo.to"

BASE_SITES = ["https://vavoo.to", "https://kool.to"]
LOKKE_PING_URL = "https://www.lokke.app/api/app/ping"
VAVOO_PING_URL = "https://www.vavoo.tv/api/app/ping"
PING_URLS = [LOKKE_PING_URL, VAVOO_PING_URL]
COUNTRY_SEPARATORS = [u"\u27be", u"\u27fe", "->", u"\u2192", u"\u00bb", u"\u203a"]
LANGUAGE = "it"
REGION = "US"

# Channel groups
CHANNEL_GROUPS = {
    "Rai": [
        "Rai 1", "Rai 2", "Rai 3", "Rai 4", "Rai 5", "Rai Movie", "Rai Premium",
        "Rai Gulp", "Rai Yoyo", "Rai Storia", "Rai Scuola", "Rai News 24",
        "Rai Sport", "Rai 4K", "Rai Italia"
    ],
    "Mediaset": [
        "Canale 5", "Italia 1", "Rete 4", "20 Mediaset", "La 5", "Italia 2", "Italia 3",
        "Cine 34", "Focus", "Iris", "Top Crime", "Boing", "Cartoonito", "Mediaset Extra",
        "Mediaset 1", "Mediaset 20", "Mediaset Italia", "Mediaset Italia 2", "Mediaset Iris",
        "Cine 34 Mediaset", "TGCOM 24", "TG COM 24"
    ],
    "Sky Cinema": [
        "Sky Cinema Uno", "Sky Cinema Due", "Sky Cinema Family", "Sky Cinema Collection",
        "Sky Cinema Comedy", "Sky Cinema Action", "Sky Cinema Romance", "Sky Cinema Suspense",
        "Sky Cinema Drama", "Sky Cinema Uno +24", "Sky Cinema Action (Backup)"
    ],
    "Sky Primafila": [
        "Sky Primafila 1", "Sky Primafila 2", "Sky Primafila 3", "Sky Primafila 4",
        "Sky Primafila 5", "Sky Primafila 6", "Sky Primafila 7", "Sky Primafila 8",
        "Sky Primafila 9", "Sky Primafila 10", "Sky Primafila 11", "Sky Primafila 12",
        "Sky Primafila 13", "Sky Primafila 14", "Sky Primafila 15", "Sky Primafila 16",
        "Sky Primafila 17"
    ],
    "Sky Sport": [
        "Sky Sport 24", "Sky Sport Football", "Sky Sport Arena", "Sky Sport Tennis",
        "Sky Sport F1", "Sky Sport Golf", "Sky Sport MotoGP", "Sky Sport NBA",
        "Sky Sport Uno", "Sky Sport Calcio", "Sky Sport Max", "Sky Sports F1",
        "Sky Super Tennis", "Sky Sport Moto GP"
    ],
    "Sky": [
        "Sky Uno", "Sky Atlantic", "Sky Arte", "Sky Serie", "Sky TG 24",
        "Sky Crime", "Sky Documentaries", "Sky Investigation", "Sky Nature"
    ],
    "Sport": [
        "Eurosport 1", "Eurosport 2", "Eurosport 2 Timvision", "Eurosport 4 Timvision",
        "Eurosport 5 Timvision", "Eurosport 6 Timvision", "Super Tennis", "Sport Italia",
        "Sportitalia Plus", "Sportitalia Solocalcio", "Dazn 1", "Dazn 2",
        "Aci Sport TV", "Bike", "Trsport"
    ],
    "Discovery/Warner": [
        "Discovery Channel", "Discovery Focus", "Discovery K2", "Discovery Nove",
        "Discovery Science", "DMAX", "Real Time", "Food Network", "HGTV", "Giallo",
        "Animal Planet", "Motortrend", "Nove", "Frisbee"
    ],
    "Kids": [
        "Cartoon Network", "Boomerang", "K2", "Super!", "Nick Jr", "Nickelodeon",
        "Baby TV", "Iunior TV", "Cartoonito (Backup)"
    ],
    "Musica": [
        "Deejay TV", "M2O", "RTL 102.5", "RDS Social TV", "RDS Social", "Kiss Kiss",
        "Kiss Kiss Italia", "Kiss Kiss Napoli", "Radio Capital", "Radio Freccia",
        "Radio 51", "VH1", "70-80.IT", "Euro Indie Music Chart TV", "51 Radio TV",
        "Radionorba TV", "FM Italia TV", "FM Italia"
    ],
    "News/Informazione": [
        "La 7", "La 7 D", "Euronews", "Bloomberg TV", "Bloomberg TV 4K",
        "Camera dei Deputati", "Senato TV", "Cusano News7", "TG Norba 24", "TV7 News",
        "Byoblu"
    ],
    "Documentari/Cultura": [
        "Nat Geo", "Nat Geo Wild", "History", "Classica", "Arte Network", "Aurora Arte",
        "Gambero Rosso", "Caccia e Pesca", "Pesca e Caccia", "Italian Fishing TV"
    ],
    "Calcio/Squadre": [
        "Milan TV", "Inter TV", "Lazio TV 13"
    ],
    "Religiosi": [
        "TV 2000", "TV2000", "Padre Pio TV", "Telepace 1", "Telepace 2", "Telepace 3",
        "Telepace 4", "Telepace Trento (History Lab)", "Maria+Vision", "Parole di Vita"
    ],
    "Shopping": [
        "QVC Italia", "QVC"
    ],
    "Svizzera": [
        "RSI LA 1", "RSI LA 2", "San Marino RTV", "RTV San Marino"
    ],
    "Intrattenimento": [
        "Cielo", "TV 8", "Comedy Central", "Blaze", "Fox", "Premium Crime",
        "Crime + Inv", "Star Channel", "Star Crime", "Skyshowtime 1", "Disney+ Film",
        "Company TV"
    ],
    "TV Locali": [
        "111 TV", "12 TV Parma", "27 Twenty Seven", "27 Twentyseven", "7 You & Me",
        "A3", "Alma TV", "Alto Adige TV", "Antenna 2", "Arancia TV", "Bella Radio TV",
        "Bellla & Monella TV", "Bergamo TV", "Cafe 24", "Canale 122", "Canale 2",
        "Canale 21 Campania", "Canale 21 Extra", "Canale 7", "Canale 8", "Canale Dieci",
        "Carina TV", "Cremona 1", "Elive TV Brescia", "Entella TV", "Equ TV",
        "Espansione TV", "Esperia TV", "Esperia TV 18", "ETV Marche", "Euro TV",
        "Extra TV", "Fano TV", "Globus Television", "Gold TV", "Granducato",
        "Icaro TV", "La C Onair", "La C TV", "La Nuova TV", "La TR3", "Lira TV",
        "Love FM TV", "OL3 Radio", "Onda Novara TV", "Onda TV", "Orler TV",
        "Peer TV Alto Adige", "Prima TV", "Primo Canale", "Primocanale", "Quarta Rete",
        "Reggio TV", "Rei TV", "Rete 8", "Rete Oro", "Rete TV Italia", "Rete Veneta",
        "Retebiella TV", "RMC 101", "RTC Telecalabria", "RTM TV", "RTP (Rete Televisiva)",
        "RTR 99 TV", "RTTR", "RTTR TV", "Stereo 5 TV", "Super TV Aristanis",
        "Super TV Brescia", "Supersix Lombardia", "Tele Abruzzo", "Tele Chiara",
        "Tele Friuli", "Tele Liguria Sud", "Tele Pavia", "Tele Tricolore",
        "Tele Tusciasabina 2000", "Telearena", "Telearte", "Telebari", "Telebelluno",
        "Teleboario", "Telecitta", "Telecolor", "Telefoggia", "Telemantova", "Telemia",
        "Telemistretta", "Telemolise", "Telenord", "Telequattro", "Telerama",
        "Teleromagna", "Telesirio", "Telespazio TV", "Teletricolore", "Teletutto",
        "Trentino TV", "TV Luna", "TV Qui (Modena)", "TV Qui", "TVA Vicenza", "TVRS",
        "Umbria TV", "VCO Azzurra TV", "Video Novara", "Videolina", "Videostar TV",
        "Videotolentino", "ÈTV Marche", "ÈTV Rete 7"
    ]
}

_sig_cache = [None, 0]
_channels_cache = [None, 0]
CACHE_TTL = 300


def _now():
    import time
    return time.time()


def _post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "User-Agent": "MediaHubMX/2"}
    if headers:
        req_headers.update(headers)
    req = Request(url, data=data, headers=req_headers)
    try:
        r = urlopen(req, timeout=30)
        status_code = r.getcode()
        try:
            response_text = r.read().decode("utf-8", errors="ignore")
            if not response_text or not response_text.strip():
                logging.debug("[vavoo] POST {} returned empty response (status: {})".format(url, status_code))
                return None
            if status_code != 200:
                logging.debug("[vavoo] POST {} returned status {}".format(url, status_code))
                return None
            return json.loads(response_text)
        finally:
            try:
                r.close()
            except Exception:
                pass
    except ValueError as e:
        logging.debug("[vavoo] POST {} JSON decode error: {}".format(url, e))
        return None
    except Exception as e:
        logging.debug("[vavoo] POST {} failed: {}".format(url, e))
        return None


def _get_addon_signature():
    logging.info("[vavoo] Requesting addon signature")
    if _sig_cache[0] and (_now() - _sig_cache[1]) < CACHE_TTL:
        logging.info("[vavoo] Signature found in cache")
        return _sig_cache[0]

    logging.info("[vavoo] Generating new signature")
    ts = int(_now() * 1000)

    payload = {
        "reason": "app-focus",
        "locale": LANGUAGE,
        "theme": "dark",
        "metadata": {
            "device": {"type": "desktop", "uniqueId": "py-{}".format(ts)},
            "os": {"name": "linux", "version": "Linux", "abis": ["x64"], "host": "node"},
            "app": {"platform": "electron"},
            "version": {"package": "tv.vavoo.app", "binary": "3.1.8", "js": "3.1.8"}
        },
        "appFocusTime": 0,
        "playerActive": False,
        "playDuration": 0,
        "devMode": False,
        "hasAddon": True,
        "castConnected": False,
        "package": "tv.vavoo.app",
        "version": "3.1.8",
        "process": "app",
        "firstAppStart": ts,
        "lastAppStart": ts,
        "ipLocation": None,
        "adblockEnabled": True,
        "proxy": {"supported": ["ss"], "engine": "Mu", "enabled": False, "autoServer": True},
        "iap": {"supported": False}
    }

    for ping_url in PING_URLS:
        logging.info("[vavoo] Trying ping: {}".format(ping_url))
        body = _post_json(ping_url, payload)
        if body and isinstance(body, dict):
            sig = body.get("addonSig")
            if sig:
                _sig_cache[0] = sig
                _sig_cache[1] = _now()
                logging.info("[vavoo] addonSig obtained successfully from {}".format(ping_url))
                return sig
        logging.warning("[vavoo] No addonSig from {}".format(ping_url))

    logging.error("[vavoo] Unable to obtain addonSig from any server")
    logging.error("[vavoo] NOTE: Vavoo service may be temporarily unavailable")
    logging.error("[vavoo] SUGGESTION: Use the non-resolved 'Vavoo Italia' bouquet which does not require signature")
    return None


def _extract_country(group):
    raw = (group or "").strip()
    if not raw:
        return "default"
    for sep in COUNTRY_SEPARATORS:
        if sep in raw:
            return raw.split(sep)[0].strip() or "default"
    return raw


def _catalog_headers(sig):
    return {
        "content-type": "application/json; charset=utf-8",
        "mediahubmx-signature": sig,
        "user-agent": "MediaHubMX/2",
        "Accept-Language": LANGUAGE,
    }


def _load_catalog(base_url, sig):
    url = base_url.rstrip("/") + "/mediahubmx-catalog.json"
    headers = _catalog_headers(sig)
    channels = []
    cursor = None

    while True:
        payload = {
            "language": LANGUAGE, "region": REGION,
            "catalogId": "iptv", "id": "iptv",
            "adult": False, "search": "", "sort": "", "filter": {},
            "cursor": cursor, "clientVersion": "3.0.2"
        }
        body = _post_json(url, payload, headers)
        if not body:
            break

        for item in (body.get("items") or []):
            if item.get("type") == "iptv" and item.get("url"):
                country = _extract_country(item.get("group", ""))
                channels.append({
                    "id": str(item.get("ids", {}).get("id") or item.get("id") or item.get("url")),
                    "url": item["url"],
                    "name": item.get("name") or "Unknown",
                    "logo": item.get("logo") or "",
                    "country": country
                })

        cursor = body.get("nextCursor")
        if not cursor:
            break

    return channels


def _get_channels():
    logging.info("[vavoo] Requesting channel list")
    if _channels_cache[0] and (_now() - _channels_cache[1]) < CACHE_TTL:
        logging.info("[vavoo] Channel list found in cache: {} channels".format(len(_channels_cache[0])))
        return _channels_cache[0]

    logging.info("[vavoo] Downloading new channel list")
    sig = _get_addon_signature()
    if not sig:
        raise Exception("[vavoo] Unable to obtain signature to load catalog")

    for base in BASE_SITES:
        logging.info("[vavoo] Trying to load catalog from: {}".format(base))
        try:
            channels = _load_catalog(base, sig)
            if channels:
                logging.info("[vavoo] {} channels loaded from {}".format(len(channels), base))
                _channels_cache[0] = channels
                _channels_cache[1] = _now()
                return channels
        except Exception as e:
            logging.error("[vavoo] Catalog from {} failed: {}".format(base, e))
            logging.exception("[vavoo] Error details:")

    logging.error("[vavoo] Unable to load catalog from any server")
    raise Exception("[vavoo] Unable to load catalog")


def _resolve_stream(channel_url, sig):
    """Resolve the stream URL from a Vavoo channel."""
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "*/*",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip, deflate",
        "mediahubmx-signature": sig,
        "accept-language": LANGUAGE,
        "connection": "close"
    }

    for base in BASE_SITES:
        url = base.rstrip("/") + "/mediahubmx-resolve.json"
        payload = {
            "language": LANGUAGE,
            "region": REGION,
            "url": channel_url,
            "clientVersion": "3.0.2"
        }

        try:
            body = _post_json(url, payload, headers)
            if not body:
                continue

            resolved_url = None
            if isinstance(body, list) and body:
                resolved_url = body[0].get("url")
            elif isinstance(body, dict):
                resolved_url = body.get("url")
                if not resolved_url:
                    resolved_url = body.get("streamUrl")

            if resolved_url:
                try:
                    from urllib.parse import unquote
                except ImportError:
                    from urllib import unquote

                resolved_url = str(resolved_url)
                prev_url = None
                while prev_url != resolved_url:
                    prev_url = resolved_url
                    resolved_url = unquote(resolved_url)

                logging.debug("[vavoo] Resolved stream: {}".format(resolved_url[:100]))
                return resolved_url
        except Exception as e:
            logging.warning("[vavoo] Resolve error from {}: {}".format(base, e))

    return None


def _classify_channel(channel_name):
    """Classify a channel into the appropriate group."""
    normalized_name = channel_name.strip()
    if normalized_name.endswith(' .c') or normalized_name.endswith(' .s'):
        normalized_name = normalized_name[:-3].strip()
    normalized_name = normalized_name.lower()

    for group_name, channel_list in CHANNEL_GROUPS.items():
        for channel_in_group in channel_list:
            if normalized_name == channel_in_group.lower().strip():
                return group_name

    return "Generalisti"


def _generate_bouquet(channels_by_group, bouquet_name=VAVOO_BOUQUET_NAME):
    """Generate the bouquet organized by groups."""
    date_str = datetime.now().strftime("%d.%m.%Y")
    lines = [
        "#NAME {}\n".format(bouquet_name),
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:\n",
        "#DESCRIPTION --- {} ---\n".format(_("Updated on {}").format(date_str)),
    ]

    group_order = [
        "Rai", "Mediaset", "Sky Cinema", "Sky Primafila", "Sky Sport", "Sky",
        "Sport", "Discovery/Warner", "Kids", "Musica", "News/Informazione",
        "Documentari/Cultura", "Calcio/Squadre", "Religiosi", "Shopping",
        "Svizzera", "Intrattenimento", "TV Locali", "Generalisti"
    ]

    for group_name in group_order:
        channels = channels_by_group.get(group_name, [])
        if not channels:
            continue

        lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0::{}\n".format(group_name))
        lines.append("#DESCRIPTION {}\n".format(group_name))

        for name, stream_url in channels:
            escaped_url = stream_url.replace(':', '%3a').replace('/', '%2f')
            lines.append("#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n".format(escaped_url, name))
            lines.append("#DESCRIPTION {}\n".format(name))

    return "".join(lines)


def process_vavoo_italia(bouquet_filename):
    """Download Vavoo catalog, filter Italy, classify by groups, write bouquet. Returns True on success."""
    logging.info("[vavoo] ===== START VAVOO ITALIA PROCESS =====")
    logging.info("[vavoo] Bouquet: {}".format(bouquet_filename))

    try:
        channels = _get_channels()
    except Exception as e:
        logging.error("[vavoo] Error loading channels: {}".format(e))
        return False

    italy = [ch for ch in channels if ch["country"].lower() == "italy"]
    logging.info("[vavoo] {} Italian channels found out of {}".format(len(italy), len(channels)))

    if not italy:
        logging.warning("[vavoo] No Italian channels found")
        return False

    logging.info("[vavoo] Classifying channels into groups")
    channels_by_group = {}
    for group_name in list(CHANNEL_GROUPS.keys()) + ["Generalisti"]:
        channels_by_group[group_name] = []

    for ch in italy:
        group = _classify_channel(ch["name"])
        channels_by_group[group].append((ch["name"], ch["url"]))
        logging.debug("[vavoo] {} -> group {}".format(ch["name"], group))

    total_channels = sum(len(channels) for channels in channels_by_group.values())

    if total_channels == 0:
        logging.error("[vavoo] No channels found after classification")
        return False

    for group_name, channels in channels_by_group.items():
        if channels:
            logging.info("[vavoo] Group '{}': {} channels".format(group_name, len(channels)))

    logging.info("[vavoo] Sorting channels within each group")
    for group_name in channels_by_group:
        channels_by_group[group_name].sort(key=lambda x: x[0].lower())

    logging.info("[vavoo] Generating bouquet content")
    content = _generate_bouquet(channels_by_group, VAVOO_BOUQUET_NAME)

    filepath = "/etc/enigma2/{}".format(bouquet_filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info("[vavoo] Bouquet written: {} ({} bytes)".format(filepath, len(content)))
        logging.info("[vavoo] ===== PROCESS COMPLETED SUCCESSFULLY =====")
        return True
    except IOError as e:
        logging.error("[vavoo] Error writing {}: {}".format(filepath, e))
        logging.exception("[vavoo] Error details:")
        return False


def process_vavoo_italia_resolved(bouquet_filename):
    """Download Vavoo catalog, filter Italy, resolve streams, classify, write bouquet. Returns True on success."""
    logging.info("[vavoo] ===== START VAVOO ITALIA RESOLVED PROCESS =====")
    logging.info("[vavoo] Bouquet: {}".format(bouquet_filename))
    logging.warning("[vavoo] WARNING: The Vavoo Resolved service may not work")
    logging.warning("[vavoo] Vavoo servers no longer allow direct stream resolution")
    logging.warning("[vavoo] SUGGESTION: Use the 'Vavoo Italia' (non-resolved) bouquet which works correctly")
    logging.info("[vavoo] Attempting resolution...")

    try:
        channels = _get_channels()
    except Exception as e:
        logging.error("[vavoo] Error loading channels: {}".format(e))
        logging.exception("[vavoo] Stack trace:")
        return False

    italy = [ch for ch in channels if ch["country"].lower() == "italy"]
    logging.info("[vavoo] {} Italian channels found out of {}".format(len(italy), len(channels)))

    if not italy:
        logging.warning("[vavoo] No Italian channels found")
        return False

    logging.info("[vavoo] Starting stream resolution and classification")
    channels_by_group = {}
    for group_name in list(CHANNEL_GROUPS.keys()) + ["Generalisti"]:
        channels_by_group[group_name] = []

    sig = _get_addon_signature()
    if not sig:
        logging.error("[vavoo] Unable to obtain signature")
        logging.error("[vavoo] Use the 'Vavoo Italia' (non-resolved) bouquet instead")
        return False

    resolved_count = 0
    failed_count = 0

    # Test on first 5 channels
    test_channels = italy[:5]
    logging.info("[vavoo] Testing resolution on {} channels...".format(len(test_channels)))

    for ch in test_channels:
        try:
            stream_url = _resolve_stream(ch["url"], sig)
            if stream_url:
                resolved_count += 1
                logging.info("[vavoo] Test OK: {} resolved".format(ch["name"]))
                break
        except Exception as e:
            failed_count += 1
            print('error: ', str(e))

    if resolved_count == 0:
        logging.error("[vavoo] Test failed: no stream resolved")
        logging.error("[vavoo] The Vavoo Resolved service is NOT available")
        logging.error("[vavoo] Use the 'Vavoo Italia' (non-resolved) bouquet instead")
        return False

    logging.info("[vavoo] Test passed! Proceeding with full resolution...")
    logging.info("[vavoo] This may take about {} seconds...".format(len(italy) * 2))

    resolved_count = 0
    failed_count = 0

    for idx, ch in enumerate(italy, 1):
        if idx % 10 == 0:
            logging.info("[vavoo] Resolution progress: {}/{} ({:.1f}%)".format(
                idx, len(italy), (idx * 100.0 / len(italy))))

        try:
            stream_url = _resolve_stream(ch["url"], sig)
            if stream_url:
                group = _classify_channel(ch["name"])
                channels_by_group[group].append((ch["name"], stream_url))
                resolved_count += 1
                logging.debug("[vavoo] {} -> resolved and classified in {}".format(ch["name"], group))
            else:
                failed_count += 1
                logging.debug("[vavoo] Stream not resolved for: {}".format(ch["name"]))
        except Exception as e:
            failed_count += 1
            logging.debug("[vavoo] Resolution error for {}: {}".format(ch["name"], e))

    logging.info("[vavoo] Resolution completed: {} successes, {} failures".format(resolved_count, failed_count))

    if resolved_count == 0:
        logging.error("[vavoo] No streams resolved - cannot create bouquet")
        logging.error("[vavoo] The Vavoo Resolved service does NOT work")
        return False

    logging.info("[vavoo] Summary by group:")
    for group_name, channels in channels_by_group.items():
        if channels:
            logging.info("[vavoo]   - Group '{}': {} channels".format(group_name, len(channels)))

    logging.info("[vavoo] Sorting channels within each group")
    for group_name in channels_by_group:
        channels_by_group[group_name].sort(key=lambda x: x[0].lower())

    logging.info("[vavoo] Generating bouquet content")
    try:
        content = _generate_bouquet(channels_by_group, VAVOO_RESOLVED_BOUQUET_NAME)
        logging.info("[vavoo] Content generated: {} bytes".format(len(content)))
    except Exception as e:
        logging.error("[vavoo] Error generating bouquet: {}".format(e))
        logging.exception("[vavoo] Stack trace:")
        return False

    filepath = "/etc/enigma2/{}".format(bouquet_filename)
    logging.info("[vavoo] Writing file: {}".format(filepath))

    try:
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            logging.error("[vavoo] Directory does not exist: {}".format(directory))
            return False

        if not os.access(directory, os.W_OK):
            logging.error("[vavoo] No write permission on: {}".format(directory))
            return False

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        if not os.path.exists(filepath):
            logging.error("[vavoo] File not found after writing: {}".format(filepath))
            return False

        file_size = os.path.getsize(filepath)
        logging.info("[vavoo] Resolved bouquet written successfully: {} ({} bytes)".format(filepath, file_size))

        if file_size == 0:
            logging.error("[vavoo] File written but empty!")
            return False

        logging.info("[vavoo] ===== PROCESS COMPLETED SUCCESSFULLY =====")
        return True

    except IOError as e:
        logging.error("[vavoo] IOError writing {}: {}".format(filepath, e))
        logging.exception("[vavoo] Stack trace:")
        return False
    except Exception as e:
        logging.error("[vavoo] Generic error writing {}: {}".format(filepath, e))
        logging.exception("[vavoo] Stack trace:")
        return False


def is_vavoo_url(url):
    """Check if the URL is for Vavoo (supports vavoo.to and kool.to)."""
    return VAVOO_HOST in url or 'kool.to' in url

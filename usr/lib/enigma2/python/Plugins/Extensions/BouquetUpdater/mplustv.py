# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import json
import logging
import re
from datetime import datetime

try:
    from . import _
except (ImportError, ValueError):
    from __init__ import _

try:
    from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse
    from urllib.request import Request, urlopen
except ImportError:
    from urllib import quote, urlencode
    from urlparse import parse_qs, urljoin, urlparse
    from urllib2 import Request, urlopen


BASE_URL = "https://myplustv.it"
DEFAULT_SOURCE_URL = BASE_URL + "/"
CHANNEL_PAGES = (
    ("Sport", BASE_URL + "/plus-tv-sport/"),
    ("Motors", BASE_URL + "/plus-tv-motori/"),
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux; Enigma2) AppleWebKit/537.36 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def is_mplustv_url(url):
    try:
        host = urlparse(url).netloc.lower().split(':', 1)[0]
    except Exception:
        return False
    return host == "myplustv.it" or host.endswith(".myplustv.it")


def _request(url, headers=None, data=None, timeout=15):
    request_headers = dict(HEADERS)
    if headers:
        request_headers.update(headers)
    if data is not None and not isinstance(data, bytes):
        data = data.encode("utf-8")
    response = urlopen(Request(url, data=data, headers=request_headers), timeout=timeout)
    return response.read().decode("utf-8", "ignore")


def _get_localtv_stream(page_url):
    html = _request(page_url)
    match = re.search(
        r'href=["\'](https?://local-tv\.it/player/[^"\']+)["\']',
        html, re.IGNORECASE)
    if not match:
        raise ValueError("local-tv.it player not found")
    player_url = match.group(1)
    player_html = _request(player_url, {"Referer": page_url})
    match = re.search(r'<source[^>]+src=["\']([^"\']+)["\']',
                      player_html, re.IGNORECASE)
    if not match:
        raise ValueError("HLS stream not found")
    return urljoin(player_url, match.group(1))


def _get_iframe(page_url):
    html = _request(page_url)
    match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']',
                      html, re.IGNORECASE)
    if not match:
        raise ValueError("WimTV iframe not found")
    return urljoin(page_url, match.group(1))


def _get_access_token(referer):
    basic = base64.b64encode(b"www:").decode("ascii")
    body = urlencode({"grant_type": "client_credentials"})
    result = _request(
        "https://platform.wim.tv/wimtv-server/oauth/token",
        {
            "Authorization": "Basic " + basic,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://platform.wim.tv",
            "Referer": referer,
        }, body)
    return json.loads(result)["access_token"]


def _play_wim(iframe_url, token, kind):
    params = parse_qs(urlparse(iframe_url).query)
    item_id = params.get("cast" if kind == "live" else "vod", [None])[0]
    if not item_id:
        raise ValueError("WimTV identifier not found")
    if kind == "live":
        endpoint = "api/public/cast/channel/{}/play".format(item_id)
    else:
        endpoint = "api/public/vod/{}/play".format(item_id)
    result = _request(
        "https://platform.wim.tv/wimtv-server/" + endpoint,
        {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Origin": "https://platform.wim.tv",
            "Referer": iframe_url,
        }, "{}")
    payload = json.loads(result)
    stream = payload.get("uniqueStreamer")
    if payload.get("srcs"):
        stream = payload["srcs"][0].get("uniqueStreamer", stream)
    if not stream:
        raise ValueError("WimTV stream not found")
    parsed = urlparse(stream)
    if kind == "live" and not parsed.path.endswith(".m3u8"):
        stream = parsed._replace(
            path=parsed.path.rstrip("/") + "/playlist.m3u8").geturl()
    return stream


def _cinema_links():
    html = _request(BASE_URL + "/cinema/")
    links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    live = set()
    vod = set()
    for link in links:
        absolute = urljoin(BASE_URL, link)
        if not is_mplustv_url(absolute):
            continue
        if "/watch_cinema/" in absolute:
            vod.add(absolute)
        elif "live" in absolute.lower():
            live.add(absolute)
    return sorted(live), sorted(vod)


def _title_from_url(url, kind):
    if kind == "vod":
        title = parse_qs(urlparse(url).query).get("title", [""])[0]
    else:
        title = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    title = re.sub(r"[-_]+", " ", title).strip()
    return title.title() or _("Unknown channel")


def _report_progress(callback, percent, status):
    if callback:
        try:
            callback(percent, status)
        except Exception:
            pass


def fetch_channels(source_url=DEFAULT_SOURCE_URL, progress_callback=None):
    del source_url  # The configured URL identifies this provider.
    groups = []
    _report_progress(progress_callback, 3, _("Starting download..."))
    for page_index, (group_name, page_url) in enumerate(CHANNEL_PAGES, 1):
        try:
            groups.append((group_name, [("Plus TV " + group_name,
                                         _get_localtv_stream(page_url))]))
        except Exception as error:
            logging.warning("[MPlusTV] %s unavailable: %s", group_name, error)
        _report_progress(progress_callback, 5 + page_index * 5,
                         _("Downloading channels {}/{}").format(
                             page_index, len(CHANNEL_PAGES)))

    try:
        live_links, vod_links = _cinema_links()
    except Exception as error:
        logging.warning("[MPlusTV] Cinema index unavailable: %s", error)
        live_links, vod_links = [], []

    token = None
    total_links = len(live_links) + len(vod_links)
    completed_links = 0
    for group_name, kind, links in (("Cinema Live", "live", live_links),
                                    ("Cinema VOD", "vod", vod_links)):
        channels = []
        for page_url in links:
            try:
                iframe = _get_iframe(page_url)
                if token is None:
                    token = _get_access_token(iframe)
                channels.append((_title_from_url(page_url, kind),
                                 _play_wim(iframe, token, kind)))
            except Exception as error:
                logging.warning("[MPlusTV] Skipping %s: %s", page_url, error)
            completed_links += 1
            percent = 20 + int((completed_links * 75) / max(total_links, 1))
            _report_progress(
                progress_callback, percent,
                _("Downloading channels {}/{}").format(
                    completed_links, total_links))
        if channels:
            groups.append((group_name, channels))
    return groups


def generate_bouquet(groups):
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [
        "#NAME MPlusTV\n",
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:\n",
        "#DESCRIPTION {}\n".format(_("Updated on {}").format(date_str)),
    ]
    index = 1
    for group_name, channels in groups:
        if not channels:
            continue
        translated_group = _(group_name)
        lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
        lines.append("#DESCRIPTION *** {} ***\n".format(translated_group))
        for name, stream_url in channels:
            lines.append(
                "#SERVICE 4097:0:1:{}:0:0:0:0:0:0:{}:{}\n".format(
                    index, quote(stream_url, safe=""), quote(name, safe="")))
            lines.append("#DESCRIPTION {}\n".format(name))
            index += 1
    return "".join(lines)


def write_bouquet(filename, content):
    path = "/etc/enigma2/{}".format(filename)
    try:
        try:
            with open(path, "w", encoding="utf-8") as output:
                output.write(content)
        except TypeError:
            import codecs
            with codecs.open(path, "w", encoding="utf-8") as output:
                output.write(content)
        return True
    except Exception as error:
        logging.error("[MPlusTV] Cannot write %s: %s", path, error)
        logging.exception("[MPlusTV] Write failure")
        return False


def process_mplustv(url, filename, progress_callback=None):
    try:
        groups = fetch_channels(url, progress_callback)
        total = sum(len(channels) for _, channels in groups)
        if not total:
            logging.warning("[MPlusTV] No channels found")
            return False
        _report_progress(progress_callback, 97, _("Creating bouquet..."))
        result = write_bouquet(filename, generate_bouquet(groups))
        _report_progress(
            progress_callback, 100,
            _("Completed!") if result else _("Failed"))
        return result
    except Exception as error:
        logging.error("[MPlusTV] Processing failed: %s", error)
        logging.exception("[MPlusTV] Stack trace")
        return False

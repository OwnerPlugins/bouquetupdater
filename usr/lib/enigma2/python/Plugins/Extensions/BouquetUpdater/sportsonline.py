# -*- coding: utf-8 -*-
from __future__ import absolute_import

import re
import logging
from datetime import datetime

from . import _

try:
    from io import open
except ImportError:
    pass
try:
    from urllib.parse import quote
    from urllib.request import urlopen, Request
except ImportError:
    from urllib import quote
    from urllib2 import urlopen, Request

SPORTSONLINE_HOST = "sportsonline.vc"

DAYS_EN = [
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY"]

# HDx/BRx channel id -> language label
HD_LANGS = {
    "hd1": "ENGLISH", "hd2": "ENGLISH", "hd3": "GERMAN", "hd4": "BELGIAN",
    "hd5": "ENGLISH", "hd6": "SPANISH", "hd7": "ITALIAN", "hd8": "ITALIAN",
    "hd9": "SPANISH", "hd10": "GERMAN", "hd11": "TURKISH & SPANISH",
}
BR_LANG = "BRAZILIAN"


def _lang_from_url(url):
    """Extract language label from stream URL based on HDx/BRx channel id."""
    m = re.search(r'/(hd\d+|br\d+)\.php', url, re.IGNORECASE)
    if not m:
        return None
    ch = m.group(1).lower()
    if ch.startswith("br"):
        return BR_LANG
    return HD_LANGS.get(ch)


def _fetch(url):
    logging.info("[sportsonline] Fetch URL: {}".format(url))
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urlopen(req, timeout=30)
        try:
            content = r.read().decode("utf-8", errors="ignore")
            logging.info(
                "[sportsonline] Download completed: {} bytes".format(
                    len(content)))
            return content
        finally:
            try:
                r.close()
            except Exception:
                pass
    except Exception as e:
        logging.error("[sportsonline] Download error {}: {}".format(url, e))
        logging.exception("[sportsonline] Error details:")
        return None


def _adjust_time_to_italian(time_str):
    """Add 1 hour to align with Italian timezone."""
    try:
        hour, minute = map(int, time_str.split(':'))
        hour = (hour + 1) % 24
        return "{:02d}:{:02d}".format(hour, minute)
    except Exception:
        return time_str


def _parse_prog(content):
    """
    Returns list of (time_str, event_name, stream_url, lang_or_None)
    for today's day section only.
    """
    logging.info("[sportsonline] Parsing program data")
    today_name = DAYS_EN[datetime.now().weekday()]
    logging.info("[sportsonline] Current day: {}".format(today_name))
    lines = [zl.strip() for zl in content.splitlines()]
    logging.info("[sportsonline] Total lines: {}".format(len(lines)))

    in_today = False
    channel_map = {}
    events = []

    ch_def_re = re.compile(r'^(HD\d+|BR\d+)\s+(.+)$', re.IGNORECASE)
    event_re = re.compile(r'^(\d{1,2}:\d{2})\s+(.+?)\s*\|\s*(https?://\S+)$')

    for line in lines:
        if not line:
            continue

        if line.upper() in DAYS_EN:
            in_today = (line.upper() == today_name)
            if in_today:
                logging.info(
                    "[sportsonline] Section {} found".format(today_name))
            channel_map = {}
            continue

        if not in_today:
            continue

        m = ch_def_re.match(line)
        if m:
            ch_id = m.group(1).upper()
            lang = re.sub(r'&amp;', '&', m.group(2).strip())
            channel_map[ch_id] = lang
            logging.debug(
                "[sportsonline] Channel defined: {} = {}".format(
                    ch_id, lang))
            continue

        m = event_re.match(line)
        if m:
            time_str = m.group(1)
            time_str = _adjust_time_to_italian(time_str)
            name = re.sub(
                r'&amp;', '&', re.sub(
                    r'&#39;', "'", m.group(2).strip()))
            url = m.group(3)
            lang = _lang_from_url(url)
            events.append((time_str, name, url, lang))
            logging.debug(
                "[sportsonline] Event: {} - {}".format(time_str, name))

    logging.info("[sportsonline] Today's events found: {}".format(len(events)))
    return events


def _generate_bouquet(events):
    date_str = datetime.now().strftime("%d.%m.%Y")
    lines = [
        "#NAME Sportsonline\n",
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:\n",
        "#DESCRIPTION --- {} ---\n".format(_("Updated on {}").format(date_str)),
    ]
    for time_str, name, url, lang in events:
        label = "{} {}".format(time_str, name)
        if lang:
            label += " ({})".format(lang)
        lines.append("#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n".format(
            quote(url), quote(label)))
        lines.append("#DESCRIPTION {}\n".format(label))
    return "".join(lines)


def process_sportsonline(url, bouquet_filename):
    """
    Download prog.txt, parse today's events, write bouquet file.
    Returns True on success.
    """
    logging.info("[sportsonline] ===== START SPORTSONLINE PROCESS =====")
    logging.info("[sportsonline] URL: {}".format(url))
    logging.info("[sportsonline] Bouquet: {}".format(bouquet_filename))

    content = _fetch(url)
    if not content:
        logging.error("[sportsonline] Download failed")
        return False

    events = _parse_prog(content)
    if not events:
        logging.warning("[sportsonline] No events found for today.")
        return False

    logging.info(
        "[sportsonline] {} events found for today.".format(
            len(events)))
    bouquet_content = _generate_bouquet(events)

    filepath = "/etc/enigma2/{}".format(bouquet_filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(bouquet_content)
        logging.info("[sportsonline] Bouquet written: {}".format(filepath))
        logging.info(
            "[sportsonline] ===== PROCESS COMPLETED SUCCESSFULLY =====")
        return True
    except IOError as e:
        logging.error(
            "[sportsonline] Error writing {}: {}".format(
                filepath, e))
        logging.exception("[sportsonline] Error details:")
        return False


def is_sportsonline_url(url):
    return SPORTSONLINE_HOST in url

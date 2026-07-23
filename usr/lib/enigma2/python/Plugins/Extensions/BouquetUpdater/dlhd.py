# -*- coding: utf-8 -*-
import re
import logging
from datetime import datetime

try:
    from . import _
except (ImportError, ValueError):
    from __init__ import _

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote, urlparse
except ImportError:
    from urllib2 import urlopen, Request
    from urllib import quote
    from urlparse import urlparse


def is_dlhd_url(url):
    """Check if the URL is for DLHD"""
    return 'dlhd.pk' in url or '24-7-channels.php' in url


def fetch_page(url):
    """Download the HTML page"""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urlopen(req, timeout=15)
    html = response.read().decode('utf-8', errors='ignore')
    return html


def parse_channels(html, base_url):
    """Extract Italian and XXX channels from the page"""
    channels = []
    xxx_channels = []

    # Pattern to extract cards
    # <a class="card" href="/watch.php?id=51" data-title="abc usa" ...>
    #   <div class="card__title">ABC USA</div>
    pattern = r'<a\s+class="card"[^>]*href="([^"]+)"[^>]*data-title="([^"]+)"[^>]*>.*?<div\s+class="card__title">([^<]+)</div>'

    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    logging.info("Found {} total cards".format(len(matches)))

    # Filter Italian and XXX channels
    for href, data_title, card_title in matches:
        # Build full URL
        if href.startswith('/'):
            full_url = base_url.rstrip('/') + href
        else:
            full_url = href

        # XXX channels (18+)
        if '18+' in data_title or '18+' in card_title:
            xxx_channels.append({
                'name': card_title.strip(),
                'url': full_url,
                'data_title': data_title.strip()
            })
        # Italian channels
        elif 'italy' in data_title.lower() or 'italy' in card_title.lower():
            # Remove "Italy" from the channel name
            clean_name = card_title.strip()
            clean_name = re.sub(
                r'\s+Italy$',
                '',
                clean_name,
                flags=re.IGNORECASE)
            clean_name = re.sub(
                r'\s+Italy\s+',
                ' ',
                clean_name,
                flags=re.IGNORECASE)

            channels.append({
                'name': clean_name,
                'url': full_url,
                'data_title': data_title.strip()
            })

    logging.info("Found {} Italian channels".format(len(channels)))
    logging.info("Found {} XXX channels".format(len(xxx_channels)))

    return channels, xxx_channels


def group_channels(channels):
    """Organizes channels by group (Rai, Sky, Mediaset, etc.)"""
    groups = {
        'RAI': [],
        'Sky Sport': [],
        'Sky Cinema': [],
        'Sky Calcio': [],
        'Sky Altro': [],
        'Mediaset': [],
        'EuroSport': [],
        'DAZN': [],
        'Altri': []
    }

    for channel in channels:
        name = channel['name']
        name_lower = name.lower()

        if name_lower.startswith('rai'):
            groups['RAI'].append(channel)
        elif 'sky sport' in name_lower and 'calcio' not in name_lower:
            groups['Sky Sport'].append(channel)
        elif 'sky cinema' in name_lower:
            groups['Sky Cinema'].append(channel)
        elif 'sky calcio' in name_lower or 'calcio' in name_lower:
            groups['Sky Calcio'].append(channel)
        elif name_lower.startswith('sky'):
            groups['Sky Altro'].append(channel)
        elif 'mediaset' in name_lower or name_lower.startswith('20 '):
            groups['Mediaset'].append(channel)
        elif 'eurosport' in name_lower:
            groups['EuroSport'].append(channel)
        elif 'dazn' in name_lower:
            groups['DAZN'].append(channel)
        else:
            groups['Altri'].append(channel)

    # Remove empty groups
    groups = {k: v for k, v in groups.items() if v}

    # Sort channels within each group
    for group in groups.values():
        group.sort(key=lambda x: x['name'])

    return groups


def generate_bouquet(groups, xxx_channels, update_date):
    """Generates the bouquet in Enigma2 format"""
    lines = ["#NAME DLHD Italy\n"]

    # Header with update date
    lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
    lines.append("#DESCRIPTION --- {} ---\n".format(
        _("Updated on {}").format(update_date)))

    idx = 1

    # Preferred group order
    group_order = ['RAI', 'Mediaset', 'Sky Sport', 'Sky Calcio', 'Sky Cinema',
                   'Sky Altro', 'EuroSport', 'DAZN', 'Altri']

    for group_name in group_order:
        if group_name not in groups:
            continue

        channels = groups[group_name]

        # Group separator
        lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
        display_name = _("Other") if group_name == 'Altri' else group_name
        lines.append("#DESCRIPTION --- {} ---\n".format(display_name))

        # Add channels of the group
        for channel in channels:
            service_line = "#SERVICE 4097:0:1:{}:0:0:0:0:0:0:{}:{}\n".format(
                idx,
                quote(channel['url']),
                quote(channel['name'])
            )
            lines.append(service_line)
            lines.append("#DESCRIPTION {}\n".format(channel['name']))
            idx += 1

    # Add XXX group if there are channels
    if xxx_channels:
        lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
        lines.append("#DESCRIPTION --- XXX ---\n")

        # Sort XXX channels by name
        xxx_channels.sort(key=lambda x: x['name'])

        for channel in xxx_channels:
            service_line = "#SERVICE 4097:0:1:{}:0:0:0:0:0:0:{}:{}\n".format(
                idx,
                quote(channel['url']),
                quote(channel['name'])
            )
            lines.append(service_line)
            lines.append("#DESCRIPTION {}\n".format(channel['name']))
            idx += 1

    return ''.join(lines)


def write_bouquet(filename, content):
    """Writes the bouquet to file"""
    filepath = "/etc/enigma2/{}".format(filename)
    try:
        # Python 2/3 compatibility
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except TypeError:
            import codecs
            with codecs.open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        logging.info(
            "Bouquet written: {} ({} bytes)".format(
                filepath, len(content)))
        return True
    except IOError as e:
        logging.error("IOError writing bouquet: {}".format(e))
        logging.exception("Stack trace:")
        return False
    except Exception as e:
        logging.error("Error writing bouquet: {}".format(e))
        logging.exception("Stack trace:")
        return False


def process_dlhd(url, filename):
    """Processes DLHD and generates the bouquet"""
    try:
        # Extract base URL
        parsed = urlparse(url)
        base_url = "{}://{}".format(
            parsed.scheme if parsed.scheme else 'https',
            parsed.netloc if parsed.netloc else 'dlhd.pk')

        # If the URL does not already point to the channels page, use it
        if '24-7-channels.php' not in url:
            url = base_url + '/24-7-channels.php'

        logging.info("Downloading DLHD page: {}".format(url))
        html = fetch_page(url)

        logging.info("Parsing Italian and XXX channels...")
        channels, xxx_channels = parse_channels(html, base_url)

        if not channels and not xxx_channels:
            logging.warning("No channels found")
            return 0

        logging.info("Grouping Italian channels...")
        groups = group_channels(channels)

        total_channels = sum(len(ch)
                             for ch in groups.values()) + len(xxx_channels)
        logging.info(
            "Found {} total channels ({} Italian in {} groups + {} XXX)".format(
                total_channels, sum(
                    len(ch) for ch in groups.values()), len(groups), len(xxx_channels)))

        # Update date
        update_date = datetime.now().strftime("%d/%m/%Y %H:%M")

        logging.info("Generating bouquet...")
        bouquet = generate_bouquet(groups, xxx_channels, update_date)

        if write_bouquet(filename, bouquet):
            return total_channels
        return 0

    except Exception as e:
        logging.error("Error in process_dlhd: {}".format(e))
        logging.exception("Stack trace:")
        return 0


if __name__ == '__main__':
    import os
    logging.basicConfig(level=logging.INFO)

    # Read URL from configuration file
    plugin_path = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(plugin_path, 'bouquet_updater.conf')

    url = None
    filename = "userbouquet.dlhd.tv"

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    conf_url, conf_filename = line.rsplit('=', 1)
                    if is_dlhd_url(conf_url):
                        url = conf_url.strip()
                        filename = conf_filename.strip()
                        break

    if url:
        process_dlhd(url, filename)
    else:
        logging.error("DLHD URL not found in configuration file")

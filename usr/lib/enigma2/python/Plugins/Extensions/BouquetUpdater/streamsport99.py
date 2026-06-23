# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import logging

# from . import _

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request
try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


def is_streamsport99_url(url):
    return 'cdnlivetv.tv/api/v1/events/sports' in url


def fetch_events(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urlopen(req, timeout=10)
    data = json.loads(response.read().decode('utf-8'))
    return data


def parse_events(data):
    channels = []
    idx = 1

    if 'cdn-live-tv' in data:
        data = data['cdn-live-tv']

    for sport, events in data.items():
        if sport.startswith('total_') or sport in ['cached', 'timestamp']:
            continue

        if not isinstance(events, list):
            continue

        for event in events:
            if not event.get('channels'):
                continue

            event_name = event.get('event', '')
            if not event_name:
                home = event.get('homeTeam', '')
                away = event.get('awayTeam', '')
                if home and away:
                    event_name = "{} vs {}".format(home, away)
                else:
                    event_name = 'Unknown Event'

            start_time = event.get('time', '')
            if start_time:
                try:
                    hours, minutes = start_time.split(':')
                    hours = int(hours)
                    hours = (hours + 2) % 24
                    start_time = "{:02d}:{}".format(hours, minutes)
                except Exception:
                    pass

            status = event.get('status', '')

            for channel in event['channels']:
                channel_name = channel.get('channel_name', 'Unknown')
                url = channel.get('url', '')

                if not url:
                    continue

                name = "{} - {} [{}] {}".format(
                    start_time,
                    event_name[:40],
                    channel_name,
                    status.upper()
                )

                channels.append({
                    'number': idx,
                    'name': name,
                    'url': url
                })
                idx += 1

    return channels


def generate_bouquet(channels):
    lines = ["#NAME StreamSport99\n"]

    for ch in channels:
        service_line = "#SERVICE 4097:0:1:{}:0:0:0:0:0:0:{}:{}".format(
            ch['number'],
            quote(ch['url']),
            quote(ch['name'])
        )
        lines.append(service_line + "\n")
        lines.append("#DESCRIPTION {}\n".format(ch['name']))

    return ''.join(lines)


def write_bouquet(filename, content):
    filepath = "/etc/enigma2/{}".format(filename)
    try:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except TypeError:
            import codecs
            with codecs.open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        logging.info("Bouquet written: {} ({} bytes)".format(filepath, len(content)))
        return True
    except IOError as e:
        logging.error("IOError writing bouquet: {}".format(e))
        logging.exception("Stack trace:")
        return False
    except Exception as e:
        logging.error("Error writing bouquet: {}".format(e))
        logging.exception("Stack trace:")
        return False


def process_streamsport99(url, filename):
    try:
        logging.info("Fetching events from CDN Live TV API: {}".format(url))
        data = fetch_events(url)
        logging.info("Parsing events...")
        channels = parse_events(data)
        logging.info("Found {} channels".format(len(channels)))

        if not channels:
            logging.warning("No channels found")
            return False

        logging.info("Generating bouquet...")
        bouquet = generate_bouquet(channels)
        return write_bouquet(filename, bouquet)
    except Exception as e:
        logging.error("Error in process_streamsport99: {}".format(e))
        logging.exception("Stack trace:")
        return False


if __name__ == '__main__':
    import os
    logging.basicConfig(level=logging.INFO)

    plugin_path = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(plugin_path, 'bouquet_updater.conf')

    url = None
    filename = "userbouquet.streamsport99.tv"

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    conf_url, conf_filename = line.rsplit('=', 1)
                    if is_streamsport99_url(conf_url):
                        url = conf_url.strip()
                        filename = conf_filename.strip()
                        break

    if url:
        process_streamsport99(url, filename)
    else:
        logging.error("StreamSport99 URL not found in configuration file")

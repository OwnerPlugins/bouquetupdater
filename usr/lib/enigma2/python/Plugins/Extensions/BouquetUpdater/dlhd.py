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
    """Verifica se l'URL è per DLHD"""
    return 'dlhd.pk' in url or '24-7-channels.php' in url


def fetch_page(url):
    """Scarica la pagina HTML"""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urlopen(req, timeout=15)
    html = response.read().decode('utf-8', errors='ignore')
    return html


def parse_channels(html, base_url):
    """Estrae i canali italiani e XXX dalla pagina"""
    channels = []
    xxx_channels = []

    # Pattern per estrarre le card
    # <a class="card" href="/watch.php?id=51" data-title="abc usa" ...>
    #   <div class="card__title">ABC USA</div>
    pattern = r'<a\s+class="card"[^>]*href="([^"]+)"[^>]*data-title="([^"]+)"[^>]*>.*?<div\s+class="card__title">([^<]+)</div>'

    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    logging.info("Trovate {} card totali".format(len(matches)))

    # Filtra canali italiani e XXX
    for href, data_title, card_title in matches:
        # Costruisci URL completo
        if href.startswith('/'):
            full_url = base_url.rstrip('/') + href
        else:
            full_url = href

        # Canali XXX (18+)
        if '18+' in data_title or '18+' in card_title:
            xxx_channels.append({
                'name': card_title.strip(),
                'url': full_url,
                'data_title': data_title.strip()
            })
        # Canali italiani
        elif 'italy' in data_title.lower() or 'italy' in card_title.lower():
            # Rimuovi "Italy" dal nome del canale
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

    logging.info("Trovati {} canali italiani".format(len(channels)))
    logging.info("Trovati {} canali XXX".format(len(xxx_channels)))

    return channels, xxx_channels


def group_channels(channels):
    """Organizza i canali per gruppo (Rai, Sky, Mediaset, ecc.)"""
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

    # Rimuovi gruppi vuoti
    groups = {k: v for k, v in groups.items() if v}

    # Ordina i canali all'interno di ogni gruppo
    for group in groups.values():
        group.sort(key=lambda x: x['name'])

    return groups


def generate_bouquet(groups, xxx_channels, update_date):
    """Genera il bouquet in formato Enigma2"""
    lines = ["#NAME DLHD Italy\n"]

    # Intestazione con data aggiornamento
    lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
    lines.append("#DESCRIPTION --- {} ---\n".format(
        _("Updated on {}").format(update_date)))

    idx = 1

    # Ordine preferito dei gruppi
    group_order = ['RAI', 'Mediaset', 'Sky Sport', 'Sky Calcio', 'Sky Cinema',
                   'Sky Altro', 'EuroSport', 'DAZN', 'Altri']

    for group_name in group_order:
        if group_name not in groups:
            continue

        channels = groups[group_name]

        # Separatore gruppo
        lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
        display_name = _("Other") if group_name == 'Altri' else group_name
        lines.append("#DESCRIPTION --- {} ---\n".format(display_name))

        # Aggiungi canali del gruppo
        for channel in channels:
            service_line = "#SERVICE 4097:0:1:{}:0:0:0:0:0:0:{}:{}\n".format(
                idx,
                quote(channel['url']),
                quote(channel['name'])
            )
            lines.append(service_line)
            lines.append("#DESCRIPTION {}\n".format(channel['name']))
            idx += 1

    # Aggiungi gruppo XXX se ci sono canali
    if xxx_channels:
        lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
        lines.append("#DESCRIPTION --- XXX ---\n")

        # Ordina i canali XXX per nome
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
    """Scrive il bouquet su file"""
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
            "Bouquet scritto: {} ({} bytes)".format(
                filepath, len(content)))
        return True
    except IOError as e:
        logging.error("Errore IOError scrittura bouquet: {}".format(e))
        logging.exception("Stack trace:")
        return False
    except Exception as e:
        logging.error("Errore scrittura bouquet: {}".format(e))
        logging.exception("Stack trace:")
        return False


def process_dlhd(url, filename):
    """Processa DLHD e genera il bouquet"""
    try:
        # Estrai base URL
        parsed = urlparse(url)
        base_url = "{}://{}".format(
            parsed.scheme if parsed.scheme else 'https',
            parsed.netloc if parsed.netloc else 'dlhd.pk')

        # Se l'URL non punta già alla pagina dei canali, usala
        if '24-7-channels.php' not in url:
            url = base_url + '/24-7-channels.php'

        logging.info("Scaricamento pagina DLHD: {}".format(url))
        html = fetch_page(url)

        logging.info("Parsing canali italiani e XXX...")
        channels, xxx_channels = parse_channels(html, base_url)

        if not channels and not xxx_channels:
            logging.warning("Nessun canale trovato")
            return 0

        logging.info("Raggruppamento canali italiani...")
        groups = group_channels(channels)

        total_channels = sum(len(ch)
                             for ch in groups.values()) + len(xxx_channels)
        logging.info(
            "Trovati {} canali totali ({} italiani in {} gruppi + {} XXX)".format(
                total_channels, sum(
                    len(ch) for ch in groups.values()), len(groups), len(xxx_channels)))

        # Data aggiornamento
        update_date = datetime.now().strftime("%d/%m/%Y %H:%M")

        logging.info("Generazione bouquet...")
        bouquet = generate_bouquet(groups, xxx_channels, update_date)

        if write_bouquet(filename, bouquet):
            return total_channels
        return 0

    except Exception as e:
        logging.error("Errore process_dlhd: {}".format(e))
        logging.exception("Stack trace:")
        return 0


if __name__ == '__main__':
    import os
    logging.basicConfig(level=logging.INFO)

    # Legge URL dal file di configurazione
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
        logging.error("URL DLHD non trovato nel file di configurazione")

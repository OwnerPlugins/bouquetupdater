# -*- coding: utf-8 -*-
from __future__ import absolute_import

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.config import config, ConfigSelection, ConfigSubsection, getConfigListEntry
from enigma import eTimer, eDVBDB

import os
import re
import logging
from datetime import datetime

# Import gettext function from __init__
from . import _

try:
    from .sportsonline import process_sportsonline, is_sportsonline_url
    from .vavoo_it import process_vavoo_italia, process_vavoo_italia_resolved, is_vavoo_url, VAVOO_BOUQUET_FILE, VAVOO_RESOLVED_BOUQUET_FILE
    from .streamsport99 import process_streamsport99, is_streamsport99_url
except ImportError:
    from sportsonline import process_sportsonline, is_sportsonline_url
    from vavoo_it import process_vavoo_italia, process_vavoo_italia_resolved, is_vavoo_url, VAVOO_BOUQUET_FILE, VAVOO_RESOLVED_BOUQUET_FILE
    from streamsport99 import process_streamsport99, is_streamsport99_url

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

PLUGIN_NAME = _("Bouquet Updater")
PLUGIN_VERSION = "3.0.10"
PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PLUGIN_PATH, 'bouquet_updater.conf')
LOG_FILE = os.path.join(PLUGIN_PATH, 'bouqUPDlog.txt')
LAST_RUN_FILE = os.path.join(PLUGIN_PATH, 'last_run.timestamp')

# Flag to avoid multiple logging initializations
_logging_initialized = False

config.plugins.BouquetUpdater = ConfigSubsection()
config.plugins.BouquetUpdater.updatehour = ConfigSelection(
    choices=[("%02d:00" % i, "%02d" % i) for i in range(24)],
    default="04"
)
config.plugins.BouquetUpdater.sources = ConfigSubsection()


def setup_logging():
    """Configure logging, clearing the log file on each startup."""
    global _logging_initialized

    if _logging_initialized:
        return

    try:
        # Remove any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Clear the log file on each startup ('w' mode)
        if os.path.exists(LOG_FILE):
            try:
                os.remove(LOG_FILE)
            except Exception:
                pass

        # Remove old log file if exists
        old_log_file = os.path.join(PLUGIN_PATH, 'bouquet_updater.log')
        if os.path.exists(old_log_file):
            try:
                os.remove(old_log_file)
                logging.info("Old log file removed: {}".format(old_log_file))
            except Exception:
                pass

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(funcName)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[logging.FileHandler(LOG_FILE, 'w', 'utf-8')]
        )

        _logging_initialized = True

        logging.info("=" * 60)
        logging.info("{} v{} - LOG STARTED".format(PLUGIN_NAME, PLUGIN_VERSION))
        logging.info("Plugin Path: {}".format(PLUGIN_PATH))
        logging.info("Config File: {}".format(CONFIG_FILE))
        logging.info("Log File: {}".format(LOG_FILE))
        logging.info("=" * 60)
    except Exception as e:
        print("[BouquetUpdater] Error setting up logging: {}".format(e))


class M3UUpdaterLogic:
    def __init__(self):
        self.sources = self._read_config()

    def _read_config(self):
        logging.info("Reading configuration file")
        if not os.path.exists(CONFIG_FILE):
            logging.error("Configuration file not found: {}".format(CONFIG_FILE))
            logging.error("The plugin cannot work without a configuration file!")
            return []

        custom_sources = []
        try:
            logging.info("Opening file: {}".format(CONFIG_FILE))
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                logging.info("Read {} lines".format(len(lines)))

                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    logging.debug("Line {}: {}".format(line_num, line if line else "(empty)"))

                    if not line:
                        continue
                    if line.startswith('#'):
                        logging.debug("Line {} ignored (comment)".format(line_num))
                        continue
                    if '=' not in line:
                        logging.warning("Line {} ignored (invalid format, missing '=')".format(line_num))
                        continue

                    # Use rsplit to split only on the last '=' (handles URLs with parameters)
                    url, filename = line.rsplit('=', 1)
                    url = url.strip()
                    filename = filename.strip()
                    custom_sources.append((url, filename))
                    logging.info("Added source: {} -> {}".format(url, filename))

            if not custom_sources:
                logging.warning("No sources found in configuration file.")
            else:
                logging.info("Configuration loaded successfully. {} sources to process.".format(len(custom_sources)))
            return custom_sources
        except Exception as e:
            logging.error("Error reading configuration: {}".format(e))
            logging.exception("Error details:")
            return []

    def _get_github_last_modified(self, url):
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=10) as response:
                last_modified = response.headers.get('Last-Modified')
                if last_modified:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(last_modified)
                    return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass
        return None

    def _download_m3u(self, url):
        logging.info("Downloading from: {}".format(url))
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            logging.debug("Request created with User-Agent: Mozilla/5.0")
            with urlopen(req, timeout=30) as response:
                status_code = response.getcode()
                logging.info("HTTP response: {}".format(status_code))
                content = response.read().decode('utf-8', errors='ignore')
                content_length = len(content)
                logging.info("Download completed: {} bytes".format(content_length))
                if content_length == 0:
                    logging.error("Received empty content!")
                    return None
                return content
        except Exception as e:
            logging.error("Download error {}: {}".format(url, e))
            logging.exception("Download error details:")
            return None

    def _parse_m3u(self, m3u_content):
        logging.info("Parsing M3U")
        if not m3u_content:
            logging.error("M3U content empty or None")
            return []

        if not m3u_content.startswith('#EXTM3U'):
            logging.error("Content is not a valid M3U file (missing #EXTM3U header)")
            logging.debug("First 100 characters: {}".format(m3u_content[:100]))
            return []

        logging.info("Valid M3U header found")
        channels = []
        group_re = re.compile(r'group-title="([^"]+)"')
        name_re = re.compile(r'#EXTINF:-1.*,(.+)')
        lines = m3u_content.splitlines()
        logging.info("Total lines to process: {}".format(len(lines)))

        for i, line in enumerate(lines):
            if line.startswith('#EXTINF'):
                group_title = None
                group_match = group_re.search(line)
                if group_match:
                    group_title = group_match.group(1).strip()

                name_match = name_re.search(line)
                if name_match and i + 1 < len(lines):
                    channel_name = name_match.group(1).strip()
                    stream_url = lines[i + 1].strip()
                    if stream_url and not stream_url.startswith('#'):
                        channels.append((channel_name, stream_url, group_title))

        logging.info("Parsing completed. {} channels found.".format(len(channels)))
        if len(channels) == 0:
            logging.warning("No channels found in M3U file!")
        return channels

    def _generate_bouquet(self, bouquet_name, channels, source_date=None):
        if not channels:
            return ""

        is_lista = 'lista' in bouquet_name.lower()
        name = _("TV List") if is_lista else bouquet_name.replace('userbouquet.', '').replace('.tv', '').capitalize()

        desc = _("Updated on {}").format(source_date) if source_date else _("Updated on {}").format(datetime.now().strftime("%d.%m.%Y"))

        lines = [
            "#NAME {}\n".format(name),
            "#SERVICE 1:64:0:0:0:0:0:0:0:0:\n",
            "#DESCRIPTION --- {} ---\n".format(desc)
        ]

        if is_lista:
            channels = self._sort_lista_channels(channels)

        current_group = None
        for channel_name, url, group_title in channels:
            if group_title and group_title != current_group:
                lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
                lines.append("#DESCRIPTION --- {} ---\n".format(group_title))
                current_group = group_title

            lines.append("#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n".format(quote(url), quote(channel_name)))
            lines.append("#DESCRIPTION {}\n".format(channel_name))

        return "".join(lines)

    def _sort_lista_channels(self, channels):
        priority_order = ['Rai', 'Mediaset', 'Film - Serie TV', 'Sport']
        grouped = {}

        for channel_name, url, group_title in channels:
            group = group_title or _('Other')
            if group not in grouped:
                grouped[group] = []
            grouped[group].append((channel_name, url, group_title))

        if 'Film - Serie TV' in grouped:
            grouped['Film - Serie TV'] = self._sort_primafila(grouped['Film - Serie TV'])

        sorted_channels = []
        for group in priority_order:
            if group in grouped:
                sorted_channels.extend(grouped[group])

        other_groups = sorted([g for g in grouped.keys() if g not in priority_order])
        for group in other_groups:
            sorted_channels.extend(grouped[group])

        return sorted_channels

    def _sort_primafila(self, channels):
        primafila = []
        others = []

        for ch in channels:
            if 'primafila' in ch[0].lower():
                primafila.append(ch)
            else:
                others.append(ch)

        primafila.sort(key=lambda x: self._extract_primafila_number(x[0]))
        return primafila + others

    def _extract_primafila_number(self, name):
        match = re.search(r'(\d+)', name)
        return int(match.group(1)) if match else 999

    def _write_bouquet_file(self, filename, content):
        filepath = "/etc/enigma2/{}".format(filename)
        logging.info("Writing bouquet: {}".format(filepath))
        try:
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                logging.error("Directory does not exist: {}".format(directory))
                return False

            logging.debug("Directory verified: {}".format(directory))
            logging.debug("Content length to write: {} bytes".format(len(content)))

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logging.info("Bouquet written successfully: {} ({} bytes)".format(filepath, file_size))
                return True
            else:
                logging.error("File not found after writing: {}".format(filepath))
                return False

        except IOError as e:
            logging.error("IOError writing {}: {}".format(filepath, e))
            logging.exception("Write error details:")
            return False
        except Exception as e:
            logging.error("Generic error writing {}: {}".format(filepath, e))
            logging.exception("Write error details:")
            return False

    def _update_bouquets_tv(self, bouquet_filenames):
        bouquets_tv_path = "/etc/enigma2/bouquets.tv"
        try:
            if not os.path.exists(bouquets_tv_path):
                logging.warning("bouquets.tv not found")
                return

            with open(bouquets_tv_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()
            modified = False

            for bouquet_filename in bouquet_filenames:
                if '"{}"'.format(bouquet_filename) not in content:
                    lines.append('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{}" ORDER BY bouquet'.format(bouquet_filename))
                    logging.info("Added {} to bouquets.tv".format(bouquet_filename))
                    modified = True

            if modified:
                with open(bouquets_tv_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
                logging.info("bouquets.tv updated")
        except Exception as e:
            logging.error("Error updating bouquets.tv: {}".format(e))

    def _reload_bouquets(self):
        """Reload bouquets and servicelist on Enigma2"""
        try:
            logging.info("Reloading servicelist...")
            eDVBDB.getInstance().reloadServicelist()
            logging.info("Reloading bouquets...")
            eDVBDB.getInstance().reloadBouquets()
            logging.info("Bouquets and servicelist reloaded successfully")
        except Exception as e:
            logging.error("Error reloading bouquets: {}".format(e))
            logging.exception("Reload error details:")

    def _save_last_run(self):
        try:
            with open(LAST_RUN_FILE, 'w') as f:
                f.write(str(datetime.now().date()))
        except Exception as e:
            logging.error("Error saving timestamp: {}".format(e))

    def run_update(self, selected_urls=None):
        if not _logging_initialized:
            setup_logging()

        logging.info("=" * 60)
        logging.info("STARTING BOUQUET UPDATE")
        logging.info("=" * 60)

        if selected_urls:
            logging.info("Mode: Selective update ({} sources selected)".format(len(selected_urls)))
        else:
            logging.info("Mode: Full update (all sources)")

        updated_bouquets = []
        sources_to_process = []
        if selected_urls is None:
            sources_to_process = self.sources
        else:
            sources_to_process = [(url, fn) for url, fn in self.sources if (url + '|' + fn) in selected_urls]

        logging.info("Sources to process: {}".format(len(sources_to_process)))
        for idx, (url, filename) in enumerate(sources_to_process, 1):
            logging.info("-" * 60)
            logging.info("[{}/{}] Processing: {}".format(idx, len(sources_to_process), url))
            logging.info("Destination bouquet: {}".format(filename))

            try:
                # Sportsonline
                if is_sportsonline_url(url):
                    logging.info("Detected type: SPORTSONLINE")
                    if process_sportsonline(url, filename):
                        logging.info("Sportsonline processed successfully")
                        updated_bouquets.append(filename)
                    else:
                        logging.error("Sportsonline: processing failed")
                    continue

                # StreamSport99
                if is_streamsport99_url(url):
                    logging.info("Detected type: STREAMSPORT99")
                    if process_streamsport99(url, filename):
                        logging.info("StreamSport99 processed successfully")
                        updated_bouquets.append(filename)
                    else:
                        logging.error("StreamSport99: processing failed")
                    continue

                # Vavoo Resolved (check bouquet filename)
                if is_vavoo_url(url) and filename == VAVOO_RESOLVED_BOUQUET_FILE:
                    logging.info("Detected type: VAVOO RESOLVED (based on filename: {})".format(filename))
                    if process_vavoo_italia_resolved(filename):
                        logging.info("Vavoo Resolved processed successfully")
                        updated_bouquets.append(filename)
                    else:
                        logging.error("Vavoo Resolved: processing failed")
                    continue

                # Normal Vavoo
                if is_vavoo_url(url):
                    logging.info("Detected type: VAVOO")
                    if process_vavoo_italia(filename):
                        logging.info("Vavoo processed successfully")
                        updated_bouquets.append(filename)
                    else:
                        logging.error("Vavoo: processing failed")
                    continue

                # Standard M3U
                logging.info("Detected type: STANDARD M3U")
                source_date = self._get_github_last_modified(url)
                if source_date:
                    logging.info("GitHub last modified: {}".format(source_date))

                logging.info("Downloading M3U...")
                m3u_content = self._download_m3u(url)
                if not m3u_content:
                    logging.error("M3U download failed")
                    continue

                logging.info("Parsing M3U...")
                channels = self._parse_m3u(m3u_content)
                if not channels:
                    logging.error("M3U parsing failed or no channels found")
                    continue

                logging.info("Generating bouquet...")
                bouquet_content = self._generate_bouquet(filename, channels, source_date)
                if self._write_bouquet_file(filename, bouquet_content):
                    logging.info("M3U bouquet written successfully")
                    updated_bouquets.append(filename)
                else:
                    logging.error("M3U bouquet write failed")

            except Exception as e:
                logging.error("CRITICAL ERROR processing {}: {}".format(url, e))
                logging.exception("Full stack trace:")

        logging.info("=" * 60)
        logging.info("UPDATE SUMMARY")
        logging.info("Bouquets updated: {}/{}".format(len(updated_bouquets), len(sources_to_process)))
        if updated_bouquets:
            for bouquet in updated_bouquets:
                logging.info("  - {}".format(bouquet))
        else:
            logging.warning("NO BOUQUETS UPDATED!")
        logging.info("=" * 60)

        if updated_bouquets:
            logging.info("Updating bouquets.tv...")
            self._update_bouquets_tv(updated_bouquets)
            logging.info("Reloading bouquets...")
            self._reload_bouquets()
            logging.info("Saving last update timestamp...")
            self._save_last_run()
            logging.info("Post-update operations completed")
        else:
            logging.warning("No bouquets updated, reloading servicelist anyway...")
            self._reload_bouquets()

        logging.info("=" * 60)
        logging.info("UPDATE FINISHED")
        logging.info("=" * 60)
        return len(updated_bouquets) > 0


class AutoUpdater:
    def __init__(self):
        self.timer = eTimer()
        self.timer.callback.append(self.check_and_run)
        self.updating = False

    def start(self):
        logging.info("Auto timer started (check every hour).")
        self.timer.start(3600000, False)

    def stop(self):
        self.timer.stop()

    def check_and_run(self):
        if self.updating:
            return

        now = datetime.now()
        update_hour_str = config.plugins.BouquetUpdater.updatehour.value
        update_hour = int(update_hour_str.split(':')[0]) if ':' in update_hour_str else int(update_hour_str)

        last_run_date = ""
        if os.path.exists(LAST_RUN_FILE):
            try:
                with open(LAST_RUN_FILE, 'r') as f:
                    last_run_date = f.read().strip()
            except IOError:
                pass

        today = str(now.date())

        if now.hour == update_hour and last_run_date != today:
            logging.info("Hour {}:00 - Starting automatic update.".format(now.hour))
            self.updating = True
            try:
                M3UUpdaterLogic().run_update()
            finally:
                self.updating = False


class UpdateProgressScreen(Screen):
    skin = """
        <screen position="center,center" size="600,200" title="Updating...">
            <widget name="status" position="20,20" size="560,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget name="progress" position="20,60" size="560,30" />
            <widget name="info" position="20,100" size="560,80" font="Regular;18" halign="center" valign="top" transparent="1" />
        </screen>
    """

    def __init__(self, session, selected_urls):
        Screen.__init__(self, session)
        self["status"] = Label(_("Initializing..."))
        self["progress"] = ProgressBar()
        self["info"] = Label("")
        self.selected_urls = selected_urls
        self.timer = eTimer()
        self.timer.callback.append(self.start_update)
        self.timer.start(100, True)

    def start_update(self):
        try:
            logic = M3UUpdaterLogic()
            sources_to_process = [(url, fn) for url, fn in logic.sources if (url + '|' + fn) in self.selected_urls]
            total = len(sources_to_process)

            for idx, (url, filename) in enumerate(sources_to_process, 1):
                progress = int((idx * 100) / total)
                self["progress"].setValue(progress)
                self["status"].setText(_("Updating {}/{}").format(idx, total))
                self["info"].setText(_("Processing: {}\n{}").format(filename, url[:50] + "..."))

                logging.info("[{}/{}] Processing: {}".format(idx, total, url))

                if is_sportsonline_url(url):
                    process_sportsonline(url, filename)
                elif is_streamsport99_url(url):
                    process_streamsport99(url, filename)
                elif is_vavoo_url(url) and filename == VAVOO_RESOLVED_BOUQUET_FILE:
                    process_vavoo_italia_resolved(filename)
                elif is_vavoo_url(url):
                    process_vavoo_italia(filename)
                else:
                    source_date = logic._get_github_last_modified(url)
                    m3u_content = logic._download_m3u(url)
                    if m3u_content:
                        channels = logic._parse_m3u(m3u_content)
                        if channels:
                            bouquet_content = logic._generate_bouquet(filename, channels, source_date)
                            logic._write_bouquet_file(filename, bouquet_content)

            self["progress"].setValue(100)
            self["status"].setText(_("Completed!"))
            self["info"].setText(_("Reloading channel list..."))

            updated_filenames = [fn for _, fn in sources_to_process]
            if updated_filenames:
                logic._update_bouquets_tv(updated_filenames)

            logic._reload_bouquets()
            logic._save_last_run()

            import time
            time.sleep(1)

            self.close(True)
        except Exception as e:
            logging.error("Update error: {}".format(e))
            logging.exception("Stack trace:")
            self.close(False)


class BouquetUpdaterScreen(ConfigListScreen, Screen):
    skin = """
        <screen position="center,center" size="720,480" title="Bouquet Updater">
            <widget name="title" position="20,15" size="680,35" font="Regular;28" halign="left" valign="center" foregroundColor="#00ffffff" transparent="1" />
            <widget name="info" position="20,55" size="680,25" font="Regular;18" halign="left" valign="center" foregroundColor="#00b0b0b0" transparent="1" />
            <ePixmap pixmap="skin_default/div-h.png" position="20,85" size="680,2" />
            <widget name="config" position="20,95" size="680,300" scrollbarMode="showOnDemand" itemHeight="35" font="Regular;20" />
            <ePixmap pixmap="skin_default/div-h.png" position="20,400" size="680,2" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,420" size="160,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="190,420" size="160,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="360,420" size="160,40" alphatest="on" />
            <widget name="key_red" position="20,420" zPosition="1" size="160,40" font="Regular;18" halign="center" valign="center" transparent="1" />
            <widget name="key_green" position="190,420" zPosition="1" size="160,40" font="Regular;18" halign="center" valign="center" transparent="1" />
            <widget name="key_yellow" position="360,420" zPosition="1" size="160,40" font="Regular;18" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)

        self["title"] = Label("{} v{}".format(_("Bouquet Updater"), PLUGIN_VERSION))
        self["info"] = Label(_("Manage automatic M3U bouquet updates"))
        self["key_red"] = Label(_("Exit"))
        self["key_green"] = Label(_("Update"))
        self["key_yellow"] = Label(_("Save"))

        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "cancel": self.keyCancel,
            "ok": self.keySave,
            "red": self.keyCancel,
            "green": self.run_manual_update,
            "yellow": self.keySave,
        }, -2)

        self.list = []
        ConfigListScreen.__init__(self, self.list, session=session)
        self.build_screen()

    @staticmethod
    def _url_label(url, filename):
        """Generate a descriptive label for the URL and bouquet"""
        if filename == VAVOO_RESOLVED_BOUQUET_FILE:
            return _("Vavoo Italia (Resolved)")
        elif filename == VAVOO_BOUQUET_FILE:
            return _("Vavoo Italia")

        if 'sportsonline' in url:
            return _("Sportsonline")

        if 'cdnlivetv' in url:
            return _("StreamSport99")

        m3u_match = re.search(r'/([^/]+)\.m3u', url)
        if m3u_match:
            return m3u_match.group(1)

        domain_match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        return domain_match.group(1) if domain_match else url

    def build_screen(self):
        self.list = [getConfigListEntry(_("Automatic update time"), config.plugins.BouquetUpdater.updatehour)]

        try:
            self.source_flags = {}
            logic = M3UUpdaterLogic()
            for url, bouquet_file in logic.sources:
                display = self._url_label(url, bouquet_file)
                key = re.sub(r'[^a-zA-Z0-9]', '_', url + bouquet_file)
                if not hasattr(config.plugins.BouquetUpdater.sources, key):
                    from Components.config import ConfigYesNo
                    setattr(config.plugins.BouquetUpdater.sources, key, ConfigYesNo(default=True))
                flag = getattr(config.plugins.BouquetUpdater.sources, key)
                self.source_flags[url + '|' + bouquet_file] = flag
                self.list.append(getConfigListEntry("{} -> {}".format(display, bouquet_file), flag))
        except Exception as e:
            logging.error("Error building screen: {}".format(e))
            logging.exception("Stack trace:")

        self["config"].setList(self.list)

    def run_manual_update(self):
        selected = []
        for key, flag in self.source_flags.items():
            if flag.value:
                selected.append(key)

        if not selected:
            self.session.open(MessageBox, _("No source selected!"), MessageBox.TYPE_WARNING, timeout=3)
            return

        has_resolved = any(VAVOO_RESOLVED_BOUQUET_FILE in key for key in selected)

        if has_resolved:
            msg = _("Starting update of {} bouquets...\n\nWARNING: Vavoo Resolved may take several minutes.\nDo not close the plugin!").format(len(selected))
        else:
            msg = _("Starting update of {} bouquets...\n\nPlease wait.").format(len(selected))

        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=3)
        self.session.openWithCallback(self._update_callback, UpdateProgressScreen, selected)

    def keySave(self):
        for x in self["config"].list:
            if x[1] and hasattr(x[1], 'save'):
                x[1].save()
        config.save()
        self.session.open(MessageBox, _("Settings saved."), MessageBox.TYPE_INFO, timeout=3)

    def _update_callback(self, success=None):
        if success:
            msg = _("Update completed!\n\nThe channel list has been reloaded.")
        else:
            msg = _("Update finished.\n\nCheck the log for details:\n{}").format(LOG_FILE)
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=5)

    def keyCancel(self):
        for x in self["config"].list:
            if x[1] and hasattr(x[1], 'cancel'):
                x[1].cancel()
        self.close()


auto_updater_instance = None


def session_start(reason, session=None):
    global auto_updater_instance
    if reason == 0:
        setup_logging()
        logging.info("{} v{} - Session started.".format(PLUGIN_NAME, PLUGIN_VERSION))
        if auto_updater_instance is None:
            auto_updater_instance = AutoUpdater()
            auto_updater_instance.start()


def autostart(reason, **kwargs):
    if reason == 0 and "session" in kwargs:
        session_start(0, session=kwargs["session"])


def main(session, **kwargs):
    session.open(BouquetUpdaterScreen)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=PLUGIN_NAME,
            description=_("Automatically update bouquets from M3U lists"),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        ),
        PluginDescriptor(
            where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART],
            fnc=autostart
        )
    ]

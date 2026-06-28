<h1 align="center">**Bouquet Updater for Enigma2**

[![Lint Status](https://github.com/OwnerPlugins/bouquetupdater/actions/workflows/pylint.yml/badge.svg)](https://github.com/OwnerPlugins/bouquetupdater/actions/workflows/pylint.yml)
[![Ruff Status](https://github.com/OwnerPlugins/bouquetupdater/actions/workflows/ruff.yml/badge.svg)](https://github.com/OwnerPlugins/bouquetupdater/actions/workflows/ruff.yml)
</h1>

<p align="center">
  <a href="https://github.com/Belfagor2005">
    <img src="https://komarev.com/ghpvc/?username=Belfagor2005&label=Repository%20Views&color=blueviolet" alt="Visitors">
  </a>
</p>

<p align="center">
  <a href="https://ko-fi.com/lululla">
    <img src="https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge" alt="Donate via Ko-fi">
  </a>
  <a href="https://paypal.me/belfagor2005">
    <img src="https://img.shields.io/badge/_-Donate-green.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge" alt="Donate via PayPal">
  </a>
</p>

# ⭐️ BouquetUpdater

**Version:** 3.0.2.0
**License:** GPL-v2

---

## Description

**Bouquet Updater** is a plugin for Enigma2‑based receivers (Dreambox, Vu+, OpenPLi, OpenATV, etc.) that automatically updates your TV channel bouquets from various online sources.

It supports:

- **Standard M3U playlists** – download from any HTTP/HTTPS URL.
- **Sportsonline** – daily sports events from `sportsonline.vc`.
- **StreamSport99** – live sports events via the CDN Live TV API.
- **Vavoo Italia** – Italian channels from `vavoo.to` and `kool.to` (both direct and resolved streams).

All user‑visible strings are translatable using `gettext` (English and Italian included).

---

## Features

- **Automatic updates** – set a daily hour for unattended updates.
- **Manual update** – update selected bouquets on demand with a progress screen.
- **Multiple source types** – automatically detect and handle different protocols.
- **Grouped bouquets** – channels are organised into logical groups (Rai, Mediaset, Sky, Sport, etc.) for easier browsing.
- **Smart M3U parsing** – supports standard headers (`#EXTM3U`, `#EXTINF`, `group-title`).
- **Detailed logging** – operations are logged to `bouqUPDlog.txt` for troubleshooting.
- **No external dependencies** – uses only standard Python libraries available on Enigma2.

---

## Installation

1. **Download** the plugin package or clone this repository.
2. **Transfer** the `BouquetUpdater` folder to:
   ```
   /usr/lib/enigma2/python/Plugins/Extensions/
   ```
3. **Restart** Enigma2 (GUI restart) – the plugin will appear in the plugin menu.
4. **Configure** your sources in the configuration file (see below).

---

## Configuration

The source list is read from:

```
/usr/lib/enigma2/python/Plugins/Extensions/BouquetUpdater/bouquet_updater.conf
```

Each line defines one source in the format:

```
URL=filename_bouquet.tv
```

- `URL` – full HTTP/HTTPS address of the M3U playlist or API endpoint.
- `filename_bouquet.tv` – the bouquet file name that will be created in `/etc/enigma2/` (e.g., `userbouquet.mychannels.tv`).

Lines starting with `#` are ignored as comments.

### Example configuration

```ini
# Standard M3U playlist
https://example.com/playlist.m3u=userbouquet.myplaylist.tv

# Sportsonline (daily events)
https://sportsoffline.vc/prog.txt=userbouquet.sportsonline.tv

# StreamSport99 API
https://api.del-server.tv/api/v1/events/sports/?user=cdnlivetv&plan=free=userbouquet.streamsport99live.tv

# Vavoo Italia (direct, no resolution)
https://vavoo.giu/catalog=userbouquet.vavooitalia.tv

# Vavoo Italia (resolved streams, slower)
https://kool.su/catalog=userbouquet.vavooitaliares.tv
```

**Important notes:**

- For **Vavoo**, the plugin distinguishes between the **direct** bouquet (`userbouquet.vavooitalia.tv`) and the **resolved** bouquet (`userbouquet.vavooitaliares.tv`). Use the same URL but different filenames.
- For **Sportsonline**, the URL must point to the `prog.txt` file.
- For **StreamSport99**, the URL must be the API endpoint containing `cdnlivetv.tv/api/v1/events/sports`.

---

## Usage

After installation and configuration:

1. Go to **Plugins** → **Bouquet Updater**.
2. The main screen shows:
   - The automatic update hour (configurable).
   - A list of all configured sources with checkboxes – enable/disable each source individually.
3. Press **Green (Update)** to run a manual update of the selected sources.
4. Press **Yellow (Save)** to save the current settings (update hour and source selection).
5. The update progress screen will show the status and write the new bouquet files.

Automatic updates run daily at the configured hour (if the receiver is on).

---

## How It Works

1. **Reading sources** – the plugin reads `bouquet_updater.conf`.
2. **Detection** – for each URL, it detects the type:
   - **Sportsonline** – downloads `prog.txt`, parses today's events, and creates a bouquet.
   - **StreamSport99** – calls the API, parses the JSON response, and creates a bouquet.
   - **Vavoo** – fetches the catalog, filters Italian channels, classifies them, and optionally resolves streams.
   - **Standard M3U** – downloads the file, parses `#EXTINF` lines, and creates a bouquet with group markers.
3. **Bouquet creation** – the generated `.tv` file is written to `/etc/enigma2/`.
4. **Bouquet registration** – if new bouquets are created, they are added to `bouquets.tv`.
5. **Reload** – the Enigma2 service list is reloaded so the new channels appear immediately.

---

## Logging

All operations are logged to:

```
/usr/lib/enigma2/python/Plugins/Extensions/BouquetUpdater/bouqUPDlog.txt
```

The log file is cleared on each plugin startup. Use it to debug any issues.

---

## Translation

The plugin uses `gettext` for internationalization.  
To add a new language:

1. Create a `.po` file for your language in the `locale/` directory.
2. Compile it to `.mo` and place it in the corresponding `LC_MESSAGES/` folder.
3. The plugin will automatically use the system language set in Enigma2.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No bouquets are updated | Check `bouquet_updater.conf` for correct syntax and URLs. |
| Vavoo Resolved fails | The resolved version may not work; use the direct Vavoo bouquet instead. |
| Plugin not visible | Ensure the folder is correctly placed in `/usr/lib/enigma2/python/Plugins/Extensions/` and restart Enigma2. |
| Update never runs automatically | Verify the set hour and that the receiver is on at that time. The timer runs hourly. |

---

### 📜 License Information [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
This is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation
This plugin is released under GPLv3. See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.html#license-text) for full details.
<img width="120" height="58" alt="GPLv3_Logo svg" src="https://github.com/user-attachments/assets/67d32b0a-2a44-4fa9-a972-202daf28808e" />

---
### 🚨 Disclaimer

The project author is not responsible for how this software is used by others. It is not intended to be used for accessing or distributing copyrighted materials without authorization.
Users are solely responsible for determining the legality of their actions.

This repository has no control over the streams, links, or the legality of the content provided by the different hosts (including all mirror sites). It is the end user's responsibility to ensure the legal use of these streams, and we strongly recommend verifying that the content complies with all applicable laws, including copyright laws and regulations of your countrys jurisdiction before use.

---

⭐️ If you find this plugin useful, please give it a star on GitHub!
Thanks! ❤️ 💞 💖 ❤️‍🔥 💗

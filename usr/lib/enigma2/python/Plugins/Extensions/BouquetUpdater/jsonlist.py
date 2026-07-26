# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import logging
import os
import re

try:
    from io import open
except ImportError:
    pass

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


JSON_SOURCE_PREFIX = "jsonlist://"
DEFAULT_JSON_DIRS = ("/usr/lib/jsonListChan", "/usr/lib64/jsonListChan")


def _json_directories(plugin_path=None):
    """Return installed and source-tree locations, without duplicates."""
    directories = []
    if plugin_path:
        # Preferred location: bundled directly inside the plugin directory.
        directories.append(os.path.join(plugin_path, "jsonListChan"))

        # In the package tree PLUGIN_PATH is usr/lib/enigma2/python/Plugins/...
        # Keep the former location for backward compatibility.
        package_lib = os.path.abspath(os.path.join(plugin_path, "../../../../.."))
        directories.append(os.path.join(package_lib, "jsonListChan"))
    directories.extend(DEFAULT_JSON_DIRS)

    result = []
    for directory in directories:
        normalized = os.path.normpath(directory)
        if normalized not in result:
            result.append(normalized)
    return result


def _bouquet_slug(json_filename):
    name = os.path.splitext(os.path.basename(json_filename))[0]
    name = re.sub(r"^lista[_ -]*canali[_ -]*", "", name, flags=re.I)
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return name or "jsonlist"


def bouquet_filename_for(json_filename):
    return "userbouquet.{}.tv".format(_bouquet_slug(json_filename))


def discover_json_sources(plugin_path=None):
    """Discover every JSON list and expose it as an updater source."""
    sources = []
    seen = set()
    for directory in _json_directories(plugin_path):
        if not os.path.isdir(directory):
            continue
        try:
            names = sorted(os.listdir(directory), key=lambda value: value.lower())
        except OSError as error:
            logging.error("[jsonlist] Cannot read %s: %s", directory, error)
            continue
        for name in names:
            if not name.lower().endswith(".json"):
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            sources.append((JSON_SOURCE_PREFIX + name, bouquet_filename_for(name)))
    return sources


def is_jsonlist_source(source):
    return source.lower().startswith(JSON_SOURCE_PREFIX)


def json_source_label(source):
    if not is_jsonlist_source(source):
        return source
    name = os.path.splitext(source[len(JSON_SOURCE_PREFIX):])[0]
    name = re.sub(r"^lista[_ -]*canali[_ -]*", "", name, flags=re.I)
    return name.replace("_", " ").strip() or "JSON list"


def _resolve_json_path(source, plugin_path=None):
    if not is_jsonlist_source(source):
        return None
    filename = os.path.basename(source[len(JSON_SOURCE_PREFIX):])
    for directory in _json_directories(plugin_path):
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def _text(value):
    if value is None:
        return ""
    try:
        return value if isinstance(value, str) else str(value)
    except UnicodeEncodeError:
        return value


def _header_string(item):
    parts = []
    headers_dict = item.get("headers_dict")
    if isinstance(headers_dict, dict):
        for key in sorted(headers_dict):
            if headers_dict[key] is not None:
                parts.append("{}={}".format(key, headers_dict[key]))

    if not parts and item.get("headers"):
        parts.append(_text(item.get("headers")).lstrip("|&"))
    if item.get("user_agent") and not any("user-agent=" in p.lower() for p in parts):
        parts.append("User-Agent={}".format(item["user_agent"]))
    if item.get("referer") and not any("referer=" in p.lower() for p in parts):
        parts.append("Referer={}".format(item["referer"]))
    if item.get("origin") and not any("origin=" in p.lower() for p in parts):
        parts.append("Origin={}".format(item["origin"]))
    return "&".join(part for part in parts if part)


def _load_channels(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        payload = payload.get("channels") or payload.get("items") or payload.get("data") or []
    if not isinstance(payload, list):
        raise ValueError("the JSON root must be a list or contain channels/items/data")

    channels = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        url = _text(item.get("stream_url") or item.get("url")).strip()
        name = _text(item.get("channel_title") or item.get("name") or item.get("title")).strip()
        if not url or not name:
            continue

        event_name = _text(item.get("event_name") or item.get("event_title")).strip()
        event_time = _text(item.get("event_time")).strip()
        group = _text(item.get("category") or item.get("event_cat") or event_name).strip()
        if event_name:
            group = "{} - {}".format(event_time, event_name) if event_time else event_name

        headers = _header_string(item)
        if headers:
            url += ("&" if "|" in url else "|") + headers
        channels.append((name, url, group or "Other"))
    return channels


def _generate_bouquet(name, channels):
    lines = ["#NAME {}\n".format(name)]
    current_group = None
    for channel_name, stream_url, group in channels:
        if group != current_group:
            lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
            lines.append("#DESCRIPTION --- {} ---\n".format(group))
            current_group = group
        lines.append("#SERVICE 4097:0:1:0:0:0:0:0:0:0:{}:{}\n".format(
            quote(stream_url, safe=""), quote(channel_name, safe="")))
        lines.append("#DESCRIPTION {}\n".format(channel_name))
    return "".join(lines)


def process_jsonlist(source, bouquet_filename, plugin_path=None,
                     output_directory="/etc/enigma2"):
    """Read a local JSON list and create/update its Enigma2 bouquet."""
    path = _resolve_json_path(source, plugin_path)
    if not path:
        logging.error("[jsonlist] Source file not found: %s", source)
        return False
    try:
        channels = _load_channels(path)
        if not channels:
            logging.error("[jsonlist] No valid channels in %s", path)
            return False
        bouquet_name = json_source_label(source)
        output_path = os.path.join(output_directory, bouquet_filename)
        if not os.path.isdir(output_directory):
            logging.error("[jsonlist] Output directory not found: %s", output_directory)
            return False
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(_generate_bouquet(bouquet_name, channels))
        logging.info("[jsonlist] Bouquet written: %s (%d channels)",
                     output_path, len(channels))
        return True
    except Exception as error:
        logging.error("[jsonlist] Error processing %s: %s", path, error)
        logging.exception("[jsonlist] Details:")
        return False

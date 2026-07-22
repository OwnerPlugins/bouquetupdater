# -*- coding: utf-8 -*-

from __future__ import absolute_import

__license__ = "GPL-v2"
__version__ = "3.1.0"

import os
import gettext

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

PluginLanguageDomain = "BouquetUpdater"
PluginLanguagePath = "Extensions/BouquetUpdater/locale"


def localeInit():
    lang = language.getLanguage()[:2]  # e.g., "it", "en"
    os.environ["LANGUAGE"] = lang
    gettext.bindtextdomain(
        PluginLanguageDomain,
        resolveFilename(
            SCOPE_PLUGINS,
            PluginLanguagePath))


def _(txt):
    return gettext.dgettext(PluginLanguageDomain, txt) if txt else ""


localeInit()
language.addCallback(localeInit)

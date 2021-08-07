#!/usr/bin/python

import os
import sys
import xbmc
import xbmcaddon

__plugin_handle__ = int(sys.argv[1])


def get_addoninfo(addon_id):
    addon = xbmcaddon.Addon(addon_id)
    return {
        "id": addon_id,
        "addon": addon,
        "language": addon.getLocalizedString,
        "version": addon.getAddonInfo("version"),
        "path": addon.getAddonInfo("path"),
        "profile": xbmc.translatePath(addon.getAddonInfo('profile'))
    }


def get_os():
    try:
        xbmc_os = os.environ.get("OS")
    except:
        xbmc_os = "unknown"
    return xbmc_os

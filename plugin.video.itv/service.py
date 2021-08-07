import os
import xbmc
import xbmcaddon

plugin_id = 'plugin.video.itv'
addon = xbmcaddon.Addon(id=plugin_id)

if addon.getSetting('delcache') == 'true':
    cache = xbmc.translatePath(os.path.join('special://temp'))

    for root, dirs, files in os.walk(cache):
        for f in files:
            if '.log' not in f:
                try:
                    os.unlink(os.path.join(root, f))
                except OSError:
                    pass

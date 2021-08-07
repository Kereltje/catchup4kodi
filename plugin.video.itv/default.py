import time
import logging
import re
import sys
import os
import datetime
import json
import six
from six.moves import urllib

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
# from hashlib import md5
# import codecs
# from bs4 import BeautifulSoup

# external libs
import utils

PLUGIN = 'plugin.video.itv'
ADDON = xbmcaddon.Addon(id=PLUGIN)
icon = xbmc.translatePath(os.path.join('special://home/addons/plugin.video.itv', 'icon.png'))
foricon = xbmc.translatePath(os.path.join('special://home/addons/plugin.video.itv', ''))

# setup cache dir
__scriptname__ = 'ITV'
__scriptid__ = "plugin.video.itv"
__addoninfo__ = utils.get_addoninfo(__scriptid__)
__addon__ = __addoninfo__["addon"]
__settings__ = xbmcaddon.Addon(id=__scriptid__)

DIR_USERDATA = xbmc.translatePath(__addoninfo__["profile"])
SUBTITLES_DIR = os.path.join(DIR_USERDATA, 'Subtitles')
IMAGE_DIR = os.path.join(DIR_USERDATA, 'Images')
FAVORITES_FILE = os.path.join(DIR_USERDATA, 'favorites')

if not os.path.isdir(DIR_USERDATA):
    os.makedirs(DIR_USERDATA)
if not os.path.isdir(SUBTITLES_DIR):
    os.makedirs(SUBTITLES_DIR)
if not os.path.isdir(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# what OS?        
environment = os.environ.get("OS", "xbox")


def download_subtitles_hls(url):
    logging.info('subtitles at =%s' % url)
    outfile = os.path.join(SUBTITLES_DIR, 'itv.srt')
    fw = open(outfile, 'w')

    if not url:
        fw.write("1\n0:00:00,001 --> 0:01:00,001\nNo subtitles available\n\n")
        fw.close()
        return outfile

    try:
        txt = open_url(url)
    except:
        fw.write("1\n0:00:00,001 --> 0:01:00,001\nNo subtitles available\n\n")
        fw.close()
        return outfile
    # six.print_(txt)

    # get styles
    styles = []
    match = re.search(r'<styling>(.+?)</styling>', txt, re.DOTALL)
    if match:
        match = re.findall(r'<style(.*?)>', match.group(1), re.DOTALL)
        if match:
            for style_line in match:
                match = re.search(r'id="(.*?)"', style_line, re.DOTALL)
                style_id = None
                if match:
                    style_id = match.group(1)

                match = re.search(r'color="(.*?)"', style_line, re.DOTALL)
                if match:
                    # Some of the subtitle files use #ffffff color coding, others use plain text.
                    if match.group(1).startswith('#'):
                        styles.append((style_id, match.group(1)[0:7]))
                    else:
                        styles.append((style_id, match.group(1)))
                    # span_replacer = make_span_replacer(styles)
    # six.print_("Retrieved styles")
    # six.print_(styles)

    # get body
    body = re.search(r'<body.*?>(.+?)</body>', txt, re.DOTALL)
    if body:
        # six.print_("Located body")
        # six.print_(body.group(1).encode('utf-8'))
        frames = re.findall(r'<p(.*?)>(.*?)</p>', body.group(1), re.DOTALL)
        if frames:
            index = 1
            # six.print_("Found %s frames"%len(frames))
            # six.print_(frames)
            for formatting, content in frames:
                match = re.search(r'begin=\"(.*?)"', formatting, re.DOTALL)
                if match:
                    # begin="00:00:27:00"
                    start = match.group(1)
                    start_value = start[0:8] + "," + start[9:11] + '0'
                else:
                    # skip as start_value is required to write an entry to file
                    continue

                match = re.search(r'end=\"(.*?)"', formatting, re.DOTALL)
                if match:
                    #      0123456789
                    # end="00:00:29:06"
                    end = match.group(1)
                    end_value = end[0:8] + "," + end[9:11] + '0'
                else:
                    # skip as end_value is required to write an entry to file
                    continue

                match = re.search(r'style=\"(.*?)"', formatting, re.DOTALL)
                if match:
                    style = match.group(1)
                else:
                    style = False

                # TODO: see if this block can be removed all together as start-mil_f and end_mil_f are not used
                # start_split = re.split(r'\.', start)
                # # six.print_(start_split)
                # if len(start_split) > 1:
                #     start_mil_f = start_split[1].ljust(3, '0')
                # else:
                #     start_mil_f = "000"
                # end_split = re.split(r'\.', end)
                # if len(end_split) > 1:
                #     end_mil_f = end_split[1].ljust(3, '0')
                # else:
                #     end_mil_f = "000"

                text = ''
                spans = re.findall(r'<span.*?tts:color="(.*?)">(.*?)<\/span>', content, re.DOTALL)
                if spans:
                    for num, (substyle, line) in enumerate(spans):
                        if num > 0:
                            text = text + '\n'
                        # six.print_(substyle, color, line.encode('utf-8'))
                        text = text + '<font color="%s">%s</font>' % (substyle, line)
                else:
                    if style:
                        color = [value for (style_id, value) in styles if style == style_id]
                        text = text + '<font color="%s">%s</font>' % (color[0], content)
                    else:
                        text = text + content
                    # six.print_(substyle, color, line.encode('utf-8'))
                entry = "%d\n%s --> %s\n%s\n\n" % (index, start_value, end_value, text)
                if entry:
                    fw.write(entry)
                    index += 1

    fw.close()
    return outfile


def create_main_menu():
    if os.path.exists(FAVORITES_FILE) is True:
        add_dir('[COLOR yellow]Favorites[/COLOR]', 'url', 12, '')

    add_dir('Shows', 'https://www.itv.com/hub/shows', 1, icon, is_folder=True)
    # add_dir('Categories',' cats', 205, icon, isFolder=True)
    # add_dir('Live', 'Live', 206, icon, isFolder=True)
    set_view('tvshows', 'default')


def sub_menu_live():
    add_dir('ITV1', 'https://www.itv.com/hub/itv', 8, foricon + 'art/1.png', is_folder=False)
    add_dir('ITV2', 'https://www.itv.com/hub/itv2', 8, foricon + 'art/2.png', is_folder=False)
    add_dir('ITV3', 'https://www.itv.com/hub/itv3', 8, foricon + 'art/3.png', is_folder=False)
    add_dir('ITV4', 'https://www.itv.com/hub/itv4', 8, foricon + 'art/4.png', is_folder=False)
    add_dir('ITVBe', 'https://www.itv.com/hub/itvbe', 8, foricon + 'art/8.jpg', is_folder=False)
    add_dir('CITV', 'https://www.itv.com/hub/citv', 8, foricon + 'art/7.png', is_folder=False)


def sub_menu_categories():
    cats = [('children', 'Children'),
            ('comedy', 'Comedy'),
            ('entertainment', 'Entertainment'),
            ('drama-soaps', 'Drama & Soaps'),
            ('factual', 'Factual'),
            ('films', 'Films'),
            ('news', 'News'),
            ('sport', 'Sport')]

    for url, title in cats:
        add_dir(title, 'https://www.itv.com/hub/categories/%s' % url, 1, icon, is_folder=True)

    set_view('tvshows', 'default')


def sub_menu_shows(url):
    f = urllib.request.urlopen(url)
    buf = f.read()
    buf = re.sub('&amp;', '&', buf)
    buf = re.sub('&middot;', '', buf)
    # six.print_("BUF %s" % buf)
    f.close()
    buf = buf.split('grid-list__item width--one-half width--custard--one-third')
    for p in buf:
        try:
            linkurl = re.compile('href="(.+?)"').findall(p)[0]
            # six.print_(linkurl)
            image = re.compile('srcset="(.+?)"').findall(p)[0]
            if '?' in image:
                image = image.split('?')[0] + '?w=512&h=288'
            # six.print_(image)
            name = re.compile('"tout__title complex-link__target theme__target">(.+?)</h3', re.DOTALL). \
                findall(p)[0].strip()
            # six.print_(name)
            episodes = re.compile('"tout__meta theme__meta">(.+?)</p', re.DOTALL).findall(p)[0].strip()
            if 'mins' in episodes:
                episodes = re.compile('>(.+?)</', re.DOTALL).findall(episodes)[0].strip()
                # six.print_(episodes)
            if 'day left' in episodes or 'days left' in episodes or episodes == '1 episode' or 'mins' in episodes:
                if 'mins' not in episodes:
                    linkurl = linkurl + '##'
                add_dir_2(name + ' - [COLOR orange]%s[/COLOR]' % episodes,
                          linkurl, 3, '', '', image, '', is_folder=False)
            else:
                if 'no episodes' not in episodes.lower():
                    add_dir(name + ' - [COLOR orange]%s[/COLOR]' % episodes, linkurl, 2, image)
        except:
            pass
    set_view('tvshows', 'show')


def sub_menu_favorites():
    import json
    try:
        with open(FAVORITES_FILE) as f:
            a = f.read()
    except:
        pass
    try:
        for i in json.loads(a):
            name = i[0]
            url = i[1]
            iconimage = i[2]
            add_dir(name, url, 204, iconimage)
    except:
        pass


def add_favorite(name, url, iconimage):
    # TODO: getting icon appears to fail
    iconimage = 'http://mercury.itv.com/browser/production/image?q=80&format=jpg&w=800&h=450&productionId=' + iconimage
    import json
    fav_list = []
    if os.path.exists(FAVORITES_FILE) is False:
        six.print_('Making Favorites File')
        fav_list.append((name.split(' -')[0], url, iconimage))
        a = open(FAVORITES_FILE, "w")
        a.write(json.dumps(fav_list))
        a.close()
    else:
        six.print_('Appending Favorites')
        with open(FAVORITES_FILE, "r") as f:
            a = f.read()
        try:
            data = json.loads(a)
            data.append((name.split(' -')[0], url, iconimage))
            b = open(FAVORITES_FILE, "w")
            b.write(json.dumps(data))
            b.close()
        except:
            fav_list.append((name.split(' -')[0], url, iconimage))
            a = open(FAVORITES_FILE, "w")
            a.write(json.dumps(fav_list))
            a.close()


def remove_favorite(name):
    import json
    six.print_('Remove Favorite')
    with open(FAVORITES_FILE) as f:
        a = f.read()
    data = json.loads(a)
    six.print_(len(data))
    for index in range(len(data)):
        try:
            if data[index][0] == name:
                del data[index]
                b = open(FAVORITES_FILE, "w")
                b.write(json.dumps(data))
                b.close()
            if (len(data)) < 1:
                os.remove(FAVORITES_FILE)
        except:
            pass


def parse_date(date_string, dt_format, thestrip):
    try:
        date = datetime.datetime.strptime(date_string, dt_format).strftime(thestrip)
    except TypeError:
        date = datetime.datetime(*(time.strptime(date_string, dt_format)[0:6])).strftime(thestrip)
    return date


def get_eps(name, url):
    f = urllib.request.urlopen(url)
    buf = f.read()
    buf = re.sub('&amp;', '&', buf)
    buf = re.sub('&middot;', '', buf)
    buf = re.sub('&#039;', '\'', buf)
    f.close()
    buf = buf.split('more-episodes')[1]
    buf = buf.split('<div id="')[0]
    buf = buf.split('grid-list__item width--one-half width--custard--one-third')
    episode_name = name.split('-')[0]

    for p in buf:
        try:
            linkurl = re.compile('href="(.+?)"').findall(p)[0]

            image = re.compile('srcset="(.+?)"').findall(p)[0]
            if '?' in image:
                image = image.split('?')[0] + '?w=512&h=288'
            name = re.compile('"tout__title complex-link__target theme__target.+?>(.+?)</h', re.DOTALL) \
                .findall(p)[0].strip()

            if 'datetime' in name:
                name = episode_name
            # episodes = re.compile('"tout__meta theme__meta">(.+?)</p',re.DOTALL).findall (p)[0].strip()
            try:
                description = re.compile('tout__summary theme__subtle">(.+?)</p', re.DOTALL).findall(p)[0].strip()
            except:
                description = ''
            # six.print_(description)

            date = re.compile('datetime="(.+?)">', re.DOTALL).findall(p)[0]
            try:
                episode_time = parse_date(str(date), '%Y-%m-%dT%H:%MZ', '%H:%M')
                episode_date = parse_date(str(date), '%Y-%m-%dT%H:%MZ', '%d/%m/%Y')
                episode_dt = '%s %s' % (episode_date, episode_time)
            except:
                episode_dt = ''

            episode_name = name
            add_dir_2(episode_name + ' - ' + episode_dt, linkurl, 3, date, name, image, description, is_folder=False)
        except:
            pass

    set_view('tvshows', 'episode')


def open_url(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko)"
                      " Version/9.0 Mobile/13G34 Safari/601.1"})
    con = urllib.request.urlopen(req)
    link = con.read()
    if six.PY3:
        return link.decode('utf-8')
    else:
        return link


def play_stream_hls_live(url, iconimage):
    ending = ''
    xbmc.log("URL to fetch: %s" % url)

    buf = open_url(url)

    video_title = re.compile('data-video-title="(.+?)"').findall(buf)[0]
    post_url = re.compile('data-html5-playlist="(.+?)"').findall(buf)[0]
    hmac = re.compile('data-video-hmac="(.+?)"').findall(buf)[0]

    data = {"user": {"itvUserId": "",
                     "entitlements": [],
                     "token": ""
                     },
            "device": {"manufacturer": "Safari",
                       "model": "5",
                       "os": {"name": "Windows NT",
                              "version": "6.1",
                              "type": "desktop"}
                       },
            "client": {"version": "4.1",
                       "id": "browser"
                       },
            "variantAvailability": {"featureset": {"min": ["hls", "aes"],
                                                   "max": ["hls", "aes"]
                                                   },
                                    "platformTag": "youview"
                                    }
            }

    req = urllib.request.Request(post_url)
    jsondata = json.dumps(data)
    if six.PY3:
        jsondataasbytes = jsondata.encode('utf-8')  # needs to be bytes
    else:
        jsondataasbytes = jsondata

    req.add_header('Host', 'simulcast.itv.com')
    req.add_header('Accept', 'application/vnd.itv.vod.playlist.v2+json')
    req.add_header('Proxy-Connection', 'keep-alive')
    req.add_header('Accept-Language', 'en-gb')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('Origin', 'https://www.itv.com')
    req.add_header('Connection', 'keep-alive')
    req.add_header('User-Agent',
                   'Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) '
                   'Version/9.0 Mobile/13G34 Safari/601.1')
    req.add_header('Referer', url)
    req.add_header('hmac', hmac)
    req.add_header('Content-Length', len(jsondataasbytes))

    xbmc.log("Attempting to fetch: %s" % url)
    xbmc.log("With data: %s" % data)
    xbmc.log("with HMAC: %s" % hmac)

    with urllib.request.urlopen(req, jsondataasbytes) as f:
        content = f.read()

    link = json.loads(content)

    stream_url_base = link['Playlist']['Video']['Base']
    bb = link['Playlist']['Video']['MediaFiles']
    try:
        sub_title_link = link['Playlist']['Video']['Subtitles'][0]['Href']
        subtitles_exist = 1
    except:
        subtitles_exist = 0

    # TODO: what if bb is empty, what is the use of iterating over bb here?
    for _ in bb:
        stream_url_resource = bb[0]['Href']

    there_are_subtitles = 0
    if __settings__.getSetting('subtitles_control') == 'true':
        if subtitles_exist == 1:
            subtitles_file = download_subtitles_hls(sub_title_link)
            six.print_("Subtitles at ", subtitles_file)
            there_are_subtitles = 1

    stream_url = stream_url_base + stream_url_resource

    liz = xbmcgui.ListItem(video_title)
    liz.setArt({'icon': 'DefaultVideo.png', 'thumb': iconimage})
    try:
        if there_are_subtitles == 1:
            liz.setSubtitles([subtitles_file])
    except:
        pass

    liz.setInfo(type='Video', infoLabels={'Title': video_title})
    liz.setProperty("IsPlayable", "true")
    liz.setPath(stream_url + ending)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)


def play_hls(url, iconimage):
    xbmc.log("URL to fetch: %s" % url)
    # xbmc.log(str(url))
    if url.endswith('##'):
        url = url.split('##')[0]
        buf = open_url(url)

        link = buf.split('data-episode-current')[1]
        url = re.compile('href="(.+?)"').findall(link)[0]

    # xbmc.log(str(url))
    ending = ''
    buf = open_url(url)

    video_title = re.compile('data-video-title="(.+?)"').findall(buf)[0]
    post_url = re.compile('data-video-id="(.+?)"').findall(buf)[0]
    hmac = re.compile('data-video-hmac="(.+?)"').findall(buf)[0]

    data = {"user": {"itvUserId": "", "entitlements": [], "token": ""},
            "device": {"manufacturer": "Safari", "model": "5",
                       "os": {"name": "Windows NT", "version": "6.1", "type": "desktop"}},
            "client": {"version": "4.1", "id": "browser"}, "variantAvailability": {
            "featureset": {"min": ["hls", "aes", "outband-webvtt"], "max": ["hls", "aes", "outband-webvtt"]},
            "platformTag": "youview"}}

    req = urllib.request.Request(post_url)
    jsondata = json.dumps(data)
    if six.PY3:
        jsondataasbytes = jsondata.encode('utf-8')  # needs to be bytes
    else:
        jsondataasbytes = jsondata

    req.add_header('Host', 'magni.itv.com')
    req.add_header('hmac', hmac)
    req.add_header('Accept', 'application/vnd.itv.vod.playlist.v2+json')
    req.add_header('Proxy-Connection', 'keep-alive')
    req.add_header('Accept-Language', 'en-gb')
    req.add_header('Accept-Encoding', 'gzip, deflate')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('Origin', 'https://www.itv.com')
    req.add_header('Connection', 'keep-alive')
    req.add_header('User-Agent',
                   'Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) '
                   'Version/9.0 Mobile/13G34 Safari/601.1')
    req.add_header('Referer', url)
    req.add_header('Content-Length', len(jsondataasbytes))

    xbmc.log("Attempting to fetch: %s" % post_url)
    xbmc.log("With data: %s" % data)
    xbmc.log("HMAC: %s" % hmac)
    xbmc.log("Refer: %s" % url)

    try:
        content = urllib.request.urlopen(req, jsondataasbytes).read()
    except:
        dialog = xbmcgui.Dialog()
        dialog.ok('ITV Player', '', 'Not Available', '')
        return ''

    link = json.loads(content)

    stream_url_base = link['Playlist']['Video']['Base']
    bb = link['Playlist']['Video']['MediaFiles']
    try:
        sub_title_link = link['Playlist']['Video']['Subtitles'][0]['Href']
        subtitles_exist = 1
    except:
        subtitles_exist = 0

    for _ in bb:
        stream_url_resource = bb[0]['Href']

    there_are_subtitles = 0
    if __settings__.getSetting('subtitles_control') == 'true':
        if subtitles_exist == 1:
            subtitles_file = download_subtitles_hls(sub_title_link)
            six.print_("Subtitles at ", subtitles_file)
            there_are_subtitles = 1

    stream_url = stream_url_base + stream_url_resource

    liz = xbmcgui.ListItem(video_title)
    liz.setArt({'icon': 'DefaultVideo.png', 'thumb': iconimage})
    try:
        if there_are_subtitles == 1:
            liz.setSubtitles([subtitles_file])
    except:
        pass
    liz.setInfo(type='Video', infoLabels={'Title': video_title})
    liz.setProperty("IsPlayable", "true")
    liz.setPath(stream_url + ending)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)


def set_view(content, view_type):
    # set content type so library shows more views and info
    if content:
        xbmcplugin.setContent(int(sys.argv[1]), content)
    # see here if auto-view is enabled(true)
    if ADDON.getSetting('auto-view') == 'true':
        # then get the view type
        xbmc.executebuiltin("Container.SetViewMode(%s)" % ADDON.getSetting(view_type))


def get_params():
    param = {}
    param_string = sys.argv[2]
    if len(param_string) >= 2:
        raw_params = sys.argv[2]
        cleaned_params = raw_params.replace('?', '')
        # TODO: this has no effect, is it a bug?
        if raw_params[len(raw_params) - 1] == '/':
            raw_params = raw_params[0:len(raw_params) - 2]
        pairsofparams = cleaned_params.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


def add_dir(name, url, mode, iconimage, plot='', is_folder=True):
    try:
        pid = iconimage.split('episode/')[1].split('?')[0]
    except:
        # TODO: does it make sense to continue?
        pid = ''

    u = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&name=" + \
        urllib.parse.quote_plus(name) + "&iconimage=" + urllib.parse.quote_plus(iconimage)

    liz = xbmcgui.ListItem(name)
    liz.setArt({'icon': 'DefaultVideo.png',
                'thumb': iconimage}
               )
    liz.setInfo(type="Video", infoLabels={"Title": name,
                                          "Plot": plot}
                )
    liz.setProperty('Fanart_Image', iconimage.replace('w=512&h=288', 'w=1280&h=720'))
    menu = []
    if mode == 2:
        menu.append(('[COLOR yellow]Add To Favourites[/COLOR]', 'RunPlugin(%s?mode=13&url=%s&name=%s&iconimage=%s)' %
                     (sys.argv[0], url, name, pid)))

    if mode == 204:
        menu.append(('[COLOR yellow]Remove Favourite[/COLOR]', 'RunPlugin(%s?mode=14&url=%s&name=%s&iconimage=%s)' %
                     (sys.argv[0], url, name, iconimage)))
    liz.addContextMenuItems(items=menu, replaceItems=False)

    if mode == 3:
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)

    if is_folder is False:
        liz.setProperty("IsPlayable", "true")
        liz.setProperty('mimetype', 'application/x-mpegURL')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=is_folder)
    return ok


def add_dir_2(name, url, mode, date, episode, iconimage, plot='', is_folder=True):
    u = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&name=" + \
        urllib.parse.quote_plus(name) + "&iconimage=" + urllib.parse.quote_plus(iconimage)

    liz = xbmcgui.ListItem(name)
    liz.setArt({'icon': 'DefaultVideo.png',
                'thumb': iconimage}
               )
    liz.setInfo(type="Video", infoLabels={"Title": name,
                                          "Plot": plot,
                                          'Premiered': date,
                                          'Episode': episode}
                )
    liz.setProperty('Fanart_Image', iconimage.replace('w=512&h=288', 'w=1280&h=720'))

    if is_folder is False:
        liz.setProperty("IsPlayable", "true")
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=is_folder)
    return ok


params = get_params()

try:
    param_url = urllib.parse.unquote_plus(params["url"])
except:
    param_url = ''

try:
    param_name = urllib.parse.unquote_plus(params["name"])
except:
    param_name = None

try:
    param_icon_url = urllib.parse.unquote_plus(params["iconimage"])
except:
    param_icon_url = None

try:
    param_mode = int(params["mode"])
except:
    param_mode = None

if param_mode is None or param_url is None or len(param_url) < 1:
    create_main_menu()
elif param_mode == 1:
    sub_menu_shows(param_url)
elif param_mode == 2:
    get_eps(param_name, param_url)
elif param_mode == 3:
    play_hls(param_url, param_icon_url)
elif param_mode == 8:
    play_stream_hls_live(param_url, param_icon_url)
elif param_mode == 12:
    sub_menu_favorites()
elif param_mode == 13:
    add_favorite(param_name, param_url, param_icon_url)
elif param_mode == 14:
    remove_favorite(param_name)
elif param_mode == 204:
    get_eps(param_name, param_url)
elif param_mode == 205:
    sub_menu_categories()
elif param_mode == 206:
    sub_menu_live()
        
xbmcplugin.endOfDirectory(int(sys.argv[1]))

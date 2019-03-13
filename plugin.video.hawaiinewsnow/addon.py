import urllib, urllib2, os, re, xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, sys, time
from cookielib import CookieJar
try:
    import json
except:
    import simplejson as json


HANDLE = int(sys.argv[1])
PATH = sys.argv[0]
QUALITY_TYPES = {'0':'360','1':'720','2':'1080'}
CATEGORY_IDS = {'91610','96072','4773','188022'}

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                splitparams={}
                splitparams=pairsofparams[i].split('=')
                if (len(splitparams))==2:
                    param[splitparams[0]]=splitparams[1]
        return param

class Plugin():
    def __init__(self):
        self.__settings__ = xbmcaddon.Addon(id='plugin.video.hawaiinewsnow')
        self.__language__ = self.__settings__.getLocalizedString
        self.home = self.__settings__.getAddonInfo('path')
        self.icon = xbmc.translatePath( os.path.join( self.home, 'icon.png' ) )
        self.fanart = xbmc.translatePath( os.path.join( self.home, 'fanart.jpg' ) )
        self.dlpath = self.__settings__.getSetting('dlpath')
        self.quality = QUALITY_TYPES[self.__settings__.getSetting('quality')]
        self.apikey = "raycom-franklyapps-khnl-9f062c65"
        self.affiliate_id = '55'
        self.baseurl = "http://developer.worldnow.com"

    def resolve_url(self,url):
        print "Resolving URL: %s" % url
        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def add_link(self, thumb, info, urlparams, fanart=None):
        if not fanart: fanart = self.fanart
        u=PATH+"?"+urllib.urlencode(urlparams)
        item=xbmcgui.ListItem(urlparams['name'], iconImage="DefaultVideo.png", thumbnailImage=thumb)
        item.setInfo(type="Video", infoLabels=info)
        item.setProperty('IsPlayable', 'true')
        item.setProperty('Fanart_Image', fanart)
        # Add the download option in the context menu if it is a MP4
        try:
            if 'url' in urlparams:
                if urlparams['url'][-4:].upper() == '.MP4':
                    params = urllib.urlencode({'name':urlparams['name'],'url':urlparams['url'],'action':'download'})
                    item.addContextMenuItems([('Download','XBMC.RunPlugin(%s?%s)' % (PATH,params))])
        except:
            pass
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item)

    def add_dir(self,thumb,info, urlparams,fanart=None):
        if not fanart: fanart = self.fanart
        u=PATH+"?"+urllib.urlencode(urlparams)
        item=xbmcgui.ListItem(urlparams['name'], iconImage="DefaultFolder.png", thumbnailImage=thumb)
        item.setInfo( type="Video", infoLabels=info )
        item.setProperty('Fanart_Image', fanart)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=True)

    def download(self,name,url):
        dialog = xbmcgui.Dialog()
        if not self.dlpath:
            dialog.ok("Download", "You must set the download folder location in the", "plugin settings before you can download anything")
            return
        if dialog.yesno("Download", 'Download "%s"?' % name):
            xbmc.executebuiltin('XBMC.Notification("Download","Beginning download...")')
            try:
                req = urllib2.urlopen(url)
                CHUNK = 16 * 1024
                with open(os.path.join(self.dlpath,name + '.mp4'),'wb') as f:
                    for chunk in iter(lambda: req.read(CHUNK), ''):
                        f.write(chunk)
                xbmc.executebuiltin('XBMC.Notification("Download","Download complete")')
            except:
                print str(sys.exc_info())  
                xbmc.executebuiltin('XBMC.Notification("Download","Error downloading file")')

    def do_http(self,full_url,type="GET",data=None):
        headers = {'User-Agent':'Apache-HttpClient/UNAVAILABLE (java 1.4)'}#,'Accept-Encoding':'gzip'}
        req = urllib2.Request(full_url,headers=headers,data=data)
        res = urllib2.urlopen(req).read()
        return res

    def get_root_menu(self):
        #KHON2
        icon = "https://lintvkhon.files.wordpress.com/2014/04/logo-khon2-large.png"
        url = 'http://khon2.com/live-stream'
	self.add_link(icon,{'Title':'Watch KHON2 Live'},{'name':'Watch KHON2 Live','action':'live','url':url},icon)
        
        #HNN Live
        url = 'http://www.hawaiinewsnow.com/category/198303/livestream'
        icon = self.icon
        self.add_link(icon,{'Title':'Watch HNN Live'},{'name':'Watch HNN Live','action':'live','url':url},icon)

        #K5 Live
        url = 'http://www.k5thehometeam.com/category/201839/livestream'
        icon = "http://vignette.wikia.nocookie.net/logopedia/images/a/aa/KFVE_2009.png/revision/latest?cb=20110424091952"
        self.add_link(icon,{'Title':'Watch K5 Live'},{'name':'Watch K5 Live','action':'live','url':url},icon)

        for cid in CATEGORY_IDS:
            url = self.baseurl + '/feed/categories/%s/clips?apikey=%s&context-affiliate-id=%s&alt=json' % (cid,self.apikey,self.affiliate_id)
            # get the icon
            res = json.loads(self.do_http(url+"&results=1"))
            fanart = icon = res['rss']['channel']['image']['url']
            title = res['rss']['channel']['title']
            self.add_dir(icon,{'Title':title},{'name':title,'action':'category','url':url+'&results=200'},icon)

    def play_live_stream(self,url):
        res = self.do_http(url)
        for url in re.findall(r"\"(https?\://(?:new\.)?livestream\.com.*)\"",res): 
            res = self.do_http(url)
            jsontext = res.split('window.config = ')[1].split(';</script>')[0]
            js = json.loads(jsontext)
            try:
                m3u8_url = js['event']['stream_info']['m3u8_url']
            except:
                xbmcgui.Dialog().notification(xbmcaddon.Addon().getAddonInfo('name'),"Stream is offline")
                return
            cj = CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            res = opener.open(m3u8_url)
            ua="Player/LG Player 1.0 for Android 5.0.1 (stagefright alternative)"
            try:
		cookies = ["_alid_=" + res.info().getheader('Set-Cookie').split('_alid_=')[1].split('; ')[0]]
            except:
                cookies = []
            try:
                cookies.append("hdntl=" + res.info().getheader('Set-Cookie').split('hdntl=')[1].split('; ')[0])
            except:
                pass
            cookie = '; '.join(cookies)
            res = res.read()
            resolutions = re.findall("RESOLUTION=(\d{3,4}x\d{3,4})",res)
            if len(resolutions) >= self.quality:
                high_res = sorted(resolutions)[self.quality]
            else:
                high_res = sorted(resolutions)[-1]
            play_m3u8 = None
            for i,line in enumerate(res.splitlines()):
                if high_res in line:
                    play_m3u8 = res.splitlines()[i+1].strip()
                    break
            if play_m3u8:
                appstr = '|'
                if cookie: appstr += 'Cookie=%s&' % cookie
                appstr += 'User-Agent=%s' % ua
                self.resolve_url(play_m3u8 + appstr)
                xbmc.Player().play(item=play_m3u8 + appstr,listitem=xbmcgui.ListItem(path=url))

    def videos_from_category(self,url):
        js = json.loads(self.do_http(url))
        for item in js['rss']['channel']['item']:
            try:
                title = item['title'].encode('utf8')
                icon = item['media:thumbnail'][0]['@url']
                videos = []
                for media in item['media:group']['media:content']:
                    if media["@type"] != "video/mp4": continue
                    videos.append(media)
            except:
                xbmc.log("Couldn't find videos for '%s'" % title,xbmc.LOGERROR)
                continue
            if not videos:
                xbmc.log("Couldn't find videos for '%s'" % title,xbmc.LOGERROR)
                for video in videos:
                    xbmc.log("%s" % video['@url'],xbmc.LOGERROR)
                continue
            the_video = None
            for video in videos:
                if video['@height'] == self.quality:
                    the_video = video
                    break
            else:
                the_video = videos[0]

            url = the_video['@url']
            duration = the_video['@duration']
            self.add_link(icon,{'Title':title},{'name':title,'action':'play','url':url},icon)
            #xbmc.log("Adding video %s" % title,xbmc.LOGERROR)

def main():
    xbmcplugin.setContent(HANDLE, 'tvshows')
    params=get_params()
    
    try:
        url=urllib.unquote_plus(params["url"])
    except:
        url=None
    try:
        name=urllib.unquote_plus(params["name"])
    except:
        name=None
    try:
        action=urllib.unquote_plus(params["action"])
    except:
        action=None

    plugin = Plugin()
    if action==None:
        plugin.get_root_menu()

    elif action=='category':
        plugin.videos_from_category(url)

    elif action=='download':
        plugin.download(name,url)

    elif action=='play':
        plugin.resolve_url(url)        

    elif action=='live':
        plugin.play_live_stream(url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


if __name__ == '__main__':
    main()


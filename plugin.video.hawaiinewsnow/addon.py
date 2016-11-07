import urllib, urllib2, os, re, xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, sys, hashlib, time, random, json, datetime
import xml.etree.ElementTree as ET
from base64 import b64decode
from cookielib import CookieJar
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer 
try:
    import json
except:
    import simplejson as json


HANDLE = int(sys.argv[1])
PATH = sys.argv[0]
QUALITY_TYPES = {'0':'low','1':'medium','2':'high'}

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
        self.cache = StorageServer.StorageServer("hawaiinewsnow", 24)
        self.__settings__ = xbmcaddon.Addon(id='plugin.video.hawaiinewsnow')
        self.__language__ = self.__settings__.getLocalizedString
        self.home = self.__settings__.getAddonInfo('path')
        self.regfile = xbmc.translatePath(os.path.join(self.home,'resources','reg'))
        self.icon = xbmc.translatePath( os.path.join( self.home, 'icon.png' ) )
        self.fanart = xbmc.translatePath( os.path.join( self.home, 'fanart.jpg' ) )
        self.dlpath = self.__settings__.getSetting('dlpath')
        #self.quality = QUALITY_TYPES[self.__settings__.getSetting('quality')]
        self.apiid = None
        self.token = None
        self.baseurl = "http://anappnews.vrvm.com/capi/hawaiinewsnow"

    def resolve_url(self,url):
        print "Resolving URL: %s" % url
        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def get_youtube_link(self,url):
        match=re.compile('https?://www.youtube.com/.+?v=(.+)').findall(url)
        link = 'plugin://plugin.video.youtube/?action=play_video&videoid='+ match[0]
        return link

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
        nonce = str(int(time.time() * 1000))
        url = full_url.split('?')[0]
        if '?' not in full_url:
            full_url += '?'
        digest_str = "%s:%s:%s:%s:%s" % (self.apiid,type,url,self.token,nonce)
        digest = hashlib.sha1(digest_str).hexdigest()
        requrl="%s&vid=%s&vnonce=%s&vdigest=%s" % (full_url,self.apiid,nonce,digest)
        headers = {'User-Agent':'Apache-HttpClient/UNAVAILABLE (java 1.4)'}#,'Accept-Encoding':'gzip'}
        req = urllib2.Request(requrl,headers=headers,data=data)
        res = urllib2.urlopen(req).read()
        return res

    def parse_regfile(self):
        with open(self.regfile) as f:
            self.apiid,self.token = f.read().split(':')

    def register(self):
        headers = {'User-Agent':'Apache-HttpClient/UNAVAILABLE (java 1.4)','Content-Type':'text/plain; charset=UTF-8'}
        url = 'http://clientreg.vervewireless.com/locales'
        data = '<localereq version="1.0"><mobileapp id="com.raycom.hnn" version="3.3.13.0" /></localereq>'
        req = urllib2.Request(url,data=data,headers=headers)
        res = urllib2.urlopen(req).read()
        xml = ET.fromstring(res)
        for locales in xml:
            for locale in locales:
                if locale.attrib['name'] == 'HNN for Android':
                    locale_key = locale.attrib['locale_key']
            break
        else:
            print "Couldn't get the locale_key"
            return
        deviceid = hashlib.md5(str(random.random())).hexdigest()
        url="http://clientreg.vervewireless.com/register"
        headers = {'User-Agent':'Apache-HttpClient/UNAVAILABLE (java 1.4)','Content-Type':'application/xml'}
        data = '<registerreq version="1.0"><mobileapp id="com.raycom.hnn" name="" version="3.3.13.0" /><mobiledevice uniqueid="' + deviceid + \
                '" vendor="LGE" model="LGLS990" firmware="5.0.1" /><mobilelocale locale="'+ locale_key +'" /></registerreq>'
        req = urllib2.Request(url,data=data,headers=headers)
        res = urllib2.urlopen(req).read()
        self.apiid = res.split('apiauth id="')[1].split('"',1)[0]
        self.token = res.split('token="')[1].split('"',1)[0]
        # Write them out to a file
        with open(self.regfile,'w') as f:
            f.write("%s:%s" % (self.apiid,self.token))
        return

    def get_root_menu(self):
        icon = "https://lintvkhon.files.wordpress.com/2014/04/logo-khon2-large.png"
        url = 'http://khon2.com/live-stream'
	self.add_link(icon,{'Title':'Watch KHON2 Live'},{'name':'Watch KHON2 Live','action':'live','url':url},icon)
        url = self.baseurl + '/hierarchy?pageName=default_client'
        res = self.do_http(url)
        xml = ET.fromstring(res)
        for videotree in xml.findall(".//outline"):
            if videotree.attrib['name'] == 'WATCH HNN NOW':
                icon = videotree.attrib['iconUrl']
                url = videotree.attrib['xmlUrl']
                self.add_link(icon,
                    {'Title':'Watch HNN Now','Plot':'Hawaii News Now live stream. Available: M-F 4:30-8am, 5-6:30pm, 9pm, 10pm; Sat & Sun 5pm, 9pm, 10pm'},
                    {'name':'Watch HNN Now','action':'live','url':url},
                    icon)
            if videotree.attrib['name'] == 'WATCH K5 Live':
                icon = videotree.attrib['iconUrl']
                url = videotree.attrib['xmlUrl']
                self.add_link(icon,{'Title':'Watch K5 Live'},{'name':'Watch K5 Live','action':'live','url':url},icon)
            if videotree.attrib['name'] == 'Video':
                icon = videotree.attrib['iconUrl']
                for cat in videotree:
                    name = cat.attrib['name']
                    url = cat.attrib['xmlUrl']
                    self.add_dir(self.icon,{'Title':name},{'name':name,'action':'category','url':url},self.icon)

    def play_live_stream(self,url):
        '''
        playtimes=[(datetime.time(4,30,00),datetime.time(8,00,00)),
                (datetime.time(17,00,00),datetime.time(18,30,00)),
                (datetime.time(21,00,00),datetime.time(21,30,00)),
                (datetime.time(22,00,00),datetime.time(22,30,00))]
        now = datetime.datetime.now().time()
        for span in playtimes:
            if now > span[0] and now < span[1]:
                break
        else:
            dialog = xbmcgui.Dialog()
            dialog.ok("Live Stream", "Content is LIVE only during these times (HST):", "Weekdays - 4:30am to 8am, 5pm to 6:30pm, 9pm, 10pm",
                    "Weekends - 5pm, 9pm, 10pm")
        '''
        res = urllib2.urlopen(url).read()
        for url in re.findall("\"(https?://new.livestream.com.*)\"",res): 
            res = urllib2.urlopen(url).read()
            jsontext = res.split('window.config = ')[1].split(';</script>')[0]
            js = json.loads(jsontext)
            m3u8_url = js['event']['stream_info']['m3u8_url']
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
        ns = {'media':"http://search.yahoo.com/mrss/"}
        xml = ET.fromstring(self.do_http(url))
        for itemtree in xml.findall(".//item"):
            title = itemtree.find('title').text.encode('utf8')
            for content in itemtree.findall('.//{%s}content' % ns['media']):
                if content.attrib['type'] == 'video/mp4':
                    url = content.attrib['url']
                    if url[-4:] == '.f4m': continue
                    icon = itemtree.find('.//{%s}thumbnail' % ns['media']).attrib['url']
                    self.add_link(icon,{'TItle':title},{'name':title,'action':'play','url':url},icon)
                    break

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
    if os.path.exists(plugin.regfile):
        plugin.parse_regfile()
    if action==None:
        plugin.register()
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


import urllib, urllib2, os, re, xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, sys, string
from base64 import b64decode
from BeautifulSoup import BeautifulSoup
import datetime
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

# Url to get IDs: amp.silverchalice.co/raycom/api/v2/list?orgId=55&scid=6&id=1&featured=true&ads=more_all
CATIDs = {'Latest':'91610','Sunrise':'4773','Sports':'96072','Popular':'188022','Weather':'75035'}

def make_request(url, headers=None):
        if headers is None:
            headers = {'User-agent' : 'Dalvik/1.6.0 (Linux; U; Android 4.1.1)'}
        try:
            req = urllib2.Request(url,None,headers)
            response = urllib2.urlopen(req,None,30)
            data = response.read()
            return data
        except urllib2.URLError, e:
            print 'We failed to open "%s".' % url
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
            if hasattr(e, 'code'):
                print 'We failed with error code - %s.' % e.code

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
        self.icon = xbmc.translatePath( os.path.join( self.home, 'icon.png' ) )
        self.fanart = xbmc.translatePath( os.path.join( self.home, 'fanart.jpg' ) )
        self.dlpath = self.__settings__.getSetting('dlpath')
        self.quality = QUALITY_TYPES[self.__settings__.getSetting('quality')]

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
             
    def get_root_menu(self):
        self.add_link(self.icon,
                {'TItle':'Hawaii News Now Live','Plot':'Hawaii News Now live stream. Availaable: M-F 4:30-8am, 5-6:30pm, 9pm, 10pm; Sat & Sun 5pm, 9pm, 10pm'},
                {'name':'Live Stream','action':'live','url':'http://khnl-lh.akamaihd.net/i/KHNL_824@54739/master.m3u8'},
                self.fanart)
        for k,v in CATIDs.iteritems():
            # we're passing the category IDs as the url
            self.add_dir(self.icon,{'Title':k,'Plot':'Play videos from category %s' % k},{'name':k,'action':'category','url':v},self.fanart)

    def videos_from_category(self,catid):
        url = 'http://amp.silverchalice.co/raycom/api/v2/query?id=' + catid + '&orgId=55&scId=6&fields=title,description,miniDescription,storyDate,affiliate,topics,bylines,images,videos,dateline,sidebar,textWithHtml&output=ampml'
        data = make_request(url)
        soup = BeautifulSoup(data)
        for i in soup.list('item'):
            name = i.title.getText().encode('utf8')
            desc = i.description.getText().encode('utf8')
            try:
                #thumb = i.find('atom:link',{'rel':'thumb'})['href']
                thumb = i.find('atom:link',{'rel':'original'})['href']
                fanart = thumb
                #fanart = i.find('atom:link',{'rel':'primary'})['href']
            except:
                thumb = self.icon
                fanart = self.fanart
            try:
                u = i.find('media:content',{'amp:rel':self.quality})['url']
            except:
                continue
            self.add_link(thumb,{'Title':name,'Plot':desc},{'name':name,'url':u,'action':'play'},fanart)

    def play_live_stream(self,url):
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
            dialog.ok("Live Stream", "This stream is only available during these times:", "Weekdays - 4:30am to 8am, 5pm to 6:30pm, 9pm, 10pm",
                    "Weekends - 5pm, 9pm, 10pm")
        self.resolve_url(url)

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

    print "Action: "+str(action)
    print "URL: "+str(url)
    print "Name: "+str(name)

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


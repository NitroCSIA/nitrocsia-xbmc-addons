import urllib, urllib2, os, re, xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, sys, string, MormonChannel2, tempfile, shutil, traceback, xbmc
from base64 import b64decode
from BeautifulSoup import BeautifulSoup
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
QUALITY_TYPES = {'0':'360p','1':'720p','2':'1080p'}
error = lambda x: xbmc.log(x,xbmc.LOGERROR)
def make_request(url, headers=None):
        if headers is None:
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:15.0) Gecko/20100101 Firefox/15.0.1'}
        try:
            req = urllib2.Request(url,None,headers)
            response = urllib2.urlopen(req)
            data = response.read()
            return data
        except urllib2.URLError, e:
            error('We failed to open "%s".' % url)
            if hasattr(e, 'reason'):
                error('We failed to reach a server.')
                error('Reason: ' +  e.reason)
            if hasattr(e, 'code'):
                error('We failed with error code - %s.' % e.code)

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
        self.cache = StorageServer.StorageServer("ldsvideos", 24)
        self.__settings__ = xbmcaddon.Addon(id='plugin.video.ldsvideos')
        self.__language__ = self.__settings__.getLocalizedString
        self.home = self.__settings__.getAddonInfo('path')
        self.icon = xbmc.translatePath( os.path.join( self.home, 'imgs', 'icon.png' ) )
        self.byufanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'byu-fanart.jpg' ) )
        self.byuicon = xbmc.translatePath( os.path.join( self.home, 'imgs', 'byu-icon.jpg' ) )
        self.mcicon = xbmc.translatePath( os.path.join( self.home, 'imgs', 'mc-icon.jpg' ) )
        self.mcfanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'mc-fanart.jpg' ) )
        self.fanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'gc-fanart.jpg' ) )
        self.ldsicon = self.icon
        self.dlpath = self.__settings__.getSetting('dlpath')
        # clear out latent items from the temp folder
        tempdir = xbmc.translatePath('special://temp')
        for filename in os.listdir(tempdir):
            if filename[:7] == "tmpimg-":
                try:
                    shutil.rmtree(os.path.join(tempdir,filename))
                except:
                    print "Couldn't delete folder %s from the temp folder" % os.path.join(tempdir,filename)

    def play_slideshow(self,url):
        res = urllib.urlopen(url)
        temp_folder = xbmc.translatePath('special://temp')
        dpath = tempfile.mkdtemp(prefix="tmpimg-",dir=temp_folder)
        temp_folder = os.path.join(temp_folder,dpath)
        extension = os.path.splitext(os.path.basename(url).split('?')[0])[1]
        if not extension: extension = "jpg"
        temp_file = os.path.join(temp_folder,"tmpimg." + extension)
        with open(temp_file,'wb') as f:
            f.write(res.read())
        res.close()
        
        xbmc.executebuiltin('SlideShow(%s)' % temp_folder)

    def resolve_url(self,url):
        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def get_youtube_link(self,url):
        match=re.compile('https?://www.youtube.com/.+?v=(.+)').findall(url)
        link = 'plugin://plugin.video.youtube/?action=play_video&videoid='+ match[0]
        return link

    def ensure_subtitle_file_exists(self, info, urlparams):
        subtitleFilename = info['Title'] + ".en.srt"
        subtitleFilename = re.sub('[^\w\-_\. ]', '_', subtitleFilename)
        rootSubtitleDirectory = os.path.join(xbmc.translatePath('special://temp'), 'subtitles')
        if not os.path.exists(rootSubtitleDirectory):
            os.makedirs(rootSubtitleDirectory)
        showSubtitleDirectory = os.path.join(rootSubtitleDirectory, info['TVShowTitle'])
        if not os.path.exists(showSubtitleDirectory):
            os.makedirs(showSubtitleDirectory)
        
        subtitleFilepath = os.path.join(showSubtitleDirectory, subtitleFilename)

        if not os.path.exists(subtitleFilepath):
            url = self.api_url + 'catalog/getvideosforcontent?contentid=%s&channel=byutv' % urlparams['id']
            res = json.loads(make_request(url,headers=self.headers))
            
            type = False
            if 'ooyalaVOD' in res:
                type = 'ooyalaVOD'
            if 'dvr' in res:
                type = 'dvr'
                
            
            if not type:
                return False
            
            if not res[type]['captionAvailable']:
                return False;
            
            subtitleData = make_request(res[type]['captionFileUrl'])
            if subtitleData == "":
                return False

            captions = re.compile('<p begin="(.+?)" end="(.+?)">(.+?)</p>').findall(subtitleData)
            idx = 1
            subtitleFile = open(subtitleFilepath, 'w+')
            for cstart, cend, caption in captions:
                cstart = cstart.replace('.',',')
                cend = cend.replace('.',',').split('"',1)[0]
                caption = caption.replace('<br/>','\n').replace('&quot;','"').replace('&gt;','>').replace('&apos;',"'").replace('&amp;','&').replace('<span tts:fontStyle="italic">','<i>').replace('</span>','</i>')
                subtitleFile.write( '%s\n%s --> %s\n%s\n\n' % (idx, cstart, cend, caption))
                idx += 1
            
            subtitleFile.close()
        
        return subtitleFilepath

    def add_link(self, thumb, info, urlparams, fanart=None, mtype="video", checkCaption=False):
        if not fanart: fanart = self.fanart
        u=PATH+"?"+urllib.urlencode(urlparams)
        item=xbmcgui.ListItem(urlparams['name'], iconImage="DefaultVideo.png", thumbnailImage=thumb)
        item.setInfo(type=mtype, infoLabels=info)
        item.setProperty('IsPlayable', 'true')
        item.setProperty('Fanart_Image', fanart)

        if checkCaption:
            subtitleFilepath = self.ensure_subtitle_file_exists(info, urlparams)
            if subtitleFilepath:
                item.setSubtitles([subtitleFilepath])
            
        try:
            if 'url' in urlparams:
                if urlparams['url'][-4:].upper() == '.MP4' or urlparams['url'][-4:].upper() == '.MP3' or urlparams['url'][-4:].upper() == '.JPG':
                    params = urllib.urlencode({'name':urlparams['name'],'url':urlparams['url'],'mode':"15"})
                    item.addContextMenuItems([('Download','XBMC.RunPlugin(%s?%s)' % (PATH,params))])
        except:
            pass
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=False)

    def add_dir(self,thumb,info, urlparams,fanart=None,mtype="video"):
        if not fanart: fanart = self.fanart
        u=PATH+"?"+urllib.urlencode(urlparams)
        item=xbmcgui.ListItem(urlparams['name'], iconImage="DefaultFolder.png", thumbnailImage=thumb)
        item.setInfo( type=mtype, infoLabels=info )
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
                with open(os.path.join(self.dlpath,os.path.basename(url)),'wb') as f:
                    for chunk in iter(lambda: req.read(CHUNK), ''):
                        f.write(chunk)
                xbmc.executebuiltin('XBMC.Notification("Download","Download complete")')
            except:
                print str(sys.exc_info())
                xbmc.executebuiltin('XBMC.Notification("Download","Error downloading file")')
             
    def get_root_menu(self):
        self.add_dir(self.mcicon,{'Title':'Mormon Channel','Plot':'Watch and listen to content from the Mormon Channel'},{'name':'Mormon Channel','mode':14},self.mcfanart)
        self.add_dir(self.byuicon,{'Title':'BYU TV','Plot':'Watch videos from BYU TV'},{'name':'BYU TV','mode':1},self.byufanart)
        self.add_dir(self.ldsicon,{'Title':'LDS.org','Plot':'Watch videos from LDS.org'},{'name':'LDS.org','mode':1})

class LDSORG(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.icon = self.ldsicon
        self.postData = xbmc.translatePath(os.path.join(self.home, 'resources', 'req'))
        self.catUrl = 'http://www.lds.org/media-library/video/categories?lang=eng'
        self.headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:15.0) Gecko/20100101 Firefox/15.0.1',
                        'Referer' : 'http://www.lds.com'}
        self.gcLiveUrl = 'http://c.brightcove.com/services/mobile/streaming/index/rendition.m3u8'
        self.baseUrl = 'http://www.lds.org'
        self.gcUrl = self.baseUrl + '/general-conference'
        self.gcfanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'gc-fanart.jpg' ) )
        self.quality = QUALITY_TYPES[self.__settings__.getSetting('lds_quality')]

    def get_menu(self):
        #self.add_link(self.icon,{'Title':'General Conference Live','Plot':'Watch the General Conference live stream!'},
        #        {'name':'Conference Live','url':self.gcLiveUrl,'mode':3},self.gcfanart)
        self.add_dir(self.icon,{'Title':'LDS.org Featured Videos','Plot':'Watch LDS.org featured videos'},
                {'name':'Featured','url':'http://www.lds.org/media-library/video?lang=eng','mode':13},self.fanart)
        self.add_dir(self.icon,{'Title':'LDS.org Video Categories','Plot':'Watch LDS.org videos sorted by category'},
                {'name':'Categories','url':self.catUrl,'mode':2},self.fanart)
        self.add_dir(self.icon,{'Title':'LDS General Conference','Plot':'Watch all General Conferences provided on LDS.org'},
                {'name':'Conferences','mode':7},self.gcfanart)

    def get_categories(self,url):
        url = url + '&start=0&end=500&order=default'
        data = make_request(url)
        soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        for i in soup.body.find("div",{"id":"primary"})("li"):
            name = i.h3.a.getText().encode('utf8')
            u = i.a['href']
            # we'll use the URL to determine if the link returns subcategories or video links
            if 'video/categories/' in i.a['href']:
                self.add_dir(i.img['src'],{'Title':name},{'name':name,'url':u,'mode':2},self.fanart)
            else:
                self.add_dir(i.img['src'],{'Title':name},{'name':name,'url':u,'mode':4},self.fanart)

    def get_video_list(self,url):
        if not url:
            return
        url = url + "&start=1&end=500&order=default"
        response = make_request(url)
        try:
            jsonData = response.split('video_data=')[1].split(';start_id=')[0]
        except:
            print "Didn't find any 'video_data'"
            return
        data = json.loads(jsonData)
        for k,v in data['videos'].iteritems():
            name = v['title'].encode('utf8')
            thumb = v['thumbURL']
            params = v['params']
            #duration = v['length']
            desc = v['description'].encode('utf8')
            for dl in v['downloads']:
                if dl['quality'] == self.quality:
                    href = dl['link']
                    size = dl['size']
                    break
            else:
                try:
                    href = v['downloads'][0]['link']
                except:
                    # If this fails then it indicates that the content can't be downloaded, we have to use a player for it
                    # Try to get the video from brightcove
                    href = self.get_brightcove_video(params)
                    if not href: continue
            self.add_link(thumb,{'Title':name,'Plot':desc},{'name':name,'url':href,'mode':5},self.fanart)

    # This function was taken from the General Conference plugin - https://github.com/viltsu/plugin.video.generalconference
    def resolve_brightcove_req_live(self,url):
        AMF_URL = 'http://c.brightcove.com/services/messagebroker/amf?playerKey=AQ~~,AAAAjP0hvGE~,N-ZbNsw4qBrgc4nqHfwj6D_S8kJzTvbq'
        LIVE_URL = url
        data = open(self.postData, 'rb')
        r = urllib2.Request(AMF_URL, data=data)
        r.add_header('Content-Type', 'application/x-amf')
        r.add_header('Content-Length', '150')
        u = urllib2.urlopen(r)
        content = u.read()
        u.close()
        content = filter(lambda x: x in string.printable, content)
        for m in re.finditer(LIVE_URL + "\?assetId=([0-9]*)", content):
            url = LIVE_URL + '?assetId=' + m.group(1)
            print "Resolving URL %s" % url
            item = xbmcgui.ListItem(path=url)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

    def get_brightcove_video(self,params):
        BC_URL = "https://secure.brightcove.com/services/viewer/htmlFederated"
        req = BC_URL + '?' + urllib.urlencode(params)
        print "Accessing Brightcove URL: %s" % req
        try:
            res = urllib2.urlopen(req).read()
            dic_str = res.split("var experienceJSON = ")[1].split(";\r\n")[0]
            js = json.loads(dic_str)
        except:
            print "ERROR: Couldn't parse Brightcove URL. %s" % traceback.format_exc().splitlines()[-1]
            return None
        largest = 0
        largest_url = None
        try:
            for r in js['data']['programmedContent']['videoPlayer']['mediaDTO']['renditions']:
                if int(r['frameHeight']) == self.quality:
                    return r['defaultURL']
                if int(r['frameHeight']) > largest:
                    largest = int(r['frameHeight'])
                    largest_url = r['defaultURL']
        except:
            print "ERROR: Couldn't handle Brightcove JSON. %s" % traceback.format_exc().splitlines()[-1]
        return largest_url

    def get_conferences(self,submode=None,url=None,sessionName=None):
        if not url:
            url = self.gcUrl
        print "url:%s" % url
        thumb = self.icon
        #data = make_request(url)
        #soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        if not submode: #Conference
            for listName in ['Conferences','Speakers','Topics']:
                try:
                    self.add_dir(thumb,{'Title':listName},{'name':listName,'mode':7,'submode':1},self.gcfanart)
                except:
                    print "ERROR: Couldn't create Generl Conerence lists"
        elif submode == 1: #List Conferences, Speakers, or Topics
            listdic = {'Conferences':1, 'Speakers':2, 'Topics':3}
            data = make_request(url)
            js_str = data.split('lists["')[listdic[sessionName]].split('"] = ')[1].split('</script>')[0].strip()[:-4] + '}'
            listData = json.loads(js_str)
            args_list = []
            for name,uri in listData.iteritems():
                name = name.encode('utf8')
                u = self.baseUrl + uri
                submode = 2 if sessionName == 'Conferences' else 3
                args_list.append((thumb,{'Title':name},{'name':name,'url':u,'mode':7,'submode':submode},self.gcfanart))
            if sessionName == "Conferences":
                args_list = sorted(args_list,key=lambda k: k[2]['name'].split()[-1], reverse=True)
            else:
                args_list = sorted(args_list,key=lambda k: k[2]['name'].lower())
            for args in args_list:
                self.add_dir(*args)
        elif submode == 2: #List Sessions
            soup = BeautifulSoup(make_request(url), convertEntities=BeautifulSoup.HTML_ENTITIES)
            for i in soup.body.findAll("span",{"class":"section__header__title"}):
                name = i.getText().encode('utf8')
                if "Session" in name or "General Relief Society Meeting" in name:
                    self.add_dir(thumb,{'Title':name},{'name':name.replace('&#x27;',"'"),'url':url,'mode':7,'submode':3},self.gcfanart)
        elif submode == 3: #List media
            data = make_request(url)
            if not data:
                raise Exception("No return from %s" % url)
            # For some reason BeautifulSoup doesn't parse the sessions properly
            session_tag = '<div class="section tile-wrapper layout--3 lumen-layout__item">'
            sessions = data.split(session_tag)
            is_session = sessionName.split()[-1] == "Session" or "General Relief Society Meeting" in sessionName
            args_list = []
            for session in sessions:
                soup = BeautifulSoup(session_tag + session, convertEntities=BeautifulSoup.HTML_ENTITIES)
                # If we're dealing with a session - see if there's a "full session" option
                if is_session:
                    if sessionName != soup.find('span').getText().replace('&#x27;',"'"):
                        continue
                    elif soup.find(text=sessionName.replace("'",'&#x27;')).parent.parent.parent.find(text="Download Video"):
                        self.add_dir(thumb,{'Title':sessionName},{'name':sessionName +" - Full Session",'url':url,'mode':7,'submode':4},thumb)
                for div in soup.findAll('div',{'class':re.compile('lumen-tile lumen-tile--horizontal lumen-tile--list.*')}):
                    media_uri = div.a['href']
                    u = self.baseUrl + media_uri
                    try:
                        thumb = "http:" + div.find('noscript')['data-desktop']
                    except:
                        pass
                    name_title = div.find('div',{'class':'lumen-tile__title'}).getText().strip().encode('utf8')
                    if not name_title:
                        try:
                            name_title = div.find('div',{'class':'lumen-tile__title'}).div.getText().strip().encode('utf8')
                        except:
                            name_title = ""
                    name_content = div.find('div',{'class':'lumen-tile__content'}).getText().strip().encode('utf8')
                    name = "%s - %s" % (name_title,name_content)
                    try:
                        name = name.encode('utf8')
                    except:
                        pass
                    args_list.append((thumb,{'Title':name},{'name':name,'url':u,'mode':7,'submode':4},thumb))
            for args in args_list:
                self.add_dir(*args)
        elif submode == 4:
            data = make_request(url)
            # For some reason BeautifulSoup doesn't parse the sessions properly
            session_tag = '<div class="section tile-wrapper layout--3 lumen-layout__item">'
            sessions = data.split(session_tag)
            is_session = sessionName.endswith(" - Full Session")
            soup = None
            for session in sessions:
                soup = BeautifulSoup(session_tag + session, convertEntities=BeautifulSoup.HTML_ENTITIES)
                if is_session:
                    if sessionName.replace(' - Full Session','') == soup.find('span').getText().replace('&#x27;',"'"):
                        break
            if soup:
                if not is_session:
                    author = soup.head.find('meta',{'name':'author'})['content']
                    description = soup.head.find('meta',{'name':'description'})['content'].encode('utf8')
                    thumb = soup.head.find('meta',{'property':'og:image'})['content']
                    title = soup.head.find('meta',{'property':'og:title'})['content'].encode('utf8')
                else:
                    title = sessionName
                    description = sessionName
                for i in soup.findAll('a',{'class':'button button--round button--blue'}):
                    name = i.getText()
                    if name == "Session":
                        name = "MP3"
                    elif name == "Talks and Music":
                        continue
                    u = i['href']
                    self.add_link(thumb,{'Title':title,'Plot':description},{'name':name,'url':u,'mode':5},thumb)
    def get_featured(self):
        url = 'http://www.lds.org/media-library/video?lang=eng'
        soup = BeautifulSoup(make_request(url), convertEntities=BeautifulSoup.HTML_ENTITIES)
        for i in soup.find('div',{'class':'feature-box'}).find('ul',{'class':"feature-preview"})('li'):
            fc = i.find('div',{'class':'feature-control'})
            name = fc.findNext('h3').getText().encode('utf8')
            desc = fc.p.getText().encode('utf8')
            u = fc.findNext('a')['href']
            thumb = "https://www.lds.org" + urllib.quote(i.findNext('img')['src'])
            if 'media-library/video/categories' in u: mode = 2
            else: mode = 4
            self.add_dir(thumb,{'Title':name,'Plot':desc},{'name':name,'url':u,'mode':mode},thumb)
        for i in soup.find('ul',{'class':'media-list'})('li'):
            name = i.findNext('h4').a.getText().encode('utf8')
            desc = i.findNext('p').getText().encode('utf8')
            u = i.find('a',{'class':'video-thumb-play'})['href']
            thumb = i.findNext('img')['src']
            try:
                soup2 = BeautifulSoup(make_request(u), convertEntities=BeautifulSoup.HTML_ENTITIES)
                for j in soup2.find('div',{'class':'galleryMeta'})('p'):
                    try:
                        if "for downloads" in j.a.getText():
                            u = j.a['href']
                            break
                    except:
                        continue
                else:
                    continue
            except:
                print "Couldn't get video link for %s. %s" % (name,traceback.format_exc().splitlines()[-1])
                continue
            if 'media-library/video/categories' in u: mode = 2
            else: mode = 4
            self.add_dir(thumb,{'Title':name,'Plot':desc},{'name':name,'url':u,'mode':mode},thumb)

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
        mode=int(params["mode"])
    except:
        mode=None
    try:
        submode=int(params["submode"])
    except:
        submode=None

    #print "Mode: "+str(mode)
    #print "URL: "+str(url)
    #print "Name: "+str(name)

    lds = LDSORG()
    plugin = Plugin()
    import BYUTV
    byu = BYUTV.BYUTV(plugin)
    mc = MormonChannel2.MormonChannel(plugin)

    if mode==None:
        plugin.get_root_menu()

    elif mode==1:
        if "LDS.org" in name:
            lds.get_menu()
        if "BYU TV" in name:
            byu.get_menu()

    elif mode==2:
        lds.get_categories(url)

    elif mode==3:
        lds.resolve_brightcove_req(url)

    elif mode==4:
        lds.get_video_list(url)

    elif mode==5:
        plugin.resolve_url(url)

    elif mode==6:
        byu.broker(params)
        #byu.play_byu_live()

    elif mode==7:
        lds.get_conferences(submode,url,name)

    elif mode==8:
        byu.get_categories()

    elif mode==9:
        byu.get_shows(submode,name)

    elif mode==10:
        guid=urllib.unquote_plus(params["guid"])
        byu.get_seasons(guid)

    elif mode==11:
        guid=urllib.unquote_plus(params["guid"])
        byu.get_episodes(name,guid,submode)

    elif mode==12:
        byu.get_popular()

    elif mode==13:
        lds.get_featured()

    # Handle all MormonChannel modes
    elif mode==14:
        mc.broker(params)

    elif mode==15:
        plugin.download(name,url)

    elif mode==16:
        plugin.play_slideshow(url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


if __name__ == '__main__':
    main()

import os
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import sys
import xbmc
import urllib2
import time
from addon import *
try:
        import json
except:
        import simplejson as json
log = lambda x: xbmc.log(x,level=xbmc.LOGWARNING)
class BYUTV(Plugin):
    def __init__(self,plugin):
        self.home = plugin.home
        self.api_url = "http://api.byutv.org/api3/"
        self.icon = plugin.byuicon 
        self.fanart = plugin.byufanart
        self.__settings__ = plugin.__settings__
        self.headers = {"x-byutv-platformkey":"xsaaw9c7y5","x-byutv-context":"web$US","content_type":"application/json","user-agent":"Mozilla/5.0 (X11; CrOS x86_64 11210.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3593.0 Safari/537.36"}

    def get_menu(self):
        # Home page id
        page_uid = "cd2346de-66ed-4d33-a763-da7ed1ba7606"
        self.get_page(page_uid,root=True)

    def get_page(self,pageid,root=False):
        url = self.api_url + 'page/getpage?pageid=%s&channel=byutv' % pageid
        log(url)
        '''
        req = urllib2.Request(url)
        for k,v in self.headers.iteritems():
            req.add_header(k,v)
        res = urllib2.urlopen(req)
        log(str(res.read()))
        '''
        res = json.loads(make_request(url,headers=self.headers))
        #import pprint
        #log(pprint.pformat(res))
        for item in res['lists'] + res['menuItems']:
            item['mode'] = 6
            if 'contentType' in item:
                if item['contentType'] not in ['Show','Episode','EpisodeRecentInShow']:
                    continue
                if item['type'] in ['EventCurrent','FilteredSchedule']:
                    continue
                elif item['type'] in ['Episode','Show']:
                    item['id'] = item['target']['value']

            else:
                if item['type'] == 'Text' and item['target']['title'] == 'Shows' and root:
                    item['type'] = 'Show'
                    item['id'] = item['target']['value']
                else:
                    continue
            self.add_dir(self.icon,{'Title':item['name']},item,self.fanart)

    def get_images(self,item):
        thumb = self.icon
        fanart = self.fanart
        try:
            for images in item['images']:
                for index,image in enumerate(images['images']):
                    if index == 1:
                        thumb = image['url']
                    fanart = image['url']
        except:
            pass
        return (thumb,fanart)

    def get_listitems(self,listid):
        
        url = self.api_url + 'list/getlistitems?listid=%s&start=0&limit=500&query=&channel=byutv' % listid
        log(url)
        res = json.loads(make_request(url,headers=self.headers))
        #import pprint
        #log(pprint.pformat(res))
        for item in res['items']:
            newitem = {}
            newitem['mode'] = 6
            if item['subtitle']:
                newitem['name'] = item['title'] + ' - ' + item['subtitle']
            else:
                newitem['name'] = item['title']
            newitem['name'] = newitem['name'].encode('utf8')
            if item['type'] == 'ShowSeason':
                newitem['id'] = item['parameters']['seasonid']
            elif item['type'] in ['Episode','Show']:
                newitem['id'] = item['target']['value']
            else:
                newitem['id'] = item['id']
            newitem['type'] = item['type']
            thumb,fanart = self.get_images(item)
            if item['type'] != 'Episode':
                self.add_dir(thumb,{'Title':newitem['name']},newitem,fanart)
            else:
                self.add_link(thumb,{'Title':item['subtitle'],
                                         'Plot':item['description'],
                                         'TVShowTitle':item['title'],
                                    },newitem,fanart)


    def get_live(self):
        url = self.api_url + 'live/getlivestream?channel=byutv'
        res = json.loads(make_request(url,headers=self.headers))
        urlCode = res['liveStreamConnectionString']
        reqUrl = 'http://player.ooyala.com/sas/player_api/v1/authorization/embed_code/Iyamk6YZTw8DxrC60h0fQipg3BfO/'+urlCode+'?device=android_3plus_sdk-hook&domain=www.ooyala.com&supportedFormats=mp4%2Cm3u8%2Cwv_hls%2Cwv_wvm2Cwv_mp4'
        data = json.loads(make_request(reqUrl))
        url = self.api_url + 'schedule/getcurrentscheduleditem?channel=byutv'
        res = json.loads(make_request(url,headers=self.headers))
        #import pprint
        #log(pprint.pformat(res))
        name = res['showTitle'] + ' - ' + res['episodeTitle']
        thumb,fanart = self.get_images(res)
        for stream in data['authorization_data'][urlCode]['streams']:
            url = b64decode(stream['url']['data'])
            log(url)
            self.add_link(thumb,{'Title':res['episodeTitle'],
                                     'Plot':res['episodeDescription'],
                                     'TVShowTitle':res['showTitle'],
                                     },{'name':name,'mode':5,'url':url},fanart)


    def play_content(self,contentid):
        url = self.api_url + 'catalog/getvideosforcontent?contentid=%s&channel=byutv' % contentid
        res = json.loads(make_request(url,headers=self.headers))
        import pprint
        log(pprint.pformat(res))
        if 'ooyalaVOD' in res.keys():
            url = res['ooyalaVOD']['videoUrl']
        else:
            url = res['dvr']['videoUrl']
        self.resolve_url(url)


    def broker(self,params):
        #print params
        if 'type' not in params.keys():
            self.get_menu()
        elif params['type'] in ['Managed','ShowSeason','Category','EpisodeRecentInShow']:
            self.get_listitems(params['id'])
        elif params['type'] == 'Episode':
            self.play_content(params['id'])
        elif params['type'] == 'Show' or params['type'] == 'EpisodeRecentInShow':
            self.get_page(params['id'])
        elif params['type'] == 'NowNextLater':
            self.get_live()

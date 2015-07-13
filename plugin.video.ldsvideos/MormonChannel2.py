import os
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
#import StorageServer
import sys
import xbmc
import urllib2
try:
        import json
except:
        import simplejson as json
from addon import *
from zipfile import ZipFile
import sqlite3

class MormonChannel(Plugin):
    LANGUAGES = {'0':1,'1':2}
    def __init__(self,plugin):
        self.home = plugin.home
        self.mdb = xbmc.translatePath(os.path.join(self.home, 'resources','mdb.sqlite'))
        self.config_url = "http://broadcast3.lds.org/crowdsource/Mobile/MormonChannel/production/v1/1/"
        self.mdb_url = None
        self.icon = plugin.mcicon 
        self.fanart = plugin.mcfanart
        self.__settings__ = plugin.__settings__
        self.language_id = MormonChannel.LANGUAGES[self.__settings__.getSetting('mc_language')]
        self.conn = sqlite3.connect(self.mdb)
        self.c = self.conn.cursor()
        # This is to map a xbmc type to the  different types of media in the sqlite database according to the ID from the item_type table
        #self.mtypes = ['video','music','video','music','video','video','pictures','video','video']
        #since you can't have Plot with music, we'll call everything video
        self.mtypes = ['video','video','video','video','video','video','pictures','video','viceo']

    def get_db(self):
        js = json.loads(make_request(self.config_url + 'config.json'))
        version = str(js['catalog_version'])
        self.mdb_url = self.config_url + version + '.sqlite.zip'
        mdbzip = make_request(self.mdb_url)
        tmppath = os.path.join(xbmc.translatePath("special://temp"),"mdb.zip")
        with open(tmppath,'wb') as f:
            f.write(mdbzip)
        z = ZipFile(tmppath,'r')
        mdb = z.open('mdb.sqlite','r')
        with open(self.mdb, 'wb') as f:
            f.write(mdb.read())
        mdb.close()
        os.remove(tmppath)   
        self.conn = sqlite3.connect(self.mdb)
        self.c = self.conn.cursor()

    def get_main_menu(self):
        self.get_db()
        self.add_dir(self.icon,{'Title':'Featured'},{'name':"Featured",'feature':True,'mode':14},self.fanart)
        for root_row in self.c.execute("SELECT collection_id FROM root WHERE language_id = %d ORDER BY sort ASC" % self.language_id).fetchall():
            collection_id = root_row[0]
            for col_row in self.c.execute("SELECT title,item FROM collection WHERE gid = %s AND language_id = %d" % (collection_id,self.language_id)).fetchall():
                title = col_row[0]
                self.add_dir(self.icon,{'Title':title.encode('utf8')},{'name':title.encode('utf8'),'collection_id':collection_id,'has_item':col_row[1],'mode':14},self.fanart)

    def get_media_type(self,collection_id):
        mtype = "video"
        for row in self.c.execute("SELECT item_id FROM item_collection_map WHERE collection_id = %s ORDER BY sort ASC" % collection_id):
            for item_row in self.c.execute("SELECT type FROM item WHERE gid = %s" % row[0]):
                mtype = self.mtypes[item_row[0]]
        return mtype

    def get_subcollections(self,params):
        for row in self.c.execute("SELECT child_collection FROM collection_map WHERE parent_collection = %s ORDER BY sort ASC" % params['collection_id']).fetchall():
            collection_id = row[0]
            for col_row in self.c.execute("SELECT title,subtitle,description,image_id,item FROM collection WHERE gid = %s AND language_id = %d" % (collection_id,self.language_id)).fetchall():
                title = col_row[0].encode('utf8')
                subtitle = col_row[1].encode('utf8')
                description = col_row[2].encode('utf8')
                image_id = col_row[3]
                has_item = col_row[4]
                (thumb_url,fanart_url) = self.get_images(image_id)
                mtype = self.get_media_type(collection_id)
                self.add_dir(thumb_url,{'Title':col_row[0],'Plot':description},{'name':title,'collection_id':collection_id,'has_item':has_item,'mode':14},fanart_url,mtype)

    def get_images(self,image_id):
        img_list = []
        for img_row in self.c.execute("SELECT width,url FROM image WHERE image_id = %s" % image_id).fetchall():
            img_list.append((img_row[0],img_row[1]))
            img_list.sort(key=lambda tup: tup[0])
                
            try: thumb_url = [url for width,url in img_list if width < 400][-1]
            except: thumb_url = None

            #try: fanart_url = [url for width,url in img_list if width > 1000][-1]
            try: fanart_url = [url for width,url in img_list][-1]
            except: fanart_url = None

        return (thumb_url,fanart_url)

    def get_radio_meta(self,meta_url):
        xml = make_request(meta_url)
        info = {}
        try: info['Artist'] = [xml.split('<artist>')[1].split('</artist>')[0].encode('utf8')]
        except: info['Artist'] = [""]
        try: info['Title'] = xml.split('<title>')[1].split('</title>')[0].encode('utf8')
        except: info['Title'] = ""
        try: 
            info['Plot'] = xml.split('<comment>')[1].split('</comment>')[0].encode('utf8')
            info['Album'] = info['Plot']
            info['TVShowTitle'] == info['Plot']
        except: pass
        try: info['Duration'] = xml.split('<length>')[1].split('</length>')[0].encode('utf8')
        except: pass
        return info

    def get_items(self,item_id,collection):
        for item_row in self.c.execute("SELECT type,title,subtitle,description,author,url,brightcove_id,\
                                       share_url,alternate_url,live_stream_meta_url,image_id,duration,downloadable \
                                       FROM item WHERE gid = %s AND language_id = %d" % (item_id,self.language_id)).fetchall():
            mtype = item_row[0]
            title = item_row[1].encode('utf8')
            subtitle = item_row[2].encode('utf8')
            description = item_row[3].encode('utf8')
            author = item_row[4].encode('utf8')
            # Determine which url is active
            urls = [item_row[5],item_row[6],item_row[7],item_row[8]]
            url = None
            for u in urls:
                if u == None or u == '': continue
                #print "%s  --  %s" % (title,u.encode('utf8'))
                try:
                    # for some reason the URLs that also have a duration of NULL, do not exist
                    if not item_row[11]:
                        res = urllib2.urlopen(u)
                        res.close()
                    url = u
                    break
                except:
                    print "Couldn't open url %s. Trying another" % u
            if url and "www.youtube.com" in url:
                url = self.get_youtube_link(url) # get youtube plugin URL
                    
            meta_url = item_row[9]
            image_id = item_row[10]
            duration = str(float(float(item_row[11])/60.0)) if item_row[11] else 0
            downloadable = item_row[12]
            (thumb_url,fanart_url) = self.get_images(image_id)
            #if mtype == 1: # Audio
            #    self.add_link(thumb_url,{'Title':title,'Album':collection,'Artist':[author],'Duration':duration},{'name':title,'url':url,'mode':5},fanart_url,self.mtypes[mtype])
            if mtype == 2 or mtype == 1: # Video
                self.add_link(thumb_url,{'Title':title,'Plot':description,'TVShowTitle':collection,'Artist':[author],'Duration':duration},{'name':title,'url':url,'mode':5},fanart_url)

            if mtype == 3 or mtype == 4: # Audio Stream and Video Stream
                info = self.get_radio_meta(meta_url)
                self.add_link(thumb_url,{},{'name':title + ' - ' + info['Title'] + ' - ' + info['Artist'][0],'url':url,'mode':5},fanart_url,self.mtypes[mtype])
            if mtype == 6: # Image
                # Take this opportunity to remove old images from the temp folder
                tempdir = xbmc.translatePath('special://temp')
                for filename in os.listdir(tempdir):
                    if filename[:7] == "tmpimg-":
                        try:
                            shutil.rmtree(os.path.join(tempdir,filename))
                        except:
                            print "Couldn't delete folder %s from the temp folder" % os.path.join(tempdir,filename)
                if not url and fanart_url:
                    url = fanart_url
                self.add_link(thumb_url,{'Title':title,'Caption':description,'Category':collection,'Author':author},{'name':title,'url':url,'mode':16},fanart_url,self.mtypes[mtype])

    def get_items_from_collection(self,params):
        for row in self.c.execute("SELECT item_id FROM item_collection_map WHERE collection_id = %s ORDER BY sort ASC" % params['collection_id']).fetchall():
            item_id = row[0]
            collection = None
            for col_row in self.c.execute("SELECT title FROM collection WHERE gid = %s" % params['collection_id']):
                collection = col_row[0]
            self.get_items(item_id,collection)

    def get_featured(self,params):
        for row in self.c.execute("SELECT collection_id,item_id FROM feature WHERE language_id = %d ORDER BY sort ASC" % self.language_id).fetchall():
            item_id = row[1]
            collection = None
            for col_row in self.c.execute("SELECT title FROM collection WHERE gid = %s" % row[0]):
                collection = col_row[0]
            self.get_items(item_id,collection)

    def broker(self,params):
        #print params
        try: collection_id = params['collection_id']
        except: collection_id = None
        try: has_item = int(params['has_item'])
        except: has_item = None
        try: feature = params['feature']
        except: feature = None
        if collection_id == None and has_item == None and feature == None:
            self.get_main_menu()
        elif feature:
            self.get_featured(params)
        elif not has_item:
            self.get_subcollections(params)
        else:
            self.get_items_from_collection(params)


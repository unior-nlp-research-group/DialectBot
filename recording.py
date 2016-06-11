
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import urllib, urllib2
import webapp2
import logging
import random
import json
import os

import key
import person
import time_util
import sys
import geoUtils
import utility

class Recording(ndb.Model):
    chat_id = ndb.IntegerProperty()
    location = ndb.GeoPtProperty()
    date_time = ndb.DateTimeProperty()
    file_id = ndb.StringProperty()
    url = ndb.StringProperty()
    random_id = ndb.FloatProperty()
    translation = ndb.StringProperty()
    location_approx_det_0 = ndb.StringProperty()  # 5 degree ~ 550Km
    location_approx_det_1 = ndb.StringProperty()  # 2 degree ~ 220Km
    location_approx_det_2 = ndb.StringProperty()  # 1 degree ~ 110Km
    location_approx_det_3 = ndb.StringProperty()  # 0.5 degrees ~ 55Km
    location_approx_det_4 = ndb.StringProperty()  # 0.1 degrees ~ 11Km

def deleteLocationApprox():
    qry = Recording.query()
    for rec in qry:
        for prop in ['location_approx_0', 'location_approx_05', 'location_approx_1', 'location_approx_15', 'location_approx_2']:
            if prop in rec._properties:
                del rec._properties[prop]
        rec.put()


def addRecording(person, file_id):
    approxLocs = getApproxLocations(person.location.lat,person.location.lon)
    r = Recording()
    r.populate(chat_id=person.chat_id, location = person.location,
               date_time=time_util.now(), file_id=file_id, random_id = random.random(),
               location_approx_det_0=approxLocs[0],
               location_approx_det_1=approxLocs[1],
               location_approx_det_2=approxLocs[2],
               location_approx_det_3=approxLocs[3],
               location_approx_det_4=approxLocs[4],
               )
    r.put()
    return r

def deleteRecording(file_id):
    rec = getRecording(file_id)
    rec.key.delete()

def getRecordingCheckIfUrl(file_id_or_url):
    if (file_id_or_url.startswith("http")):
        rec = Recording.query(Recording.url == file_id_or_url).get()
    else:
        rec = Recording.query(Recording.file_id == file_id_or_url).get()
    return rec

def getRecording(file_id):
    rec = Recording.query(Recording.file_id == file_id).get()
    return rec

def addTranslation(file_id, translation):
    rec = getRecording(file_id)
    rec.translation = translation
    rec.put()

def getRandomRecording():
    r = random.random()
    random_entry = Recording.query(Recording.random_id>r).order(Recording.random_id).get()
    if not random_entry:
        random_entry = Recording.query(Recording.random_id<r).order(-Recording.random_id).get()
    if random_entry:
        logging.debug("Random number: " + str(r) + " Selected random id: " + str(random_entry.random_id))
    return random_entry

def getClosestRecording(lat, lon, clusterSizeKm=50):
    approxLocs = getApproxLocations(lat,lon)
    level = 4
    qry = Recording.query(Recording.location_approx_det_4==approxLocs[4])
    if qry.count()==0:
        level = 3
        qry = Recording.query(Recording.location_approx_det_3==approxLocs[3])
        if qry.count()==0:
            level = 2
            qry = Recording.query(Recording.location_approx_det_2==approxLocs[2])
            if qry.count()==0:
                level = 1
                qry = Recording.query(Recording.location_approx_det_1==approxLocs[1])
                if qry.count()==0:
                    level = 0
                    qry = Recording.query(Recording.location_approx_det_0==approxLocs[0])

    if qry.count()==0:
        return None
    logging.debug("Level: " + str(level) + " Qry size: " + str(qry.count()))
    if qry.count()==1:
        return qry.get()
    else:
        minDstRecs = []
        minDst = sys.maxint
        for r in qry:
            dst = geoUtils.distance((lat,lon),(r.location.lat, r.location.lon))
            if dst<(minDst-clusterSizeKm):
                minDst = dst
                minDstRecs = [r]
            elif dst<(minDst+clusterSizeKm):
                minDstRecs.append(r)
        size = len(minDstRecs)
        randomIndx = int(size*random.random())
        return minDstRecs[randomIndx]


def testVivaldi():
    file = open("vivaldi/citiesGPS.tsv")
    count = 0
    for line in file:
        count += 1
    logging.debug('number of lines: ' + str(count))

def removeFormatVoice():
    qry = Recording.query()
    count = 0
    for rec in qry:
        if 'format_voice' in rec._properties:
            del rec._properties['format_voice']
            rec.put()
            count+=1
    return count

def getApproxLocations(lat, lon):
    return [
        getApproxLocationSingle(lat, lon, 0, 5),     # 5 degree ~ 550Km
        getApproxLocationSingle(lat, lon, 0, 2),     # 2 degree ~ 220Km
        getApproxLocationSingle(lat, lon, 0),        # 1 degree ~ 110Km
        getApproxLocationSingle(lat, lon, 1, 5),     # 0.5 degrees ~ 55Km
        getApproxLocationSingle(lat, lon, 1),        # 0.1 degrees ~ 11Km
    ]

def getApproxLocationSingle(lat, lon, roundIndex, base=None):
    if base:
        return str(base*round(lat/base,roundIndex)) + ',' + str(base*round(lon/base,roundIndex))
    else:
        return str(round(lat,roundIndex)) + ',' + str(round(lon,roundIndex))

def initializeApproxLocations():
    qry = Recording.query()
    for r in qry:
        loc = r.location
        approxLocs = getApproxLocations(loc.lat,loc.lon)
        r.location_approx_det_0 = approxLocs[0]  # 5 degree ~ 550Km
        r.location_approx_det_1 = approxLocs[1]  # 2 degree ~ 220Km
        r.location_approx_det_2 = approxLocs[2]  # 1 degree ~ 110Km
        r.location_approx_det_3 = approxLocs[3]  # 0.5 degrees ~ 55Km
        r.location_approx_det_4 = approxLocs[4]  # 0.1 degrees ~ 11Km
        r.put()
    logging.info("Finished initializing approx locations")

def deleteVivaldi():
    ndb.delete_multi(
        Recording.query(Recording.chat_id==0).fetch(keys_only=True)
    )

def countVivaldi():
    return Recording.query(Recording.chat_id==0).count()

def importVivaldi():
    vivaldiBaseUrl = "https://dl.dropboxusercontent.com/u/12016006/Vivaldi/ogg/"
    cityFile = open("vivaldi/citiesGPS.tsv")
    #recFile = open("vivaldi/recStructure_3_4.tsv")
    recFile = open("vivaldi/sample_10_feb_16.tsv")
    cityDictionary = {}
    count = 0
    for line in cityFile:
        city_gps = line.split("\t")
        city = city_gps[0]
        #logging.debug("'" + city_gps[1] + "'")
        loc_string = city_gps[1] #(45.6051865, 10.6900516)
        loctext_split = loc_string[1:-2].split(", ") #trim the \n
        loc = {'latitude': float(loctext_split[0]), 'longitude': float(loctext_split[1])}
        cityDictionary[city] = loc
    listOfRecEntities = []
    for line in recFile:
        # region|translation|city|file
        rtcf = line.split("\t")
        translation = rtcf[1] + " (credits to Vivaldi project, see https://www2.hu-berlin.de/vivaldi)"
        city = rtcf[2]
        locGps =  cityDictionary[city]
        locGeoPt =  ndb.GeoPt(locGps['latitude'], locGps['longitude'])
        fileName = rtcf[3][:-1] #trim the \n
        url = vivaldiBaseUrl + fileName
        r = Recording()
        r.populate(chat_id=0, location = locGeoPt,
               date_time=time_util.now(), url=url, random_id = random.random(), translation = translation)
        listOfRecEntities.append(r)
        count += 1
        if (count==50):
            ndb.put_multi(listOfRecEntities)
            listOfRecEntities = []
            count = 0
    ndb.put_multi(listOfRecEntities)


###########################
## RECORDINGS MAP
###########################

# Run from GAE remote API:
# 	{GAE Path}\remote_api_shell.py -s dialectbot.appspot.com
# 	import export_as_csv

class DownloadRecordingHandler(webapp2.RequestHandler):
    def get(self, file_id):
        if file_id.endswith('.oga'):
            file_id = file_id[:-4]
        urlfetch.set_default_fetch_deadline(60)
        logging.debug("Requested file_id: " + file_id)
        rec = getRecording(file_id)
        if rec:
            resp = urllib2.urlopen(key.BASE_URL + 'getFile', urllib.urlencode(
                {'file_id': rec.file_id})).read()
            file_path = json.loads(resp)['result']['file_path']
            urlFile = key.BASE_URL_FILE + file_path
            logging.debug("Url file: " + urlFile)
            voiceFile = urllib.urlopen(urlFile).read()

            self.response.headers['Content-Type'] = 'application/octet-stream'
            self.response.headers['Content-Disposition'] = 'filename="%s.oga"' % (file_id)
            self.response.out.write(voiceFile)
        else:
            logging.debug("Rec not found")
            self.response.write('No recording found')
            self.response.set_status(404)

        #url = self.request.get() #'url'
        #if file_id:
        #    self.response.write(file_id)
        #json.dumps(json.load(urllib2.urlopen(key.BASE_URL + 'setWebhook', urllib.urlencode({'url': url}))))


"""
def downloadRecordings():
    qry = Recording.query(Recording.file_id !=None)
    count = 0
    for rec in qry:
        resp = urllib2.urlopen(key.BASE_URL + 'getFile', urllib.urlencode(
            {'file_id': rec.file_id})).read()
        outputFile = "recordings/" + rec.file_id + ".oga"
        if not os.path.isfile(outputFile):
            logging.info('asked for file: ')
            logging.info(resp)
            file_path = json.loads(resp)['result']['file_path']
            logging.info('file path:' + file_path)
            urlFile = key.BASE_URL_FILE + file_path
            urllib.urlretrieve(urlFile, outputFile)


def createBlobs():
    voice_url = "https://api.telegram.org/file/bot173222627:AAEzrbHcQ4nstRxVxyk-JeLeMaWmNyUtQrA/voice/file_11.oga"
    voice = urllib2.urlopen(voice_url).read()

class ViewPhotoHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, photo_key):
        if not blobstore.get(photo_key):
            self.error(404)
        else:
            self.send_blob(photo_key)
"""

class ServeDynamicAudioGeoJsonFileHandler(webapp2.RequestHandler):
    def get(self):
        dict = createAudioGeoJsonDict()
        self.response.write(json.dumps(dict, indent=4))

def createAudioGeoJsonFile():
    dict = createAudioGeoJsonDict()
    with open('audiomap/audiomapdata.geojson', 'w') as fp:
        json.dump(dict, fp, indent=4)

maxRandomNoise = 0.01 #about 1 Km

def createAudioGeoJsonDict(addRandomCoordNoise=True):
    featureList = []
    qry = Recording.query(Recording.file_id != None)
    for rec in qry:
        longitude = rec.location.lon
        latitude = rec.location.lat
        if addRandomCoordNoise:
            longitude += utility.getRandomFloat(maxRandomNoise)
            latitude += utility.getRandomFloat(maxRandomNoise)
        name_text = person.getPersonByChatId(rec.chat_id).getName()
        translation_text = rec.translation.encode('utf-8') if rec.translation else "(nessuna traduzione)"
        audioUrl = "http://dialectbot.appspot.com/recordings/{0}.oga".format(rec.file_id)
        feature = {
            "type": "Feature",
            "properties": {
                "name": "<p>{0}: {1}</p>".format(name_text, translation_text),
                "html": "<p><audio width='300' height='32' src='{0}' "
                        "controls='controls'><br />"
                        "Your browser does not support the audio element.<br /></audio></p>".format(audioUrl)
            },
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude]
            }
        }
        featureList.append(feature)
    return {
        "type": "FeatureCollection",
        "features": featureList
    }




"""
{
  "type": "FeatureCollection",
  "features": [
  {
    "type": "Feature",
    "properties": {
      "name": "<a href='http://www.freesound.org/people/genghis%20attenborough/sounds/212798/'>Deep basement</a>",
      "html": "<p><audio width='300' height='32' src='http://www.freesound.org/data/previews/212/212798_205108-lq.mp3' controls='controls'><br />Your browser does not support the audio element.<br /></audio></p>"
    },
    "geometry": {
      "type": "Point",
      "coordinates": [-100,34]
    }
  },{
    "type": "Feature",
    "properties": {
      "name": "<a href='http://www.freesound.org/people/John%20Sipos/sounds/125696/'>Atlantis docks then lands.</a>",
      "html": "<p><audio width='300' height='32' src='http://www.freesound.org/data/previews/125/125696_593024-lq.mp3' controls='controls'><br />Your browser does not support the audio element.<br /></audio></p>"
    },
    "geometry": {
      "type": "Point",
      "coordinates": [-84,40]
    }
  }
  ]
}
"""
from flask import Flask, json, request
from flask_restful import reqparse, abort, Api, Resource
import os
import logging
import requests
from requests_futures import sessions
from datetime import datetime
import hashlib
import sys

from cayennelpp import LppFrame
from cayennelpp.lpp_type import get_lpp_type

TAO_API_KEY = os.environ.get('TAO_API_KEY')
if not TAO_API_KEY: raise AttributeError('You must supply the TAO_API_KEY environment variable !')

#format='%(levelname)s:%(message)s', 
logging.basicConfig(level=os.environ.get('LOGLEVEL', 'INFO'))

log = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(app)

def txtPagesBuilder(*texts):
    container = {}
    pages = container['pages'] = []
    for text in texts:
        pages.append({'text': text})

    return container

## TAO ligne L
### Services
# {"ref":"L","refSup":"","operatorId":"TAO","mnemo":"L","name":"Ligne PONT EUROPE - CHEMIN HALAGE - BUS","type":"BUS","equipment":"","dests":["2","8570","8571","3"]}

### Dests
# {"ref":"8570","refSup":"","operatorId":"TAO","name":"Quais De Loire","direction":"A","service":"L"}
# {"ref":"8571","refSup":"","operatorId":"TAO","name":"Quais De Loire","direction":"A","service":"L"}

### Stops
# {"ref":"285","refSup":"","operatorId":"TAO","stopId":"285","name":"Cdt de Poli","x":6755878,"y":616632,"cap":270,"services":["L"],"dests":["8570"],"publicPlaces":[],"equipment":"","valuableStops":false},
# {"ref":"286","refSup":"","operatorId":"TAO","stopId":"286","name":"Cdt de Poli","x":6755875,"y":616640,"cap":91,"services":["L"],"dests":["8570"],"publicPlaces":[],"equipment":"","valuableStops":false}
# {"ref":"224","refSup":"","operatorId":"TAO","stopId":"224","name":"Chemin de Halage","x":6756114,"y":620090,"cap":78,"services":["L"],"dests":["8570"],"publicPlaces":[],"equipment":"","valuableStops":false}

## TAO ligne B
### Dests
# {"ref":"201","refSup":"","operatorId":"TAO","name":"Georges Pompidou","direction":"R","service":"B"} => OUEST
# {"ref":"225","refSup":"","operatorId":"TAO","name":"Clos Du Hameau","direction":"A","service":"B"} => EST
# {"ref":"225","refSup":"","operatorId":"TAO","name":"Clos Du Hameau","direction":"R","service":"B"}

### Stops
# {"ref":"1692","refSup":"","operatorId":"TAO","stopId":"1692","name":"Beaumonts","x":6756185,"y":616854,"cap":260,"services":["B"],"dests":["201"],"publicPlaces":[],"equipment":"","valuableStops":false} => OUEST
# {"ref":"1693","refSup":"","operatorId":"TAO","stopId":"1693","name":"Beaumonts","x":6756172,"y":616849,"cap":78,"services":["B"],"dests":["225"],"publicPlaces":[],"equipment":"","valuableStops":false} => EST

def buildTaoApiRollingKey():
    now_AAAAMMJJHH_24h = datetime.now().strftime("%Y%m%d%H") #From TAO doc, the format should be : %Y%m%d%H%M
    log.info('TAO API key: [%s] ; Date token: [%s]', TAO_API_KEY, now_AAAAMMJJHH_24h)
    rollingKey = hashlib.md5(TAO_API_KEY.encode('utf-8') + now_AAAAMMJJHH_24h.encode('utf-8')).hexdigest()
    log.info('=> TAO API rolling key: [%s]', rollingKey)
    return rollingKey

def taoBusTimesQuery(taoServiceRef, taoStopId):
    rollingKey = buildTaoApiRollingKey()
    taoQuery = 'http://94.143.218.36/ws.php?module=json&key=%s&function=getBusTimes&stopId=%d&refService=%s' % (rollingKey, taoStopId, taoServiceRef)
    log.info('TAO query: [%s]', taoQuery)
    r = requests.get(taoQuery)
    log.debug('TAO response: [%s]', r.text)

    resObj = json.loads(r.text)
    if len(resObj['busTimes']) > 0:
        return resObj['busTimes'][0]

    return None

def buildTaoBusTimesQuery(taoServiceRef, taoStopId):
    rollingKey = buildTaoApiRollingKey()
    taoQuery = 'http://94.143.218.36/ws.php?module=json&key=%s&function=getBusTimes&stopId=%d&refService=%s' % (rollingKey, taoStopId, taoServiceRef)
    log.info('TAO query: [%s]', taoQuery)

    return taoQuery

class Hello(Resource):
    def get(self):
        return {'hello': 'world'}

class LoremIspum(Resource):
    def get(self):
        return txtPagesBuilder('Hello World !', 'Hello Max ;-)')

class TaoController(Resource):
    def get(self):
        session = sessions.FuturesSession(max_workers=10)
        httpFutures = []

        serviceRefAndStopIdArray = [('B', 1693), ('L', 286), ('L ret', 224)]
        text = ''
        for serviceRefAndStopId in serviceRefAndStopIdArray:
            serviceRef = serviceRefAndStopId[0]
            stopId = serviceRefAndStopId[1]
            #response = taoBusTimesQuery(serviceRef, stopId)
            query = buildTaoBusTimesQuery(serviceRef, stopId)
            httpFutures.append(session.get(query))

        for i, future in enumerate(httpFutures):
            serviceRefAndStopId = serviceRefAndStopIdArray[i]
            serviceRef = serviceRefAndStopId[0]
            stopId = serviceRefAndStopId[1]
            httpResponse = future.result()
            resObj = json.loads(httpResponse.text)
            if len(resObj['busTimes']) > 0:
                response = resObj['busTimes'][0]
            else:
                response = None

            text += '%s: ' % serviceRef
            if response:
                timeDatas = response['timeDatas']
                for timeData in timeDatas:
                    text += '%d ' % timeData['minutes']
                
                serviceDisruption = response['serviceDisruption']
                if serviceDisruption:
                    text += '\n/!\ %s' % serviceDisruption
            else:
                text += 'no data!'
            
            text += '\n'

        return txtPagesBuilder(text)

parser = reqparse.RequestParser()
parser.add_argument('data')
class SensorsController(Resource):
    def post(self):
        args = parser.parse_args(strict=True)
        log.info("Received a payload: %s" % json.dumps(args))
        return {"message": "ok"}

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import requests
import time

MEASUREMENT_DEFAULT_NAME = 'web-data'
MEASUREMENT_SOURCE = 'web-api'

INFLUX_URL = "http://influxdb:8086"
INFLUX_USER = 'admin'
INFLUX_PASSWORD = 'admin'
INFLUX_DB_NAME = 'web_public'

write_api = None
query_api = None

def buildInfluxDbClient():
    influxClient = InfluxDBClient(url=INFLUX_URL, token="", org="testOrg", timeout=3000, enable_gzip=True)

    return influxClient

def createInluxDbBucket():
    # Create DB if it does not exists
    print(f'Attempt creation of InfluxDB bucket {INFLUX_DB_NAME} ...')
    createDbQuery = f'CREATE DATABASE "{INFLUX_DB_NAME}";'
    res = requests.post(f'{INFLUX_URL}/query', data={'q': createDbQuery})
    #print(res.status_code, res.reason)
    res.raise_for_status()

createInluxDbBucket()

influxClient = buildInfluxDbClient()
write_api = influxClient.write_api(write_options=SYNCHRONOUS)
query_api = influxClient.query_api()

# measurement: "nom", tags: map, time: "2009-11-10T23:00:00Z", fields: map
def publishData(measurement, tags, time, fields):
    p = Point(measurement).time(time)
    #log.info("Will plublish %s" % (str(p)))

    for key, value in tags.items():
        p.tag(key, value)

    for key, value in fields.items():
        p.field(key, value)

    write_api.write(bucket=INFLUX_DB_NAME, record=p)
    log.info("Published data point in influxdb.")

def processLpp(deviceUid, payload):
    # First case : payload contain raw data
    time = datetime.utcnow()
    formattedTime = time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    log.info("formattedTime: %s", formattedTime)

    #measurement = topic.replace("/", ".")
    measurement = MEASUREMENT_DEFAULT_NAME

    currentChannel = None
    lppDataIterator = iter(payload.data)
    doneLooping = False
    fields = None
    while not doneLooping:
        lppData = None
        try:
            lppData = next(lppDataIterator)
            #log.info("Looping on LPP data: %s", lppData)

        except StopIteration:
            doneLooping = True

        if (doneLooping or not currentChannel or lppData.channel != currentChannel):
            # Changing channel
            if (fields) :
                tags = { 
                    'source': MEASUREMENT_SOURCE, 
                    'deviceUid': deviceUid, 
                    'qualifier': 'lpp',
                    'channel': currentChannel
                }
                publishData(measurement, tags, formattedTime, fields)

            if (lppData):
                currentChannel = lppData.channel
                fields = {}

        if (lppData):
            dataType = get_lpp_type(lppData.type).name
            dataValue = lppData.value[0]
            #log.info("New field: %s => %s", dataType, dataValue)
            fields[dataType] = dataValue


lppJsonParser = reqparse.RequestParser()
lppJsonParser.add_argument('lpp')
class LppController(Resource):
    def post(self, deviceUid=None):
        if (deviceUid):
            log.info("Posted data for device #%s" % deviceUid)

        frame = None
        if (request.content_type.startswith('application/json')):
            log.info("Received a json LPP: %s" % request.json)
            args = parser.parse_args(strict=True)
            log.info("JSON payload: %s" % json.dumps(args))
            lppBase64Payload = args['lpp']
            frame = LppFrame().from_base64(lppBase64Payload)

        elif (request.content_type.startswith('application/octet-stream')):
            lppBinaryPayload = request.data
            log.info("Received a binary LPP: %s" % lppBinaryPayload)
            frame = LppFrame().from_bytes(lppBinaryPayload)
            #lppPayload = ''.join(["%02x" % char for char in lppData])
            #log.info("Hex LPP in string format: %s" % lppPayload)
       
        if (deviceUid and frame):
            log.info("Frame LPP: %s" % frame)
            try:
                processLpp(deviceUid, frame)
            except Exception as e:
               log.error('Error trying to process LPP !', exc_info=e)
               abort(400, "Unable to process LPP !")

        return {"message": "ok"}


api.add_resource(Hello, '/')
api.add_resource(LoremIspum, '/loremIpsum')
api.add_resource(TaoController, '/tao')
api.add_resource(SensorsController, '/sensors')
api.add_resource(LppController, '/lpp/<deviceUid>')


if __name__ == '__main__': 
  
    app.run(host = "0.0.0.0", debug = True) 



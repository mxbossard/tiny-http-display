from flask import Flask, json
from flask_restful import reqparse, abort, Api, Resource
import os
import logging
import requests
from requests_futures import sessions
from datetime import datetime
import hashlib

TAO_API_KEY = os.environ.get('TAO_API_KEY')
if not TAO_API_KEY: raise AttributeError('You must supply the TAO_API_KEY environment variable !')

#format='%(levelname)s:%(message)s', 
logging.basicConfig(level=os.environ.get('LOGLEVEL', 'DEBUG'))

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

        serviceRefAndStopIdArray = [('B', 1693), ('L1', 285), ('L2', 286)]
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

api.add_resource(Hello, '/')
api.add_resource(LoremIspum, '/loremIpsum')
api.add_resource(TaoController, '/tao')


if __name__ == '__main__': 
  
    app.run(host = "0.0.0.0", debug = True) 



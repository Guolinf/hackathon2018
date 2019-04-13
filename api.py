
import json
import random
import os
import os.path

from flask_cors import CORS

import psycopg2

from werkzeug.utils import secure_filename

from flask import Flask
from flask import request
from flask import Response
from flask import jsonify, redirect


from flask_spyne import Spyne
from spyne.protocol.http import HttpRpc
from spyne.protocol.soap import Soap11
from spyne.protocol.json import JsonDocument
from spyne.model.primitive import Unicode, Integer
from spyne.model.complex import Iterable
from spyne.model.fault import Fault

from spyne import Application, rpc, ServiceBase, \
    Integer, Unicode, Boolean

from spyne.model.complex import ComplexModel

from spyne import Iterable
from spyne.protocol.json import JsonDocument
from spyne.server.wsgi import WsgiApplication


import parsexml


app = Flask(__name__)
CORS(app)

connection = psycopg2.connect(database="main", user="main", password="foobar")
cursor = connection.cursor()



def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join("./static/", filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return str(exc)




@app.route('/', methods=['GET'])
def index():  # pragma: no cover
    content = get_file('index.html')
    return Response(content, mimetype="text/html")


@app.route('/googleTest.js', methods=['GET'])
def jsfile():  # pragma: no cover
    content = get_file('googleTest.js')
    return Response(content, mimetype="application/javascript")


@app.route('/trash.png', methods=['GET'])
def trashfile():  # pragma: no cover
    content = get_file('trash.png')
    return Response(content, mimetype="image/png")


upload_folder = "./uploads/"

ALLOWED_EXTENSIONS = ['gpx']

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/path', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        res = parsexml.parse(open(filepath))
        print "Got %d points" % (len(res),)

        parsexml.insertpath(res, connection, cursor)

        return redirect("/")

    return 'failed'


@app.route('/litter', methods=['PUT'])
def putLitter():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    sql = "insert into litter values (now(), ST_MakePoint(%s, %s))"
    cursor.execute(sql, (lon, lat))

    # find polygon for point
    sql = "select gid from bins, litter where ST_contains(bins.the_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))"
    cursor.execute(sql, (lon, lat))
    if cursor.description != None:
        x = cursor.fetchall()
        print "Found bins: %s" % (x,)
        gid = x[0][0]
        sql = "select count(*) from bins, litter where gid = %s and ST_Contains(bins.the_geom, litter.location::geometry)"
        cursor.execute(sql, (gid,))
        x = cursor.fetchall()
        count = x[0][0]
        sql = "update bins set dirtiness = %s where gid = %s"
        cursor.execute(sql, (count, gid))
    else:
        # no bin found
        pass

    connection.commit()

    result = {'result': 'ok'}

    resp = jsonify(result)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/litter', methods=['OPTIONS'])
def optionsLitter():
    resp = Response()
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/litter', methods=['GET'])
def getLitter():
    latmin = request.args.get('latmin', None)
    latmax = request.args.get('latmax', None)
    lonmin = request.args.get('lonmin', None)
    lonmax = request.args.get('lonmax', None)

    if latmin == None or latmax == None or lonmin == None or lonmax == None:
        return jsonify({'result': 'missing parameters'})


    sql = "select extract(epoch from(reportdate)), st_x(st_asewkt(location)), st_y(st_asewkt(location)) from litter where location && ST_MakeEnvelope(%s, %s, %s, %s,  4326)"
    cursor.execute(sql, (latmin, latmax, lonmin, lonmax))
    if cursor.description != None:
        x = cursor.fetchall()
    else:
        x = []

    geo = makeLitterGeoJSON(x)
    connection.commit()

    resp = jsonify(geo)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/bins', methods=['GET'])
def getBins():
    latmin = request.args.get('latmin', None)
    latmax = request.args.get('latmax', None)
    lonmin = request.args.get('lonmin', None)
    lonmax = request.args.get('lonmax', None)

    #if latmin == None or latmax == None or lonmin == None or lonmax == None:
    #    return jsonify({'result': 'missing parameters'})


    #sql = "select ST_AsGeoJSON(ST_Scale(ST_Translate(the_geom, 0.0, 20), 1.0, 0.7)) from hex_grid"
    #sql = "select ST_AsGeoJSON(ST_translate(ST_Scale(the_geom, 1.0, 0.4), 0.0, 38.46)) from hex_grid"
    sql = "select ST_AsGeoJSON(the_geom), dirtiness, walks from bins"
    cursor.execute(sql)
    x = cursor.fetchall()

    geo = makeBinsGeoJSON(x)
    connection.commit()

    resp = jsonify(geo)
    return resp


def makeLitterGeoJSON(points):
    res = []
    for i in points:
        data = {
          'type': 'Feature',
          'geometry': {
            'type': 'Point',
            'coordinates': [i[1], i[2]]
          },
          "properties": {
          "name": "Litter"
          }
        }
        res.append(data)

    return {
      "type": "FeatureCollection",
      "features": res
    }


bin_dirty_palette = {
  1: '#ffb3b3',
#  2: '#ff9999',
  2: '#ff8080',
#  4: '#ff6666',
  3: '#ff4d4d',
#  6: '#ff3333',
  4: '#ff1a1a',
  5: '#ff0000',
}

bin_walks_palette = {
1: '#b3ff99',
2: '#9fff80',
3: '#8cff66',
4: '#79ff4d',
5: '#66ff33',
}

def makeBinsGeoJSON(thelist):
    res = []
    for i in thelist:
        igeo = json.loads(i[0])

        dirtiness = i[1]
        walks = i[2]

        if dirtiness == 0 and walks == 0:
            continue

        #red = 0#min(dirtiness*30, 255) #random.randint(0, 255)
        #green = 0#255-red # random.randint(0, 255)
        #blue = 0#random.randint(0, 255)
        opacity = 0.0

        if dirtiness > 0:
            color = bin_dirty_palette.get(dirtiness, "#ff0000") #min(dirtiness*50, 255)
            opacity = 0.6
        else:
            #green = min(walks*50, 255)
            color = bin_walks_palette.get(walks, '#66ff33')
            opacity = 0.8

        data = {
          'type': 'Feature',
          'geometry': igeo,
          "properties": {
            'fill': color, #"#%02X%02X%02X" % (red, green, blue),
            'opacity': opacity,
          }
        }
        res.append(data)

    return {
      "type": "FeatureCollection",
      "features": res
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, threaded=False)

"""
spyne = Spyne(app)

@spyne.srpc(Unicode, _returns=Unicode)
def newLitter(username):
    if x == None:
        raise Fault(faultcode='Client', faultstring='Account not found', detail={'uid': username})

    return "ok"

"""

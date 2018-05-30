
import sys

import xmltodict
import psycopg2


def parse(fh):
    data = fh.read()
    #test = open('/home/ubuntu/20180407_223645.gpx').read().
    o = xmltodict.parse(data)
    trkseg = o['gpx']['trk']['trkseg']
    #print len(trkseg)
    res = []
    for i in trkseg:
        i = i['trkpt']
        #print type(i)
        if not isinstance(i, list):
            continue
        for trkpt in i:
            #print trkpt
            lat = trkpt['@lat']
            lon = trkpt['@lon']
            #print lat, lon
            res.append( (lon, lat) )

    return res


def insertpath(points, connection, cursor):

    sql = "insert into paths (path) values (ST_GeomFromText('LINESTRING(%s)', 4326))"
    linestring = ", ".join( [" ".join(i) for i in points] )
    print linestring
    sql = sql % (linestring,)
    cursor.execute(sql, (linestring,))

    sql = "SELECT LASTVAL();"
    cursor.execute(sql)
    if cursor.description == None:
        raise Exception("no lastval?")

    x = cursor.fetchall()
    myid = x[0][0]
    print "myid: %s" % (myid,)

    sql = "update bins set walks = walks+1,dirtiness=0 where gid in (select gid from bins, paths where paths.id = %s and ST_Crosses(bins.the_geom, paths.path))"
    cursor.execute(sql, (myid,))

    connection.commit()


if __name__ == '__main__':
    fh = open(sys.argv[1])
    res = parse(fh)
    print "Got %d points" % (len(res),)

    connection = psycopg2.connect(database="main", user="main", password="foobar")
    cursor = connection.cursor()
    insertpath(res, connection, cursor)


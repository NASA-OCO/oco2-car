import pymysql
import json
from glob import glob
from datetime import datetime


def ingestMODIS():
    with open('../config.json', 'r') as cFile:
        cInfo = cFile.read()
    cVars = json.loads(cInfo)
    dbuser = str(cVars['dbuser'])
    dbpass = str(cVars['dbpass'])
    dbname = str(cVars['dbname'])
    dbhost = str(cVars['dbhost'])

    db = pymysql.connect(host=dbhost, user=dbuser, passwd=dbpass, db=dbname, ssl={"any_non_empty_dict": True})
    cur = db.cursor()

    sql = 'SELECT t.selectionID, DATE(t.targetTimeUTC), s.name FROM selectedTargets t, sites s WHERE t.modisImage IS NULL AND s.targetID=t.targetID AND selectDate IS NOT NULL'
    cur.execute(sql)
    rows = cur.fetchall()
    for thisRow in rows:
        selectionID = thisRow[0]
        date = thisRow[1]
        name = thisRow[2]

        modisPNG = glob(
            'site/images/modis/*_%s_%s.png' % (date, name))
        if modisPNG:
            modis = modisPNG[0].split('/')[-1]
            sql = 'UPDATE selectedTargets SET modisImage="%s" WHERE selectionID=%s AND selectDate IS NOT NULL'
            cur.execute(sql, (modis, selectionID))
            db.commit()

    db.close()

    return

def ingestVIIRS():
    with open('../config.json', 'r') as cFile:
        cInfo = cFile.read()
    cVars = json.loads(cInfo)
    dbuser = str(cVars['dbuser'])
    dbpass = str(cVars['dbpass'])
    dbname = str(cVars['dbname'])
    dbhost = str(cVars['dbhost'])
 
    db = pymysql.connect(host=dbhost, user=dbuser, passwd=dbpass, db=dbname, ssl={"any_non_empty_dict": True})
    cur = db.cursor()

    sql = 'SELECT t.selectionID, DATE(t.targetTimeUTC), s.name FROM selectedTargets t, sites s WHERE t.viirsImage IS NULL AND s.targetID=t.targetID AND selectDate IS NOT NULL'
    cur.execute(sql)
    rows = cur.fetchall()
    for thisRow in rows:
        selectionID = thisRow[0]
        date = thisRow[1]
        name = thisRow[2]

        viirsPNG = glob('site/images/viirs/*_%s_%s.png' % (date, name))
        if viirsPNG:
            viirs = viirsPNG[0].split('/')[-1]
            sql = 'UPDATE selectedTargets SET viirsImage="%s" WHERE selectionID=%s AND selectDate IS NOT NULL'
            cur.execute(sql, (viirs, selectionID))
            db.commit()

    db.close()

    return

if __name__ == '__main__':
    """
    This script will ingest new MODIS and VIIRS
    plots into the database.
    """
    ingestMODIS()
    ingestVIIRS()

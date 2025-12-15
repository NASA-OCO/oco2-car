import pymysql
import sys
import json
from datetime import datetime


def openDB():
    with open('../config.json', 'r') as cFile:
        cInfo = cFile.read()
    cVars = json.loads(cInfo)
    dbuser = str(cVars['dbuser'])
    dbpass = str(cVars['dbpass'])
    dbname = str(cVars['dbname'])
    dbhost = str(cVars['dbhost'])
 
    db = pymysql.connect(host=dbhost, user=dbuser, passwd=dbpass, db=dbname, ssl={"any_non_empty_dict": True})
    cur = db.cursor()
 
    return (db, cur)


def ingestFile(db, cur):
    sql = 'SELECT odfID FROM odfFiles WHERE YEAR(date) >= "2022"'
    cur.execute(sql)
    results = cur.fetchall()
    missingTargetFiles = []
    for thisID in results:
        sql = 'SELECT COUNT(*) FROM futureTargets WHERE odfID=%s'
        cur.execute(sql, (thisID))
        checkID = cur.fetchone()
        if checkID[0] == 0:
            sql = 'SELECT targetFile FROM odfFiles WHERE odfID=%s'
            cur.execute(sql, (thisID))
            tFile = cur.fetchone()
            missingTargetFiles.append([thisID, tFile[0]])
    if len(missingTargetFiles) != 0:
        for thisFile in missingTargetFiles:
            featureCheck = 0
            print('Ingesting: %s' % thisFile[1])
            odfID = thisFile[0][0]
            filename = thisFile[1]
            with open(filename) as f:
                contents = [line.rstrip() for line in f]

            contents = contents[1:]

            for c in contents:
                info = c.split('\t')
                startDate = datetime.strptime(info[0], '%Y-%m-%dT%H:%M:%S.%fZ')
                endDate = datetime.strptime(info[1], '%Y-%m-%dT%H:%M:%S.%fZ')
                orbit = info[2]
                path = info[3]
                name = info[4]
                note = info[5]
                if 'feature' in note and startDate.weekday() == 3:
                  featureCheck += 1
                if featureCheck >= 2:
                  if len(name) != 3:
                       try:
                            sql = 'INSERT INTO futureTargets SET targetID=(SELECT targetID FROM sites WHERE name="%s"), startDate="%s", endDate="%s", orbit=%s, path=%s, note="%s", odfID=%s'
                            cur.execute(sql, (name, startDate, endDate, orbit, path, note, odfID))
                            db.commit()
                       except pymysql.err.IntegrityError:
                            print('%s already in database' % c)
                            pass
                       sql = "UPDATE futureTargets SET selected=1 WHERE note LIKE '%default%' AND odfID=%s"
                       cur.execute(sql, (odfID))
                       db.commit()
                  else:
                       try:
                            sql = 'INSERT INTO futureContacts SET name="%s", startDate="%s", endDate="%s", orbit=%s, path=%s, note="%s", odfID=%s'
                            cur.execute(sql, (name, startDate, endDate, orbit, path, note, odfID))
                            db.commit()
                       except pymysql.err.IntegrityError:
                            print('%s already in database' % c)
                            pass
    else:
        print('Nothing to ingest')

    return

def updateDiff(db, cur):
    sql = 'SELECT odfID, diffFile FROM odfFiles WHERE diffFile IS NOT NULL'
    cur.execute(sql)
    results = cur.fetchall()
    for thisDiff in results:
        with open(thisDiff[1]) as f:
            contents = [line.rstrip() for line in f]
        contents = contents[1:]
        for c in contents:
            info = c.split('\t')
            orbit = info[0] 
            path = info[1]
            originalName = info[2]
            newName = info[3]        
            sql = 'UPDATE futureTargets SET selected=0 WHERE odfID=%s AND orbit=%s AND path=%s'
            cur.execute(sql, (thisDiff[0], orbit, path))
            db.commit()
            sql = 'UPDATE futureTargets SET selected=1 WHERE odfID=%s AND orbit=%s AND path=%s AND targetID=(SELECT targetID FROM sites WHERE name="%s")'
            cur.execute(sql, (thisDiff[0], orbit, path, newName))
            db.commit()
    return

def closeDB(db):
    db.close()

    return

if __name__ == '__main__':
    """
    This script will parse target_options files and insert
    information about future targets into the database.
    """
    db, cur = openDB()
    ingestFile(db, cur)
    updateDiff(db, cur)
    closeDB(db)

import pymysql
import ssl
import json
from urllib.request import urlopen


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


def readData(url):
    ssl._create_default_https_context = ssl._create_unverified_context
    data = urlopen(url)
    info = []
    for l in data:
        if l != '':
            info.append(l.rstrip())
    #info = info[2:]

    return info


def updateDB(info, db, cur):
    for i in info:
        splitInfo = str(i).split('::')
        site = splitInfo[0]
        status = splitInfo[1]
        message = splitInfo[2][:-1]

        if status == 'Yes':
            tcconStatusValue = 1
        elif status == 'No':
            tcconStatusValue = 0
        else:
            tcconStatusValue = 3

        site = site[2:]

        sql = 'SELECT targetID FROM tcconInfo WHERE tcconName="%s"'
        cur.execute(sql, (site))
        try:
            targetID = cur.fetchall()
        except IndexError:
            print('No targetID for %s' % site)
            continue
        if targetID:
            sql = 'UPDATE sites SET tcconStatusValue=%s, tcconStatusText="%s" WHERE targetID=%s'
            cur.execute(sql, (tcconStatusValue, message, targetID[0][0]))
            db.commit()
    return


def closeDB(db):
    db.close()
    
    return


if __name__ == '__main__':
    """
    This script will gather status updates on TCCON validation 
    sites and then update them in the CAR database.    
    """
    url = 'https://parkfalls.gps.caltech.edu/car/opstat/car'
    info = readData(url)
    db, cur = openDB()
    update = updateDB(info, db, cur)
    closeDB(db)

import pymysql
import sys
import json
from datetime import datetime
from glob import glob


def ingestFile(fileList):
    with open('../config.json', 'r') as cFile:
        cInfo = cFile.read()
    cVars = json.loads(cInfo)
    dbuser = str(cVars['dbuser'])
    dbpass = str(cVars['dbpass'])
    dbname = str(cVars['dbname'])
    dbhost = str(cVars['dbhost'])

    db = pymysql.connect(host=dbhost, user=dbuser, passwd=dbpass, db=dbname, ssl={"any_non_empty_dict": True})
    cur = db.cursor()

    for thisFile in fileList:
        sql = 'SELECT odfID FROM odfFiles WHERE odfFile="%s"'
        cur.execute(sql, thisFile)
        results = cur.fetchall()
        odfID = results[0][0]
        try:
            diffFile = sorted(glob('odf/%s/switched_targets*' % thisFile.split('/')[5]))[-1]
        except IndexError:
            diffFile = None
        try:
            newVersion = sorted(glob('/odf/%s/oc2_*002.odf' % thisFile.split('/')[5]))[-1]
            newVersion='002'
        except IndexError:
            newVersion = None
        
        if diffFile != None and newVersion != None:
            sql = 'UPDATE odfFiles SET diffFile="%s", version="002" WHERE odfID=%s'
            cur.execute(sql, (diffFile, odfID))
            db.commit()     
    db.close()

    return


if __name__ == '__main__':
    """
    This script will look for updates to files that were updated
    via the Future Targets page, and logs them into the database.
    """
    fileList = glob('odf/*/*v001*.odf')
    ingestFile(fileList)

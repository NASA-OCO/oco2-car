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
        odfFilename = thisFile
        sql = 'SELECT odfID FROM odfFiles WHERE odfFile="%s"'
        cur.execute(sql, (odfFilename))
        results = cur.fetchone()
        if results == None:
            date = datetime.strptime('_'.join(thisFile.split(
                '/')[5].split('_')[0:3]), '%Y_%m_%d').strftime('%Y-%m-%d 00:00:00')
            version = thisFile.split('/')[-1].split('_')[-1].split('.')[0]
            try:
                diffFile = sorted(glob('odf/switched_targets*'))[-1]
            except IndexError:
                diffFile = None
            try:
                targetFile = sorted(glob('odf/target_options.txt'))[-1]
            except IndexError:
                targetFile = None
            if diffFile == None and targetFile == None:
                sql = 'INSERT INTO odfFiles SET odfFile="%s", date="%s", version="%s", diffFile=NULL, targetFile=NULL' 
                cur.execute(sql, (odfFilename, date, version))
            elif targetFile == None and diffFile != None:
                sql = 'INSERT INTO odfFiles SET odfFile="%s", date="%s", version="%s", diffFile="%s", targetFile=NULL' 
                cur.execute(sql, (odfFilename, date, version, diffFile))
            elif targetFile != None and diffFile == None:
                sql = 'INSERT INTO odfFiles SET odfFile="%s", date="%s", version="%s", diffFile=NULL, targetFile="%s"' 
                cur.execute(sql, (odfFilename, date, version, targetFile))
            else:
                sql = 'INSERT INTO odfFiles SET odfFile="%s", date="%s", version="%s", diffFile="%s", targetFile="%s"' 
                cur.execute(sql, (odfFilename, date, version, diffFile, targetFile))
            db.commit()

            try:
                newODFs = sorted(glob('odf/*.odf'))
                newFile = newODFs[-1]
                if '001' not in newFile:
                    newVersion = newFile.split('/')[-1].split('_')[-1].split('.')[0]
                    sql = 'SELECT version FROM odfFiles WHERE odfFile="%s" AND date="%s" AND version="%s"'
                    cur.execute(sql, (odfFilename, date, version))
                    result = cur.fetchone()
                    try:
                        if int(newVersion) > int(result[0]):
                            sql = 'UPDATE odfFiles SET version="%s" WHERE odfFile="%s" AND date="%s" AND version="%s"'
                            cur.execute(sql, (newVersion, odfFilename, date, version))
                            db.commit()
                    except ValueError:
                        pass
            except IndexError:
                pass
                
    db.close()

    return


if __name__ == '__main__':
    """
    This script will look for new ODF file and record them
    into the database with their companion files.
    """
    fileList = glob('odf/*/*v001*.odf')
    ingestFile(fileList)

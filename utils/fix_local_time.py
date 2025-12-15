import pymysql
import json
from datetime import datetime
from dateutil import tz



with open('../config.json', 'r') as cFile:
    cInfo = cFile.read()
cVars = json.loads(cInfo)
dbuser = str(cVars['dbuser'])
dbpass = str(cVars['dbpass'])
dbname = str(cVars['dbname'])
dbhost = str(cVars['dbhost'])


if __name__ == '__main__':
    """
    This script will set a target's local time based on UTC times for that target in the database.
    """
    db = pymysql.connect(host=dbhost, user=dbuser, passwd=dbpass, db=dbname, ssl={"any_non_empty_dict": True})
    cur = db.cursor()


    sql = 'SELECT s.selectionID, s.targetTimeUTC, t.timezone FROM selectedTargets s, sites t WHERE s.targetID=t.targetID ORDER BY selectionID ASC'
    cur.execute(sql)
    results = cur.fetchall()

    for r in results:
        selectionID = r[0]
        targetTimeUTC = r[1]
        timezone = r[2]

        from_tz = tz.gettz('UTC')
        to_tz = tz.gettz(timezone)
        utc = targetTimeUTC.replace(tzinfo=from_tz)
        targetTimeLocal = utc.astimezone(to_tz).strftime('%Y-%m-%d %H:%M:%S')

        sql = 'UPDATE selectedTargets SET targetTimeLocal="%s" WHERE selectionID=%s'
        cur.execute(sql, (targetTimeLocal, selectionID))
        db.commit()

    db.close()

import datetime
import pymysql
import json

def cookieCleanUp(db, cur):
  now = datetime.datetime.now()
  now = now.strftime("%Y-%m-%d %H:%M:%S")
  sql = 'DELETE FROM authentication WHERE expirationDate < "%s"' 
  cur.execute(sql, (now))
  db.commit()

  return

if __name__ == "__main__":
  """
  This script will clean up expired cookies for users in the database.
  """
  with open('../config.json','r') as cFile:
    cInfo = cFile.read()
  cVars = json.loads(cInfo)
  dbuser = str(cVars['dbuser'])
  dbpass = str(cVars['dbpass'])
  dbname = str(cVars['dbname'])
  dbhost = str(cVars['dbhost'])
    
  db = pymysql.connect(host=dbhost, user=dbuser, passwd=dbpass, db=dbname, ssl={"any_non_empty_dict": True})
  cur = db.cursor()
  cookieCleanUp(db, cur)
  db.close

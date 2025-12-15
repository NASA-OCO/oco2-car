import bottle_mysql
import ldap
import datetime
import uuid
import json
import ast
import csv
import os
import glob
import smtplib
import subprocess
import shutil
from dateutil import tz
from dateutil.relativedelta import relativedelta
from bottle import Bottle, run, route, redirect, template, static_file, request, response, post, get, put, HTTPError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from xhtml2pdf import pisa
from math import sin, cos, acos, radians, degrees

with open('config.json', 'r') as cFile:
    cInfo = cFile.read()
cVars = json.loads(cInfo)
dbuser = str(cVars['dbuser'])
dbpass = str(cVars['dbpass'])
dbname = str(cVars['dbname'])
dbhost = str(cVars['dbhost'])
webhost = str(cVars['webhost'])
webport = str(cVars['webport'])
ldap_server = str(cVars['ldap_server'])
base_dn = str(cVars['base_dn'])
search_filter = str(cVars['search_filter'])
search_field = str(cVars['search_field'])

app = Bottle()
plugin = bottle_mysql.Plugin(
    dbuser=dbuser, dbpass=dbpass, dbname=dbname, dbhost=dbhost)
app.install(plugin)

# Common functions

def checkToken(db, username, token):
    db.execute(
        'SELECT COUNT(*) AS count FROM tokens WHERE username=%s AND token=%s', (username, token,))
    results = db.fetchone()
    if results['count'] == 1:
        tokenCheck = True
        return tokenCheck
    else:
        tokenCheck = False
        return tokenCheck


# Static files

@app.route('/js/<filename:re:.*\.js>')
def server_static(filename):
    return static_file(filename, root='site/js')

@app.route('/images/modis/<filename:re:.*\.png>')
def server_static(filename):
    return static_file(filename, root='site/images/modis')

@app.route('/images/viirs/filename:re:.*\.png>')
def server_static(filename):
    return static_file(filename, root='site/images/viirs')

@app.route('/tofs/<filename:re:.*\.tof>')
def server_static(filename):
    return static_file(filename, root='tofs')

@app.route('/tmp/<filename:re:.*\.tof>')
def server_static(filename):
    return static_file(filename, root='tmp')

@app.route('/cars/<filename:re:.*\.pdf>')
def server_static(filename):
    return static_file(filename, root='cars')

@app.route('/docs/<filename:re:.*\.pdf>')
def server_static(filename):
    return static_file(filename, root='docs')

@app.route('/odf/<filename:re:.*\.odf>')
def server_static(filename):
    return static_file(filename, root='odf')

@app.route('/odf<filename:re:.*\.txt>')
def server_static(filename):
    return static_file(filename, root='odf')

@app.route('/kml/sites/<filename:re:.*\.kml>')
def server_static(filename):
    return static_file(filename, root='kml/sites')

@app.route('/kml/paths/Both/<filename:re:.*\.kml>')
def server_static(filename):
    return static_file(filename, root='kml/paths/Both')

@app.route('/kml/paths/Nadir/<filename:re:.*\.kml>')
def server_static(filename):
    return static_file(filename, root='kml/paths/Nadir')

@app.route('/kml/paths/Glint/<filename:re:.*\.kml>')
def server_static(filename):
    return static_file(filename, root='kml/paths/Glint')

@app.route('/kml/target_data/<filename:re:.*\.zip>')
def server_static(filename):
    return static_file(filename, root='kml/target_data')

@app.route('/plots/<filename:re:.*\.png>')
def server_static(filename):
    return static_file(filename, root='plots')


# Web Pages

# Home page


@app.route('/')
def index():
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    return template('site/index.html', menuFile=menuFile, footerFile=footerFile)

# TOFs page


@app.route('/tofs')
def tofs(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            fileList = glob.glob('tofs/*.tof')
            latestFile = max(fileList, key=os.path.getctime).split('/')[-1]
            latestFileStub = 'tofs/' + \
                '_'.join(latestFile.split('_')[0:5]) + '*.tof'
            checkDuplicates = sorted(glob.glob(latestFileStub))
            if len(checkDuplicates) > 1:
                latestFile = checkDuplicates[-1].split('/')[-1]
                unusedFiles = checkDuplicates[0:-1]
                for f in unusedFiles:
                    ignoreFile = f.split('/')[-1]
                    db.execute(
                        'SELECT COUNT(filename) AS filename FROM tofFiles WHERE filename=%s', (ignoreFile,))
                    row = db.fetchone()
                    checkIgnoredFile = row['filename']
                    if checkIgnoredFile == 0:
                        db.execute(
                            'INSERT INTO tofFiles SET filename=%s, ignored=1, createTime="2022-01-01 00:00:00"', (ignoreFile,))
            db.execute(
                'SELECT COUNT(filename) AS filename FROM tofFiles WHERE filename=%s', (latestFile,))
            row = db.fetchone()
            fileCheck = row['filename']
            if fileCheck != 0:
                latestFile = None
            else:
                pathInfo = 'tofs/'
                latestFile = pathInfo + latestFile
            db.execute(
                'SELECT * FROM tofFiles WHERE ignored=0 order by createTime DESC')
            row = db.fetchall()
            return template('site/tofs.html', menuFile=menuFile, footerFile=footerFile, row=row, latestFile=latestFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)

# Upload a new TOF


@app.route('/tofs/upload', method='POST')
def upload_tof(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            tofFile = request.files.get('tofFile')
            latestFile = request.forms.get('latestFile')
            overwriteFile = request.forms.get('overwriteFile')
            if tofFile.filename == 'empty':
                tofFile = None
            # First, make sure we have a file to work with.  If not, send the user an error message telling them there's no file.
            if tofFile == None and latestFile == None and overwriteFile == None:
                message = 'You did not select a TOF file and there is no latest TOF file available.  Please go back and select a file to upload.'
                return template('site/tofs-upload-error.html', menuFile=menuFile, footerFile=footerFile, message=message)
            # The overwrite file takes precedence since it only has a value if there's an overwrite situation.
            if overwriteFile != None:
                name = overwriteFile.split('/')[-1].split('.')[0]
                ext = '.' + overwriteFile.split('/')[-1].split('.')[-1]
                save_path='tofs/'
                os.remove('tofs/%s%s' % (name, ext))   
                shutil.move('tmp/%s%s' % (name, ext), '%s%s%s' % (save_path, name, ext))
            else:
                try:
                    # For whatever kind of TOF is uploaded, we need to check that it has a .tof extension.  If not, error out.
                    name, ext = os.path.splitext(tofFile.filename)
                    if ext not in ('.tof'):
                        message = 'This file extension is not allowed.  Please go back and upload a .tof file.'
                        return template('site/tofs-upload-error.html', menuFile=menuFile, footerFile=footerFile, message=message)
                    save_path = 'tofs/'
                    # Try to save the uploaded TOF file
                    try:
                        tofFile.save(save_path)
                    # If there's no uploaded TOF file, then we have a latest file or overwrite file situation
                    except OSError:
                        db.execute('SELECT tofID FROM tofFiles where filename=%s', (tofFile.filename,))
                        row = db.fetchone()
                        # If this is an overwrite situation, then make sure the file hasn't already been ingested into the DB.  If it has, let the user know.
                        if row != None:
                            message='A file with the same name as the one you are trying to upload has already been ingested into the database.  Please contact the website developer for assistance.'
                            return template('site/tofs-upload-error.html', menuFile=menuFile, footerFile=footerFile, message=message)
                        # Assuming the user is ok with an overwrite, save the file to the tmp/ directory.  Will move it into place on the 2nd pass through this form.
                        try:
                            tofFile.save('tmp/')
                        # If somehow the overwrite file is still in tmp/ when the user goes to overwrite, remove it and then try to save it again 
                        except OSError:
                            os.remove('tmp/%s%s' % (name, ext))
                            tofFile.save('tmp/')
                        overwriteFile = '%s%s%s' % (save_path, name, ext)
                        # Let the user know a file exists with the same names as the file they're trying to upload.  If they're ok with it, we'll pass through this form again.
                        message = 'You are attempting to upload a new file that has the same name as one already on the filesystem.  Neither file has been ingested into the database yet.  If you would like to proceed uploading the file you submitted rather than the one of the filesystem, click the button below.  Otherwise, go back to the TOFs page and select the latest file.'
                        return template('site/tofs-upload-overwrite.html', menuFile=menuFile, footerFile=footerFile, message=message, overwriteFile=overwriteFile)
                # If there's no TOF file being uploaded (and nothing overwritten) then we'll use the latest file.
                except AttributeError:
                    tofFile = latestFile
                    name = tofFile.split('/')[-1].split('.')[0]
                    ext = '.' + tofFile.split('.')[1]
                    save_path = 'tofs/'
            # Make sure the file isn't already in the DB; this is not for an overwrite situation since that gets stopped in its tracks above if a file with the same name is already in there.
            db.execute(
                'SELECT tofID, filename FROM tofFiles WHERE filename LIKE %s', (name[:-8] + "%",))
            row = db.fetchone()
            if row != None:
                db.execute('DELETE FROM tofFiles WHERE tofID=%s',
                           (row['tofID'],))
            # Begin the ingest process
            minGCDate = None
            maxGCDate = None
            gcInfo = []
            selectionInfo = []
            with open('%s%s%s' % (save_path, name, ext)) as f:
                contents = [line.rstrip() for line in f]
            for line in contents:
                if '.tof' in line:
                    filename = line.split(' ')[-1]
                elif 'Header' in line or 'BEGIN' in line or 'END' in line:
                    pass
                elif 'Creation Time' in line:
                    createTime = line.split(' ')[-1].replace('T', ' ')
                elif '#' not in line:
                    infoParts = line.split('\t')
                    if len(infoParts) == 4:
                        gcDateTime = datetime.datetime.strptime(
                            ' '.join(infoParts[0:2]), '%y/%m/%d %H:%M:%S')
                        if minGCDate == None:
                            minGCDate = gcDateTime
                        maxGCDate = gcDateTime
                        orbit = infoParts[3]
                        info = {'gcDateTime': gcDateTime,
                                'orbit': orbit}
                        gcInfo.append(info)
                    elif len(infoParts) == 10:
                        siteID = infoParts[0]
                        name = infoParts[1]
                        targetTimeUTC = datetime.datetime.strptime(
                            ' '.join(infoParts[2:4]), '%y/%m/%d %H:%M:%S')
                        db.execute(
                            'SELECT timezone FROM sites WHERE siteID=%s AND name=%s', (siteID, name,))
                        tzInfo = db.fetchall()
                        for t in tzInfo:
                            timezone = t['timezone']
                        from_tz = tz.gettz('UTC')
                        to_tz = tz.gettz(timezone)
                        utc = targetTimeUTC.replace(tzinfo=from_tz)
                        targetTimeLocal = utc.astimezone(
                            to_tz).strftime('%Y-%m-%d %H:%M:%S')
                        orbit = infoParts[4]
                        path = infoParts[5]
                        obsTimeFormatted = infoParts[6]
                        obsTime = (int(obsTimeFormatted.split(':')[
                            0]) * 60) + int(obsTimeFormatted.split(':')[1])
                        firstOrbit = infoParts[7]
                        lastOrbit = infoParts[8]
                        minGlintAngle = infoParts[9]
                        info = {'siteID': siteID,
                                'name': name,
                                'targetTimeUTC': targetTimeUTC,
                                'targetTimeLocal': targetTimeLocal,
                                'orbit': orbit,
                                'path': path,
                                'obsTime': obsTime,
                                'firstOrbit': firstOrbit,
                                'lastOrbit': lastOrbit,
                                'minGlintAngle': minGlintAngle,
                                'gcDateTime': gcDateTime}
                        selectionInfo.append(info)
                    else:
                        pass
                else:
                    pass
            db.execute('INSERT INTO tofFiles (filename, createTime, maxGCDate, minGCDate, createdDate, createdBy) VALUES (%s, %s, %s, %s, %s, %s)',
                       (filename, createTime, maxGCDate, minGCDate, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username,))
            db.execute(
                'SELECT tofID FROM tofFiles WHERE filename=%s', (filename,))
            row = db.fetchone()
            thisTofID = row['tofID']
            for thisG in gcInfo:
                db.execute('INSERT INTO gcs SET tofID=%s, gcDateTime=%s, orbit=%s',
                           (thisTofID, thisG['gcDateTime'], thisG['orbit'],))
            for thisS in selectionInfo:
                if thisS['targetTimeUTC'].date() <= maxGCDate.date():
                    db.execute('INSERT INTO selectedTargets SET tofID=%s, targetID=(SELECT targetID FROM sites WHERE siteID=%s AND name=%s), targetTimeUTC=%s, targetTimeLocal=%s, orbit=%s, path=%s, obsTime=%s, firstOrbit=%s, lastOrbit=%s, minGlintAngle=%s, gcID=(SELECT gcID FROM gcs WHERE gcDateTime=%s AND tofID=%s)',
                               (thisTofID, thisS['siteID'], thisS['name'], thisS['targetTimeUTC'], thisS['targetTimeLocal'], thisS['orbit'], thisS['path'], thisS['obsTime'], thisS['firstOrbit'], thisS['lastOrbit'], thisS['minGlintAngle'], thisS['gcDateTime'], row['tofID']))
            db.execute('SELECT * FROM tofFiles WHERE tofID=%s', (thisTofID,))
            row = db.fetchall()
            # Make sure the most current ODF file is available for the Future Targets page
            os.system('python utils/insert_odf_files.py; python utils/parse_target_options.py > tmp/insert_odf_files_status_parse_target_options_status.txt')
            return template('site/tofs-imported.html', menuFile=menuFile, footerFile=footerFile, row=row)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)

# E-mail after TOF upload


@ app.route('/tofs/email/<tofID>')
def email_tof(db, tofID):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            db.execute('SELECT s.name, s.timezone, t.targetTimeUTC, t.targetTimeLocal FROM selectedTargets t, sites s WHERE t.tofID=%s AND s.targetID=t.targetID AND s.name != "noTarget" ORDER BY s.name, t.targetTimeUTC ASC', (tofID,))
            row = db.fetchall()
            db.execute('SELECT DISTINCT s.name, s.emailRecipients FROM tofFiles f, selectedTargets t, sites s WHERE t.tofID=%s AND s.targetID=t.targetID AND t.tofID=f.tofID AND s.name !="noTarget" ORDER BY s.name ASC', (tofID,))
            sites = db.fetchall()
            db.execute(
                'SELECT minGCdate, maxGCdate FROM tofFiles WHERE tofID=%s', (tofID,))
            dateRange = db.fetchall()
            return template('site/tofs-email.html', menuFile=menuFile, footerFile=footerFile, row=row, sites=sites, dateRange=dateRange, tofID=tofID)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/tofs/email/send', method='POST')
def email_tof_send(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            emailType = request.forms.get('emailType')
            tofID = request.forms.get('tofID')
            db.execute('SELECT s.name, s.timezone, t.targetTimeUTC, t.targetTimeLocal FROM selectedTargets t, sites s WHERE t.tofID=%s AND s.targetID=t.targetID AND s.name != "noTarget" ORDER BY s.name, t.targetTimeUTC ASC', (tofID,))
            row = db.fetchall()
            db.execute('SELECT DISTINCT s.name, s.emailRecipients FROM tofFiles f, selectedTargets t, sites s WHERE t.tofID=%s AND s.targetID=t.targetID AND t.tofID=f.tofID AND s.name !="noTarget" ORDER BY s.name ASC', (tofID,))
            sites = db.fetchall()
            db.execute(
                'SELECT minGCdate, maxGCdate FROM tofFiles WHERE tofID=%s', (tofID,))
            dateRange = db.fetchall()
            for thisSite in sites:
                if emailType == 'debug':
                    toaddr = ', '.join(['contact1@mail.com', 'contact2@mail.com'])
                else:
                    toaddr = thisSite['emailRecipients'] + \
                        ', contact1@mail.com, contact2@mail.com'
                server = smtplib.SMTP('localhost', 25)
                server.ehlo()
                fromaddr = 'test@mail.com'
                subject = 'Target List: %s %s to %s UTC' % (
                    thisSite['name'], dateRange[0]['minGCdate'], dateRange[0]['maxGCdate'])
                msg = MIMEMultipart()
                msg['From'] = fromaddr
                msg['To'] = toaddr
                msg['Subject'] = subject
                body = 'Dear Team,<br /><br />'
                body += 'Your validation site is included in the list of potential targets for the following period, from %s UTC to %s UTC. The dates and times under consideration for your site are:<br /><br />' % (
                        dateRange[0]['minGCdate'], dateRange[0]['maxGCdate'])
                body += '<ul style="list-style: circle; margin-left:40px;">'
                for thisRow in row:
                    if thisRow['name'] == thisSite['name']:
                        body += '<li>%s %s %s  (%s UTC)</li>' % (
                                thisRow['name'], thisRow['targetTimeLocal'], thisRow['timezone'], thisRow['targetTimeUTC'])
                body += '</ul>'
                body += '<br />'
                body += 'Please notify us if your site should not be targeted for any of these opportunities.<br /><br />'
                body += 'Selections will be made by 5 PM Pacific Time before a scheduled target and you will be notified at that time if your site has been selected.<br /><br />'
                body += 'The Team thanks you, in advance, for your participation! Questions or concerns can be directed to <a href="mailto:contact1@mail.com">Contact</a>.<br /><br />'
                body += 'Thank you,<br /><br />'
                body += 'The Team<br /><br />'
                body += '<br/>'
                msg.attach(MIMEText(body, 'html', 'utf-8'))
                text = msg.as_string()
                try:
                    server.sendmail(fromaddr, toaddr.split(','), text)
                    server.close
                    print('Message sent')
                except:
                    print('Message failed to send.')
            db.execute(
                'UPDATE tofFiles SET weekOneEmailDate = NOW() WHERE tofID=%s', (tofID,))
            return template('site/tofs-email-send.html', menuFile=menuFile, footerFile=footerFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/tofs/ignore', method='POST')
def tofs_ignore(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            latestFile = request.forms.get('latestFile')
            if latestFile == None:
                return template('site/tofs-next-file-ignored.html', menuFile=menuFile, footerFile=footerFile, message='There is no latest file on the system to ignore. Please go back to the TOFs page.')
            else:
                tofFile = latestFile.split('/')[-1]
                db.execute(
                    'INSERT INTO tofFiles SET filename=%s, ignored=1, createTime="2022-01-01 00:00:00"', (tofFile,))
                return template('site/tofs-next-file-ignored.html', menuFile=menuFile, footerFile=footerFile, message='This TOF file will be ignored.')
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


# Sites page


@ app.route('/sites')
def sites(db):
    db.execute('SELECT siteID, name, description, ROUND(ST_X(targetGeo), 2) as targetLon, ROUND(ST_Y(targetGeo), 2) as targetLat, targetAlt, ROUND(ST_X(tcconGeo), 2) as tcconLon, ROUND(ST_Y(tcconGeo), 2) as tcconLat, tcconAlt, tcconStatusText, tcconStatusValue, tcconStatusLink, timezone, contact, emailRecipients FROM sites WHERE display=1 ORDER BY name ASC')
    row = db.fetchall()
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    return template('site/sites.html', footerFile=footerFile, menuFile=menuFile, row=row)


# Individual site targets page


@ app.route('/sites/<siteName>')
def site_name(db, siteName):
    db.execute('SELECT ROUND(ST_X(s.targetGeo), 2) as targetLon, ROUND(ST_Y(s.targetGeo), 2) as targetLat, g.gcDateTime, s.name, t.obsMode, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.selectDate, t.carFile, t.tofID, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.ocoDataInfo, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData, s.accuWeatherLink, s.wuWeatherLink FROM selectedTargets t, sites s, gcs g WHERE t.targetID=s.targetID AND t.gcID=g.gcID AND t.display=1 AND name=%s AND t.selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (siteName,))
    row = db.fetchall()
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    checked = ''
    return template('site/selected-targets-site.html', footerFile=footerFile, menuFile=menuFile, row=row, siteName=siteName, checked=checked)


@app.route('/sites/<siteName>', method='POST')
def site_name(db, siteName):
    try:
        showAllTargets = request.forms.dict['showAllTargets'][0]
    except KeyError:
        showAllTargets = None
    if showAllTargets == 'on':
        db.execute('SELECT ROUND(ST_X(s.targetGeo), 2) as targetLon, ROUND(ST_Y(s.targetGeo), 2) as targetLat, g.gcDateTime, s.name, t.obsMode, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.selectDate, t.carFile, t.tofID, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.ocoDataInfo, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData, s.accuWeatherLink, s.wuWeatherLink FROM selectedTargets t, sites s, gcs g WHERE t.targetID=s.targetID AND t.gcID=g.gcID AND t.display=1 AND name=%s ORDER BY g.gcDateTime ASC', (siteName,))
        checked = 'CHECKED'
    else:
        db.execute('SELECT ROUND(ST_X(s.targetGeo), 2) as targetLon, ROUND(ST_Y(s.targetGeo), 2) as targetLat, g.gcDateTime, s.name, t.obsMode, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.selectDate, t.carFile, t.tofID, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.ocoDataInfo, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACe(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData, s.accuWeatherLink, s.wuWeatherLink FROM selectedTargets t, sites s, gcs g WHERE t.targetID=s.targetID AND t.gcID=g.gcID AND t.display=1 AND name=%s AND t.selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (siteName,))
        checked = ''
    row = db.fetchall()
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    return template('site/selected-targets-site.html', footerFile=footerFile, menuFile=menuFile, row=row, siteName=siteName, checked=checked)

# Site Stats Page


@ app.route('/site-stats')
def site_stats(db):
    db.execute(
        'SELECT targetID, name, description FROM sites WHERE display=1 ORDER BY name ASC')
    row = db.fetchall()
    info = []
    for site in row:
        db.execute('SELECT MAX(targetTimeUTC) as targetTimeUTC FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
        row = db.fetchone()
        lastTargetTime = row['targetTimeUTC']
        db.execute(
            'SELECT COUNT(*) as numSelections FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
        row = db.fetchone()
        numSelections = row['numSelections']
        info.append({'name': site['name'],
                     'description': site['description'],
                     'lastTargetTime': lastTargetTime,
                     'numSelections': numSelections})

    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    return template('site/site-stats.html', footerFile=footerFile, menuFile=menuFile, row=info)

# Selected targets page


@ app.route('/selected-targets')
def selected_targets(db):
    today = datetime.datetime.now()
    endRange = today.date().strftime("%Y-%m-%d")
    sixMonthsAgo = datetime.datetime.now() - relativedelta(months=6)
    startRange = sixMonthsAgo.date().strftime("%Y-%m-%d")
    db.execute('SELECT g.gcDateTime as groundContactTime, s.name, t.orbit, t.obsMode, t.orbitURL, t.path, t.selectionID, t.targetTimeUTC, t.carFile, t.selectDate, t.tofID, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.ocoDataInfo, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData FROM selectedTargets t, sites s, gcs g WHERE g.gcID=t.gcID AND t.targetID=s.targetID AND t.display=1 AND DATE(g.gcDateTime) >= %s AND DATE(g.gcDateTime) <= %s AND t.selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (startRange, endRange,))
    row = db.fetchall()
    checked = ''
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    return template('site/selected-targets.html', footerFile=footerFile, menuFile=menuFile, row=row, endRange=endRange, startRange=startRange, checked=checked)


@ app.route('/selected-targets', method='POST')
def selected_targets_post(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    startRange = request.forms.get('startRange')
    endRange = request.forms.get('endRange')
    if len(startRange) != 10 or len(endRange) != 10:
        message = 'You have entered an invalid start date or end date.  Please go back and make sure both dates are in YYYY-MM-DD format.'
        return template('site/selected-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
    try:
        endDateCheck = datetime.datetime.strptime(endRange, '%Y-%m-%d')
        startDateCheck = datetime.datetime.strptime(startRange, '%Y-%m-%d')
    except ValueError:
        message = 'You have entered an invalid start date or end date.  Please go back and make sure both dates are in YYYY-MM-DD format.'
        return template('site/selected-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
    if startDateCheck > endDateCheck:
        message = 'You entered a start time greater than the end time.  Please go back and adjust your date entries.'
        return template('site/selected-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
    try:
        showNoTargets = request.forms.dict['showNoTarget'][0]
    except KeyError:
        showNoTargets = None
    try:
        outputFile = request.forms.dict['outputFile'][0]
    except KeyError:
        outputFile = None
    if outputFile == 'on':
        return redirect('/api/report/selected-sites-output?showNoTarget=%s&startRange=%s&endRange=%s' % (showNoTargets, startRange, endRange))
    if showNoTargets == 'on':
        db.execute('SELECT g.gcDateTime as groundContactTime, s.name, t.selectionID, t.orbit, t.obsMode, t.orbitURL, t.path, t.targetTimeUTC, t.carFile, t.selectDate, t.tofID, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.ocoDataInfo, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData FROM selectedTargets t, sites s, gcs g WHERE g.gcID=t.gcID AND t.targetID=s.targetID AND t.display=1 AND DATE(g.gcDateTime) >= %s AND DATE(g.gcDateTime) <= %s AND s.name != "noTarget" AND t.selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (startRange, endRange,))
    else:
        db.execute('SELECT g.gcDateTime as groundContactTime, s.name, t.selectionID, t.orbit, t.obsMode, t.orbitURL, t.path, t.targetTimeUTC, t.carFile, t.selectDate, t.tofID, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.ocoDataInfo, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData FROM selectedTargets t, sites s, gcs g WHERE g.gcID=t.gcID AND t.targetID=s.targetID AND t.display=1 AND DATE(g.gcDateTime) >= %s AND DATE(g.gcDateTime) <= %s AND selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (startRange, endRange,))
    row = db.fetchall()
    if showNoTargets == 'on':
        checked = 'CHECKED'
    else:
        checked = ''
    return template('site/selected-targets.html', footerFile=footerFile, menuFile=menuFile, row=row, endRange=endRange, startRange=startRange, checked=checked)

# Active targets page


@ app.route('/active-targets')
def active_targets(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            startRange = tomorrow.date().strftime("%Y-%m-%d")
            sevenDaysFromNow = datetime.datetime.now() + relativedelta(days=7)
            endRange = sevenDaysFromNow.date().strftime("%Y-%m-%d")
            db.execute(
                'SELECT DISTINCT orbit FROM gcs WHERE DATE(gcDateTime) >= %s AND DATE(gcDateTime) <= %s', (startRange, endRange,))
            orbitNums = db.fetchall()
            gcIDresults = []
            for thisOrbit in orbitNums:
                db.execute(
                    'SELECT MAX(tofID) AS tofID FROM gcs WHERE orbit = %s', (thisOrbit['orbit'],))
                maxTOF = db.fetchone()
                db.execute('SELECT gcID FROM gcs WHERE tofID = %s AND orbit = %s',
                           (maxTOF['tofID'], thisOrbit['orbit'],))
                getGC = db.fetchone()
                gcIDresults.append(str(getGC['gcID']))
            gcList = ','.join(gcIDresults)
            if gcList != '':
                sql = 'SELECT selectionID FROM selectedTargets s WHERE gcID in (%s)'
                db.execute(sql, (gcList,))
                selectionResults = db.fetchall()
                selectionIDs = []
                for s in selectionResults:
                    selectionIDs.append(str(s['selectionID']))
                selectionList = ','.join(selectionIDs)
                sql = 'SELECT g.gcDateTime as groundContactTime, s.name, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.targetTimeLocal, t.minGlintAngle, t.obsMode, SEC_TO_TIME(t.obsTime) AS obsTime, f.filename, s.tcconStatusText, s.tcconStatusValue, s.tcconStatusLink, s.accuWeatherLink, t.selectionID FROM selectedTargets t, sites s, tofFiles f, gcs g WHERE g.gcID=t.gcID AND t.targetID=s.targetID AND t.display=1 AND t.selectionID IN (%s) AND t.tofID=f.tofID AND t.orbit != 0 ORDER BY t.orbit, g.gcDateTime, s.name ASC'
                db.execute(sql, (selectionList,))
                row = db.fetchall()
            else:
                row = ()
            if row != ():
                for r in row:
                    if r['accuWeatherLink'] != None:
                        d0 = datetime.datetime.utcnow().date()
                        d1 = r['targetTimeUTC'].date()
                        dayDiff = d1-d0
                        dayDiff = dayDiff.days
                        r['accuWeatherLink'] += '?day=%s' % dayDiff
            return template('site/active-targets.html', footerFile=footerFile, menuFile=menuFile, row=row, endRange=endRange, startRange=startRange, tomorrow=tomorrow.date())
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/active-targets', method='POST')
def active_targets_post(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            startRange = request.forms.get('startRange')
            endRange = request.forms.get('endRange')
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            sevenDaysAgo = (datetime.datetime.now() -
                            datetime.timedelta(days=7))
            if len(startRange) != 10 or len(endRange) != 10:
                message = 'Please go back and enter valid start and end dates in YYYY-MM-DD format.'
                return template('site/active-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            try:
                if datetime.datetime.strptime(startRange, '%Y-%m-%d') < sevenDaysAgo:
                    message = 'You may only go back 7 days.  Please go back and select a new date.'
                    return template('site/active-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            except ValueError:
                message = 'Please go back and enter a valid start date in YYYY-MM-DD format.'
                return template('site/active-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            try:
                endDateCheck = datetime.datetime.strptime(endRange, '%Y-%m-%d')
            except ValueError:
                message = 'Please go back and enter a valid end date in YYYY-MM-DD format.'
                return template('site/active-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            if datetime.datetime.strptime(startRange, '%Y-%m-%d') > datetime.datetime.strptime(endRange, '%Y-%m-%d'):
                message = 'You entered a start time greater than the end time.  Please go back and adjust your date entries.'
                return template('site/active-targets-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            try:
                outputFile = request.forms.dict['outputFile'][0]
            except KeyError:
                outputFile = None
            if outputFile == 'on':
                return redirect('/api/report/active-sites-output?startRange=%s&endRange=%s' % (startRange, endRange))
            db.execute(
                'SELECT DISTINCT orbit FROM gcs WHERE DATE(gcDateTime) >= %s AND DATE(gcDateTime) <= %s', (startRange, endRange,))
            orbitNums = db.fetchall()
            gcIDresults = []
            for thisOrbit in orbitNums:
                db.execute(
                    'SELECT MAX(tofID) AS tofID FROM gcs WHERE orbit = %s', (thisOrbit['orbit'],))
                maxTOF = db.fetchone()
                db.execute('SELECT gcID FROM gcs WHERE tofID = %s AND orbit = %s',
                           (maxTOF['tofID'], thisOrbit['orbit'],))
                getGC = db.fetchone()
                gcIDresults.append(str(getGC['gcID']))
            gcList = ','.join(gcIDresults)
            if gcList != '':
                sql = 'SELECT selectionID FROM selectedTargets s WHERE gcID in (%s)'
                db.execute(sql, (gcList,))
                selectionResults = db.fetchall()
                selectionIDs = []
                for s in selectionResults:
                    selectionIDs.append(str(s['selectionID']))
                selectionList = ','.join(selectionIDs)
                sql = 'SELECT g.gcDateTime as groundContactTime, s.name, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.targetTimeLocal, t.minGlintAngle, t.obsMode, SEC_TO_TIME(t.obsTime) AS obsTime, f.filename, s.tcconStatusText, s.tcconStatusValue, s.tcconStatusLink, s.accuWeatherLink, t.selectionID FROM selectedTargets t, sites s, tofFiles f, gcs g WHERE g.gcID=t.gcID AND t.targetID=s.targetID AND t.display=1 AND t.selectionID IN (%s) AND t.tofID=f.tofID AND t.orbit != 0 ORDER BY t.orbit, g.gcDateTime, s.name ASC'
                db.execute(sql, (selectionList,))
                row = db.fetchall()
            else:
                row = ()
            if row != ():
                for r in row:
                    if r['accuWeatherLink'] != None:
                        d0 = datetime.datetime.utcnow().date()
                        d1 = r['targetTimeUTC'].date()
                        dayDiff = d1-d0
                        dayDiff = dayDiff.days
                        r['accuWeatherLink'] += '?day=%s' % dayDiff
            return template('site/active-targets.html', footerFile=footerFile, menuFile=menuFile, row=row, endRange=endRange, startRange=startRange, tomorrow=tomorrow.date())
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)

# Select Targets


@ app.route('/select-target')
def select_targets(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            searchDate = (datetime.datetime.now() +
                          datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            db.execute(
                'SELECT COUNT(*) count FROM selectedTargets WHERE selectDate=%s', (searchDate,))
            todayCheck = db.fetchone()['count']
            # if todayCheck > 0:
            #    searchDate = (datetime.datetime.now() +
            #                  datetime.timedelta(days=2)).strftime('%Y-%m-%d')
            db.execute(
                'SELECT DISTINCT orbit FROM gcs WHERE DATE(gcDateTime) = %s', (searchDate,))
            orbitNums = db.fetchall()
            gcIDresults = []
            for thisOrbit in orbitNums:
                db.execute(
                    'SELECT MAX(tofID) AS tofID FROM gcs WHERE orbit = %s', (thisOrbit['orbit'],))
                maxTOF = db.fetchone()
                db.execute('SELECT gcID FROM gcs WHERE tofID = %s AND orbit = %s',
                           (maxTOF['tofID'], thisOrbit['orbit'],))
                getGC = db.fetchone()
                gcIDresults.append(str(getGC['gcID']))
            gcList = ','.join(gcIDresults)
            passGCID = None
            if gcList != '':
                sql = 'SELECT selectionID FROM selectedTargets s WHERE gcID in (%s)'
                db.execute(sql, (gcList,))
                selectionResults = db.fetchall()
                selectionIDs = []
                for s in selectionResults:
                    selectionIDs.append(str(s['selectionID']))
                selectionList = ','.join(selectionIDs)
                sql = 'SELECT s.selectionID, t.targetID, t.name, s.targetTimeUTC, s.targetTimeLocal, s.minGlintAngle, s.path, s.obsMode, ST_Y(t.targetGeo) AS targetLat, SEC_TO_TIME(s.obsTime) AS obsTime, s.tcconDataAvailable, s.tcconDataStatus, t.tcconStatusText, t.tcconStatusValue, t.tcconStatusLink FROM selectedTargets s, sites t WHERE t.targetID=s.targetID AND s.selectionID IN (%s) AND s.selectedBy IS NULL AND s.selectDate IS NULL'
                db.execute(sql, (selectionList,))
                siteInfo = db.fetchall()
                info = []
                for thisSite in siteInfo:
                    db.execute('SELECT COUNT(*) as numSelections FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (thisSite['targetID'],))
                    results = db.fetchone()
                    numOfSelections = results['numSelections']
                    db.execute('SELECT targetTimeUTC FROM selectedTargets WHERE targetID=%s ORDER BY selectDate DESC LIMIT 1', (thisSite['targetID'],))
                    results = db.fetchone()
                    lastSelection = results['targetTimeUTC']
                    H = 15.0 * 1.5
                    N = datetime.datetime.strptime(
                        searchDate, '%Y-%m-%d').timetuple().tm_yday
                    decl = 23.45*sin(radians(360*(N-81)/365))
                    cospart = cos(
                        radians(thisSite['targetLat'])) * cos(radians(decl))
                    sinpart = sin(
                        radians(thisSite['targetLat'])) * sin(radians(decl))
                    cos_SZA = cos(radians(H))*cospart + sinpart
                    SZA_rads = acos(cos_SZA)
                    sza = degrees(SZA_rads)
                    i = {'name': thisSite['name'],
                         'targetTimeUTC': thisSite['targetTimeUTC'],
                         'targetTimeLocal': thisSite['targetTimeLocal'],
                         'minGlintAngle': thisSite['minGlintAngle'],
                         'obsTime': thisSite['obsTime'],
                         'path': thisSite['path'],
                         'obsMode': thisSite['obsMode'],
                         'sza': round(sza, 4),
                         'tcconDataAvailable': thisSite['tcconDataAvailable'],
                         'tcconDataStatus': thisSite['tcconDataStatus'],
                         'tcconStatusText': thisSite['tcconStatusText'],
                         'tcconStatusValue': thisSite['tcconStatusValue'],
                         'tcconStatusLink': thisSite['tcconStatusLink'],
                         'numOfSelections': numOfSelections,
                         'lastSelection': lastSelection,
                         'selectionID': thisSite['selectionID']}
                    info.append(i)
                passGCID = gcList.split(',')[0]
            else:
                info = []
            db.execute(
                'SELECT targetID, name, description FROM sites WHERE display=1 ORDER BY name ASC')
            siteRow = db.fetchall()
            siteInfo = []
            for site in siteRow:
                db.execute('SELECT MAX(targetTimeUTC) as targetTimeUTC FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
                detailRow = db.fetchone()
                lastTargetTime = detailRow['targetTimeUTC']
                db.execute(
                    'SELECT COUNT(*) as numSelections FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
                countRow = db.fetchone()
                numSelections = countRow['numSelections']
                siteInfo.append({'name': site['name'],
                                 'description': site['description'],
                                 'lastTargetTime': lastTargetTime,
                                 'numSelections': numSelections})
            db.execute('SELECT g.gcDateTime, t.name, s.selectionID, s.targetTimeUTC, s.targetTimeLocal, s.selectDate, s.emailTime, s.selectedBy, s.carFile FROM gcs g, sites t, selectedTargets s WHERE g.gcID=s.gcID AND t.targetID=s.targetID AND s.selectDate IS NOT NULL AND s.selectedBy IS NOT NULL AND DATE(g.gcDateTime)=%s ', (searchDate,))
            alreadySelected = db.fetchall()
            db.execute(
                'SELECT note FROM notes WHERE startDate <= %s AND endDate >= %s', (searchDate, searchDate,))
            noteInfo = db.fetchall()
            if len(noteInfo) == 0:
                noteInfo = None
            return template('site/select-target.html', footerFile=footerFile, menuFile=menuFile, info=info, searchDate=searchDate, alreadySelected=alreadySelected, passGCID=passGCID, siteInfo=siteInfo, noteInfo=noteInfo)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/select-target', method='POST')
def select_targets_post(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            searchDate = request.forms.get('selectDate')
            sevenDaysAgo = (datetime.datetime.now() -
                            datetime.timedelta(days=7))
            try:
                if datetime.datetime.strptime(searchDate, '%Y-%m-%d') < sevenDaysAgo:
                    message = 'You may only go back 7 days.  Please go back and select a new date.'
                    return template('site/select-target-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            except ValueError:
                message = 'Please go back and enter a valid date in YYYY-MM-DD format.'
                return template('site/select-target-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            if len(searchDate) != 10:
                message = 'Please go back and enter a valid date in YYYY-MM-DD format.'
                return template('site/select-target-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            db.execute(
                'SELECT DISTINCT orbit FROM gcs WHERE DATE(gcDateTime) = %s', (searchDate,))
            orbitNums = db.fetchall()
            gcIDresults = []
            for thisOrbit in orbitNums:
                db.execute(
                    'SELECT MAX(tofID) AS tofID FROM gcs WHERE orbit = %s', (thisOrbit['orbit'],))
                maxTOF = db.fetchone()
                db.execute('SELECT gcID FROM gcs WHERE tofID = %s AND orbit = %s',
                           (maxTOF['tofID'], thisOrbit['orbit'],))
                getGC = db.fetchone()
                gcIDresults.append(str(getGC['gcID']))
            gcList = ','.join(gcIDresults)
            passGCID = None
            if gcList != '':
                sql = 'SELECT selectionID FROM selectedTargets s WHERE gcID in (%s)'
                db.execute(sql, (gcList,))
                selectionResults = db.fetchall()
                selectionIDs = []
                for s in selectionResults:
                    selectionIDs.append(str(s['selectionID']))
                selectionList = ','.join(selectionIDs)
                sql = 'SELECT s.selectionID, t.targetID, t.name, s.targetTimeUTC, s.targetTimeLocal, s.minGlintAngle, s.path, s.obsMode, SEC_TO_TIME(s.obsTime) AS obsTime, ST_Y(t.targetGeo) AS targetLat, s.tcconDataAvailable, s.tcconDataStatus, t.tcconStatusText, t.tcconStatusValue, t.tcconStatusLink FROM selectedTargets s, sites t WHERE t.targetID=s.targetID AND s.selectionID IN (%s) AND s.selectedBy IS NULL AND s.selectDate IS NULL'
                db.execute(sql, (selectionList,))
                siteInfo = db.fetchall()
                info = []
                for thisSite in siteInfo:
                    db.execute('SELECT COUNT(*) as numSelections FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (thisSite['targetID'],))
                    results = db.fetchone()
                    numOfSelections = results['numSelections']
                    db.execute('SELECT selectDate FROM selectedTargets WHERE targetID=%s ORDER BY selectDate DESC LIMIT 1', (thisSite['targetID'],))
                    results = db.fetchone()
                    lastSelection = results['selectDate']
                    H = 15.0 * 1.5
                    N = datetime.datetime.strptime(
                        searchDate, '%Y-%m-%d').timetuple().tm_yday
                    decl = 23.45*sin(radians(360*(N-81)/365))
                    cospart = cos(
                        radians(thisSite['targetLat'])) * cos(radians(decl))
                    sinpart = sin(
                        radians(thisSite['targetLat'])) * sin(radians(decl))
                    cos_SZA = cos(radians(H))*cospart + sinpart
                    SZA_rads = acos(cos_SZA)
                    sza = degrees(SZA_rads)
                    i = {'name': thisSite['name'],
                         'targetTimeUTC': thisSite['targetTimeUTC'],
                         'targetTimeLocal': thisSite['targetTimeLocal'],
                         'minGlintAngle': thisSite['minGlintAngle'],
                         'path': thisSite['path'],
                         'obsMode': thisSite['obsMode'],
                         'obsTime': thisSite['obsTime'],
                         'sza': round(sza, 4),
                         'tcconDataAvailable': thisSite['tcconDataAvailable'],
                         'tcconDataStatus': thisSite['tcconDataStatus'],
                         'tcconStatusValue': thisSite['tcconStatusValue'],
                         'tcconStatusLink': thisSite['tcconStatusLink'],
                         'tcconStatusText': thisSite['tcconStatusText'],
                         'numOfSelections': numOfSelections,
                         'lastSelection': lastSelection,
                         'selectionID': thisSite['selectionID']}
                    info.append(i)
                passGCID = gcList.split(',')[0]
            else:
                info = []
            db.execute(
                'SELECT targetID, name, description FROM sites WHERE display=1 ORDER BY name ASC')
            siteRow = db.fetchall()
            siteInfo = []
            for site in siteRow:
                db.execute('SELECT MAX(targetTimeUTC) as targetTimeUTC FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
                detailRow = db.fetchone()
                lastTargetTime = detailRow['targetTimeUTC']
                db.execute(
                    'SELECT COUNT(*) as numSelections FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
                countRow = db.fetchone()
                numSelections = countRow['numSelections']
                siteInfo.append({'name': site['name'],
                                 'description': site['description'],
                                 'lastTargetTime': lastTargetTime,
                                 'numSelections': numSelections})
            db.execute('SELECT g.gcDateTime, t.name, s.selectionID, s.targetTimeUTC, s.targetTimeLocal, s.selectDate, s.emailTime, s.selectedBy, s.carFile FROM gcs g, sites t, selectedTargets s WHERE g.gcID=s.gcID AND t.targetID=s.targetID AND s.selectDate IS NOT NULL AND s.selectedBy IS NOT NULL AND DATE(g.gcDateTime)=%s ', (searchDate,))
            alreadySelected = db.fetchall()
            db.execute(
                'SELECT note FROM notes WHERE startDate <= %s AND endDate >= %s', (searchDate, searchDate,))
            noteInfo = db.fetchall()
            if len(noteInfo) == 0:
                noteInfo = None
            print(noteInfo)
            return template('site/select-target.html', footerFile=footerFile, menuFile=menuFile, info=info, searchDate=searchDate, alreadySelected=alreadySelected, passGCID=passGCID, siteInfo=siteInfo, noteInfo=noteInfo)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/select-target/confirm', method='POST')
def select_targets_confirm(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            gcID = request.forms.get('passGCID')
            selectDate = datetime.datetime.now()
            selectionID = request.forms.get('selectionID')
            if selectionID != 'noTarget':
                db.execute(
                    'UPDATE selectedTargets SET selectDate=%s, selectedBy=%s WHERE selectionID=%s', (selectDate.date(), username, selectionID,))
                db.connection.commit()
                carTemplate = open(
                    'site/car-generate.html', 'r')
            else:
                db.execute('INSERT INTO selectedTargets SET targetID=0, orbit=0, display=1, path=0, targetTimeUTC=(SELECT gcDateTime FROM gcs WHERE gcID=%s), targetTimeLocal=(SELECT gcDateTime FROM gcs WHERE gcID=%s), minGlintAngle=0, obsTime=0, gcID=%s, tofID=(SELECT tofID FROM gcs WHERE gcID=%s), selectDate=%s, selectedBy=%s', (gcID, gcID, gcID, gcID, selectDate.date(), username,))
                db.connection.commit()
                db.execute('SELECT MAX(selectionID) AS selectionID FROM selectedTargets WHERE targetID=0 AND orbit=0 AND display=1 AND path=0 AND targetTimeUTC=(SELECT gcDateTime FROM gcs WHERE gcID=%s) AND targetTimeLocal=(SELECT gcDateTime FROM gcs WHERE gcID=%s) AND minGlintAngle=0 AND obsTime=0 AND gcID=%s AND tofID=(SELECT tofID FROM gcs WHERE gcID=%s)', (gcID, gcID, gcID, gcID,))
                results = db.fetchone()
                selectionID = results['selectionID']
                carTemplate = open(
                    'site/car-generate-no-target.html', 'r')
            db.execute(
                'SELECT selectDate FROM selectedTargets WHERE selectionID=%s', (selectionID,))
            carFile = 'cars/%s_CAR.pdf' % selectDate.strftime('%Y%m%d_%H%M%S')
            htmlFile = 'html/%s_CAR.html' % selectDate.strftime(
                '%Y%m%d_%H%M%S')
            templateText = carTemplate.readlines()
            carTemplate.close()
            db.execute('SELECT g.gcDateTime, s.emailTime, t.name, t.description, s.targetTimeUTC, s.targetTimeLocal, s.firstOrbit, s.lastOrbit, t.siteID FROM gcs g, sites t, selectedTargets s WHERE g.gcID=s.gcID AND t.targetID=s.targetID AND s.selectionID=%s', (selectionID,))
            info = db.fetchone()
            info['gcDateTime'] = info['gcDateTime'].strftime(
                '%Y-%m-%d %H:%M:%S')
            info['targetTimeLocal'] = info['targetTimeLocal'].strftime(
                '%Y-%m-%d %H:%M:%S')
            info['targetTimeUTC'] = info['targetTimeUTC'].strftime(
                '%Y-%m-%d %H:%M:%S')
            if info['emailTime'] != None:
                info['emailTime'] = info['emailTime'].strftime(
                    '%Y-%m-%d %H:%M:%S')
            else:
                info['emailTime'] = str(info['emailTime'])
            for (thisIndex, thisLine) in enumerate(templateText):
                if "{{filename}}" in thisLine:
                    templateText[thisIndex] = thisLine.replace(
                        "{{filename}}", carFile.split('/')[-1])
                else:
                    pass
            htmlTemplate = open(htmlFile, 'w')
            htmlTemplate.write(' '.join(templateText))
            htmlTemplate.close()
            resultFile = open(carFile, 'w+b')
            with open(htmlFile, 'r') as f:
                htmlInfo = f.read()
            pisaStatus = pisa.CreatePDF(htmlInfo, dest=resultFile)
            resultFile.close()
            db.execute('UPDATE selectedTargets SET carFile=%s WHERE selectionID=%s',
                       (carFile, selectionID,))
            os.remove(htmlFile)
            return template('site/select-target-confirm.html', footerFile=footerFile, menuFile=menuFile, info=info, carFile=carFile, selectedBy=username, selectDate=selectDate.date().strftime('%Y-%m-%d'), selectionID=selectionID)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/select-target/deselect/<selectionID>')
def select_targets_deselect(db, selectionID):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            db.execute(
                'UPDATE selectedTargets SET selectDate=NULL, emailTime=NULL, selectedBy=NULL, carFile=NULL WHERE selectionID=%s', (selectionID,))
            return template('site/select-target-deselect.html', footerFile=footerFile, menuFile=menuFile, url="/select-target")
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


# E-mail after target selection and CAR generation


@ app.route('/car/email/<selectionID>')
def email_car(db, selectionID):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            db.execute('SELECT g.gcDateTime, t.siteID, t.name, s.selectedBy, t.emailRecipients, s.targetTimeLocal, s.targetTimeUTC FROM gcs g, sites t, selectedTargets s WHERE t.targetID=s.targetID AND g.gcID=s.gcID AND s.selectionID=%s', (selectionID,))
            info = db.fetchone()
            return template('site/selected-email.html', menuFile=menuFile, footerFile=footerFile, info=info, selectionID=selectionID)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/car/email/send', method='POST')
def email_car_send(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            emailType = request.forms.get('emailType')
            selectionID = request.forms.get('selectionID')
            db.execute('SELECT s.carFile, gcDateTime, t.siteID, s.targetTimeUTC, s.targetTimeLocal, t.name, t.emailRecipients, s.selectedBy FROM gcs g, sites t, selectedTargets s WHERE t.targetID=s.targetID AND g.gcID=s.gcID AND s.selectionID=%s', (selectionID,))
            info = db.fetchone()
            # CAR PDF email to OPS team
            if emailType == 'debug':
                toaddr = ['contact1@mail.com', 'contact2@mail.com']
            else:
                toaddr = ['test@mail.com']
            server = smtplib.SMTP('localhost', 25)
            server.ehlo()
            fromaddr = 'test@mail.com'
            subject = 'Validation CAR: %s Ground Contact' % info['gcDateTime']
            msg = MIMEMultipart()
            msg['From'] = fromaddr
            msg['To'] = ', '.join(toaddr)
            msg['Subject'] = subject
            body = 'Attached is the CAR to enable RTS # %s %s for the:' % (
                info['siteID'], info['name'])
            body += '<br />'
            body += '<br />'
            body += '%s Ground Contact' % info['gcDateTime']
            body += '<br />'
            body += '<br />'
            body += 'signed by'
            body += '<br />'
            body += info['selectedBy']
            body += '<br />'
            body += '<br />'
            body += 'Please confirm receipt of this email.'
            body += '<br />'
            body += '<br />'
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            pdf = MIMEApplication(open(info['carFile'], 'rb').read())
            pdf.add_header('Content-Disposition', 'attachment',
                           filename=info['carFile'].split('/')[-1])
            msg.attach(pdf)
            text = msg.as_string()
            try:
                server.sendmail(fromaddr, toaddr, text)
                server.close
                print('Message sent')
            except:
                print('Message failed to send.')
            # Text messages to OPS team
            if emailType == 'debug':
                toaddr = ['8005555555@verizon.com']
            else:
                toaddr = ['8005555555@verizon.com','8885555555@tmobile.com']
            server = smtplib.SMTP('localhost', 25)
            server.set_debuglevel(1)
            server.ehlo()
            fromaddr = 'test@mail.com'
            subject = ''
            msg = MIMEMultipart()
            msg['From'] = fromaddr
            msg['To'] = ', '.join(toaddr)
            msg['Subject'] = subject
            body = 'We created a CAR for the %s uplink (RTS # %s = %s). Contact Contact1 (8005555555) if no e-mail is received.' % (info['gcDateTime'], info['siteID'], info['name'])
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            text = msg.as_string()
            try:
                server.sendmail(fromaddr, toaddr, text)
                server.close
                print('Text message sent')
            #except:
            #     print('Text message failed to send.')
            except SMTPResponseException as e:
                error_code = e.smtp_code
                error_message = e.smtp_error
                print(error_message)
            # Send email to site PIs to let them know they've been selected
            if emailType == 'debug':
                toaddr = ', '.join(['contact1@mail.com', 'contact2@mail.com'])
            else:
                toaddr = info['emailRecipients']
            server = smtplib.SMTP('localhost', 25)
            server.ehlo()
            fromaddr = 'test@mail.com'
            subject = 'Target Selection: %s %s' % (info['name'], info['targetTimeLocal'])
            msg = MIMEMultipart()
            msg['From'] = fromaddr
            msg['To'] = toaddr
            msg['Subject'] = subject
            body = 'Hello,'
            body += '<br />'
            body += '<br />'
            body += 'This is to notify you that the site mentioned below has been selected as a target:'
            body += '<br />'
            body += '<br />'
            body += '%s %s (%s)' % (info['name'], info['targetTimeLocal'], info['targetTimeUTC'])
            body += '<br />'
            body += '<br />'
            body += 'We just wanted to let you know about the observation. If you have data that you would like to share with us to help us with validation of data, please let us know. Questions or concerns can be directed to:'
            body += '<br />'
            body += '<ul>'
            body += '<li>Contact1 (contact1@mail.com)</li>'
            body += '</ul>'
            body += '<br />'            
            body += '<br />'            
            body += 'Thank you,'
            body += '<br />'            
            body += 'The Team'
            body += '<br />'            
            body += '<br />'                                    
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            text = msg.as_string()
            try:
                server.sendmail(fromaddr, toaddr.split(','), text)
                server.close
                print('Message sent')
            except:
                print('Message failed to send.')
            db.execute(
                'UPDATE selectedTargets SET emailTime = NOW() WHERE selectionID=%s', (selectionID,))
            return template('site/selected-email-send.html', menuFile=menuFile, footerFile=footerFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)

# Future Targets page


@ app.route('/future-targets')
def future_targets(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            db.execute('SELECT odfID FROM odfFiles ORDER BY date DESC, version DESC LIMIT 1')
            currentOdfID = db.fetchone()
            currentOdfID = currentOdfID['odfID']
            db.execute(
                'SELECT MIN(startDate) AS startDate FROM futureTargets WHERE odfID=%s', (currentOdfID,))
            minDate = db.fetchone()
            minDate = minDate['startDate']
            db.execute('SELECT f.orbit, o.date, f.startDate FROM futureTargets f, odfFiles o WHERE f.odfID=%s AND date(f.startDate) >= date(o.date) AND f.startDate <= (DATE_ADD((SELECT MIN(DATE(startDate)) FROM futureTargets WHERE odfID=%s), INTERVAL 8 DAY)) AND f.odfID=o.odfID', (currentOdfID, currentOdfID,))
            orbitResults = db.fetchall()
            info = {}
            for o in orbitResults:
                db.execute(
                    'SELECT COUNT(*) AS count FROM futureTargets WHERE orbit=%s AND odfID=%s', (o['orbit'], currentOdfID,))
                countCheck = db.fetchone()
                singleDefaultCheck = False
                if countCheck['count'] == 1:
                    db.execute(
                        'SELECT note FROM futureTargets WHERE orbit=%s AND odfID=%s', (o['orbit'], currentOdfID,))
                    noteInfo = db.fetchone()
                    if 'default' in noteInfo['note']:
                        singleDefaultCheck = True
                    db.execute(
                        'SELECT COUNT(*) AS count FROM futureContacts WHERE orbit=%s AND odfID=%s', (o['orbit'], currentOdfID,))
                    contactCheck = db.fetchone()
                    contactCheck = contactCheck['count']
                    if contactCheck >= 1:
                        singleDefaultCheck = False
                if countCheck['count'] > 1 or singleDefaultCheck == False:
                    print(o['orbit'])
                    db.execute(
                        'SELECT s.name, s.tcconStatusValue, f.heading, f.orbit, f.path, DATE(f.startDate) AS startDate, DAYOFWEEK(f.startDate) AS dayOfWeek, f.endDate as fullEndDate, f.rangeKm, f.note, f.selected, REPLACE(REPLACE(targetFile, "odf/", "http://website.com/"), "/target_options.txt", "/path") as orbitURL FROM futureTargets f, sites s, odfFiles o WHERE f.odfID=o.odfID AND f.orbit=%s AND s.targetID=f.targetID AND f.odfID=%s ORDER BY s.name ASC', (o['orbit'], currentOdfID,))
                    results = db.fetchall()
                    info[o['orbit']] = {'list': ''}
                    info[o['orbit']]['list'] = list(results)
                    info[o['orbit']]['path'] = info[o['orbit']]['list'][0]['path']
                    info[o['orbit']]['date'] = info[o['orbit']
                                                    ]['list'][0]['startDate']
                    info[o['orbit']]['dayOfWeek'] = info[o['orbit']
                                                         ]['list'][0]['dayOfWeek']
                    info[o['orbit']]['orbitURL'] = info[o['orbit']
                                                        ]['list'][0]['orbitURL']
                    db.execute('SELECT disposition FROM orfFiles WHERE orbit=%s AND odfID=%s', (o['orbit'], currentOdfID))
                    orfInfo = db.fetchone()
                    if orfInfo == None:
                        info[o['orbit']]['disposition'] = None
                    else:
                        info[o['orbit']]['disposition'] = orfInfo['disposition']
                    db.execute(
                        'SELECT COUNT(*) AS count FROM futureContacts WHERE orbit=%s AND odfID=%s', (o['orbit'], currentOdfID,))
                    contactCheck = db.fetchone()
                    info[o['orbit']]['contactCheck'] = contactCheck['count']
                    selections = []
                    selectedStatus = 'noTargetSelected'
                    for r in results:
                        selections.append(r['name'] + ' (' + r['note'] + ')')
                        if r['selected'] == 1:
                            selectedStatus = r['name']
                    info[o['orbit']]['selected'] = selectedStatus
                    info[o['orbit']]['selections'] = selections
                    cardinalDirs = [0, 45, 90, 135, 180, 225, 270, 315]
                    cardinalNames = ['North', 'North-East', 'East',
                                     'South-East', 'South', 'South-West', 'West', 'North-West']
                    for j in info[o['orbit']]['list']:
                        j['deltaTime'] = False
                        for i, cardinal in enumerate(cardinalDirs):
                            if abs(j['rangeKm'] - cardinal) < 22.5:
                                j['heading'] = cardinalNames[i] + \
                                    ' (' + \
                                    str(float(j['heading'])) + ' degrees)'
                        j['outOfBounds'] = False
                        if 'glint spot violation' in j['note']:
                            j['outOfBounds'] = True
                        if 'default' in j['note'] and j['startDate'] < (minDate.date() + datetime.timedelta(days=7)):
                            j['outOfBounds'] = True
                        db.execute(
                            'SELECT * FROM futureContacts WHERE orbit=%s AND odfID=%s AND (note="X-band" OR note="S-band")', (j['orbit'], currentOdfID,))
                        contactInfo = db.fetchone()
                        if contactInfo:
                            j['outOfBounds'] = True
                            j['note'] += '  (N/A - Contact Scheduled)'
                            deltaTime = contactInfo['startDate'] - \
                                j['fullEndDate']
                            deltaMins, deltaSecs = divmod(
                                deltaTime.total_seconds(), 60)
                            j['deltaTime'] = 'Time from Target LOS to GS AOS = %sm%ss' % (
                                deltaMins, deltaSecs)
            orbits = []
            for o in info.keys():
                orbits.append(o)
            db.execute('SELECT DISTINCT o.odfID, o.targetFile, o.diffFile FROM odfFiles o, futureTargets f WHERE f.odfID=(SELECT odfID FROM odfFiles ORDER BY date DESC, version DESC LIMIT 1) AND o.odfID=f.odfID')
            results = db.fetchone()
            targetOptionsFile = results['targetFile']
            diffFile = results['diffFile']
            if diffFile == None:
                diffFileURL = None
            else:
                diffFileURL = '/'.join(diffFile.split('/')[4:])
            odfID = results['odfID']
            return template('site/future-targets.html', footerFile=footerFile, menuFile=menuFile, info=info, orbits=orbits, targetOptionsFile=targetOptionsFile, diffFile=diffFile, diffFileURL=diffFileURL, odfID=odfID)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@app.route('/future-targets/confirm', method='POST')
def future_targets_confirm(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            orbits = request.forms.get('orbits')[1:-1]
            odfID = request.forms.get('odfID')
            orbitList = orbits.split(',')
            info = {}
            for o in orbitList:
                try:
                    db.execute(
                        'SELECT t.name FROM futureTargets f, sites t WHERE f.targetID=t.targetID AND f.selected=1 AND f.orbit=%s AND f.odfID=%s', (o.strip(), odfID, ))
                    nameResults = db.fetchone()
                    if nameResults == None:
                        original = None
                    else:
                        original = nameResults['name']
                    db.execute(
                        'SELECT path FROM futureTargets WHERE orbit=%s', (o.strip(),))
                    pathResults = db.fetchone()
                    thisDisposition = request.forms.get(
                        o.strip() + '-selection')
                    if thisDisposition != None:
                        if thisDisposition.split(' ')[0] != 'noTargetSelected':
                            info[o.strip()] = {'selected': thisDisposition.split(' ')[
                                0], 'original': original, 'path': pathResults['path'], 'orbit': o.strip()}
                except IndexError:
                    pass
            return template('site/future-targets-confirm.html', footerFile=footerFile, menuFile=menuFile, info=info, odfID=odfID)


@ app.route('/future-targets/email', method='POST')
def future_targets_email(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            odfID = request.forms.get('odfID')
            info = ast.literal_eval(request.forms.get('info'))
            emailType = request.forms.get('emailType')
            db.execute(
                'SELECT odfFile, version FROM odfFiles WHERE odfID=%s', (odfID,))
            results = db.fetchone()
            odfFile = results['odfFile']
            currentVersion = results['version']
            odfFile = odfFile.replace('001', currentVersion)
            now = datetime.datetime.now().strftime('%Y-%m-%dT%H%M%S')
            path = 'odf/' + odfFile.split('/')[5]
            diffFile = 'switched_targets_' + now + '.txt'
            if not os.path.isdir(path):
                os.mkdir(path)
            diffs = []
            with open(path + '/' + diffFile, 'w') as f:
                f.write('Orbit #\tPath #\tOriginal Target\tSelected Target\n')
                for key, value in info.items():
                    db.execute(
                        'UPDATE futureTargets SET selected=0 WHERE orbit=%s AND odfID=%s', (key, odfID,))
                    db.execute(
                        'UPDATE futureTargets SET selected=1 WHERE orbit=%s AND targetID=(SELECT targetID FROM sites WHERE name=%s AND odfID=%s)', (key, value['selected'], odfID,))
                    if value['original'] != value['selected']:
                        f.write(key + '\t' + str(value['path']) + '\t' +
                                str(value['original']) + '\t' + value['selected'] + '\n')
                        diffs.append([str(value['path']), str(
                            value['original']), str(value['selected']), str(value['orbit'])])
            with open(odfFile, 'r') as f:
                odfLines = f.readlines()
            newVersion = '00' + str(int(currentVersion) + 1)
            newFilename = odfFile.replace(currentVersion, newVersion)
            for i, thisLine in enumerate(odfLines):
                if 'Filename:' in thisLine:
                    odfLines[i] = thisLine.replace(
                        odfFile.split('/')[-1], newFilename.split('/')[-1])
                if 'Create time:' in thisLine:
                    newTime = datetime.datetime.utcnow().strftime(
                        '%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    oldTime = thisLine.split(' ')[-1].split('\n')[0]
                    odfLines[i] = thisLine.replace(oldTime, newTime)
            for thisDiff in diffs:
                ocoPath = thisDiff[0]
                origSite = thisDiff[1]
                if origSite == 'None':
                    origSite = ''
                newSite = thisDiff[2]
                ocoOrbit = thisDiff[3]
                origSiteOrbit = ',%s,' % (ocoOrbit)
                newSiteOrbit = ',%s,' % (ocoOrbit)
                for i, thisLine in enumerate(odfLines):
                    if ocoPath in thisLine and origSiteOrbit in thisLine:
                        #odfLines[i] = thisLine.replace(
                        #    origSiteOrbit, newSiteOrbit)
                        lineParts = thisLine.split(',')
                        lineParts[3] = newSite
                        odfLines[i] = ','.join(lineParts)
            with open(newFilename, 'w') as f:
                for thisLine in odfLines:
                    f.write(thisLine)
            db.execute('UPDATE odfFiles SET diffFile=%s, version=%s WHERE odfID=%s',
                       (path + '/' + diffFile, newVersion, odfID,))
            db.execute(
                'SELECT fullName FROM users WHERE username=%s', (username,))
            userInfo = db.fetchone()
            fullName = userInfo['fullName']
            with open(path + '/' + diffFile, 'r') as f:
                diffInfo = f.read()
            diffInfo = diffInfo.replace('\t', '&emsp;').replace('\n', '<br/>')
            diffCheck = subprocess.run(
                ['diff', odfFile, newFilename], stdout=subprocess.PIPE)
            diffCheckInfo = diffCheck.stdout.decode('utf-8')
            diffCheckInfo = diffCheckInfo.replace('\n', '<br />')
            if emailType == 'debug':
                toaddr = ['contact1@mail.com', 'contact2@mail.com']
            else:
                toaddr = ['contact1@mail.com', 'contact2@mail.com']
            server = smtplib.SMTP('localhost', 25)
            server.ehlo()
            fromaddr = 'test@mail.com'
            subject = 'Updated ODF for Week of %s' % '_'.join(odfFile.split('/')[6].split('_')[1:4])
            msg = MIMEMultipart()
            msg['From'] = fromaddr
            msg['To'] = ', '.join(toaddr)
            msg['Subject'] = subject
            body = 'Hello,'
            body += '<br />'
            body += '<br />'
            body += 'The Team has created an updated ODF for next week. Some targets have been switched out; this is a summary of those changes:'
            body += '<br />'
            body += '<br />'
            body += diffInfo
            body += '<br />'
            body += '<br />'
            body += 'Here is the diff output comparing the updated ODF to the original:'
            body += '<br />'
            body += '<br />'
            body += diffCheckInfo
            body += '<br />'
            body += '<br />'
            body += 'Please review the attached file and, if approved, place it in the appropriate transfer folder on the cluster.'
            body += '<br />'
            body += '<br />'
            body += 'The updated ODF can also be found on the cluster here:'
            body += '<br />'
            body += '<br />'
            body += '%s' % (newFilename)
            body += '<br />'
            body += '<br />'
            body += 'Thank you!'
            body += '<br />'
            body += '<br />'
            body += 'Signed,'
            body += '<br />'
            body += '%s' % fullName
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            odf = MIMEApplication(open(newFilename, 'rb').read())
            odf.add_header('Content-Disposition', 'attachment',
                           filename=newFilename.split('/')[-1])
            msg.attach(odf)
            text = msg.as_string()
            try:
                server.sendmail(fromaddr, toaddr, text)
                server.close
                print('Message sent')
            except:
                print('Message failed to send.')
            return template('site/future-targets-email.html', footerFile=footerFile, menuFile=menuFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)

# Notes page


@ app.route('/notes')
def notes(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            return template('site/notes.html', footerFile=footerFile, menuFile=menuFile, message=None, catchURL=request.url)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/notes', method='POST')
def notes_submitted(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            note = request.forms.get('note')
            endDate = request.forms.get('endDate')
            startDate = request.forms.get('startDate')
            if len(startDate) != 10 or len(endDate) != 10:
                message = 'You have entered an invalid start date or end date.  Please go back and make sure both dates are in YYYY-MM-DD format.'
                return template('site/notes-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            try:
                endDateCheck = datetime.datetime.strptime(endDate, '%Y-%m-%d')
                startDateCheck = datetime.datetime.strptime(
                    startDate, '%Y-%m-%d')
            except ValueError:
                message = 'You have entered an invalid start date or end date.  Please go back and make sure both dates are in YYYY-MM-DD format.'
                return template('site/notes-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            if startDateCheck > endDateCheck:
                message = 'You entered a start time greater than the end time.  Please go back and adjust your date entries.'
                return template('site/notes-date-error.html', footerFile=footerFile, menuFile=menuFile, message=message)
            db.execute('INSERT INTO notes SET note=%s, userID=(SELECT userID FROM users WHERE username=%s), startDate=%s, endDate=%s',
                       (note, username, startDate, endDate,))
            return template('site/notes-submitted.html', footerFile=footerFile, menuFile=menuFile, message='Note added.', catchURL=request.url)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


# Login page


@ app.route('/login')
def login():
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    message = ''
    if request.cookies.get('caruser'):
        return redirect('/sites')
    else:
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL='https://website.com')


@ app.route('/login', method='POST')
def login_post(db):
    username = request.forms.get('user')
    password = request.forms.get('password')
    catchURL = request.forms.get('catchURL')
    # Uses LDAP-related fields from the config.json file
    user_dn = "uid="+username  # concatenate any additional filters here
    connect = ldap.initialize(ldap_server)
    try:
        # if authentication successful, get the full user data
        connect.bind_s(user_dn, password)
        result = connect.search_s(
            base_dn, ldap.SCOPE_SUBTREE, search_filter, [search_field])
        # return all user data results
        connect.unbind_s()
        string_results = [x.decode('utf-8')
                          for x in result[0][1][search_field]]
        if user_dn in string_results:
            menuFile = 'site/includes/menu.html'
            footerFile = 'site/includes/footer.html'
            ts = datetime.datetime.now()+datetime.timedelta(hours=10)
            cookieHex = uuid.uuid4().hex
            response.set_cookie('caruser',  cookieHex + '.' + username,
                                path='/', expires=ts, httponly=True, secure=True)
            db.execute('INSERT INTO authentication (username, cookie, expirationDate) VALUES (%s, %s, %s)',
                       (username, cookieHex, ts.strftime('%Y-%m-%d %H:%M:%S'),))
            return redirect(catchURL)
        else:
            menuFile = 'site/includes/menu.html'
            footerFile = 'site/includes/footer.html'
            message = 'Authentication failure, please try again.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    except ldap.LDAPError:
        connect.unbind_s()
        menuFile = 'site/includes/menu.html'
        footerFile = 'site/includes/footer.html'
        message = 'Authentication failure, please try again.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)

# Add new site form


@ app.route('/add-site')
def add_site(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            return template('site/add-site.html', footerFile=footerFile, menuFile=menuFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/add-site', method='POST')
def do_add_site(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            menuFile = 'site/includes/menu.html'
            footerFile = 'site/includes/footer.html'
            siteID = request.forms.get('siteID')
            tcconName = request.forms.get('tcconName')
            tcconID = request.forms.get('tcconID')
            name = request.forms.get('name')
            description = request.forms.get('description')
            targetGeo = request.forms.get('targetGeo')
            targetGeo = targetGeo.replace(',', ' ')
            targetGeo = 'POINT(%s)' % targetGeo
            targetAlt = request.forms.get('targetAlt')
            tcconGeo = request.forms.get('tcconGeo')
            tcconGeo = tcconGeo.replace(',', ' ')
            tcconGeo = 'POINT(%s)' % tcconGeo
            tcconAlt = request.forms.get('tcconAlt')
            contact = request.forms.get('contact')
            tcconStatusText = request.forms.get('tcconStatusText')
            tcconStatusValue = request.forms.getall('tcconStatusValue')
            tcconStatusLink = request.forms.get('tcconStatusLink')
            emailRecipients = request.forms.get('emailRecipients')
            timezone = request.forms.get('timezone')
            accuWeatherLink = request.forms.get('accuWeatherLink')
            wuWeatherLink = request.forms.get('wuWeatherLink')
            if not tcconName:
                tcconName = None
            if not tcconID:
                tcconID = None
            if not description:
                description = None
            if not siteID:
                siteID = None
            if not description:
                description = None
            if not targetGeo:
                targetGeo = None
            if not targetAlt:
                targetAlt = None
            if not contact:
                contact = None
            if not tcconStatusText:
                tcconStatusText = None
            if not tcconStatusLink:
                tcconStatusLink = None
            if not emailRecipients:
                emailRecipients = None
            if not tcconStatusValue or tcconStatusValue[0] == 3:
                tcconStatusValue = [None]
            if not tcconGeo:
                tcconGeo = None
            if not tcconAlt:
                tcconAlt = None
            if not timezone:
                timezone = None
            if not accuWeatherLink:
                accuWeatherLink = None
            if not wuWeatherLink:
                wuWeatherLink = None
            db.execute("INSERT INTO sites SET siteID=%s, name=%s, description=%s, targetGeo=ST_GeometryFromText(%s), targetAlt=%s, tcconGeo=ST_GeometryFromText(%s), tcconAlt=%s, contact=%s, tcconStatusText=%s, tcconStatusLink=%s, emailRecipients=%s, display=1, tcconStatusValue=%s, timezone=%s, accuWeatherLink=%s, wuWeatherLink=%s",
                       (siteID, name,  description, targetGeo, targetAlt, tcconGeo, tcconAlt, contact, tcconStatusText, tcconStatusLink, emailRecipients, tcconStatusValue[0], timezone, accuWeatherLink, wuWeatherLink,))
            db.execute("SELECT targetID FROM sites WHERE siteID=%s AND name=%s", (siteID, name,))
            row = db.fetchone()
            targetID = row['targetID'] 
            db.execute("INSERT INTO tcconInfo SET tcconName=%s, tcconID=%s, targetID=%s", (tcconName, tcconID, targetID,))
            return template('site/add-site-confirm.html', footerFile=footerFile, menuFile=menuFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message)


# Update a site
@ app.route('/update-site/<siteName>')
def update_site(db, siteName):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            db.execute('SELECT s.siteID, s.name, s.description, ST_X(s.targetGeo) as targetLon, ST_Y(s.targetGeo) as targetLat, s.targetAlt, s.contact, s.tcconStatusText, s.tcconStatusValue, s.tcconStatusLink, s.emailRecipients, s.display, ST_X(s.tcconGeo) as tcconLon, ST_Y(s.tcconGeo) as tcconLat, s.tcconAlt, s.timezone, s.accuWeatherLink, s.wuWeatherLink, t.tcconID, t.tcconName FROM sites s, tcconInfo t WHERE s.name=%s AND t.targetID=s.targetID', (siteName,))
            row = db.fetchall()
            return template('site/update-site.html', footerFile=footerFile, menuFile=menuFile, row=row, siteName=siteName)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message, catchURL=request.url)


@ app.route('/update-site', method='POST')
def do_update_site(db):
    menuFile = 'site/includes/menu.html'
    footerFile = 'site/includes/footer.html'
    if request.cookies.get('caruser'):
        cookieInfo = request.cookies.get('caruser')
        cookieHex = cookieInfo.split('.')[0]
        username = cookieInfo.split('.')[1]
        now = datetime.datetime.now()
        db.execute('SELECT COUNT(*) AS count FROM authentication WHERE cookie=%s AND username=%s AND expirationDate >= %s',
                   (cookieHex, username, now.strftime('%Y-%m-%d %H:%M:%S'),))
        results = db.fetchone()
        if results['count'] == 1:
            originalName = request.forms.get('originalName')
            siteID = request.forms.get('siteID')
            name = request.forms.get('name')
            tcconName = request.forms.get('tcconName')
            tcconID = request.forms.get('tcconID')
            description = request.forms.get('description')
            targetGeo = request.forms.get('targetGeo')
            targetGeo = targetGeo.replace(',', ' ')
            targetGeo = 'POINT(%s)' % targetGeo
            targetAlt = request.forms.get('targetAlt')
            tcconGeo = request.forms.get('tcconGeo')
            tcconGeo = tcconGeo.replace(',', ' ')
            tcconGeo = 'POINT(%s)' % tcconGeo
            tcconAlt = request.forms.get('tcconAlt')
            contact = request.forms.get('contact')
            tcconStatusText = request.forms.get('tcconStatusText')
            tcconStatusValue = request.forms.getall('tcconStatusValue')
            tcconStatusLink = request.forms.get('tcconStatusLink')
            emailRecipients = request.forms.get('emailRecipients')
            display = request.forms.getall('display')
            timezone = request.forms.get('timezone')
            accuWeatherLink = request.forms.get('accuWeatherLink')
            wuWeatherLink = request.forms.get('wuWeatherLink')
            if not tcconName:
                tcconName = None
            if not tcconID:
                tcconID = None
            if not description:
                description = None
            if not siteID:
                siteID = None
            if not description:
                description = None
            if not targetGeo:
                targetGeo = None
            if not targetAlt:
                targetAlt = None
            if not contact:
                contact = None
            if not tcconStatusText:
                tcconStatusText = None
            if not tcconStatusLink:
                tcconStatusLink = None
            if not emailRecipients:
                emailRecipients = None
            if not tcconStatusValue or tcconStatusValue[0] == 3:
                tcconStatusValue = [None]
            if not tcconGeo:
                tcconGeo = None
            if not tcconAlt:
                tcconAlt = None
            if not timezone:
                timezone = None
            if not accuWeatherLink:
                accuWeatherLink = None
            if not wuWeatherLink:
                wuWeatherLink = None
            db.execute('UPDATE sites SET siteID=%s, name=%s, description=%s, targetGeo=ST_GeometryFromText(%s), targetAlt=%s, contact=%s, tcconStatusText=%s, tcconStatusLink=%s, emailRecipients=%s, display=%s, tcconStatusValue=%s, timezone=%s, tcconGeo=ST_GeometryFromText(%s), tcconAlt=%s, accuWeatherLink=%s, wuWeatherLink=%s WHERE name=%s',
                       (siteID, name, description, targetGeo, targetAlt, contact, tcconStatusText, tcconStatusLink, emailRecipients, display[0], tcconStatusValue[0], timezone, tcconGeo, tcconAlt, accuWeatherLink, wuWeatherLink, originalName,))
            db.execute('SELECT targetID FROM sites WHERE siteID=%s AND name=%s', (siteID, name,))
            row = db.fetchone()
            targetID = row['targetID']
            db.execute('SELECT targetID FROM tcconInfo WHERE targetID=%s', (targetID,))
            row = db.fetchone()
            db.execute('UPDATE tcconInfo SET tcconName=%s, tcconID=%s WHERE targetID=%s', (tcconName, tcconID, targetID,))
            return template('site/update-site-confirm.html', footerFile=footerFile, menuFile=menuFile)
        else:
            message = 'Access denied.  Please login.'
            return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message)
    else:
        message = 'Access denied.  Please login.'
        return template('site/login.html', footerFile=footerFile, menuFile=menuFile, message=message)


# Path Viewer
@ app.route('/path/<selectionID>')
def path_viewer(db, selectionID):
    db.execute('SELECT ST_X(t.targetGeo) as xCoord, ST_Y(t.targetGeo) as yCoord, t.name, s.path, s.obsMode FROM selectedTargets s, sites t WHERE s.targetID=t.targetID AND s.selectionID=%s', (selectionID,))
    row = db.fetchone()
    site = row['name']
    path = row['path']
    mode = row['obsMode']
    xCoord = row['xCoord']
    yCoord = row['yCoord']
    siteKML = 'kml/sites/%s.kml' % site
    if mode == 'Glint':
        pathKML = 'kml/paths/Glint/file.kml' % path
    elif mode == 'Nadir':
        pathKML = 'kml/paths/Nadir/file.kml' % path
    else:
        pathKML = 'kml/paths/Both/file.kml' % path

    return template('site/path-viewer.html', xCoord=xCoord, yCoord=yCoord, siteKML=siteKML, pathKML=pathKML, path=path, site=site)

# Reports
# Report on site stats


@ app.route('/api/report/site-stats', method='GET')
def site_stats_contacts_report(db):
    db.execute(
        'SELECT targetID, name, description FROM sites WHERE display=1 ORDER BY name ASC')
    row = db.fetchall()
    info = []
    for site in row:
        db.execute('SELECT MAX(targetTimeUTC) as targetTimeUTC FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
        row = db.fetchone()
        lastTargetTime = row['targetTimeUTC']
        db.execute(
            'SELECT COUNT(*) as numSelections FROM selectedTargets WHERE selectDate IS NOT NULL AND targetID=%s', (site['targetID'],))
        row = db.fetchone()
        numSelections = row['numSelections']
        info.append({'name': site['name'],
                     'description': site['description'],
                     'lastTargetTime': lastTargetTime,
                     'numSelections': numSelections,
                     'tcconDataReturn': '-',
                     'oco2DataReturn': '-'})

    reportFilename = 'reports/site_stats_report.csv'
    openFile = open(reportFilename, 'w')
    file = csv.writer(openFile, delimiter=',', quotechar='"')
    header = ['Site', 'Target Name', 'Number of Selections',
              'Last Target Time (UTC)', 'TCCON Data Return', 'OCO-2 Data Return']
    file.writerow(header)
    for dataPoint in info:
        dataRow = [dataPoint['description'], dataPoint['name'], dataPoint['numSelections'],
                   dataPoint['lastTargetTime'], dataPoint['tcconDataReturn'], dataPoint['oco2DataReturn']]
        file.writerow(dataRow)
    openFile.close()

    return static_file('site_stats_report.csv', root='reports', download='site_stats_report.csv')


@ app.route('/api/report/selected-sites-output', method='GET')
def selected_sites_report(db):
    showNoTargets = request.query.showNoTargets
    startRange = request.query.startRange
    endRange = request.query.endRange
    if showNoTargets == 'on':
        db.execute('SELECT g.gcDateTime AS groundContactTime, s.name, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.selectDate, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData FROM selectedTargets t, sites s, gcs g WHERE t.gcID=g.gcID AND t.targetID=s.targetID AND t.display=1 AND DATE(g.gcDateTime) >= %s AND DATE(g.gcDateTime) <= %s AND s.name != "noTarget" AND selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (startRange, endRange,))
    else:
        db.execute('SELECT g.gcDateTime AS groundContactTime, s.name, t.orbit, t.orbitURL, t.path, t.targetTimeUTC, t.selectDate, t.emailTime, t.tcconDataAvailable, t.tcconDataStatus, t.ocoDataAvailable, t.ocoDataStatus, t.selectedBy, t.modisImage, REPLACE(t.modisImage, ".png", "_thumbnail.png") AS modisThumbnail, t.viirsImage, REPLACE(t.viirsImage, ".png", "_thumbnail.png") AS viirsThumbnail, t.aeronetData FROM selectedTargets t, sites s, gcs g WHERE t.gcID=g.gcID AND t.targetID=s.targetID AND t.display=1 AND DATE(g.gcDateTime) >= %s AND DATE(g.gcDateTime) <= %s AND selectDate IS NOT NULL ORDER BY g.gcDateTime ASC', (startRange, endRange,))
    row = db.fetchall()

    reportFilename = 'reports/selected_sites_report.csv'
    openFile = open(reportFilename, 'w')
    file = csv.writer(openFile, delimiter=',', quotechar='"')
    header = ['Ground Contact Time', 'Target Name', 'Orbit', 'Path', 'Target Time (UTC)', 'Select Date', 'Email Time (PT)',
              'TCCON Data Available', 'TCCON Data Status', 'OCO-2 Data Available', 'OCO-2 Data Status', 'MODIS Image', 'Aeronet Data', 'Selected By']
    file.writerow(header)
    for dataPoint in row:
        dataRow = [dataPoint['groundContactTime'], dataPoint['name'], dataPoint['orbit'], dataPoint['path'], dataPoint['targetTimeUTC'], dataPoint['selectDate'], dataPoint['emailTime'],
                   dataPoint['tcconDataAvailable'], dataPoint['tcconDataStatus'], dataPoint['ocoDataAvailable'], dataPoint['ocoDataStatus'], dataPoint['modisThumbnail'], dataPoint['viirsThumbnail'], dataPoint['aeronetData'], dataPoint['selectedBy']]
        file.writerow(dataRow)
    openFile.close()

    return static_file('selected_sites_report.csv', root='reports', download='selected_sites_report.csv')


@ app.route('/api/report/active-sites-output', method='GET')
def active_sites_report(db):
    startRange = request.query.startRange
    endRange = request.query.endRange
    db.execute('SELECT DISTINCT orbit FROM gcs WHERE DATE(gcDateTime) >= %s AND DATE(gcDateTime) <= %s',
               (startRange, endRange,))
    orbitNums = db.fetchall()
    gcIDresults = []
    for thisOrbit in orbitNums:
        db.execute(
            'SELECT MAX(tofID) AS tofID FROM gcs WHERE orbit = %s', (thisOrbit['orbit'],))
        maxTOF = db.fetchone()
        db.execute('SELECT gcID FROM gcs WHERE tofID = %s AND orbit = %s',
                   (maxTOF['tofID'], thisOrbit['orbit'],))
        getGC = db.fetchone()
        gcIDresults.append(str(getGC['gcID']))
    gcList = ','.join(gcIDresults)
    if gcList != '':
        sql = 'SELECT selectionID FROM selectedTargets s WHERE gcID in (%s)'
        db.execute(sql, (gcList,))
        selectionResults = db.fetchall()
        selectionIDs = []
        for s in selectionResults:
            selectionIDs.append(str(s['selectionID']))
        selectionList = ','.join(selectionIDs)
        sql = 'SELECT g.gcDateTime, s.name, s.siteID, t.targetTimeUTC, f.filename FROM gcs g, sites s, tofFiles f, selectedTargets t WHERE t.gcID=g.gcID AND t.tofID=f.tofID AND t.targetID=s.targetID AND t.selectionID IN (%s) AND t.display=1 AND t.orbit !=0 ORDER BY g.gcDateTime ASC'
        db.execute(sql, (selectionList,))
        row = db.fetchall()
        reportFilename = 'reports/active_sites_report.csv'
        openFile = open(reportFilename, 'w')
        file = csv.writer(openFile, delimiter=',', quotechar='"')
        header = ['gcdatetime', 'targetname',
                  'siteid', 'targettime', 'filename']
        file.writerow(header)
        for dataPoint in row:
            dataRow = [dataPoint['gcDateTime'], dataPoint['name'],
                       dataPoint['siteID'], dataPoint['targetTimeUTC'], dataPoint['filename']]
            file.writerow(dataRow)
        openFile.close()

    return static_file('active_sites_report.csv', root='reports', download='active_sites_report.csv')


run(app, host=webhost, port=webport, debug=True)

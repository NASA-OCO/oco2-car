import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
import pytz
import pymysql
import json

def load_selected_targets(db, cur, days):
    daysBack = dt.datetime(2022,4,26) - dt.timedelta(days=days)
    sql = 'SELECT t.filename, s.path FROM selectedTargets s, tofFiles t WHERE date(s.targetTimeUTC) >= "%s" AND s.selectDate IS NOT NULL AND s.tofID=t.tofID'
    return pd.read_sql(sql, db, params=[daysBack.date()])


def plot_path_usage(db, cur, plot_file, days):
    df = load_selected_targets(db, cur, days)
    counts = df.groupby('path').count()
    counts = counts[counts.index > 0]
    colors = [_bar_color(c) for c in counts['filename']]
    with plt.rc_context({'font.size': 12}):
        _, ax = plt.subplots(figsize=(16,3))
        counts.plot.bar(y='filename', color=colors, ax=ax, label='')
        ax.set_ylabel('# selects in last {} days'.format(days-1))
        ax.set_xlabel('Path')
        ax.set_yticks(list(range(counts['filename'].max()+1)))
        ax.grid()
        ax.get_legend().remove()

        tz = pytz.timezone('US/Pacific')
        now = tz.localize(dt.datetime.now())
        ax.set_title('Generated at {:%Y-%m-%d %H:%M %Z}'.format(now))
        if plot_file:
            plt.savefig(plot_file, bbox_inches='tight')


def _bar_color(count):
    colors = {0: 'green', 1: 'green', 2: 'gold', 3: 'darkorange', 4: 'red'}
    if count < 0:
        return colors[0]
    elif count > 4:
        return colors[4]
    else:
        return colors[count]


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

def closeDB(db):
    db.close()

    return

def main():
    db,cur = openDB()
    plot_file = 'plots/path_usage.png'
    days = 65
    plot_path_usage(db, cur, plot_file, days)
    closeDB(db)


if __name__ == '__main__':
    """
    This script generates the Path Count plot show on the 
    Site Statiscs page.
    """
    main()


import datetime as dt
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import os
import pandas as pd
from pathlib import Path
import pytz
import re
import sys
import warnings
import pymysql
import json
from glob import glob


def read_odf(odf_file):
    with open(odf_file) as f:
        for line in f:
            if not line.startswith('#'):
                break
            else:
                last_line = line
    # Last line of the header should be something like: # Column Headers:  Day,...
    # Extract the column headers
    headers = last_line.split(':')[1].split(',')
    headers = [x.strip() for x in headers]
    df = pd.read_csv(odf_file, comment='#', header=None)
    df.columns = headers
    return df


def load_science_modes_for_paths(paths, db, cur, n_occurrences=8, max_time_window=pd.Timedelta(days=500)):
    odfs_rev_chrono = list_odfs_reverse_chronological(db, cur)
    odf_df = build_odf_df(odfs_rev_chrono, paths,
                          n_occurrences, max_time_window)
    odf_df = set_target_mode_for_selected(odf_df, db, cur)
    if not isinstance(paths, str):
        xx = odf_df['OCO-2 Reference Ground Path'].apply(lambda p: p in paths)
        return odf_df[xx]
    else:
        return odf_df


def list_odfs_reverse_chronological(db, cur):
    urls = pd.read_sql(
        'SELECT DISTINCT targetTimeUTC FROM selectedTargets WHERE selectDate IS NOT NULL ORDER BY targetTimeUTC DESC', db)

    odfs = []
    for url in urls.tolist():

        # Update this path
        these_odfs = sorted(glob('/path/to/odf/files/*.odf'))
        # There will usually be at least two versions of the ODF. We want the latest one, which should be the
        # last one alphabetically (though if there's > 9 versions this might break)
        if len(these_odfs) > 0:
            odfs.append(these_odfs[-1])
#         else:
#             print(f'No ODF file in {p}')
    return odfs


def build_odf_df(odf_files, paths, n_occurrences, max_time_window):
    i = 0
    odf_df = read_odf(odf_files[i])
    odf_df['ODF File'] = str(odf_files[i])
    last_date = _extract_odf_date(odf_files[i])
    if paths == 'all':
        # Assume that every ODF file has all the paths - they seem to, as they look like they always
        # cover a 16 day repeat cycle
        paths = set(odf_df['OCO-2 Reference Ground Path'])
        if 0 in paths:
            paths.remove(0)
    while _need_more_instances(odf_df, paths, n_occurrences):
        i += 1
        new_odf = read_odf(odf_files[i])
        new_odf['ODF File'] = str(odf_files[i])
        xx = new_odf['Absolute Orbit #'] < odf_df['Absolute Orbit #'].min()
        odf_df = pd.concat([odf_df, new_odf[xx]])

        if last_date - _extract_odf_date(odf_files[i]) > max_time_window:
            print('Could not find enough occurrences of at least one path in the allowed time window', file=sys.stderr)
            break
    return odf_df.reset_index()


def _need_more_instances(odf_df, paths, n_occurrences):
    instances = odf_df.groupby(
        'OCO-2 Reference Ground Path').count().iloc[:, 0]
    return (instances[paths] < n_occurrences).any()


def _extract_odf_date(odf_file):
    odf_file = Path(odf_file).name
    datestr = re.search(r'oc2_(\d{4}_\d{2}_\d{2})', odf_file).group(1)
    return pd.to_datetime(datestr, format='%Y_%m_%d')


def set_target_mode_for_selected(odf_df, db, cur):
    first_orbit = odf_df['Absolute Orbit #'].min()
    last_orbit = odf_df['Absolute Orbit #'].max()
    sql = ('SELECT orbit FROM selectedTargets WHERE '
           'orbit >= %s AND '
           'orbit <= %s AND '
           'selectDate IS NOT NULL' % (first_orbit, last_orbit))
    target_orbits = pd.read_sql(sql, db)['orbit']

    target_orbits = set(target_orbits)
    xx = odf_df['Absolute Orbit #'].apply(lambda o: o in target_orbits)
    odf_df.loc[xx, 'Science Mode'] = 'TARGET'
    return odf_df


def path_use_plot(odf_target_df, path_as_x=True, show_orbit=False, path_targets=dict(), ax=None):
    colors = {'GLINT': 'dodgerblue', 'NADIR': 'springgreen', 'TARGET': 'red'}
    modes = odf_target_df.set_index(
        ['OCO-2 Reference Ground Path', 'Absolute Orbit #']).sort_index()['Science Mode']

    if ax is None:
        _, ax = plt.subplots(figsize=(16, 3))

    last_path = -1
    x_incr = -1
    y_max = 0
    paths = []
    #import pdb; pdb.set_trace()
    for (path, orb), mode in modes.items():
        if path != last_path:
            y = 0
            x_incr += 1
            paths.append(path)
        else:
            y += 1

        last_path = path
        y_max = max(y_max, y)
        x = path if path_as_x else x_incr
        ax.plot(x, y, ls='none', marker='o', color=colors[mode])
        if show_orbit:
            ax.text(x, y, str(orb))

    if not path_as_x:
        #import pdb; pdb.set_trace()
        ax2 = ax.twiny()
        ax.set_xticks(range(0, x_incr+1))
        ax2.set_xticks(range(0, x_incr+1))
        ax2.set_xlim(ax.get_xlim())
        labels = [path_targets.get(p, '(?)') for p in paths]

        ax.set_xticklabels(labels)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
        ax2.set_xticklabels(paths)

        ax.set_xlabel('Target')
        ax2.set_xlabel('Path')
    else:
        ax.set_xlabel('Path')
        if path_targets:
            warnings.warn('path_targets is ignored unless path_as_x is False')

    ax.set_ylabel('Orbit')

    legend_elements = [Line2D(
        [0], [0], ls='none', marker='o', color=c, label=k) for k, c in colors.items()]
    ax.legend(handles=legend_elements, loc='right', bbox_to_anchor=(1.15, 0.5))
    ax.set_yticks([0, y_max])
    ax.set_yticklabels(['Earlier', 'Later'])


def make_path_use_plot_for_upcoming_targets(db, cur, plot_file):
    sql = 'SELECT g.gcDateTime FROM selectedTargets s, gcs g WHERE s.tofID=(SELECT tofID FROM tofFiles WHERE ignored !=1 ORDER BY createTime DESC LIMIT 1) AND g.gcID=s.gcID AND s.selectDate=(SELECT MAX(selectDate) FROM selectedTargets) ORDER BY selectDate DESC LIMIT 1'
    cur.execute(sql)
    after = cur.fetchall()
    if len(after) == 0:
        sql = 'SELECT g.gcDateTime FROM selectedTargets s, gcs g WHERE s.tofID=(SELECT tofID FROM tofFiles WHERE ignored !=1 ORDER BY createTime DESC LIMIT 1,1) AND g.gcID=s.gcID AND s.selectDate=(SELECT MAX(selectDate) FROM selectedTargets) ORDER BY selectDate DESC LIMIT 1'
        cur.execute(sql)
        after = cur.fetchall()
    after = after[0][0]
    sql = 'SELECT s.path AS pathnum, t.name AS targetname FROM sites t, selectedTargets s, gcs g WHERE g.gcDateTime > "%s" AND g.gcID=s.gcID AND s.path !=0 AND s.tofID=(SELECT tofID FROM tofFiles WHERE ignored != 1 ORDER BY createTime DESC LIMIT 1) AND s.targetID=t.targetID ORDER BY g.gcDateTime, s.targetTimeUTC'
    upcoming_targets = pd.read_sql(sql, db, params=[after.strftime('%Y-%m-%d %H:%M:%S')])
    upcoming_paths = list(upcoming_targets['pathnum'].unique())
    targets_by_path = dict()
    for p, pdf in upcoming_targets.groupby('pathnum'):
        targets_by_path[p] = '\n'.join(pdf['targetname'])

    modes = load_science_modes_for_paths(upcoming_paths, db, cur)
    path_use_plot(modes, path_as_x=False, path_targets=targets_by_path)
    tz = pytz.timezone('US/Pacific')
    now = tz.localize(dt.datetime.now())
    plt.title('Generated at {:%Y-%m-%d %H:%M %Z}'.format(now))
    plt.savefig(plot_file, bbox_inches='tight')


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
    db, cur = openDB()
    plot_file = 'plots/mode_usage.png'
    make_path_use_plot_for_upcoming_targets(db, cur, plot_file)
    closeDB(db)


if __name__ == '__main__':
    """
    This script generates the Mode Usage plot show on the 
    Site Statiscs page.
    """
    main()

#!/usr/bin/env python

import re
import os
import urllib
import sys, getopt
from xml.etree.ElementTree import parse

TVDB_URL = 'http://thetvdb.com/api/'

SEARCH_URL = 'GetSeries.php?seriesname={query}'

SERIES_INFO_URL = '/series/{id}/en.xml'
SERIES_EPISODES_URL = '/series/{id}/all/en.xml'

APIKEY = '15C9D64D3EFCC581'

# Video file extensions
exts = ('.mkv', '.mp4', '.avi')


##### REGULAR EXPRESSIONS FOR FILE NAME SEARCHES

# Multi episode files, like 'S09E01 - E02"
multi_ep_regex = re.compile('([sS][0-9]+[eE][0-9]+.*[eE][0-9]+)|([0-9]+(x|\.)[0-9]+(x|\.)[0-9]+)')

# Looks for strings like "S09E01" or "9x01", "9.01"
single_ep_regex = re.compile('([sS][0-9]+.?[eE][0-9]+)|([0-9]+(x|\.)[0-9]+)')

# Regex for file extensions
video_ext_regex = re.compile('(\.mkv|\.avi|\.mp4)')

s_rgx = re.compile('[sS][0-9]+')
e_rgx = re.compile('[eE][0-9]+')
alt_rgx = re.compile('(x|\.)')



class Show(dict):
    def __init__(self, title):
        dict.__init__(self)
        self.title = title

    def __getitem__(self, season):
        if season in self:
            return dict.__getitem__(self, season)
        else:
            dict.__setitem__(self, season, Season(title=self.title, season=season))
            return dict.__getitem__(self, season)

    def __repr__(self):
        return "{name:s} - {num_seas:d} Seasons".format(name=self.title,
                                                        num_seas=len(self))


class Season(dict):
    def __init__(self, title, season):
        dict.__init__(self)
        self.title = title
        self.season = season

    def __getitem__(self, episode):
        if episode in self:
            return dict.__getitem__(self, episode)
        else:
            dict.__setitem__(self, episode, Episode(title=None,
                                                    season_num=None,
                                                    episode_num=None))
            return dict.__getitem__(self, episode)

    def __repr__(self):
        return ("List of episodes for season {:d}:\n".format(self.season) +
                "\n".join(self.get_episode_list()))

    def get_episode_list(self):
        return [str(ep.ep) + " - " +  ep.title for ep in self.values()]

        
class Episode:
    def __init__(self, title, season, ep, air_date=None):
        self.title = title
        self.season = season
        self.ep = ep
        self.air_date = air_date

    def __repr__(self):
        return "S{season:02d}E{ep:02d} {title:s} - Aired: {air:s}".format(air=self.air_date,
                                                                           season=self.season,
                                                                           ep=self.ep,
                                                                           title=self.title)


def get_show_info(series_id):

    url = TVDB_URL + APIKEY + SERIES_INFO_URL.format(id=series_id)
    raw_xml = urllib.urlopen(url)
    show_xml = parse(raw_xml).getroot()

    show = show_xml.find('Series')

    show_name = show.find('SeriesName').text
    show_id = show.find('id').text

    print '{id} - {name}'.format(id=show_id, name=show_name)


    
    
def search(query):
    url = TVDB_URL + SEARCH_URL.format(query=query)
    raw_xml = urllib.urlopen(url)
    search_xml = parse(raw_xml).getroot()

    results = search_xml.findall('Series')

    results_array = []
    
    for i, result in enumerate(results):
        show_name = result.find('SeriesName').text
        show_id = result.find('id').text

        results_array.append((i, show_name, show_id))

    return results_array


def get_show_episodes(series_id):
    url = TVDB_URL + APIKEY + SERIES_EPISODES_URL.format(id=series_id)
    raw_xml = urllib.urlopen(url)
    all_eps = parse(raw_xml).getroot()

    info = all_eps.find('Series')
    show_name = info.find('SeriesName').text

    show = Show(show_name)

    for ep in all_eps.findall('Episode'):
        season_num = ep.find("SeasonNumber").text
        ep_num = ep.find("EpisodeNumber").text
        ep_name = ep.find("EpisodeName").text
        air_date = ep.find("FirstAired").text

        season_num.encode('utf-8') if season_num else None
        ep_num.encode('utf-8') if ep_num else None
        ep_name.encode('utf-8') if ep_name else None
        air_date.encode('utf-8') if air_date else None

        season_num = int(season_num)
        ep_num = int(ep_num)
        
        show[season_num][ep_num] = Episode(ep_name,
                                           season_num,
                                           ep_num,
                                           air_date)
    return show


def get_show(show_name, num = None):
    search_results = search(show_name)

    if len(search_results) == 0:
        print 'No results. Try another query'
        return None
        
    elif len(search_results) == 1:
        return get_show_episodes(search_results[0][2])
    
    elif num is not None:
        return get_show_episodes(search_results[num][2])
    
    else:
        print "Search results has more than 1 result:"
        for r in search_results:
            print 'num: {:d} \t show: {:s}'.format(r[0], r[1])
        
        print "\nUse function with the 'num' argument. Eg. get_show('seinfeld', 0)"

        return None


def rename_all_shows_in_dir(dir, show_name = None, num = None):

    dirpath = os.path.realpath(dir)

    if show_name is None:
        # If no show_name is given, uses folder name
        show_name = os.path.basename(dirpath)
    show = get_show(show_name, num=num)

    if show is None:
        print "{:s} has multiple search results. Rerun function with a number arugument".format(show_name)
        print "Eg. rename_all_shows_in_dir('seinfeld', 0)"
        return None

    # Looks through each folder to find episode files
    for root, directory, files in os.walk(dir):
        
        # Gets all files in the directory that is not hidden and has a video extension
        ep_files = [f for f in files if f.endswith(exts) and f[0] != '.']

        # Loop through each video file
        for i in xrange(0, len(ep_files)):
            old_file_name = ep_files[i]

            rename_file(show, root, old_file_name)


def rename_file(show, root, old_name):

    file_ext = video_ext_regex.search(old_name).group()
    
    season_ep, ep_name = get_ep_info_from_filename(old_name, show)

    ## Uncomment if you want show name in the file name
    # new_name = "{title:s} - {seas_ep:s} - {ep_name:s}{ext:s}".format(title=show.title,
    #                                                                  seas_ep=season_ep,
    #                                                                  ep_name=ep_name,
    #                                                                  ext=file_ext)

    new_name = "{seas_ep:s} - {ep_name:s}{ext:s}".format(seas_ep=season_ep,
                                                         ep_name=ep_name,
                                                         ext=file_ext)
    
    if old_name != new_name:
        print old_name + "\t -> \t" + new_name
        os.rename(root + '/' + old_name, root + '/' + new_name)
            
            
def get_ep_info_from_filename(file_name, show):

    # check if file contains two episodes. Eg something like S09E01-E02
    multi = multi_ep_regex.search(file_name)
    
    if multi:
        season_ep_label, ep_name = extract_ep_info_multi(multi.group(), show)
    else:
        single = single_ep_regex.search(file_name)
        season_ep_label, ep_name = extract_ep_info_single(single.group(), show)

    for ch in list('!@#%^&:/'):
        if ch in ep_name:
            ep_name = ep_name.replace(ch, '_')
                   
    return season_ep_label, ep_name        



def extract_ep_info_multi(label, show):
    """ Takes the season and ep label of a multi episode file (eg. S09E01 & E02) and a Show
    object as input, returns the formatted season and episode label and episode name """

    # Get season number
    season_label = s_rgx.search(label)
    if season_label:
        season_label = season_label.group()
        season = int(season_label[1:])

        # Gets the episode numbers
        ep_labels = [ep.group() for ep in e_rgx.finditer(label)]
        eps = [int(ep[1:]) for ep in ep_labels]

    else:
        labels_split = alt_rgx.split(label)
        season = int(labels_split[0])
        eps = [int(labels_split[2]), int(labels_split[4])]
    
    ep_title_1 = show[season][eps[0]].title
    ep_title_2 = show[season][eps[1]].title

    season_ep_label = "S{season:02d}E{ep1:02d}-E{ep2:02d}".format(season=season,
                                                                      ep1=eps[0],
                                                                      ep2=eps[1])
    # Seaches for parenthesis like "<Episode name> (1)"
    ep_part_parens = re.compile('\([0-9]\)')
    
    parens_1 = ep_part_parens.search(ep_title_1)
    parens_2 = ep_part_parens.search(ep_title_2)
    
    if parens_1 and parens_2:
        ep_title_1_clean = ep_title_1[:parens_1.start()].strip()
        ep_title_2_clean = ep_title_2[:parens_2.start()].strip()

        
        # If the episode names are the same, then set title as first episode name
        if ep_title_1_clean == ep_title_2_clean:
            ep_name = ep_title_1_clean.encode('utf-8')
    else:
        ep_name = ep_title_1 + ' and ' + ep_title_2
    
    return season_ep_label, ep_name


def extract_ep_info_single(label, show):
    """ Takes the season and ep label of a single episode file (eg. S09E01) and a Show
    object as input, returns the formatted season and episode label and episode name """

    season_label = s_rgx.search(label)
    episode_label = e_rgx.search(label)

    # check if file's season and episode is formatted as 'S01E01' or not.
    if season_label and episode_label:
        season_num = int(label[season_label.start()+1 : season_label.end()])
        ep_num     = int(label[episode_label.start()+1 : episode_label.end()])
    else:
        s3 = alt_rgx.search(label)
        season_num = int(label[:s3.start()])
        ep_num     = int(label[s3.start()+1:])

    season_ep_label = 'S{season:02d}E{ep:02d}'.format(season=season_num,
                                                      ep=ep_num)
    
    ep_name = show[season_num][ep_num].title.encode('utf-8')

    return season_ep_label, ep_name


def main(argv):

    show_name, num = None, None
    
    try:
        opts, _ = getopt.getopt(argv, 's:n:')
    except:
        print "tvdb.py -s 'seinfeld' -n 0"
    
    for opt, arg in opts:
        if opt == '-s':
            show_name = arg
        elif opt == '-n':
            num = int(arg)
            
    rename_all_shows_in_dir(os.getcwd(), show_name=show_name, num=num)


if __name__ == "__main__":
    main(sys.argv[1:])

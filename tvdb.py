import urllib
from xml.etree.ElementTree import parse

TVDB_URL = 'http://thetvdb.com/api/'
APIKEY = '15C9D64D3EFCC581'

SERIES_INFO_URL = '/series/{id}/en.xml'
SERIES_EPISODES_URL = '/series/{id}/all/en.xml'

SEARCH_URL = 'GetSeries.php?seriesname={query}'

class Show(dict):

    def __init__(self):
        dict.__init__(self)

    def __getitem__(self, season):
        if season in self:
            return dict.__getitem__(self, season)
        else:
            dict.__setitem__(self, season, Season())
            return dict.__getitem__(self, season)

class Season(dict):

    def __init__(self):
        dict.__init__(self)

    def __getitem__(self, episode):
        if episode in self:
            return dict.__getitem__(self, episode)
        else:
            dict.__setitem__(self, episode, Episode(title=None, season_num=None, episode_num=None))
            return dict.__getitem__(self, episode)
    
class Episode:

    def __init__(self, title, season, ep, air_date=None):
        self.title = title
        self.season = season
        self.ep = ep
        self.air_date = air_date

    def __repr__(self):
        return "S{season:02d}E{ep:02d} - {title:s}".format(season=self.season, ep=self.ep, title=self.title)



def get_show_info(series_id):
    # Construct api URL
    raw_xml = urllib.urlopen(TVDB_URL + APIKEY + SERIES_INFO_URL.format(id=series_id))

    show_xml = parse(raw_xml).getroot()

    show = show_xml.find('Series')
    
    show_name = show.find('SeriesName').text
    show_id = show.find('id').text

    print '{id} - {name}'.format(id=show_id, name=show_name)

def search(query):
    
    raw_xml = urllib.urlopen(TVDB_URL + SEARCH_URL.format(query=query))

    search_xml = parse(raw_xml).getroot()
    results = search_xml.findall('Series')

    for i, result in enumerate(results):
        show_name = result.find('SeriesName').text
        show_id = result.find('id').text

        print i, show_id, show_name


def get_show_episodes(series_id):
    url = TVDB_URL + APIKEY + SERIES_EPISODES_URL.format(id=series_id)
    raw_xml = urllib.urlopen(url)

    all_eps = parse(raw_xml).getroot()

    show = Show()
    
    for ep in all_eps.findall('Episode'):
        season_num = ep.find("SeasonNumber").text.encode('utf-8')
        ep_num = ep.find("EpisodeNumber").text.encode('utf-8')
        ep_name = ep.find("EpisodeName").text.encode('utf-8')

        season_num = int(season_num)
        ep_num = int(ep_num)

        show[season_num][ep_num] = Episode(ep_name, season_num, ep_num)

    return show


# search('simpsons')    
# get_show_info(71663)    
simps = get_show_episodes(71663)        

show = simps
####  FILE NAME FORMAT 
season = 1

for epnum in show[season]:
    ep = show[season][epnum]
    print "S{:02d}E{:02d} - {:s}".format(ep.season, ep.ep, ep.title)


import os
directory = '/Users/kevinchou/Movies/The Simpsons/Season 1/'

all_files = sorted(os.listdir(directory))

ext = '.avi'
ep_files = [f for f in all_files if f[-4:] == ext]

if len(show[season]) == len(ep_files):
    for i in xrange(0, len(ep_files)):
        ep = i+1
        ep_name = show[season][ep].title
        new_file_name = "S{:02d}E{:02d} - {:s}{:s}".format(season, ep, ep_name, ext)
        old_file_name = ep_files[i]

        print old_file_name, new_file_name

        #os.rename(directory + old_file_name, directory + new_file_name)





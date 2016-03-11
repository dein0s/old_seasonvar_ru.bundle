# -*- coding: utf-8 -*-
import re
from updater import Updater

COMMON = SharedCodeService.common

ART = 'art-default.jpg'
ICON = 'icon-default.png'


def Start():
  HTTP.CacheTime = CACHE_1HOUR

  ObjectContainer.title1 = COMMON.TITLE
  ObjectContainer.art = R(ART)

  DirectoryObject.thumb = R(ICON)
  DirectoryObject.art = R(ART)
  EpisodeObject.thumb = R(ICON)
  EpisodeObject.art = R(ART)
  VideoClipObject.thumb = R(ICON)
  VideoClipObject.art = R(ART)
    # JSON.CacheTime = CACHE_1HOUR
    # HTTP.CacheTime = CACHE_1HOUR
    # pass

    # Plugin.AddViewGroup('Infolist', viewMode='InfoList', mediaType='items')
    # Plugin.AddViewGroup('List', viewMode='List', mediaType='items')


@handler(COMMON.PREFIX, 'seasonvar_ru', art=ART, thumb=ICON)
def Main():
    oc = ObjectContainer(
        title2=COMMON.TITLE,
        no_cache=True
    )

    Updater(COMMON.PREFIX+'/update', oc)

    oc.add(
        DirectoryObject(
            key=Callback(
                latest_updates,
            ),
            title=COMMON.LATEST_UPDATES,
        )
    )

    oc.add(
        InputDirectoryObject(
            key=Callback(search_serials),
            title=COMMON.SEARCH,
            prompt=COMMON.SEARCH_PROMT
        )
    )

    oc.add(
        DirectoryObject(
            key=None,
            title=COMMON.ABC_SELECT_RU
        )
    )

    oc.add(
        DirectoryObject(
            key=None,
            title=COMMON.ABC_SELECT_EN
        )
    )

    oc.add(
        DirectoryObject(
            key=None,
            title=COMMON.BOOKMARKS
        )
    )

    return oc


@route(COMMON.PREFIX + '/get_private')
def get_private():
    # url = 'http://seasonvar.ru/?mod=login'
    url = 'http://seasonvar.ru/'
    mod = {
        'login': '?mod=login',
        'pause': '?mod=pause'
    }
    creds = {
        'login': Prefs['login'],
        'password': Prefs['password']
    }
    HTTP.Request(url=url + mod['login'], values=creds, method='POST')
    Log.Debug('PD_COOKIES: %s' % HTTP.CookiesForURL(url))
    res = HTML.ElementFromString(HTTP.Request(url=url + mod['pause'], cacheTime=CACHE_1HOUR).content)
    Log.Debug('PD_RES: %s' % res)


@route(COMMON.PREFIX + '/search_serials', query=unicode)
def search_serials(query):
    if not api_key():  # todo move to main/start ?
        return api_key_missing()

    oc = ObjectContainer(title2=COMMON.SEARCH)  # todo think about strings for titles

    result = search(query)

    result_to_display = {}

    for item in result:
        season_id = get_season_id(item)
        title = format_season_display_title(item)
        thumb = item['poster_small']
        show_name = item['name']

        Data.SaveObject(season_id + '_raw', item)

        if show_name in result_to_display.keys():
            result_to_display[show_name].append(season_id)
        else:
            result_to_display[show_name] = [season_id]

        oc.add(
            DirectoryObject(
                key=Callback(get_season_info,
                             season_id=season_id
                             ),
                title=title,
                thumb=thumb
            )
        )

    # for key, value in result_to_display.iteritems():
    #     pass
        # oc.add(
        #     DirectoryObject(
        #
        #     )
        # )

    # Log(result_to_display)

    return oc


@route(COMMON.PREFIX + "/latest_updates")
def latest_updates():
    if not api_key():  # todo move to main?
        return api_key_missing()

    oc = ObjectContainer(
        title2=COMMON.LATEST_UPDATES,
    )

    result = get_latest()

    for item in result:
        season_id = get_season_id(item)
        title = format_season_display_title(item)
        thumb = item['poster_small']

        Data.SaveObject(season_id + '_raw', item)

        oc.add(
            DirectoryObject(
                key=Callback(get_season_info,
                             season_id=season_id,
                             ),
                title=title,
                thumb=thumb
            )
        )

    return oc


@route(COMMON.PREFIX + '/get_season_info')
def get_season_info(season_id):
    if Data.Exists(season_id + '_raw'):
        current_season = gather_update_season_data(season_id, update=True)
    else:
        current_season = gather_update_season_data(season_id)

    translates = current_season['playlist'].keys()

    if len(translates) == 1:
        return get_episodes(season_id)
    else:
        return get_seasons_or_translates(season_id)


@route(COMMON.PREFIX + '/get_episodes')
def get_episodes(season_id, translate=None):
    if Data.Exists(season_id):
        current_season = Data.LoadObject(season_id)
    else:
        current_season = gather_update_season_data(season_id)
    current_playlist = current_season['playlist']
    current_season_number = current_season['season']
    translate = unicode(translate if translate is not None else current_playlist.keys()[0])

    oc = ObjectContainer(
        title2=u'%s (%s)%s' % (
            current_season['title'],
            translate,
            '' if current_season_number == 0 else u' - %s сезон' % current_season_number
        ),
        content=ContainerContent.Episodes
    )

    for episode in current_playlist[translate]:
        try:
            episode['id'] = int(re.match(r'\d{1,3}', episode['name']).group())
        except AttributeError:
            episode['id'] = 0
        oc.add(
            COMMON.get_video_object(current_season, season_id, translate, episode['id'])
        )

    Data.SaveObject(season_id, current_season)

    return oc


@route(COMMON.PREFIX + '/get_seasons_or_translates')
def get_seasons_or_translates(season_id, seasons=False, seasons_list=None):

    if not seasons:
        if Data.Exists(season_id):
            current_season = Data.LoadObject(season_id)
        else:
            current_season = gather_update_season_data(season_id)
        current_season_number = current_season['season']
        translates = current_season['playlist'].keys()

        dummy_index = 1

        oc = ObjectContainer(
            title2=u'%s %s' % (
                current_season['title'],
                '' if current_season_number == 0 else u' - %s сезон' % current_season_number
            ),
            content=ContainerContent.Seasons,
        )

        for translate in translates:
            url = COMMON.MetaUrl('%s/?%s||%s||%s' % (COMMON.SEASONVAR_URL, season_id, translate, '_dummy_'))
            Log('URL_HERE %s' % url)
            oc.add(
                SeasonObject(
                    key=Callback(
                        get_episodes,
                        season_id=season_id,
                        translate=translate
                    ),
                    rating_key=COMMON.get_episode_url(url),
                    index=dummy_index,
                    title=translate,
                    source_title=COMMON.SEASONVAR_URL,
                    thumb=current_season['thumb_l'],
                    summary=current_season['summary']
                )
            )
            dummy_index += 1

        return oc

    else:
        for season in seasons_list:
            oc = ObjectContainer(
                title2=u'%s' % season,
                content=ContainerContent.Seasons,
            )

        pass


@route(COMMON.PREFIX + '/gather_season_data', season_id=str, update=bool, gather_all=bool)  # todo checking fix
def gather_update_season_data(season_id, update=False):
    current_season_data = get_season_by_id(season_id)

    data = {
        'season_id': season_id,
        'thumb_l': current_season_data['poster'],
        'thumb_s': current_season_data['poster_small'],
        'title': current_season_data['name'],
        'original_title': current_season_data.get('name_original'),
        'year': current_season_data['year'],
        'summary': current_season_data['description'],
        'genre': current_season_data['genre'],
        'country': current_season_data['country'],
        'rating': average_rating(current_season_data.get('rating')),
        'season': current_season_data.get('season_number', 1),
        'playlist': form_playlist_by_translate(current_season_data, external=False),
    }

    if update:
        season_item = Data.LoadObject(season_id + '_raw')
        data['directors'] = season_item.get('director')
        data['roles'] = season_item.get('role')
        data['update_message'] = season_item.get('message')
        data['last_changed'] = season_item.get('create_time')

        Data.Remove(season_id + '_raw')

    if data['season'] == 0 or data['season'] == '0':
        data.update({'season': 1})

    Data.SaveObject(season_id, data)

    return data


@route(COMMON.PREFIX + COMMON.GET_METADATA)
def get_metadata(season_id):
    if Data.Exists(season_id):
        return JSON.StringFromObject(Data.LoadObject(season_id))
    else:
        Log.Error('No data found for season_id %s' % season_id)
        raise Ex.MediaNotAvailable


######################################################################################
# Seasonvar API
######################################################################################

def perform_api_request(**kwargs):
    if api_key():
        key = Prefs['api_key']
        data = {
            'key': key
        }

        if kwargs:
            for key, value in kwargs.iteritems():
                data[key] = value

        response = JSON.ObjectFromString(
            HTTP.Request(
                url=COMMON.API_URL,
                values=data
            ).content
        )
        return response
    else:
        raise Ex.MediaNotAuthorized


def search(query):
    result = perform_api_request(
        command='search',
        query=query
    )

    return result


def get_latest(day_count=1, seasonInfo=True):
    result = perform_api_request(
        command='getUpdateList',
        day_count=day_count,
        seasonInfo=seasonInfo
    )

    return result


def get_season_by_id(season_id):
    result = perform_api_request(
        command='getSeason',
        season_id=season_id
    )

    return result


######################################################################################
# Formatting
######################################################################################
def form_playlist_by_translate(season, external=True):
    data = dict()
    season_data = get_season_by_id(season) if external else season
    for item in season_data.get('playlist'):
        if 'perevod' in item.keys():
            if item['perevod'] in data.keys():
                data[item['perevod']].append(item)
            else:
                data[item['perevod']] = [item]
        else:
            if 'no_translate' in data.keys():
                data['no_translate'].append(item)
            else:
                data['no_translate'] = [item]

    return data


def get_season_id(season_item):
    if isinstance(season_item['id'], tuple):
        return str(season_item['id'][0])
    else:
        return str(season_item['id'])


def format_season_display_title(season_data):
    if 'season' in season_data.keys():
        if isinstance(season_data['season'], tuple) or isinstance(season_data['season'], list):
            season_number = season_data['season'][0]
        else:
            season_number = season_data['season']
    else:
        season_number = 1
    show_name = season_data['name']

    Log.Debug('Season_id %s and season_number %s' % (season_data['id'], season_number))

    title = u'%s - %s %s' % (show_name, season_number, u'сезон')

    if 'message' in season_data.keys():
        title += u' %s' % season_data['message']

    if 'create_time'in season_data.keys():
        changed = Datetime.FromTimestamp(float(season_data['create_time'])).strftime('%d-%m-%Y')
        title += u' %s' % changed

    return title


def average_rating(ratings):
    result = 0.0

    if ratings:
        for rater in ratings.iterkeys():
            ratio = float(ratings.get(rater).get('ratio'))
            result += ratio

        result = result / len(list(ratings.iterkeys()))

    return result


######################################################################################
# Checks and error messages
######################################################################################
def api_key():
    return Prefs['api_key']


def api_key_missing():
    return MessageContainer(
        'API key error',
        'Missing API key in settings'
    )

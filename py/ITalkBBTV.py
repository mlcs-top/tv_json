# -*- coding: utf-8 -*-
# by @Qist
"""
ITalkBB TV - 海外华人影视
"""
import re
import json
import requests
from datetime import datetime
from base.spider import Spider

try:
    import js2py
    HAS_JS2PY = True
except ImportError:
    HAS_JS2PY = False


class Spider(Spider):
    def getName(self):
        return 'ITalkBB TV'

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def __init__(self):
        self.name = 'ITalkBB TV'
        self.host = 'https://www.italkbbtv.com'
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
            'Referer': 'https://www.italkbbtv.com/'
        }
        self.timeout = 20

        self.class_names = '电视剧&直播频道&短剧&综艺&电影&动画'.split('&')
        self.class_urls = 'drama/62c670dc1dca2d424404499c&live/62ac4e2e4beefe535864769d&shorts/66b1d25cf2dde82c215f9b59&variety/62ce7417c7daaa4a5d3fea14&movie/62ac4ef36e0b5a13ed291544&cartoon/62ac4e6e4beefe53586478ca'.split('&')

        self.key_map = {
            'drama': 'dramaSeriesLists',
            'movie': 'movieSeriesLists',
            'variety': 'varietySeriesLists',
            'cartoon': 'cartoonSeriesLists',
            'shorts': 'shortsSeriesLists'
        }

    def get_nuxt_data(self, html):
        if not html:
            return None
        m = re.search(r'window\.__NUXT__=([\s\S]*?);</script>', html)
        if not m:
            return None
        js_expr = m.group(1)
        try:
            result = js2py.eval_js(js_expr)
            return result.to_dict()
        except Exception as e:
            print(f"get_nuxt_data error: {e}")
        return None

    def pick_pic(self, obj):
        if not obj:
            return ''
        images = obj.get('images', {}) or {}
        poster_list = images.get('poster', []) or []
        landscape_list = images.get('landscape', []) or []
        poster = poster_list[0] if poster_list else ''
        landscape = landscape_list[0] if landscape_list else ''
        return poster or landscape or obj.get('imgUrl', '')

    def join_stars(self, stars):
        if not isinstance(stars, list):
            return ''
        return '/'.join([s.get('name', '') for s in stars if s.get('name')])

    def make_vod_from_series(self, series, fallback_name=''):
        if not series:
            return None
        root_id = series.get('root_id', '')
        series_id = series.get('id', '') or series.get('series_id', '')
        route = 'shortsPlay' if root_id == '66b1d25cf2dde82c215f9b59' else 'play'
        type_name = series.get('rootName', '') or series.get('categoryName', '')
        remark = (series.get('latest_episode_name', '') or
                  series.get('latest_episode_shortname', '') or
                  ('更新至' + str(series.get('episode_count', ''))) if series.get('episode_count') else '')
        released_at = series.get('released_at')
        vod_year = ''
        if released_at:
            try:
                vod_year = str(datetime.fromtimestamp(released_at).year)
            except:
                pass
        stars = series.get('stars', {}) or {}
        return {
            'vod_id': route + '$' + series_id,
            'vod_name': series.get('name', '') or fallback_name,
            'vod_pic': self.pick_pic(series),
            'vod_remarks': remark,
            'vod_year': vod_year,
            'type_name': type_name,
            'vod_content': series.get('description', ''),
            'vod_actor': self.join_stars(stars.get('actor', []) or []),
            'vod_director': self.join_stars(stars.get('director', []) or [])
        }

    def make_vod_from_channel(self, ch):
        if not ch:
            return None
        return {
            'vod_id': 'live@' + (ch.get('id', '') or ''),
            'vod_name': ch.get('name', ''),
            'vod_pic': self.pick_pic(ch),
            'vod_remarks': ch.get('categoryName', '') or ch.get('rootName', ''),
            'vod_year': '',
            'type_name': ch.get('categoryName', ''),
            'vod_content': '',
            'vod_actor': '',
            'vod_director': ''
        }

    def make_vod_from_card(self, card):
        if not card:
            return None
        series = card.get('series') or card.get('target') or card
        fallback = card.get('name', '') or card.get('title', '')
        vod = self.make_vod_from_series(series, fallback)
        if not vod:
            return None
        if not vod['vod_name']:
            vod['vod_name'] = fallback
        if not vod['vod_pic']:
            vod['vod_pic'] = (self.pick_pic(card) or
                              ((card.get('image', {}) or {}).get('poster', '')) or
                              ((card.get('image', {}) or {}).get('landscape', '')))
        if not vod['vod_remarks']:
            vod['vod_remarks'] = card.get('description', '')
        return vod

    def unique_by_id(self, vod_list):
        seen = {}
        result = []
        for v in vod_list:
            vid = v.get('vod_id', '') if v else ''
            if vid and vid not in seen:
                seen[vid] = 1
                result.append(v)
        return result

    def homeContent(self, filter):
        result = {'class': [], 'list': []}
        for name, cid in zip(self.class_names, self.class_urls):
            result['class'].append({'type_name': name, 'type_id': cid})

        url = f"{self.host}/drama/62c670dc1dca2d424404499c"
        html = self.fetch(url)
        nuxt = self.get_nuxt_data(html)
        if nuxt:
            try:
                store = nuxt.get('state', {}).get('pageList', {}).get('dramaSeriesLists', {})
                data = store.get('62c670dc1dca2d424404499c', {})
                series_list = data.get('series', [])
                vods = []
                for s in series_list:
                    v = self.make_vod_from_series(s)
                    if v:
                        vods.append(v)
                result['list'] = self.unique_by_id(vods)
            except Exception as e:
                print(f"homeContent parse error: {e}")
        return result

    def homeVideoContent(self):
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': int(pg), 'pagecount': 999, 'limit': 24, 'total': 999999}
        parts = tid.split('/')
        alias = parts[0]
        cid = parts[1] if len(parts) > 1 else ''

        # 直播频道特殊处理
        if alias == 'live':
            return self._live_category(tid, pg)

        url = f"{self.host}/{tid}"
        if int(pg) > 1:
            url += f"?page={pg}"
        html = self.fetch(url)
        nuxt = self.get_nuxt_data(html)
        if nuxt:
            try:
                store = nuxt.get('state', {}).get('pageList', {}).get(self.key_map.get(alias, ''), {})
                data = store.get(cid, {})
                series_list = data.get('series', [])
                vods = []
                for s in series_list:
                    v = self.make_vod_from_series(s)
                    if v:
                        vods.append(v)
                result['list'] = self.unique_by_id(vods)
            except Exception as e:
                print(f"categoryContent parse error: {e}")
        return result

    def _live_category(self, tid, pg):
        result = {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 100, 'total': 0}
        url = f"{self.host}/{tid}"
        html = self.fetch(url)
        nuxt = self.get_nuxt_data(html)
        if nuxt:
            try:
                channels = nuxt.get('state', {}).get('pageList', {}).get('liveChannelsList', []) or []
                vods = []
                for ch in channels:
                    v = self.make_vod_from_channel(ch)
                    if v:
                        vods.append(v)
                result['list'] = vods
                result['total'] = len(vods)
            except Exception as e:
                print(f"_live_category parse error: {e}")
        return result

    def detailContent(self, ids):
        if not ids or not ids[0]:
            return {'list': []}
        vid = ids[0]

        # 直播频道
        if vid.startswith('live@'):
            ch_id = vid.replace('live@', '')
            return self._live_detail(ch_id)

        parts = vid.split('$')
        route = parts[0] if len(parts) > 1 else 'play'
        sid = parts[1] if len(parts) > 1 else vid
        url = f"{self.host}/{route}/{sid}"
        html = self.fetch(url)
        nuxt = self.get_nuxt_data(html)
        if not nuxt:
            return {'list': []}
        try:
            play = nuxt.get('state', {}).get('play', {})
            info = play.get('SeriesInfo', {})
            eps = play.get('EpisodeList', [])
            vod = self.make_vod_from_series(info) or {'vod_id': vid}
            tabs = 'ITalkBB短剧' if route == 'shortsPlay' else 'ITalkBB'
            play_urls = []
            for ep in eps:
                name = ep.get('shortname', '') or ep.get('name', '')
                ep_id = ep.get('id', '')
                play_urls.append(f"{name}${route}@{sid}@{ep_id}")
            vod['vod_id'] = vid
            vod['vod_name'] = info.get('name', '') or vod.get('vod_name', '')
            vod['vod_pic'] = self.pick_pic(info) or vod.get('vod_pic', '')
            vod['type_name'] = info.get('rootName', '') or info.get('categoryName', '') or vod.get('type_name', '')
            vod['vod_content'] = info.get('description', '') or vod.get('vod_content', '')
            stars = info.get('stars', {}) or {}
            vod['vod_actor'] = self.join_stars(stars.get('actor', []) or [])
            vod['vod_director'] = self.join_stars(stars.get('director', []) or [])
            vod['vod_remarks'] = (info.get('latest_episode_name', '') or
                                  info.get('latest_episode_shortname', '') or
                                  vod.get('vod_remarks', ''))
            vod['vod_play_from'] = tabs
            vod['vod_play_url'] = '#'.join(play_urls)
            return {'list': [vod]}
        except Exception as e:
            print(f"detailContent parse error: {e}")
            return {'list': []}

    def _live_detail(self, ch_id):
        # 直播频道直接返回播放地址
        return {
            'list': [{
                'vod_id': 'live@' + ch_id,
                'vod_name': ch_id,
                'vod_play_from': 'ITalkBB直播',
                'vod_play_url': f'直播${ch_id}'
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/?keyword={key}"
        html = self.fetch(url)
        nuxt = self.get_nuxt_data(html)
        vod_list = []
        if nuxt:
            try:
                data = nuxt.get('data', [{}])[0]
                banners = data.get('bannerData', []) or []
                groups = data.get('serverGroupDataList', []) or []
                for card in banners:
                    v = self.make_vod_from_card(card)
                    if v:
                        vod_list.append(v)
                for g in groups:
                    for card in (g.get('list', []) or []):
                        v = self.make_vod_from_card(card)
                        if v:
                            vod_list.append(v)
            except Exception as e:
                print(f"searchContent parse error: {e}")
        filtered = []
        for v in vod_list:
            if not v or not v.get('vod_name'):
                continue
            text = ' '.join([v.get('vod_name', ''), v.get('vod_remarks', ''),
                             v.get('vod_content', ''), v.get('type_name', '')])
            if key in text:
                filtered.append(v)
        return {'list': self.unique_by_id(filtered)}

    def playerContent(self, flag, id, vipFlags):
        # 直播频道
        if id.startswith('live@'):
            ch_id = id.replace('live@', '')
            return {
                'parse': 0,
                'url': f'{self.host}/live/{ch_id}',
                'header': self.header,
                'playUrl': ''
            }
        parts = id.split('@')
        route = parts[0] if len(parts) > 1 else 'play'
        sid = parts[1] if len(parts) > 1 else ''
        eid = parts[2] if len(parts) > 2 else ''
        url = f"{self.host}/{route}/{sid}"
        if eid:
            url += f"?ep={eid}"
        return {
            'parse': 1,
            'url': url,
            'header': self.header,
            'playUrl': ''
        }

    def fetch(self, url):
        try:
            resp = requests.get(url, headers=self.header, timeout=self.timeout)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception as e:
            print(f"fetch error: {e}")
            return None

    def localProxy(self, param):
        return None

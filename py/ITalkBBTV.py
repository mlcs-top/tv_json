# -*- coding: utf-8 -*-
# by @Qist
"""
ITalkBB TV - 海外华人影视
"""
import re
import requests
from base.spider import Spider


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

    def parse_list_page(self, html):
        if not html:
            return []
        cards = re.findall(r'<a[^>]*href="(/(?:play|shortsPlay)/[a-f0-9]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        vods = []
        seen = set()
        for href, content in cards:
            sid = href.split('/')[-1]
            if sid in seen:
                continue
            seen.add(sid)
            name = ''
            title_match = re.search(r'title="([^"]+)"', content)
            if title_match:
                name = title_match.group(1).strip()
            if not name:
                info_match = re.search(r'info-title[^>]*>([^<]+)', content)
                if info_match:
                    name = info_match.group(1).strip()
            if not name:
                alt_match = re.search(r'alt="[^"]*[《]([^》]+)[》]', content)
                if alt_match:
                    name = alt_match.group(1).strip()
            img_match = re.search(r'<img[^>]*src="([^"]+)"', content)
            pic = img_match.group(1) if img_match else ''
            remarks = ''
            ep_match = re.search(r'(全\d+集|更新至\d+集)', content)
            if ep_match:
                remarks = ep_match.group(1)
            if name:
                route = 'shortsPlay' if '/shortsPlay/' in href else 'play'
                vods.append({
                    'vod_id': route + '$' + sid,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': remarks
                })
        return vods

    def parse_live_page(self, html):
        if not html:
            return []
        m = re.search(r'window\.__NUXT__=([\s\S]*?);</script>', html)
        if not m:
            return []
        js = m.group(1)
        channels = re.findall(r'\{[^{}]*id:"([a-f0-9]+)"[^{}]*name:"([^"]+)"', js)
        vods = []
        seen = set()
        for ch_id, name in channels:
            if ch_id in seen:
                continue
            seen.add(ch_id)
            vods.append({
                'vod_id': 'live@' + ch_id + '@' + name,
                'vod_name': name,
                'vod_pic': '',
                'vod_remarks': '直播'
            })
        return vods

    def _get_live_name(self, ch_id):
        """从直播页获取频道名称"""
        html = self.fetch(self.host + '/live/62ac4e2e4beefe535864769d')
        if not html:
            return ch_id
        m = re.search(r'window\.__NUXT__=([\s\S]*?);</script>', html)
        if not m:
            return ch_id
        js = m.group(1)
        match = re.search(r'\{[^{}]*id:"' + ch_id + r'"[^{}]*name:"([^"]+)"', js)
        return match.group(1) if match else ch_id

    def homeContent(self, filter):
        result = {'class': [], 'list': []}
        for name, cid in zip(self.class_names, self.class_urls):
            result['class'].append({'type_name': name, 'type_id': cid})
        html = self.fetch(self.host + '/drama/62c670dc1dca2d424404499c')
        result['list'] = self.parse_list_page(html)
        return result

    def homeVideoContent(self):
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': int(pg), 'pagecount': 999, 'limit': 24, 'total': 999999}
        alias = tid.split('/')[0]
        url = self.host + '/' + tid
        if int(pg) > 1:
            url += '?page=' + str(pg)
        html = self.fetch(url)
        if alias == 'live':
            result['list'] = self.parse_live_page(html)
            result['total'] = len(result['list'])
            result['pagecount'] = 1
        else:
            result['list'] = self.parse_list_page(html)
        return result

    def detailContent(self, ids):
        if not ids or not ids[0]:
            return {'list': []}
        vid = ids[0]

        # 直播频道: live@ch_id 或 live@ch_id@name
        if vid.startswith('live@'):
            parts = vid.split('@', 2)
            ch_id = parts[1] if len(parts) > 1 else ''
            ch_name = parts[2] if len(parts) > 2 else self._get_live_name(ch_id)
            return {'list': [{
                'vod_id': vid,
                'vod_name': ch_name,
                'vod_play_from': 'ITalkBB直播',
                'vod_play_url': '直播$' + ch_id
            }]}

        parts = vid.split('$')
        route = parts[0] if len(parts) > 1 else 'play'
        sid = parts[1] if len(parts) > 1 else vid
        html = self.fetch(self.host + '/' + route + '/' + sid)
        if not html:
            return {'list': []}

        # 从<title>提取名称
        name = ''
        title_match = re.search(r'<title>([^<|｜]+)', html)
        if title_match:
            name = title_match.group(1).strip()

        m = re.search(r'window\.__NUXT__=([\s\S]*?);</script>', html)
        if not m:
            return {'list': [{'vod_id': vid, 'vod_name': name}]}

        js = m.group(1)

        # 提取SeriesInfo (用花括号匹配)
        desc = ''
        pic = ''
        si_start = js.find('SeriesInfo:{')
        if si_start >= 0:
            depth = 0
            i = si_start + len('SeriesInfo:')
            while i < len(js):
                if js[i] == '{': depth += 1
                elif js[i] == '}':
                    depth -= 1
                    if depth == 0: break
                i += 1
            info = js[si_start:i+1]
            dm = re.search(r'description:"([^"]*)"', info)
            if dm: desc = dm.group(1)
            pm = re.search(r'poster:\["([^"]*)"', info)
            if pm: pic = pm.group(1).replace('\\u002F', '/').replace('\\u002f', '/')
            # name可能是变量引用，只有当是字符串时才用
            nm = re.search(r',name:"([^"]*)"', info)
            if nm and nm.group(1):
                name = nm.group(1)

        actor = '/'.join(re.findall(r'actor:\[\{[^}]*name:"([^"]+)"', js)[:5])
        director = '/'.join(re.findall(r'director:\[\{[^}]*name:"([^"]+)"', js))

        # 提取EpisodeList
        eps = []
        ep_start = js.find('EpisodeList:[')
        if ep_start >= 0:
            depth = 0
            i = ep_start + len('EpisodeList:')
            while i < len(js):
                if js[i] == '[': depth += 1
                elif js[i] == ']':
                    depth -= 1
                    if depth == 0: break
                i += 1
            ep_section = js[ep_start:i+1]
            eps = re.findall(r'id:"([a-f0-9]{24})".*?name:"([^"]*?)".*?shortname:"([^"]*?)"', ep_section)
            # 如果没匹配到shortname，尝试只匹配id和name
            if not eps:
                eps = re.findall(r'id:"([a-f0-9]{24})".*?name:"([^"]*)"', ep_section)
                eps = [(eid, nm, '') for eid, nm in eps]

        tabs = 'ITalkBB短剧' if route == 'shortsPlay' else 'ITalkBB'
        play_urls = []
        for ep_id, ep_name, ep_short in eps:
            display = ep_short or ep_name or ep_id[-4:]
            play_urls.append(display + '$' + route + '@' + sid + '@' + ep_id)

        # 电影如果没有剧集，构造单集播放
        if not play_urls:
            play_urls.append('播放$' + route + '@' + sid + '@')

        return {'list': [{
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': '',
            'vod_year': '',
            'type_name': '',
            'vod_content': desc,
            'vod_actor': actor,
            'vod_director': director,
            'vod_play_from': tabs,
            'vod_play_url': '#'.join(play_urls)
        }]}

    def searchContent(self, key, quick, pg="1"):
        html = self.fetch(self.host + '/?keyword=' + key)
        vods = self.parse_list_page(html)
        filtered = [v for v in vods if key in (v.get('vod_name', '') + v.get('vod_remarks', ''))]
        return {'list': filtered}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith('live@'):
            parts = id.split('@', 2)
            ch_id = parts[1] if len(parts) > 1 else ''
            return {'parse': 1, 'url': self.host + '/live/' + ch_id,
                    'header': self.header, 'playUrl': ''}
        parts = id.split('@')
        route = parts[0] if len(parts) > 1 else 'play'
        sid = parts[1] if len(parts) > 1 else ''
        eid = parts[2] if len(parts) > 2 else ''
        url = self.host + '/' + route + '/' + sid
        if eid:
            url += '?ep=' + eid
        return {'parse': 1, 'url': url, 'header': self.header, 'playUrl': ''}

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

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
        """从列表页HTML提取vod列表"""
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
            # 名称: span class="info-title" 或 img alt中的《》
            name = ''
            name_match = re.search(r'info-title[^>]*>([^<]+)', content)
            if name_match:
                name = name_match.group(1).strip()
            if not name:
                alt_match = re.search(r'alt="[^"]*[《]([^》]+)[》]', content)
                if alt_match:
                    name = alt_match.group(1).strip()
            # 图片
            img_match = re.search(r'<img[^>]*src="([^"]+)"', content)
            pic = img_match.group(1) if img_match else ''
            # 备注 (集数)
            remarks = ''
            ep_match = re.search(r'(全\d+集|更新至\d+集)', content)
            if ep_match:
                remarks = ep_match.group(1)
            if name:
                vods.append({
                    'vod_id': 'play$' + sid,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': remarks
                })
        return vods

    def parse_live_page(self, html):
        """从直播页HTML提取频道列表"""
        if not html:
            return []
        m = re.search(r'window\.__NUXT__=([\s\S]*?);</script>', html)
        if not m:
            return []
        js = m.group(1)
        # 提取直播频道: id:"xxx" ... name:"CCTV-1"
        channels = re.findall(r'\{[^{}]*id:"([a-f0-9]+)"[^{}]*name:"([^"]+)"', js)
        vods = []
        seen = set()
        for ch_id, name in channels:
            if ch_id in seen:
                continue
            seen.add(ch_id)
            if any(kw in name for kw in ['CCTV', '卫视', '频道', '新闻', '综合', '影视', '体育', '少儿', '科教', '农业']):
                vods.append({
                    'vod_id': 'live@' + ch_id,
                    'vod_name': name,
                    'vod_pic': '',
                    'vod_remarks': '直播'
                })
        return vods

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
        parts = tid.split('/')
        alias = parts[0]

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

        # 直播频道
        if vid.startswith('live@'):
            return {'list': [{'vod_id': vid, 'vod_name': vid.replace('live@', ''),
                              'vod_play_from': 'ITalkBB直播', 'vod_play_url': '直播$' + vid.replace('live@', '')}]}

        parts = vid.split('$')
        route = parts[0] if len(parts) > 1 else 'play'
        sid = parts[1] if len(parts) > 1 else vid
        url = self.host + '/' + route + '/' + sid
        html = self.fetch(url)
        if not html:
            return {'list': []}

        # 从详情页提取信息
        m = re.search(r'window\.__NUXT__=([\s\S]*?);</script>', html)
        if not m:
            return {'list': []}
        js = m.group(1)

        # 提取系列名称
        name = ''
        name_match = re.search(r'SeriesInfo:\{[^}]*name:"([^"]+)"', js)
        if name_match:
            name = name_match.group(1)

        # 提取描述
        desc = ''
        desc_match = re.search(r'SeriesInfo:\{[^}]*description:"([^"]*)"', js)
        if desc_match:
            desc = desc_match.group(1)

        # 提取图片
        pic = ''
        pic_match = re.search(r'SeriesInfo:\{[^}]*poster:\["([^"]+)"', js)
        if pic_match:
            pic = pic_match.group(1).replace('\\u002F', '/')

        # 提取演员
        actor = ''
        actor_matches = re.findall(r'actor:\[\{[^}]*name:"([^"]+)"', js)
        if actor_matches:
            actor = '/'.join(actor_matches[:5])

        # 提取导演
        director = ''
        dir_match = re.findall(r'director:\[\{[^}]*name:"([^"]+)"', js)
        if dir_match:
            director = '/'.join(dir_match)

        # 提取剧集列表
        eps = re.findall(r'\{[^{}]*id:"([a-f0-9]+)"[^{}]*name:"([^"]*)"[^{}]*shortname:"([^"]*)"', js)
        if not eps:
            eps = re.findall(r'\{[^{}]*shortname:"([^"]*)"[^{}]*id:"([a-f0-9]+)"', js)
            eps = [(eid, sn, sn) for sn, eid in eps]
        if not eps:
            # 更宽松的匹配
            eps = re.findall(r'id:"([a-f0-9]{24})"[^}]*name:"([^"]*)"', js)

        tabs = 'ITalkBB短剧' if route == 'shortsPlay' else 'ITalkBB'
        play_urls = []
        for ep_id, ep_name in eps[:50]:
            display = ep_name or ep_id[-4:]
            play_urls.append(display + '$' + route + '@' + sid + '@' + ep_id)

        vod = {
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
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = self.host + '/?keyword=' + key
        html = self.fetch(url)
        vods = self.parse_list_page(html)
        # 客户端过滤
        filtered = [v for v in vods if key in (v.get('vod_name', '') + v.get('vod_remarks', ''))]
        return {'list': filtered}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith('live@'):
            return {'parse': 0, 'url': self.host + '/live/' + id.replace('live@', ''),
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

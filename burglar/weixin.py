# coding: utf-8

import re
import json
import datetime
import requests
from lxml import etree, html
from .utils import read_cache, write_cache, get_cache_file, logger

SITE_BASE = 'http://weixin.sogou.com/gzh?openid='
INDEX_BASE = 'http://weixin.sogou.com/gzhjs?openid='
XML_PATTERN = re.compile(r'<\?xml.*?>')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Burglar)'}


def parse_item(key, url, cache=None):
    logger.debug('Parse start - %s' % url)
    if cache and key in cache:
        return cache[key]

    resp = requests.get(url, headers=HEADERS)
    text = resp.text.encode('utf-8')
    el = html.fromstring(text)
    el_content = el.get_element_by_id('js_content')

    for img in el_content.xpath('*//img'):
        src = img.get('data-src')
        img.set('src', src)
        img.attrib.pop('data-src', None)
        img.attrib.pop('data-w', None)
        img.attrib.pop('data-s', None)
        img.attrib.pop('data-ratio', None)

    # clean style
    for tag in el_content.xpath('//*[@style]'):
        tag.attrib.pop('class', None)
        tag.attrib.pop('style', None)

    body = html.tostring(el_content, encoding='unicode')
    el_title = el.get_element_by_id('activity-name')
    el_date = el.get_element_by_id('post-date')

    title = el_title.text
    published = el_date.text
    published = '%sT00:00:00Z' % published.strip()

    now = datetime.datetime.utcnow()
    now = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.debug('Parse end - %s' % url)
    return {
        'title': title,
        'url': url,
        'body': body,
        'published': published,
        'updated': now,
    }


def parse_xml(text):
    text = XML_PATTERN.sub('', text)
    text = text.encode('utf-8')
    el = etree.fromstring(text)
    el_id = el.find('item/*/docid')
    el_url = el.find('item/*/url')
    return el_id.text, el_url.text


def parse(title, openid, use_cache=True):
    cache_file = get_cache_file(openid + '.json')
    cache = read_cache(cache_file, use_cache)

    index_url = INDEX_BASE + openid
    resp = requests.get(index_url, headers=HEADERS)
    text = resp.text
    start = text.find('(') + 1
    end = text.rfind(')')
    content = text[start:end]
    data = json.loads(content)
    keys = []
    entries = []
    for item in data['items']:
        key, url = parse_xml(item)
        keys.append(key)
        entry = parse_item(key, url, cache)
        cache[key] = entry
        entries.append(entry)

    write_cache(cache_file, cache, keys)
    url = SITE_BASE + openid
    return {'title': title, 'url': url, 'entries': entries}

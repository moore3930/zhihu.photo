#!/usr/bin/env python
# encoding=utf-8

import os
import re

from pymongo import MongoClient
from xtls.basecrawler import BaseCrawler
from xtls.codehelper import no_exception
from xtls.logger import get_logger
from xtls.timeparser import now
from xtls.util import BeautifulSoup
from xtls.util import sha1

from config import *

logger = get_logger(__file__)
MONGO = MongoClient(MONGO_HOST, MONGO_PORT)
CATEGORY_PATTERN = re.compile(ur'\[(.+?)\](.+?)\[(\d+)[P|p]\]')
HOST = 'http://cl.xlzd.me/'


def save(content, filename):
    save_path = os.path.join(FILE_PATH, filename[:4])
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    file_path = os.path.join(save_path, filename)
    with open(file_path, 'wb') as fp:
        fp.write(content)


class ClCrawler(BaseCrawler):
    def __init__(self, start=1, end=1):
        super(ClCrawler, self).__init__(start=start, end=end)

    @no_exception(on_exception=None)
    def find_imgs(self, uri):
        url = HOST + uri
        soup = BeautifulSoup(self.get(url))
        img_list = []
        for input in soup.find_all('input', type="image"):
            img_list.append({
                'url': input['src'],
                'hash': '',
            })
        return img_list

    @no_exception(on_exception=None)
    def parse_cat_tr(self, tr):
        tds = tr.find_all('td')
        if len(tds) != 5:
            return None
        title = tds[1].getText().strip().replace('\n', '').replace('\t', '')
        title_sp = CATEGORY_PATTERN.findall(title)
        if not title_sp:
            return None
        data = {
            '_id': sha1(title),
            'category': title_sp[0][0],
            'title': title_sp[0][1],
            'img_count': int(title_sp[0][2]),
            'raw_path': tds[1].find('a')['href'],
            'pub_date': tds[2].find('div', class_='f10').getText()
        }
        imgs = self.find_imgs(data['raw_path'])
        if not imgs:
            return None
        data['images'] = imgs
        return data

    @classmethod
    def save(cls, data):
        data['update'] = now()
        MONGO[DB][T66Y_COLL].update_one(
            {'_id': data['_id']},
            {'$set': data},
            upsert=True
        )

    def parse_catalog(self, soup):
        for idx, tr in enumerate(soup.find_all('tr', class_='tr3 t_one'), 1):
            print idx,
            data = self.parse_cat_tr(tr)
            if not data:
                continue
            self.save(data)
            # print json.dumps(data, ensure_ascii=False, sort_keys=True, indent=4)
            # break

    def run(self):
        for page in xrange(self.end, self.start - 1, -1):
            html = self.get('http://www.t66y.com/thread0806.php?fid=8&search=&page=' + str(page))
            soup = BeautifulSoup(html)
            self.parse_catalog(soup)


def main():
    crawler = ClCrawler()
    crawler.run()


if __name__ == '__main__':
    main()
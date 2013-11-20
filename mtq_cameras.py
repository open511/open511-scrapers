#coding: utf-8
"""
Scrapes traffic cameras from Quebec511 into Open511
"""

import logging
import re

from django.contrib.gis.geos import Point

from lxml import etree
from lxml.builder import E
import requests

from open511.utils.serialization import geom_to_xml_element, get_base_open511_element, XML_LANG

logger = logging.getLogger(__name__)

ALL_QUEBEC_BOUNDS = {
    'xMin': '-79.9',
    'yMin': '44.4',
    'xMax': '-53.4',
    'yMax': '62.5'
}

BASE_LIST_URL = 'http://carte.quebec511.gouv.qc.ca/fr/Element.ashx'
BASE_DETAIL_URL = 'http://carte.quebec511.gouv.qc.ca/fr/Fenetres/FenetreCamera.aspx?id='

JURISDICTION_ID = 'mtq.scrapers.open511.org'

def get_list_of_cameras(bounds=ALL_QUEBEC_BOUNDS, lang='fr'):
    params = {
        'action': 'Camera',
        'lang': lang
    }
    params.update(bounds)

    resp = requests.get(BASE_LIST_URL, params=params)
    return resp.json()

def get_english_names(bounds=ALL_QUEBEC_BOUNDS):
    return dict(
        (r['id'], r['info']) for r in get_list_of_cameras(bounds, lang='en')
    )

def get_image_url(camera_id):
    resp = requests.get(BASE_DETAIL_URL + unicode(camera_id))
    return re.search(r'http://www\.quebec511\.info/images/fr/cameras/[^/]+/cam/\d+.jpg', resp.content).group(0)


def main():

    logging.basicConfig()

    base = get_base_open511_element(lang='fr')
    cameras = E.cameras()
    base.append(cameras)

    english_names = get_english_names()

    for camera_info in get_list_of_cameras():
        camera = E.camera(
            E.id(JURISDICTION_ID + '/' + unicode(camera_info['id'])),
            E.name(camera_info['info'])
        )
        if english_names[camera_info['id']]:
            ename = E.name(english_names[camera_info['id']])
            ename.set(XML_LANG, 'en')
            camera.append(ename)

        camera.append(
            E.geography(
                geom_to_xml_element(
                    Point(float(camera_info['lng']), float(camera_info['lat']), srid=4326)
                )
            )
        )

        try:
            camera.append(
                E.media_files(
                    E.link(rel="related", href=get_image_url(camera_info['id']), type="image/jpeg")
                )
            )
        except Exception as e:
            logger.exception("Couldn't fetch image for camera #%s" % camera_info['id'])
            continue
        cameras.append(camera)

    print etree.tostring(base, pretty_print=True)


if __name__ == '__main__':
    main()

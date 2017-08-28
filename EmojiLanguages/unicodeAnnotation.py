# coding=utf-8

import requests
from xml.etree import ElementTree
from collections import defaultdict

EMOJI_DATA_URL = 'http://unicode.org/Public/emoji/5.0'

ANNOTATION_URL = 'http://unicode.org/repos/cldr/trunk/common//annotations/'
ANNOTATION_DERIVED_URL = 'http://unicode.org/repos/cldr/trunk/common/annotationsDerived/'

def processAnnotationFromUrl(language_code):
    annotation_dict = defaultdict(set)
    for base_url in [ANNOTATION_URL, ANNOTATION_DERIVED_URL]:
        url = base_url + '{}.xml'.format(language_code)
        print 'parsing {}'.format(url)
        #response = requests.get(url, stream=True)
        #response.raw.decode_content = True
        response = requests.get(url)
        root = ElementTree.fromstring(response.content)
        for annotation in root.iter('annotation'):
            emoji = annotation.attrib['cp'].encode('utf-8')
            annotation_entries = [a.strip() for a in annotation.text.split('|')]
            annotation_dict[emoji].update(annotation_entries)
    return annotation_dict

def processAnnotationFromFile(language_code):
    BASE_DIR = '/Users/fedja/Downloads/cldr-common-31.0.1/common/annotations/'
    file = BASE_DIR + '{}.xml'.format(language_code)
    tree = ElementTree.parse(file)
    root = tree.getroot()
    annotation_dict = defaultdict(set)
    for annotation in root.iter('annotation'):
        emoji = annotation.attrib['cp'].encode('utf-8')
        annotation_entries =  [a.strip() for a in annotation.text.split('|')]
        annotation_dict[emoji].update(annotation_entries)
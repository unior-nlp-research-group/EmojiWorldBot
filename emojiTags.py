# -*- coding: utf-8 -*-

import jsonUtil
import languages


EMOJI_TAGS_LANGUAGE = {} # language_code: EMOJI_INFO
EMOJI_TAGS_LANG_PATH = lambda lang_code: 'EmojiData/LangTags/emoji_tags_{}.json'.format(lang_code)

def getLanguageEmojiInfoDict(language_code):
    if not languages.langCodeInCLDR(language_code):
        return None
    dict = EMOJI_TAGS_LANGUAGE.get(language_code, None)
    if dict == None:
        filePath = EMOJI_TAGS_LANG_PATH(language_code)
        dict = jsonUtil.json_load_byteified_file(filePath)
        EMOJI_TAGS_LANGUAGE[language_code] = dict
    return dict

def getTagsForEmoji(emoji, language_code):
    dict = getLanguageEmojiInfoDict(language_code)
    if dict:
        return dict.get(emoji, [])
    return []

def getEmojisForTag(tag, language_code, wordOnly=True):
    dict = getLanguageEmojiInfoDict(language_code)
    if dict:
        if wordOnly:
            result = [e for e,tag_list in dict.items() if any(tag in t.lower().split() for t in tag_list)]
        else:
            result = [e for e, tag_list in dict.items() if any(tag in t.lower() for t in tag_list)]
        return result
    return []


##################
# BUILD FUNCTIONS
##################

ANNOTATION_URL = 'http://unicode.org/repos/cldr/trunk/common/annotations/'
ANNOTATION_DERIVED_URL = 'http://unicode.org/repos/cldr/trunk/common/annotationsDerived/'

def getEmojiLanguageTagsFromUrl(language_code):
    import emojiUtil
    import requests
    from xml.etree import ElementTree
    from collections import defaultdict
    annotation_dict = defaultdict(set)
    for base_url in [ANNOTATION_URL, ANNOTATION_DERIVED_URL]:
        url = base_url + '{}.xml'.format(language_code)
        print 'parsing {}'.format(url)
        response = requests.get(url)
        root = ElementTree.fromstring(response.content)
        for annotation in root.iter('annotation'):
            emoji = annotation.attrib['cp'].encode('utf-8')
            emoji = emojiUtil.checkIfEmojiAndGetNormalized(emoji)
            if emoji in emojiUtil.ALL_EMOJIS:
                annotation_entries = [a.strip() for a in annotation.text.encode('utf-8').split('|')]
                annotation_dict[emoji].update(annotation_entries)
    annotation_dict_list = {k:list(v) for k,v in annotation_dict.items()}
    return annotation_dict_list

########################################################
# TO RUN EVERY TIME UNICODE DATA ANNOTATION CHANGES
########################################################
def buildLanguageTagsFiles():
    from languages import LANG_STRUCTURE
    import json
    for iso_lang_code in LANG_STRUCTURE.keys():
        file_path = EMOJI_TAGS_LANG_PATH(iso_lang_code)
        with open(file_path, 'w') as f:
            CLDR_lang_code = LANG_STRUCTURE[iso_lang_code][languages.CLDR_CODE_HEADER]
            if CLDR_lang_code:
                print("iso_lang: {}  cldr_code: {}".format(iso_lang_code, CLDR_lang_code))
                d = getEmojiLanguageTagsFromUrl(CLDR_lang_code)
                json.dump(d, f, ensure_ascii=False, indent=4, sort_keys=True)
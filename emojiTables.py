# -*- coding: utf-8 -*-

import json
import os
from collections import defaultdict

import util

# ================================
# BUILDING DICTIONARIES FROM FILES
# ================================

EMOJI_TO_TEXT_DICTIONARIES = {}

for lang_file_json in os.listdir("EmojiLanguages"):
    if not lang_file_json.startswith("_"):
        with open("EmojiLanguages/"+lang_file_json) as f:
            EMOJI_TO_TEXT_DICTIONARIES[lang_file_json[:-5]] = {
                key.encode('utf-8'): [x.encode('utf-8') for x in set(value)]
                for key, value in json.load(f).iteritems()
                }

#with open("EmojiLanguages/_emojiDesc.json") as f:
#    EMOJI_DESCRIPTIONS = {
#        key.encode('utf-8'): value.encode('utf-8')
#        for key, value in json.load(f).iteritems()
#    }

#ALL_EMOJIS = EMOJI_DESCRIPTIONS.keys()

ALL_EMOJIS = EMOJI_TO_TEXT_DICTIONARIES['English'].keys()

ALL_EMOJIS_UNI = [e.decode('utf-8') for e in ALL_EMOJIS]

ENGLISH_EMOJI_TO_TEXT_DICTIONARY = EMOJI_TO_TEXT_DICTIONARIES["English"]

TEXT_TO_EMOJI_DICTIONARIES = {}

for lang, dict in EMOJI_TO_TEXT_DICTIONARIES.iteritems():
    lang_dictionary = defaultdict(lambda: [])
    for emoji, tags in dict.iteritems():
        for t in tags:
            t_norm = util.normalizeString(t)
            #t_norm = t.lower()
            lang_dictionary[t_norm].append(emoji) # adding the tag (could be multiple words)
            tagSplit = t_norm.split(' ')
            if len(tagSplit)>1:
                for word_tag in tagSplit:
                    lang_dictionary[word_tag].append(emoji) # adding each word in the tag
    TEXT_TO_EMOJI_DICTIONARIES[lang] = lang_dictionary



# =========================================
# BUILDING DICTIONARIES FROM KAMUSI SERVER
# =========================================


KAMUSI_SERVER = "http://lsir-kamusi.epfl.ch:3000"
KAMUSI_SERVER_LANGUAGES = KAMUSI_SERVER + "/emojibot/languages"
KAMUSI_SERVER_LANG_DICT = KAMUSI_SERVER + "/emojibot/getall/" # + *language name* (as in KAMUSI_SERVER_LANGUAGES)

"""
kamusi_languages_json = json.loads(urllib2.urlopen(KAMUSI_SERVER_LANGUAGES).read())
#logging.debug("Loaded languages from kamusi: " + ', '.join(kamusi_languages_json['languages']))
ALL_LANGUAGES = sorted(l.encode('utf-8') for l in kamusi_languages_json['languages'])
ALL_LANGUAGES_LOWERCASE = [normalizeString(l) for l in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS = ['/' + remove_accents_roman_chars(item) for item in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS_LOWERCASE = [normalizeString(l) for l in ALL_LANGUAGES_COMMANDS]
ALL_LANGUAGES_COMMANDS_AC = ['/' + remove_accents_roman_chars(item) for item in ALL_LANGUAGES if item[0] in char_range('A','C')]
ALL_LANGUAGES_COMMANDS_DJ = ['/' + remove_accents_roman_chars(item) for item in ALL_LANGUAGES if item[0] in char_range('D','J')]
ALL_LANGUAGES_COMMANDS_KP = ['/' + remove_accents_roman_chars(item) for item in ALL_LANGUAGES if item[0] in char_range('K','P')]
ALL_LANGUAGES_COMMANDS_RZ = ['/' + remove_accents_roman_chars(item) for item in ALL_LANGUAGES if item[0] in char_range('R','Z')]

EMOJI_TO_TEXT_DICTIONARIES = {}

for language in ALL_LANGUAGES:
    languaged_kamusi_json = json.loads(urllib2.urlopen(KAMUSI_SERVER_LANG_DICT + language).read())
    language_dic = {}
    for k,v in languaged_kamusi_json.iteritems():
        tags = list(set([x['term'].encode('utf-8') for x in v]))
        language_dic[k.encode('utf-8')] = tags
    EMOJI_TO_TEXT_DICTIONARIES[language] = language_dic

#with open("EmojiLanguages/_emojiDesc.json") as f:
#    EMOJI_DESCRIPTIONS = {
#        key.encode('utf-8'): value.encode('utf-8')
#        for key, value in json.load(f).iteritems()
#    }


ALL_EMOJIS = EMOJI_TO_TEXT_DICTIONARIES['English'].keys()

TEXT_TO_EMOJI_DICTIONARIES = {}

for lang, dict in EMOJI_TO_TEXT_DICTIONARIES.iteritems():
    lang_dictionary = defaultdict(lambda: [])
    for emoji, tags in dict.iteritems():
        for t in tags:
            t_norm = normalizeString(t)
            #t_norm = t.lower()
            lang_dictionary[t_norm].append(emoji) # adding the tag (could be multiple words)
            tagSplit = t_norm.split(' ')
            if len(tagSplit)>1:
                for word_tag in tagSplit:
                    lang_dictionary[word_tag].append(emoji) # adding each word in the tag
    TEXT_TO_EMOJI_DICTIONARIES[lang] = lang_dictionary
"""
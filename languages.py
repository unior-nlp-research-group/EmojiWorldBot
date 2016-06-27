# -*- coding: utf-8 -*-

"""
import sys
sys.path.append('/usr/local/google_appengine/')
sys.path.append('/usr/local/google_appengine/lib/yaml/lib/')
if 'google' in sys.modules:
    del sys.modules['google']
"""

import logging
import utility
from google.appengine.ext import ndb

import re
import urllib2

import urllib
import jsonUtil

import json
import csv

DEFAULT_LANGUAGE_CODE = 'eng'

LANG_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/" \
                       "1_6aHfioIMUXBklrVKO3VubuUHHgW4swuVeKsG_zqnes/" \
                       "export?format=tsv" \
                       "&gid=735383332"

# HEADERS = ["count", "bot_version", "lang_code", "lang_name", "alt_names", "roman_script", "has_diacritics", "user_ids"]


def createLanguageStructureFile():
    lang_json = getLanguageStructureFromUrl()
    with open("EmojiLanguages/_languages.json", 'w') as emojiFile:
        json.dump(lang_json, emojiFile, indent=4, ensure_ascii=False)


def getLanguageStructureFromFile():
    with open("EmojiLanguages/_languages.json") as f:
        return jsonUtil.json_load_byteified(f)

def getLanguageStructureFromUrl():
    languageStructure = {}
    try:
        spreadSheetTsv = urllib2.urlopen(LANG_SPREADSHEET_URL)
        spreadSheetReader = csv.reader(spreadSheetTsv, delimiter='\t')
        next(spreadSheetReader)  # skip first row
        for row in spreadSheetReader:
            lang_code = row[2].strip()
            if lang_code:
                langItem = {}
                langItem["lang_name"] = row[3].strip()
                langItem["alt_names"] = [x.strip().lower() for x in row[4].split(',')]
                langItem["roman_script"] = True if row[5].upper() == 'TRUE' else False
                langItem["has_diacritics"] = True if row[6].upper() == 'TRUE' else False
                langItem["user_ids"] = [int(x) for x in row[4].split(',') if utility.representsInt(x)]
                languageStructure[row[2]] = langItem
    except Exception, e:
        logging.debug("Problem retreiving language structure from url: " + str(e))
        return getLanguageStructureFromFile()
    return languageStructure


# ================================
# LANGUAGE STRUCTURE
# ================================

#"lang_code", "lang_name", "alt_names", "roman_script", "has_diacritics", "user_ids"

#LANG_STRUCTURE = getLanguageStructureFromFile()
LANG_STRUCTURE = getLanguageStructureFromUrl()


def getLanguageName(lang_code):
    return LANG_STRUCTURE[lang_code]['lang_name']

def getLanguageCodeByLanguageVariation(variationNameList):
    for key, value in LANG_STRUCTURE.iteritems():
        for name in variationNameList:
            if name in value['lang_name'] or name.lower() in value['alt_names']:
                return key
    return None

def isRomanScript(lang_code):
    return LANG_STRUCTURE[lang_code]['roman_script']

def hasDiacritics(lang_code):
    return LANG_STRUCTURE[lang_code]['has_diacritics']

# ================================
# Language list and commands list
# ================================


def makeLanguageCommand(lang_name):
    return '/' + re.sub('[() -]+', '_', utility.normalizeString(lang_name).title()).strip('_')

ALL_LANG_CODES = LANG_STRUCTURE.keys()
ALL_LANGUAGES = [x['lang_name'] for x in LANG_STRUCTURE.values()]

ALL_LANGUAGES_LOWERCASE = [l.lower() for l in ALL_LANGUAGES]

ALL_LANGUAGES_COMMANDS = [makeLanguageCommand(item) for item in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS_SORTED = sorted(ALL_LANGUAGES_COMMANDS)

ALL_LANGUAGES_COMMANDS_AC = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('A', 'C')]
ALL_LANGUAGES_COMMANDS_DJ = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('D', 'J')]
ALL_LANGUAGES_COMMANDS_KP = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('K', 'P')]
ALL_LANGUAGES_COMMANDS_RZ = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('R', 'Z')]


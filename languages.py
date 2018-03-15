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

import re
import urllib2

import jsonUtil

import json
import csv

DEFAULT_LANGUAGE_CODE = 'eng'

LANG_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/" \
                       "1_6aHfioIMUXBklrVKO3VubuUHHgW4swuVeKsG_zqnes/" \
                       "export?format=csv" \
                       "&gid=735383332"

# HEADERS = [
#   'Count', 'ISO Code', 'Language Name (eng)', 'Bot Version',
#   'Based on roman script (for upper case check)', 'lower case diacritics',
#   'CLDR Code', 'Contact Email', 'upper case diacritics',
#   'Has diacritics (only for roman script, for diacritic check)', 'Contact Name',
#   'Alternative Language Names (comma separated)', 'Telegram user id']

LANG_CODE_HEADER = 'ISO Code'
CLDR_CODE_HEADER = "CLDR Code"
LANG_NAME_HEADER = "Language Name (eng)"
ALT_NAMES_HEADER = 'Alternative Language Names (comma separated)'
ROMAN_SCRIPT_HEADER = 'Based on roman script (for upper case check)'
HAS_DIACRITICS_HEADER = 'Has diacritics (only for roman script, for diacritic check)'

def getLanguageStructureFromUrl():
    import utility
    spreadsheet_dict = utility.import_url_csv_to_dict_list(LANG_SPREADSHEET_URL)
    languageStructure = {}
    user_ids_header = 'Telegram user id'
    for dict in spreadsheet_dict:
        lang_code = dict.get(LANG_CODE_HEADER, None)
        if lang_code:
            langItem = {}
            langItem[CLDR_CODE_HEADER] = dict[CLDR_CODE_HEADER].strip()
            langItem[LANG_NAME_HEADER] = dict[LANG_NAME_HEADER].strip()
            langItem[ALT_NAMES_HEADER] = [x.strip().lower() for x in dict[ALT_NAMES_HEADER].split(',')]
            langItem[ROMAN_SCRIPT_HEADER] = True if dict[ROMAN_SCRIPT_HEADER].upper() == 'TRUE' else False
            langItem[HAS_DIACRITICS_HEADER] = True if dict[HAS_DIACRITICS_HEADER].upper() == 'TRUE' else False
            langItem[user_ids_header] = [int(x) for x in dict[user_ids_header].split(',') if utility.representsInt(x)]
            languageStructure[lang_code] = langItem
    return languageStructure

def createLanguageStructureFile():
    lang_json = getLanguageStructureFromUrl()
    with open("EmojiLanguages/_languages.json", 'w') as emojiFile:
        json.dump(lang_json, emojiFile, indent=4, ensure_ascii=False)

def getLanguageStructureFromFile():
    with open("EmojiLanguages/_languages.json") as f:
        return jsonUtil.json_load_byteified(f)


# ================================
# LANGUAGE STRUCTURE
# ================================

#"lang_code", "lang_name", "alt_names", "roman_script", "has_diacritics", "user_ids"

LANG_STRUCTURE = getLanguageStructureFromFile()
#LANG_STRUCTURE = getLanguageStructureFromUrl()

def getLanguageName(lang_code):
    return LANG_STRUCTURE[lang_code][LANG_NAME_HEADER]

def getLanguageCodeByLanguageVariation(variationNameList):
    for key, value in LANG_STRUCTURE.iteritems():
        for name in variationNameList:
            if name in value[LANG_NAME_HEADER] or name.lower() in value[ALT_NAMES_HEADER]:
                return key
    return None

def isRomanScript(lang_code):
    return LANG_STRUCTURE[lang_code][ROMAN_SCRIPT_HEADER]

def hasDiacritics(lang_code):
    return LANG_STRUCTURE[lang_code][HAS_DIACRITICS_HEADER]

def langCodeInCLDR(lang_code):
    return LANG_STRUCTURE[lang_code][CLDR_CODE_HEADER]!=''

# ================================
# Language list and commands list
# ================================

def makeLanguageCommand(lang_name):
    return '/' + re.sub('[() -]+', '_', utility.normalizeString(lang_name).title()).strip('_')

ALL_LANG_CODES = LANG_STRUCTURE.keys()

ALL_LANGUAGES = [x[LANG_NAME_HEADER] for x in LANG_STRUCTURE.values()]

ALL_LANGUAGES_LOWERCASE = [l.lower() for l in ALL_LANGUAGES]

ALL_LANGUAGES_COMMANDS = [makeLanguageCommand(item) for item in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS_SORTED = sorted(ALL_LANGUAGES_COMMANDS)

ALL_LANGUAGES_COMMANDS_AC = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('A', 'C')]
ALL_LANGUAGES_COMMANDS_DJ = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('D', 'J')]
ALL_LANGUAGES_COMMANDS_KP = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('K', 'P')]
ALL_LANGUAGES_COMMANDS_RZ = [item for item in ALL_LANGUAGES_COMMANDS_SORTED if item[1] in utility.char_range('R', 'Z')]


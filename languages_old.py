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

# ================================
# Language ndb module
# ================================

class Language(ndb.Model):
    # id = code
    name = ndb.StringProperty()
    alternative_names = ndb.StringProperty(repeated=True)

    def getLanguageName(self):
        return self.name.encode('utf-8')


def getLanguageName(lang_code):
    entry = Language.get_by_id(lang_code)
    if entry:
        return entry.name.encode('utf-8')
    return None

def getLanguageCodeByLanguageVariation(variationNameList):
    logging.debug("Variation list: " + str(variationNameList))
    variationNameList_uni = [x.title().decode('utf-8') for x in variationNameList]
    entry = Language.query(ndb.OR(
        Language.name.IN(variationNameList_uni),
        Language.alternative_names.IN(variationNameList_uni))
    ).get()
    if entry:
        return entry.key.id().encode('utf-8')
    return None

# ================================
# Script preparation
# ================================

KAMUSI_SERVER_LANGUAGES_URL = "http://lsir-kamusi.epfl.ch:3000/emojibot/languages"
#[ {"name":"Amharic","lang_code":"amh"}, {"name":"Arabic","lang_code":"ara"}, ... ]

def populateLanguageTable():
    response = urllib.urlopen(KAMUSI_SERVER_LANGUAGES_URL)
    list = jsonUtil.json_loads_byteified(response.read())
    toAdd = []
    for dict in list:
        l = Language(
            id=dict['lang_code'],
            name=dict['name'],
            alternative_names = []
        )
        toAdd.append(l)
    ndb.put_multi(toAdd)
    print "Successuffully added {0} languages".format(str(len(toAdd)))

def fetchLanguageCodes():
    codes = []
    entries = Language.query().fetch(keys_only=True)
    for e in entries:
        codes.append(e.id())
    return codes

def fetchLanguageNamesAndCodes():
    codes = []
    names = []
    entries = Language.query().fetch(projection=[Language.name])
    for e in entries:
        names.append(e.getLanguageName())
        codes.append(e.key.id())
    return codes, names


def addLanguageVariation(lang_code, variationName):
    variationName = variationName.title()
    entry = Language.get_by_id(lang_code)
    if entry:
        variationName_uni = variationName.decode('utf-8')
        if variationName_uni==entry.name or variationName_uni in entry.alternative_names:
            return False, '{0} is already a valid language name for {1}'.format(
                variationName, entry.getLanguageName())
        entry.alternative_names.append(variationName)
        entry.put()
        return True, 'Successfully added language name variation {0} for {1}'.format(
            variationName, entry.getLanguageName())
    else:
        return False, 'Not a valid lang_code'

def removeLanguageVariation(lang_code, variationName):
    entry = Language.get_by_id(lang_code)
    if entry:
        variationName_uni = variationName.decode('utf-8')
        if variationName_uni in entry.alternative_names:
            entry.alternative_names.remove(variationName_uni)
            entry.put()
            return True, 'Successfully removed language name variation {0} for {1}'.format(
                variationName, entry.getLanguageName())
        else:
            return False, 'Language variation {0} not present for {1}'.format(
                variationName, entry.getLanguageName())
    else:
        return False, 'Not a valid lang_code'


# ================================
# Language list and commands list
# ================================


def makeLanguageCommand(lang_name):
    return re.sub('[() -]+', '_', lang_name).strip('_')

ALL_LANG_CODES, ALL_LANGUAGES = fetchLanguageNamesAndCodes()

ALL_LANGUAGES_LOWERCASE = [l.lower() for l in ALL_LANGUAGES]

ALL_LANGUAGES_COMMANDS = ['/' + makeLanguageCommand(item) for item in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS_LOWERCASE = [makeLanguageCommand(l.lower()) for l in ALL_LANGUAGES_COMMANDS]

ALL_LANGUAGES_COMMANDS_AC = ['/' + makeLanguageCommand(item) for item in ALL_LANGUAGES if item[0] in utility.char_range('A', 'C')]
ALL_LANGUAGES_COMMANDS_DJ = ['/' + makeLanguageCommand(item) for item in ALL_LANGUAGES if item[0] in utility.char_range('D', 'J')]
ALL_LANGUAGES_COMMANDS_KP = ['/' + makeLanguageCommand(item) for item in ALL_LANGUAGES if item[0] in utility.char_range('K', 'P')]
ALL_LANGUAGES_COMMANDS_RZ = ['/' + makeLanguageCommand(item) for item in ALL_LANGUAGES if item[0] in utility.char_range('R', 'Z')]


"""

# ================================
# BUILDING LANGUAGES FROM FILES
# ================================

ISO_LANGUAGES = {}

with open('EmojiLanguages/_iso-639-3_Name_Index.tsv','rb') as tsvin:
    tsvin = csv.reader(tsvin, delimiter='\t')
    header = tsvin.next()
    for row in tsvin:
        ISO_LANGUAGES[row[0]]=(row[1],row[2])

with open("EmojiLanguages/_langCodeDict.json") as f:
    LANG_CODE_DICT = json.load(f)

CODE_LANG_DICT = {v:k for k,v in LANG_CODE_DICT.iteritems()}

with open("EmojiLanguages/_langFamLangFlag.json") as f:
    EMOJI_FAM_LANG_FLAG = json.load(f)

ALL_LANGUAGES = sorted(LANG_CODE_DICT.keys())
"""


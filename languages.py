# -*- coding: utf-8 -*-

import json
import csv

import util

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


#list of list
#ALL_LANGUAGES = [[l.encode('utf-8') for l in langDict.keys()] for langDict in EMOJI_FAM_LANG_FLAG.values()]
#ALL_LANGUAGES = sorted([item for sublist in ALL_LANGUAGES for item in sublist])

ALL_LANGUAGES = sorted(LANG_CODE_DICT.keys())

ALL_LANGUAGES_LOWERCASE = [l.lower() for l in ALL_LANGUAGES]

ALL_LANGUAGES_COMMANDS = ['/' + item for item in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS_LOWERCASE = [l.lower() for l in ALL_LANGUAGES_COMMANDS]
ALL_LANGUAGES_COMMANDS_AC = ['/' + item for item in ALL_LANGUAGES if item[0] in util.char_range('A','C')]
ALL_LANGUAGES_COMMANDS_DJ = ['/' + item for item in ALL_LANGUAGES if item[0] in util.char_range('D','J')]
ALL_LANGUAGES_COMMANDS_KP = ['/' + item for item in ALL_LANGUAGES if item[0] in util.char_range('K','P')]
ALL_LANGUAGES_COMMANDS_RZ = ['/' + item for item in ALL_LANGUAGES if item[0] in util.char_range('R','Z')]

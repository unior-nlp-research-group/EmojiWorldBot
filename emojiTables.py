# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

from google.appengine.api import urlfetch
import webapp2
import json

import logging
import urllib
import jsonUtil
import languages
import random
import utility
import tagging

####
# LIST WITH ALL EMOJI IN UTF-8
####

def fetchAllEmojiFromFile():
    with open("EmojiLanguages/_emojis.json") as f:
        return jsonUtil.json_load_byteified(f)

def createEmojiFile():
    with open("EmojiLanguages/_emojiDesc.json") as f:
        emojiDescrDict = jsonUtil.json_load_byteified(f)
    emojis = emojiDescrDict.keys()
    with open("EmojiLanguages/_emojis.json", 'w') as emojiFile:
        json.dump(emojis, emojiFile, indent=4, ensure_ascii=False)

ALL_EMOJIS = fetchAllEmojiFromFile()  # fetchAllEmoji()

def getRandomEmoji():
    return random.choice(ALL_EMOJIS)


# =========================================
# LanguageEmojiTag ndb model
# =========================================

class LanguageEmojiTag(ndb.Model):
    # id = 'lang_code emoji'
    emoji = ndb.StringProperty()
    lang_code = ndb.StringProperty()
    default_tags = ndb.StringProperty(repeated=True)
    users_tags = ndb.StringProperty(repeated=True)
    has_users_tags = ndb.ComputedProperty(lambda self: len(self.users_tags) > 0)
    has_tags = ndb.ComputedProperty(lambda self: len(self.default_tags)>0 or len(self.users_tags)>0 )
    #all_normalized_tags =  ndb.ComputedProperty(
    #    lambda self: [utility.normalizeString(x.encode('utf-8')) for x in self.default_tags + self.users_tags] )
    random_id = ndb.FloatProperty()

    def getEmoji(self):
        return self.emoji.encode('utf-8')

    def getRandomTag(self):
        tags = self.default_tags + self.users_tags
        if len(tags)>0:
            return random.choice(tags).encode('utf-8')
        return None

    def getTagList(self):
        return [x.encode('utf-8') for x in self.default_tags + self.users_tags]

    def getUserTagList(self):
        return [x.encode('utf-8') for x in self.users_tags]

    def computeAllNormalizedTags(self):
        return [utility.normalizeString(x.encode('utf-8')) for x in self.default_tags + self.users_tags]

def getId(lang_code, emoji):
    logging.debug("lang_code: " + str(lang_code))
    logging.debug("emoji: " + str(emoji))
    return lang_code + ' ' + emoji

def getEntry(lang_code, emoji):
    id = getId(lang_code, emoji)
    return LanguageEmojiTag.get_by_id(id)

def getRandomLanguageEmojiTagEntryWithTags(lang_code):
    r = random.random()
    random_entry = LanguageEmojiTag.query(
        LanguageEmojiTag.lang_code==lang_code,
        LanguageEmojiTag.has_tags == True,
        LanguageEmojiTag.random_id>r).order(LanguageEmojiTag.random_id).get()
    if not random_entry:
        random_entry = LanguageEmojiTag.query(
            LanguageEmojiTag.lang_code == lang_code,
            LanguageEmojiTag.has_tags == True,
            LanguageEmojiTag.random_id<r).order(-LanguageEmojiTag.random_id).get()
    return random_entry

def getRandomTag(lang_code):
    randomEntryWithTags = getRandomLanguageEmojiTagEntryWithTags(lang_code)
    return randomEntryWithTags.getRandomTag()

def getRandomEmojiHavingTags(lang_code):
    randomEntryWithTags = getRandomLanguageEmojiTagEntryWithTags(lang_code)
    if randomEntryWithTags:
        return randomEntryWithTags.getEmoji()
    return None

def getTagList(lang_code, emoji_utf):
    entry =  getEntry(lang_code, emoji_utf)
    if entry:
        return entry.getTagList()
    return []

def getEmojiList(lang_code, tag):
    tagLower = tag.lower()
    entries = LanguageEmojiTag.query(
        ndb.AND(LanguageEmojiTag.lang_code == lang_code,
                ndb.OR(
                    LanguageEmojiTag.default_tags == tag,
                    LanguageEmojiTag.default_tags == tagLower,
                    LanguageEmojiTag.users_tags == tag,
                    LanguageEmojiTag.users_tags == tagLower
                )
        )
    ).fetch(projection=[LanguageEmojiTag.emoji])
    return [e.getEmoji() for e in entries]

def addUserDefinedTag(lang_code, emoji, proposedTag):
    logging.debug("In addUserDefinedTag")
    entry = getEntry(lang_code, emoji)
    logging.debug("entry: " + str(entry))
    assert entry != None
    entry.users_tags.append(proposedTag)
    entry.put()

def getLanguagesWithUserTags():
    entries = LanguageEmojiTag.query(
        LanguageEmojiTag.has_users_tags == True,
        projection=[LanguageEmojiTag.lang_code],
        distinct=True
    ).fetch()
    return [x.lang_code for x in entries]


####
# BUILDING DICTIONARIES FROM KAMUSI SERVER
####

KAMUSI_SERVER_LANG_DICT_URL = "http://lsir-kamusi.epfl.ch:3000/emojibot/getall/" # + *language_code*
#{"emoji1":["tag1","tag2", ...], "emoji2":["tag1", ... ], ... }

def populateLanguageEmojiTagTable():
    language_codes = languages.fetchLanguageCodes()
    total = 0
    for lang_code in language_codes:
        url = KAMUSI_SERVER_LANG_DICT_URL + lang_code
        response = urllib.urlopen(url)
        emojiTagsDict = jsonUtil.json_loads_byteified(response.read())
        toAdd = []
        withTags = 0
        for emoji in ALL_EMOJIS:
            tags = []
            if emoji in emojiTagsDict:
                tags = emojiTagsDict[emoji]
                withTags += 1
            let = LanguageEmojiTag(
                id= getId(lang_code, emoji),
                emoji = emoji,
                lang_code = lang_code,
                default_tags=tags,
                users_tags = [],
                random_id=random.random()
            )
            toAdd.append(let)
        ndb.put_multi(toAdd)
        print "Successuffully added {0} emoji for {1} ({2} have tags)".format(str(len(toAdd)), lang_code, str(withTags))
        total += len(toAdd)
    print "LOADED {0} emojis in total".format(str(total))

def updateTables():
    language_codes = languages.fetchLanguageCodes()
    #language_codes = ['ita']
    for lang_code in language_codes:
        toAdd = []
        entries = LanguageEmojiTag.query(LanguageEmojiTag.lang_code == lang_code).fetch()
        for e in entries:
            e.random_id = random.random()
            toAdd.append(e)
        ndb.put_multi(toAdd)
        print "UPDATED {0} emojis for {1}".format(str(len(toAdd)),lang_code)

####
# emoji tag eng_definitions
####

KAMUSI_SERVER_EMOJI_TAG_WORDNETDEF_URL = "http://lsir-kamusi.epfl.ch:3000/emojibot/getdef"
#[ ['tag1','def1',[<emoji_set1>]], ['tag2','def2',[<emoji_set2>]], ... ]


#==============================
# REQUEST HANDLERS
#==============================

class LanguageUserTagsStatsHandler(webapp2.RequestHandler):
    def get(self):
        #urlfetch.set_default_fetch_deadline(60)
        full = self.request.get('full') == 'true'
        lang = self.request.get('lang')
        languages = tagging.getLanguagesWithProposedTags() if lang=='' else [lang]
        result = {}
        for lang_code in languages:
            qry = LanguageEmojiTag.query(
                LanguageEmojiTag.lang_code==lang_code,
                LanguageEmojiTag.has_users_tags==True
            )
            result[lang_code] = {
                "emoji with new agreed tags": qry.count(),
                "users who have played": tagging.getNumberUsersWhoHavePlayed(lang_code),
                "emoji with new proposed tags": tagging.getNumberOfEmojiBeingTagged(lang_code)
            }
            if full:
                entries = qry.fetch()
                result[lang_code]['full info']= [
                    {
                        'emoji': e.emoji,
                        'tags': e.users_tags
                    }
                    for e in entries
                ]
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(result, indent=4, ensure_ascii=False))


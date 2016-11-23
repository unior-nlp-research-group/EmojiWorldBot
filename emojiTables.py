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
        urlfetch.set_default_fetch_deadline(60)
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


# =========================================
# Emoji ndb model
# =========================================
"""
class Emoji(ndb.Model):
    # id = 'emoji'
    unicode_description = ndb.StringProperty()

    def getUnicodeDescription(self):
        return self.unicode_description.encode('utf-8')


def fetchAllEmojiFromDB():
    emojis = []
    entries = Emoji.query().fetch(keys_only=True)
    for e in entries:
        emojis.append(e.id())
    return emojis

ALL_EMOJIS = fetchAllEmojiFromDB()

####
# BUILDING Emoji table from file
####

def populateEmojiTable():
    with open("EmojiLanguages/_emojiDesc.json") as f:
      emojiDescrDict = jsonUtil.json_load_byteified(f)
    toAdd = []
    for emoji, description in emojiDescrDict.iteritems():
        e = Emoji(
            id= emoji,
            unicode_description = description,
        )
        toAdd.append(e)
    ndb.put_multi(toAdd)
    print "Successuffully added {0} emojis in emoji table".format(str(len(toAdd)))


"""

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



# ================================
# BUILDING EMOJI DICTIONARIES FROM FILES
# ================================
"""
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
"""


# ================================
# Emoji FileId for emoji images
# ================================
"""
class EmojiFileId(ndb.Model):
    # id = emoji
    file_id = ndb.StringProperty()

def addEmojiFileId(emoji_utf, file_id):
    emoji_uni = emoji_utf.decode('utf-8')
    p = EmojiFileId(
        id=emoji_uni,
        file_id=file_id,
    )
    p.put()
    return p

def getEmojiFileIdEntry(emoji_utf):
    emoji_uni = emoji_utf.decode('utf-8')
    return EmojiFileId.get_by_id(emoji_uni)

def deleteAllEmojiFileIds():
    ndb.delete_multi(EmojiFileId.query().fetch(keys_only=True))
"""

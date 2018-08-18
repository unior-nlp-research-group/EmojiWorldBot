# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

import webapp2
import json

import logging
import random
import utility
import userTagging
import emojiTags

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

    def updateTagList(self, new_tags):
        need_update = False
        tags = self.getTagList()
        for nt in new_tags:
            if nt not in tags:
                tags.append(nt)
                need_update = True
        if need_update:
            self.put()
        return tags

    def getUserTagList(self):
        return [x.encode('utf-8') for x in self.users_tags]

    def computeAllNormalizedTags(self):
        return [utility.normalizeString(x.encode('utf-8')) for x in self.default_tags + self.users_tags]

def getId(lang_code, emoji):
    logging.debug("lang_code: " + str(lang_code))
    logging.debug("emoji: " + str(emoji))
    return '{} {}'.format(lang_code, emoji)

def getEntry(lang_code, emoji):
    id = getId(lang_code, emoji)
    return LanguageEmojiTag.get_by_id(id)

def addEntry(lang_code, emoji, default_tags, put=True):
    entry_id = getId(lang_code, emoji)
    p = LanguageEmojiTag(
        id = entry_id,
        emoji = emoji,
        lang_code=lang_code,
        default_tags=default_tags,
        random_id = random.random()
    )
    if put:
        p.put()
    return p

def addEmojiLangInTableIfNotExists(lang_code, emoji):
    entry = getEntry(lang_code, emoji)
    if entry == None:
        default_tags = emojiTags.getTagsForEmoji(emoji, lang_code)
        addEntry(lang_code, emoji, default_tags)


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
    default_tags = emojiTags.getTagsForEmoji(emoji_utf, lang_code)
    if entry:
        all_tags = entry.updateTagList(default_tags)
    else:
        addEntry(lang_code, emoji_utf, default_tags)
        all_tags = default_tags
    return all_tags

def getEmojiList(lang_code, tag, show_alpha_names):
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
    result = [e.getEmoji() for e in entries]
    emojis_in_unicode_tags = emojiTags.getEmojisForTag(tag, lang_code)
    result.extend(emojis_in_unicode_tags)
    result = list(set(result))
    if show_alpha_names:
        from emojiUtil import getAlphaName
        #return ["{} :{}:".format(x,utility.escapeMarkdown(getAlphaName(x))) for x in result]
        return ["{} :{}:".format(x, getAlphaName(x)) for x in result]
    return result

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


#==============================
# REQUEST HANDLERS
#==============================

class LanguageUserTagsStatsHandler(webapp2.RequestHandler):
    def get(self):
        #urlfetch.set_default_fetch_deadline(60)
        full = self.request.get('full') == 'true'
        lang = self.request.get('lang')
        languages = userTagging.getLanguagesWithProposedTags() if lang == '' else [lang]
        result = {}
        for lang_code in languages:
            qry = LanguageEmojiTag.query(
                LanguageEmojiTag.lang_code==lang_code,
                LanguageEmojiTag.has_users_tags==True
            )
            result[lang_code] = {
                "emoji with new agreed tags": qry.count(),
                "users who have played": userTagging.getNumberUsersWhoHavePlayed(lang_code),
                "emoji with new proposed tags": userTagging.getNumberOfEmojiBeingTagged(lang_code)
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


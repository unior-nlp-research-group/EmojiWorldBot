# -*- coding: utf-8 -*-


from google.appengine.ext import ndb
from google.appengine.api import urlfetch
import webapp2

import json

import logging
import parameters
import person
import emojiTables
import utility
import languages

from collections import defaultdict


###################
# MAIN CLASS Tagging
###################

class UserTagging(ndb.Model):
    # id = lang_code chat_id
    timestamp = ndb.DateTimeProperty(auto_now=True)
    chat_id = ndb.IntegerProperty()
    lang_code = ndb.StringProperty()
    ongoingAlreadyTaggedEmojis = ndb.IntegerProperty(default=0) #number of emoji given to user already tagged by other useres
    ongoingUpperCaseTags = ndb.IntegerProperty(default=0)
    last_emoji = ndb.StringProperty()
    emojiTagsTable = ndb.PickleProperty()
    disableDiacriticsWarning = ndb.BooleanProperty(default=False)
    # emoji -> tag

    def wasEmojiTagged(self, emoji_utf):
        #emoji_uni = emoji_utf.decode('utf-8')
        #return self.emojiTagsTable.has_key(emoji_uni)
        return self.emojiTagsTable.has_key(emoji_utf)

    def getNumberOfTaggedEmoji(self):
        return len(self.emojiTagsTable)

    def setLastEmoji(self, emoji, random):
        self.last_emoji = emoji
        if random:
            self.ongoingAlreadyTaggedEmojis = 0
        else:
            self.ongoingAlreadyTaggedEmojis += 1
        self.put()

    def getLanguageCode(self):
        return self.lang_code.encode('utf-8')

    def getLastEmoji(self):
        if self.last_emoji:
            return self.last_emoji.encode('utf-8')
        return None

    def removeLastEmoji(self, put=False):
        self.last_emoji = ''
        if put:
            self.put()

    def addTagsToLastEmoji(self, tags, put=False):
        last_emoji_utf = self.getLastEmoji()
        self.emojiTagsTable[last_emoji_utf] = tags
        if put:
            self.put()

    def currentLanguageHasRomanLetters(self):
        return languages.isRomanScript(self.getLanguageCode())

    def currentLanguageHasDiacritics(self):
        return languages.hasDiacritics(self.getLanguageCode())

    def updateUpperCounts(self, tag, put=False):
        if self.currentLanguageHasRomanLetters():
            self.updateTagUpperCount(tag)
            if put:
                self.put()

    # returns
    # 0 (more than x consecutive non-upper cases),
    # 1 (less than x consectuve upper-cases),
    # 2 (more than x consecutive upper-cases)
    def updateTagUpperCount(self, tag):
        if tag[0].isupper():
            if self.ongoingUpperCaseTags < 0:
                self.ongoingUpperCaseTags = 0
            else:
                self.ongoingUpperCaseTags += 1
        else:
            if self.ongoingUpperCaseTags > 0:
                self.ongoingUpperCaseTags = 0
            elif self.ongoingUpperCaseTags > -parameters.COUNT_CONSECUTIVE_UPPER_WORDS_BEFORE_MESSAGE:
                self.ongoingUpperCaseTags -= 1

    def tagUpperCountLevel(self):
        if self.currentLanguageHasRomanLetters():
            if self.ongoingUpperCaseTags >= parameters.COUNT_CONSECUTIVE_UPPER_WORDS_BEFORE_MESSAGE:
                return 2
            if self.ongoingUpperCaseTags > -parameters.COUNT_CONSECUTIVE_UPPER_WORDS_BEFORE_MESSAGE:
                return 1
        return 0

    def hasSeenEnoughKnownEmoji(self):
        return self.ongoingAlreadyTaggedEmojis >= parameters.MAX_NUMBER_OF_ALREADY_KNOWN_EMOJI_IN_A_ROW

    def setDisableDiacriticsWarning(self, value, put=True):
        self.disableDiacriticsWarning = True
        if put:
            self.put()

def getUserTaggingId(person):
    return person.getLanguageCode() + ' ' + str(person.chat_id)

def getUserTaggingEntry(person):
    unique_id = getUserTaggingId(person)
    return UserTagging.get_by_id(unique_id)

def getOrInsertUserTaggingEntry(person):
    userTagginEntry = getUserTaggingEntry(person)
    unique_id = getUserTaggingId(person)
    if not userTagginEntry:
        userTagginEntry = UserTagging(
            id=unique_id,
            chat_id = person.chat_id,
            lang_code = person.getLanguageCode(),
            emojiTagsTable = {}
        )
        userTagginEntry.put()
    return userTagginEntry

def getNumberUsersWhoHavePlayed(lang_code):
    return UserTagging.query(
        UserTagging.lang_code == lang_code,
    ).count()

def getLanguagesWithProposedTags():
    entries = UserTagging.query(
        projection=[UserTagging.lang_code],
        distinct=True
    ).fetch()
    return [x.lang_code for x in entries]

###################
# MAIN CLASS AggregatedEmojiTags
###################

class AggregatedEmojiTags(ndb.Model):
    # id = lang_code emoji
    timestamp = ndb.DateTimeProperty(auto_now=True)
    lang_code = ndb.StringProperty()
    emoji = ndb.StringProperty()
    annotators_count = ndb.IntegerProperty(default=0)
    tags_count = ndb.IntegerProperty(default=0)
    tagsCountTable = ndb.PickleProperty() #defaultdict(int)

    def getLanguageCode(self):
        return self.lang_code.encode('utf-8')

def getAggregatedEmojiTagsId(lang_code_utf, emoji_utf):
    return lang_code_utf + ' ' + emoji_utf

def getAggregatedEmojiTagsEntry(lang_code, emoji_uni):
    unique_id = getAggregatedEmojiTagsId(lang_code, emoji_uni)
    return AggregatedEmojiTags.get_by_id(unique_id)

@ndb.transactional(retries=100, xg=True)
def addInAggregatedEmojiTags(userTaggingEntry):
    lang_code_utf = userTaggingEntry.getLanguageCode()
    emoji_utf = userTaggingEntry.getLastEmoji()
    tags = userTaggingEntry.emojiTagsTable[emoji_utf]
    unique_id = getAggregatedEmojiTagsId(lang_code_utf, emoji_utf)
    aggregatedEmojiTags = AggregatedEmojiTags.get_by_id(unique_id)
    if not aggregatedEmojiTags:
        aggregatedEmojiTags = AggregatedEmojiTags(
            id=unique_id,
            parent=None,
            namespace=None,
            lang_code=lang_code_utf,
            emoji=emoji_utf,
            tagsCountTable=defaultdict(int)
        )
    for t in tags:
        aggregatedEmojiTags.tagsCountTable[t] +=1
    aggregatedEmojiTags.annotators_count += 1
    aggregatedEmojiTags.tags_count += len(tags)
    aggregatedEmojiTags.put()
    return aggregatedEmojiTags

def getPrioritizedEmojiForUser(userTaggingEntry):
    emoji_esclusion_list = userTaggingEntry.emojiTagsTable.keys()
    lang_code = userTaggingEntry.lang_code
    entries = AggregatedEmojiTags.query(
        AggregatedEmojiTags.lang_code == lang_code,
        AggregatedEmojiTags.annotators_count <= parameters.MAX_ANNOTATORS_PER_PRIORITIZED_EMOJI,
    ).order(AggregatedEmojiTags.annotators_count).iter(projection=[AggregatedEmojiTags.emoji])
    for e in entries:
        emoji_utf = e.emoji.encode('utf-8')
        if emoji_utf not in emoji_esclusion_list:
            return emoji_utf
        #logging.debug("Discarding {0} because already seen by user".format(emoji_utf))
    return None

# returns annotatorsCount, tagsCount, stats
def getTaggingStats(userTaggingEntry):
    lang_code = userTaggingEntry.getLanguageCode()
    emoji_utf = userTaggingEntry.getLastEmoji()
    aggregatedEmojiTags = getAggregatedEmojiTagsEntry(lang_code, emoji_utf)
    if aggregatedEmojiTags:
        return  aggregatedEmojiTags.annotators_count, \
                aggregatedEmojiTags.tags_count, \
                aggregatedEmojiTags.tagsCountTable
    return 0, 0, {}


def getStatsFeedbackForTagging(userTaggingEntry, proposedTag):
    annotatorsCount, tagsCount, tagsCountDict = getTaggingStats(userTaggingEntry)
    logging.debug('stats: ' + str(tagsCountDict))
    msg = ''
    if tagsCount == 0:
        msg += "🏅 You are the first annotator for this term for this emoji!"
    else:
        msg += '\n'
        """
        if annotatorsCount==1:
            msg += "{0} person has provided a new term for this emoji:\n".format(str(annotatorsCount))
        else:
            msg += "{0} people have provided new terms for this emoji:\n".format(str(annotatorsCount))
        """
        agreement = proposedTag in tagsCountDict.keys()
        sortedTagsInDict = sorted(tagsCountDict.keys(), key=tagsCountDict.get, reverse=True)
        if agreement:
            agreementCount = tagsCountDict[proposedTag]
            # CHECK IF TO GO PUBLIC
            if agreementCount + 1 == parameters.MIN_COUNT_FOR_USER_TAG_TO_BE_PUBLIC:
                msg += "\n🎉🎉🎉 This tag has reached the required number of votes and will be added in the dictionary!\n"
                emojiTables.addUserDefinedTag(userTaggingEntry.getLanguageCode(), userTaggingEntry.getLastEmoji(), proposedTag)
            else:
                if agreementCount == 1:
                    msg += "🎉 1 person agrees with your term! 😊 \n"
                else:
                    msg += "🎉 {0} people agree with your term! 😊 \n".format(str(agreementCount))

            sortedTagsInDict.remove(proposedTag)
        else:
            msg += "🤔 So far, no one agrees with you.\n"
        maxSize = parameters.MAX_NUMBER_OF_DISPLAYED_TAGS_ALTERNATIVE
        for k in sortedTagsInDict[:maxSize]:
            count = tagsCountDict[k]
            msg += "  {0} suggested: {1}\n".format(str(count), k)
        restCount = sum( tagsCountDict[k] for k in sortedTagsInDict[maxSize:])
        if restCount>0:
            msg += "  ... {0} suggested other things".format(str(restCount))
    return msg

def getNumberOfEmojiBeingTagged(lang_code):
    return AggregatedEmojiTags.query(
        AggregatedEmojiTags.lang_code == lang_code,
    ).count()

#==============================
# REQUEST HANDLERS
#==============================
class TaggingUserTableHandler(webapp2.RequestHandler):
    def get(self, lang_code):
        #urlfetch.set_default_fetch_deadline(60)
        full = self.request.get('full') == 'true'
        qry = UserTagging.query(UserTagging.lang_code == lang_code)
        result = {}
        for entry in qry:
            user = person.getPersonByChatId(entry.chat_id)
            result[entry.chat_id] = {
                "name": user.getFirstName() if user else "Unknown ({0})".format(str(entry.chat_id)),
                "total taggings": len(entry.emojiTagsTable),
            }
            if full:
                result[entry.chat_id]["translation table"] = entry.emojiTagsTable
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(result, indent=4, ensure_ascii=False))

class TaggingAggregatedTableHandler(webapp2.RequestHandler):
    def get(self, lang_code):
        #urlfetch.set_default_fetch_deadline(60)
        qry = AggregatedEmojiTags.query(AggregatedEmojiTags.lang_code==lang_code)
        result = {}
        for entry in qry:
            result[entry.emoji.encode('utf-8')] = {
                "annotators count": entry.annotators_count,
                "tagging table": entry.tagsCountTable
            }
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(result, indent=4, ensure_ascii=False))

#======================
# VERY DANGEREOUS OPERATIONS
#======================


def deleteTagging(lang_code=None):
    if lang_code:
        ndb.delete_multi(UserTagging.query(
            UserTagging.lang_code == lang_code).fetch(keys_only=True))
        ndb.delete_multi(AggregatedEmojiTags.query(
            UserTagging.lang_code == lang_code).fetch(keys_only=True))
        ndb.delete_multi(
            emojiTables.LanguageEmojiTag.query(
                emojiTables.LanguageEmojiTag.lang_code == lang_code,
                emojiTables.LanguageEmojiTag.has_users_tags == True).fetch(keys_only=True))
    else:
        ndb.delete_multi(UserTagging.query().fetch(keys_only=True))
        ndb.delete_multi(AggregatedEmojiTags.query().fetch(keys_only=True))
        ndb.delete_multi(
            emojiTables.LanguageEmojiTag.query(
                emojiTables.LanguageEmojiTag.has_users_tags == True).fetch(keys_only=True))

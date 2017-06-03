# -*- coding: utf-8 -*-

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

from random import randint
import logging
import key
import json

import person

from collections import defaultdict
import parameters

###################
# MAIN CLASS TranslationTag
###################

class UserTranslationTag(ndb.Model):
    # id = src_language dst_language chat_id
    timestamp = ndb.DateTimeProperty(auto_now=True)
    #last_message_id = ndb.IntegerProperty()
    chat_id = ndb.IntegerProperty()
    src_language = ndb.StringProperty()
    dst_language = ndb.StringProperty()
    ongoingAlreadyTranslatedEmojis = ndb.IntegerProperty(default=0)  # number of emoji given to user already translated by other useres
    last_emoji = ndb.StringProperty()
    last_src_tag = ndb.StringProperty()
    dst_tag_set = ndb.PickleProperty(default=[])
    emojiSrcTagTranslationTable = ndb.PickleProperty() #{}
    #tmp_emojiSrcTagTranslationTable = ndb.StringProperty()
    #emoji -> (last_src_tag, translation)
    # "None of the options" -> ''
    # SKIP -> None

    def wasEmojiTranslated(self, emoji_utf):
        #emoji_uni = emoji_utf.decode('utf-8')
        #return self.emojiSrcTagTranslationTable.has_key(emoji_uni)
        return self.emojiSrcTagTranslationTable.has_key(emoji_utf)

    #def setLastMessageId(self, msgId):
    #    self.last_message_id = msgId

    def getNumberOfTranslatedEmoji(self):
        return len(self.emojiSrcTagTranslationTable)

    def setLastEmojiAndSrcTag(self, emoji, last_src_tag, random):
        logging.debug("Setting last emoji {0} and src_tag {1}".format(emoji, last_src_tag))
        self.last_emoji = emoji
        self.last_src_tag = last_src_tag
        if random:
            self.ongoingAlreadyTranslatedEmojis = 0
        else:
            self.ongoingAlreadyTranslatedEmojis += 1

    def getLastEmoji(self):
        if self.last_emoji:
            return self.last_emoji.encode('utf-8')
        return None

    def removeLastEmoji(self, put=False):
        self.last_emoji = ''
        if put:
            self.put()

    def getLastSrcTag(self):
        return self.last_src_tag.encode('utf-8')

    def addTranslationToLastEmojiSrcTag(self, translation, put=True):
        # translation == None if skipped, translation == '' if none of the options apply
        last_emoji_utf = self.last_emoji.encode('utf-8')
        last_src_tag_utf = self.last_src_tag.encode('utf-8')
        if self.wasEmojiTranslated(last_emoji_utf):
            return False #attempting to translate the same emoji twice
        logging.debug("Addding translation {0} to last emoji {1} and src_tag {2}".format(str(translation), last_emoji_utf, last_src_tag_utf))
        self.emojiSrcTagTranslationTable[last_emoji_utf] = (last_src_tag_utf, translation)
        #self.tmp_emojiSrcTagTranslationTable = str(self.emojiSrcTagTranslationTable)
        if put:
            self.put()
        return True

    def hasSeenEnoughKnownEmoji(self):
        return self.ongoingAlreadyTranslatedEmojis >= parameters.MAX_NUMBER_OF_ALREADY_KNOWN_EMOJI_IN_A_ROW

    def getLastSrcTagLastTranslation(self):
        last_emoji_utf = self.last_emoji.encode('utf-8')
        return self.emojiSrcTagTranslationTable[last_emoji_utf]  # (lastSrctag, translation)

def getUserTranslationsId(person):
    return person.getLanguageCode() + ' ' + str(person.chat_id)

def getUserTranslationEntry(person):
    unique_id = getUserTranslationsId(person)
    return UserTranslationTag.get_by_id(unique_id)

def getOrInsertUserTranslationTagEntry(person, src_language):
    unique_id = getUserTranslationsId(person)
    userTranslationTagEntry = UserTranslationTag.get_by_id(unique_id)
    if not userTranslationTagEntry:
        userTranslationTagEntry = UserTranslationTag(
            id=unique_id,
            chat_id = person.chat_id,
            src_language = src_language,
            dst_language = person.language,
            emojiSrcTagTranslationTable = {}
        )
        userTranslationTagEntry.put()
    return userTranslationTagEntry

###################
# MAIN CLASS AggregatedEmojiTranslations
###################

class KeyKeyIntDict(dict):
    def __missing__(self, key):
        self[key] = defaultdict(int)
        return self[key]

class AggregatedEmojiTranslations(ndb.Model):
    # id = src_language dst_language language emoji
    timestamp = ndb.DateTimeProperty(auto_now=True)
    src_language = ndb.StringProperty()
    dst_language = ndb.StringProperty()
    emoji = ndb.StringProperty()
    annotators_count = ndb.IntegerProperty(default=0)
    translationsCountTable = ndb.PickleProperty() #default=KeyKeyIntDict()
    # src_tag -> translation_tag -> count
    #tmp_translationsCountTable = ndb.StringProperty()


def getAggregatedEmojiTranslationsId(emoji_uni, dst_language_uni, src_language_uni):
    return src_language_uni.encode('utf-8') + ' ' + dst_language_uni.encode('utf-8') + ' ' + emoji_uni.encode('utf-8')

def getAggregatedEmojiTranslationsEntry(emoji_uni, dst_language_uni, src_language_uni):
    unique_id = getAggregatedEmojiTranslationsId(emoji_uni, dst_language_uni, src_language_uni)
    return AggregatedEmojiTranslations.get_by_id(unique_id)

@ndb.transactional(retries=100, xg=True)
def addInAggregatedEmojiTranslations(userTranslationsEntry):
    src_language_uni = userTranslationsEntry.src_language
    dst_language_uni = userTranslationsEntry.dst_language
    emoji_uni = userTranslationsEntry.last_emoji
    unique_id = getAggregatedEmojiTranslationsId(emoji_uni, dst_language_uni, src_language_uni)
    aggregatedEmojiTranslations = AggregatedEmojiTranslations.get_by_id(unique_id)
    if not aggregatedEmojiTranslations:
        aggregatedEmojiTranslations = AggregatedEmojiTranslations(id=unique_id, parent=None, namespace=None,
                                                  src_language=src_language_uni, dst_language=dst_language_uni, emoji=emoji_uni)
        aggregatedEmojiTranslations.translationsCountTable = KeyKeyIntDict()
    logging.debug('addInAggregatedEmojiTranslations emoji: {0} Old stats: {1}'.format(
        emoji_uni.encode('utf-8'), str(aggregatedEmojiTranslations.translationsCountTable)))
    userLastSrcTag_utf, lastTranslation_utf = userTranslationsEntry.getLastSrcTagLastTranslation()
    logging.debug('last emoji: {0} last src_tag: {1} last translation: {2}'.format(emoji_uni.encode('utf-8'), userLastSrcTag_utf, lastTranslation_utf))
    if lastTranslation_utf!=None: #None is uses when skipped
        aggregatedEmojiTranslations.translationsCountTable[userLastSrcTag_utf][lastTranslation_utf] +=1
    #aggregatedEmojiTranslations.tmp_translationsCountTable = str(aggregatedEmojiTranslations.translationsCountTable)
    aggregatedEmojiTranslations.annotators_count += 1
    aggregatedEmojiTranslations.put()
    logging.debug('addInAggregatedEmojiTranslations emoji: {0} New stats: {1}'.format(
        emoji_uni.encode('utf-8'), str(aggregatedEmojiTranslations.translationsCountTable)))
    return aggregatedEmojiTranslations

def getPrioritizedEmojiSrcTagForUser(userTranslationsEntry):
    emoji_esclusion_list = userTranslationsEntry.emojiSrcTagTranslationTable.keys()
    src_language = userTranslationsEntry.src_language
    dst_language = userTranslationsEntry.dst_language
    entries = AggregatedEmojiTranslations.query(
        AggregatedEmojiTranslations.src_language == src_language,
        AggregatedEmojiTranslations.dst_language == dst_language,
        AggregatedEmojiTranslations.annotators_count <= parameters.MAX_ANNOTATORS_PER_PRIORITIZED_EMOJI,
    ).order(AggregatedEmojiTranslations.annotators_count)
        #.iter(projection=[AggregatedEmojiTranslations.emoji)
    for entry in entries:
        emoji_utf = entry.emoji.encode('utf-8')
        if emoji_utf not in emoji_esclusion_list:
            if len(entry.translationsCountTable) == 0:
                continue
            else:
                srcTag = min(entry.translationsCountTable,
                             key=lambda k: sum([x for x in entry.translationsCountTable[k].values()]))
                #srcTag = entry.translationsCountTable.keys()[randint(0, len(entry.translationsCountTable) - 1)]
            return emoji_utf, srcTag
    return None, None


def getUserTagsForEmoji(emoji_utf, dst_language_utf, src_language_utf="English"):
    src_language_uni = src_language_utf.decode('utf-8')
    dst_language_uni = dst_language_utf.decode('utf-8')
    emoji_uni = emoji_utf.decode('utf-8')
    aggregatedEmojiTranslations = getAggregatedEmojiTranslationsEntry(
        emoji_uni, dst_language_uni, src_language_uni)
    if not aggregatedEmojiTranslations:
        return None
    return {tag: count
            for tag, count in aggregatedEmojiTranslations.translationsCountTable.iteritems()
            if count >= parameters.MIN_COUNT_FOR_USER_TAG_TO_BE_PUBLIC
    }

# returns annotatorsCount, stats
def getTranslationStats(userTranslationsEntry):
    src_language_uni = userTranslationsEntry.src_language
    dst_language_uni = userTranslationsEntry.dst_language
    emoji_uni = userTranslationsEntry.last_emoji
    aggregatedEmojiTranslations = getAggregatedEmojiTranslationsEntry(
        emoji_uni, dst_language_uni, src_language_uni)
    if aggregatedEmojiTranslations:
        userLastSrcTag_utf = userTranslationsEntry.last_src_tag
        termTranslationsDict = aggregatedEmojiTranslations.translationsCountTable[userLastSrcTag_utf]
        termAnnotatorsCount = sum([x for x in termTranslationsDict.itervalues()])
        return  termAnnotatorsCount, termTranslationsDict
    return 0, {}

def getStatsFeedbackForTranslation(userTranslationsEntry, proposedTranslation):
    termAnnotatorsCount, termTranslationsDict = getTranslationStats(userTranslationsEntry)
    logging.debug('stats: ' + str(termTranslationsDict))
    userLastSrcTag_utf  = userTranslationsEntry.last_src_tag.encode('utf-8')
    proposedTranslationStr = '✖️ NONE' if proposedTranslation == '' else proposedTranslation
    msg = "Your answer: {0} ➡ ️{1}\n".format(userLastSrcTag_utf, proposedTranslationStr)
    if termAnnotatorsCount == 0:
        msg += "🏅 You are the first translator of this term for this emoji!"
    else:
        '''
        if termAnnotatorsCount==1:
            msg += "{0} other person voted on this term:\n".format(str(termAnnotatorsCount))
        else:
            msg += "{0} other people voted on this term:\n".format(str(termAnnotatorsCount))
        '''
        agreementCount = termTranslationsDict[proposedTranslation]
        disagreementCount = termAnnotatorsCount - agreementCount

        if agreementCount==1:
            msg += "😊 {0} person agrees with you!\n".format(str(agreementCount))
        else:
            msg += "😊 {0} people agree with you!\n".format(str(agreementCount))

        if disagreementCount == 1:
            msg += "😊 {0} person has a different opinion.\n".format(str(disagreementCount))
        else:
            msg += "😊 {0} people have a different opinion.\n".format(str(disagreementCount))

        other_stats = {
            translation: count
            for translation, count in termTranslationsDict.iteritems()
            if translation!=proposedTranslation and count >= parameters.MIN_COUNT_FOR_USER_TAG_TO_BE_PUBLIC
        }
        if other_stats:
            msg += "Other answers:\n"
        for k, v in sorted(other_stats.items(), key=lambda x: x[1], reverse=True):
            k_str = '✖️ NONE' if k == '' else k
            msg += "  - {0} suggested: {1}\n".format(str(v), k_str)
    return msg

#####################
# REQUEST HANDLERS
#####################
class TranslationUserTableHandler(webapp2.RequestHandler):
    def get(self, language):
        #urlfetch.set_default_fetch_deadline(60)
        qry = UserTranslationTag.query(UserTranslationTag.dst_language == language)
        full = self.request.get('full') == 'true'
        result = {}
        for entry in qry:
            name = person.getPersonByChatId(entry.chat_id).getLanguageName()
            result[entry.chat_id] = {
                "name": name,
                "total translations": len(entry.emojiSrcTagTranslationTable),
            }
            if full:
                result[entry.chat_id]["translation table"] = entry.emojiSrcTagTranslationTable
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(result, indent=4, ensure_ascii=False))

class TranslationAggregatedTableHandler(webapp2.RequestHandler):
    def get(self, language):
        #urlfetch.set_default_fetch_deadline(60)
        qry = AggregatedEmojiTranslations.query(AggregatedEmojiTranslations.dst_language==language)
        result = {}
        for entry in qry:
            result[entry.emoji.encode('utf-8')] = {
                "annotators count": entry.annotators_count,
                "translation table": entry.translationsCountTable
            }
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.out.write(json.dumps(result, indent=4, ensure_ascii=False))


#####################
# CONSISTENCY CHECK
#####################
def consistencyCheck(language=None):
    if language:
        qry1 = UserTranslationTag.query(UserTranslationTag.dst_language == language)
    else:
        qry1 = UserTranslationTag.query()
    totalAnnotation1 = 0
    for entry in qry1:
        totalAnnotation1 += len(entry.emojiSrcTagTranslationTable)
    if language:
        qry2 = AggregatedEmojiTranslations.query(AggregatedEmojiTranslations.dst_language == language)
    else:
        qry2 = AggregatedEmojiTranslations.query()

    totalAnnotation2 = 0
    for entry in qry2:
        assert entry.annotators_count == sum(x for counter in entry.translationsCountTable.values() for x in counter.values()), \
            "Annotators count not equal to sum in translationCountTable in entry: " + str(entry)
        totalAnnotation2 += entry.annotators_count

    assert totalAnnotation1==totalAnnotation2, \
        str(totalAnnotation1) + "!=" + str(totalAnnotation2)

#####################
# DANGEREOUS OPERATIONS
#####################

def fixCounts():
    qry = AggregatedEmojiTranslations.query()
    count = 0
    toUpdate = []
    for entry in qry:
        sumTable = sum(x for counter in entry.translationsCountTable.values() for x in counter.values())
        if entry.annotators_count != sumTable:
            entry.annotators_count = sumTable
            count += 1
            toUpdate.append(entry)
    ndb.put_multi(toUpdate)
    print count

def cleanData():
    listOfEntities = []
    count = 0
    for entry in AggregatedEmojiTranslations.query():
        if 'tmp_translationsCountTable' in entry._properties:
            del entry._properties['tmp_translationsCountTable']
            listOfEntities.append(entry)
            count += 1
            if count % 10 == 0:
                print count
    ndb.put_multi(listOfEntities)

def deleteData():
    total = 0
    count = 0
    toDelete = []
    for entry in AggregatedEmojiTranslations.query():
        total+=1
        if len(entry.translationsCountTable)==0:
            count +=1
            toDelete.append(entry.key)
    print str(count) + "/" + str(total)
    ndb.delete_multi(
        toDelete
    )
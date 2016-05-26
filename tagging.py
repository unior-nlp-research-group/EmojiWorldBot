# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

import logging
import parameters

from collections import defaultdict


###################
# MAIN CLASS Tagging
###################

class UserTagging(ndb.Model):
    # id = language chat_id
    timestamp = ndb.DateTimeProperty(auto_now=True)
    chat_id = ndb.IntegerProperty()
    language = ndb.StringProperty()
    ongoingAlreadyTaggedEmojis = ndb.IntegerProperty(default=0) #number of emoji given to user already tagged by other useres
    last_emoji = ndb.StringProperty()
    emojiTagsTable = ndb.PickleProperty() #{}
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

    def getLastEmoji(self):
        return self.last_emoji.encode('utf-8')

    def addTagsToLastEmoji(self, tags):
        last_emoji_utf = self.last_emoji.encode('utf-8')
        self.emojiTagsTable[last_emoji_utf] = tags
        #self.last_emoji = ''
        self.put()

    def hasSeenEnoughKnownEmoji(self):
        return self.ongoingAlreadyTaggedEmojis >= parameters.MAX_NUMBER_OF_ALREADY_KNOWN_EMOJI_IN_A_ROW

def getUserTaggingId(person):
    return person.getLanguage() + ' ' + str(person.chat_id)

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
            language = person.language,
            emojiTagsTable = {}
        )
        userTagginEntry.put()
    return userTagginEntry

###################
# MAIN CLASS AggregatedEmojiTags
###################

class AggregatedEmojiTags(ndb.Model):
    # id = language emoji
    timestamp = ndb.DateTimeProperty(auto_now=True)
    language = ndb.StringProperty()
    emoji = ndb.StringProperty()
    annotators_count = ndb.IntegerProperty(default=0)
    tags_count = ndb.IntegerProperty(default=0)
    tagsCountTable = ndb.PickleProperty() #defaultdict(int)

def getAggregatedEmojiTagsId(language_uni, emoji_uni):
    return language_uni.encode('utf-8') + ' ' + emoji_uni.encode('utf-8')

def getAggregatedEmojiTagsEntry(language_uni, emoji_uni):
    unique_id = getAggregatedEmojiTagsId(language_uni, emoji_uni)
    return AggregatedEmojiTags.get_by_id(unique_id)

@ndb.transactional(retries=100, xg=True)
def addInAggregatedEmojiTags(userTaggingEntry):
    language_uni = userTaggingEntry.language
    emoji_uni = userTaggingEntry.last_emoji
    emoji_utf = emoji_uni.encode('utf-8')
    tags = userTaggingEntry.emojiTagsTable[emoji_utf]
    unique_id = getAggregatedEmojiTagsId(language_uni, emoji_uni)
    aggregatedEmojiTags = AggregatedEmojiTags.get_by_id(unique_id)
    if not aggregatedEmojiTags:
        aggregatedEmojiTags = AggregatedEmojiTags(
            id=unique_id,
            parent=None,
            namespace=None,
            language=language_uni,
            emoji=emoji_uni,
            tagsCountTable=defaultdict(int)
        )
    logging.debug('addInAggregatedEmojiTags {0}. Old stats: {1}'.format(
        emoji_uni.encode('utf-8'), str(aggregatedEmojiTags.tagsCountTable)))
    for t in tags:
        aggregatedEmojiTags.tagsCountTable[t] +=1
    aggregatedEmojiTags.annotators_count += 1
    aggregatedEmojiTags.tags_count += len(tags)
    aggregatedEmojiTags.put()
    logging.debug('addInAggregatedEmojiTags {0}. New stats: {1}'.format(
        emoji_uni.encode('utf-8'), str(aggregatedEmojiTags.tagsCountTable)))
    return aggregatedEmojiTags

def getPrioritizedEmojiForUser(userTaggingEntry):
    emoji_esclusion_list = userTaggingEntry.emojiTagsTable.keys()
    language = userTaggingEntry.language
    entries = AggregatedEmojiTags.query(
        AggregatedEmojiTags.language == language,
        AggregatedEmojiTags.annotators_count <= parameters.MAX_ANNOTATORS_PER_PRIORITIZED_EMOJI,
    ).order(AggregatedEmojiTags.annotators_count).iter(projection=[AggregatedEmojiTags.emoji])
    for e in entries:
        emoji_utf = e.emoji.encode('utf-8')
        if emoji_utf not in emoji_esclusion_list:
            return emoji_utf
    return None

# returns annotatorsCount, tagsCount, stats
def getTaggingStats(userTaggingEntry):
    language = userTaggingEntry.language
    emoji_uni = userTaggingEntry.last_emoji
    aggregatedEmojiTags = getAggregatedEmojiTagsEntry(language, emoji_uni)
    if aggregatedEmojiTags:
        return  aggregatedEmojiTags.annotators_count, \
                aggregatedEmojiTags.tags_count, \
                aggregatedEmojiTags.tagsCountTable
    return 0, 0, {}

def getStatsFeedbackForTagging(userTaggingEntry, newTags):
    annotatorsCount, tagsCount, tagsCountDict = getTaggingStats(userTaggingEntry)
    logging.debug('stats: ' + str(tagsCountDict))
    msg = ''
    if tagsCount == 0:
        msg += "🏅 You are the first annotator of this term for this emoji!"
    else:
        msg += "There were {0} other people who provided terms for this emoji:\n".format(str(annotatorsCount))
        intersection = list(set(newTags) & set(tagsCountDict.keys()))
        if len(intersection)==0:
            msg += "🤔 So far, no other person has suggested any of the terms you have provided.\n"
            selected_stats = {
                tag: count
                for tag, count in tagsCountDict.iteritems() if count >= parameters.MIN_COUNT_FOR_TAGS_SUGGESTED_BY_OTHER_USERS
            }
            for k, v in sorted(selected_stats.items(), key=lambda x: x[1], reverse=True):
                msg += "  - {0} suggested: {1}\n".format(str(v), k)
        else:
            msg += "😊 Some of the terms you have proposed are matching with other people, " \
                   "and they will become available in the search!\n"
            selected_stats = {
                tag: count
                for tag, count in tagsCountDict.iteritems() if tag in intersection
            }
            for k, v in sorted(selected_stats.items(), key=lambda x: x[1], reverse=True):
                msg += "  - {0} agreed on: {1}\n".format(str(v), k)
    return msg

def getUserTagsForEmoji(language_utf, emoji_utf):
    language_uni = language_utf.decode('utf-8')
    emoji_uni = emoji_utf.decode('utf-8')
    aggregatedEmojiTags = getAggregatedEmojiTagsEntry(language_uni, emoji_uni)
    if not aggregatedEmojiTags:
        return None
    return {tag: count
            for tag, count in aggregatedEmojiTags.tagsCountTable.iteritems()
            if count >= parameters.MIN_COUNT_FOR_TAGS_SUGGESTED_BY_OTHER_USERS
    }


#future = acct.put_async()
#@ndb.transactional

###################
# MAIN CLASS AggregatedTagEmojis
###################

class AggregatedTagEmojis(ndb.Model):
    # id = language tag
    language = ndb.StringProperty()
    tag = ndb.StringProperty()
    emojiCountTable = ndb.PickleProperty() # defaultdict(int)

def getAggregatedTagEmojisId(language_utf, tag_utf):
    return language_utf + ' ' + tag_utf

def getAggregatedTagEmojisEntry(language_utf, tag_utf):
    unique_id = getAggregatedTagEmojisId(language_utf, tag_utf)
    return AggregatedTagEmojis.get_by_id(unique_id)

@ndb.transactional(retries=100, xg=True)
def addInAggregatedTagEmojis(userTaggingEntry):
    language_utf = userTaggingEntry.language.encode('utf-8')
    #emoji_utf = userTaggingEntry.last_emoji.encode('utf-8')
    last_emoji_utf = userTaggingEntry.last_emoji.encode('utf-8')
    tags = userTaggingEntry.emojiTagsTable[last_emoji_utf]
    for t in tags:
        unique_id = getAggregatedTagEmojisId(language_utf, t)
        aggregatedEmojisTags = AggregatedTagEmojis.get_by_id(unique_id)
        if not aggregatedEmojisTags:
            aggregatedEmojisTags = AggregatedTagEmojis(
                id=unique_id,
                parent=None,
                namespace=None,
                language=language_utf,
                emojiCountTable = defaultdict(int)
            )
        emoji_utf = userTaggingEntry.last_emoji.encode('utf-8')
        aggregatedEmojisTags.emojiCountTable[emoji_utf] +=1
        aggregatedEmojisTags.put()

def getUserEmojisForTag(language_utf, tag_utf):
    aggregatedTagEmojis = getAggregatedTagEmojisEntry(language_utf, tag_utf)
    if not aggregatedTagEmojis:
        return None
    return {emoji: count
            for emoji, count in aggregatedTagEmojis.emojiCountTable.iteritems()
            if count >= parameters.MIN_COUNT_FOR_TAGS_SUGGESTED_BY_OTHER_USERS
    }

# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

import logging
import key

import person

from collections import defaultdict


###################
# HELPER CLASS Tmp_UserTranslationTag
###################

class Tmp_UserTranslationTag(ndb.Model):
    #id = str(chat_id)
    last_mod = ndb.DateTimeProperty(auto_now=True)
    en_tag = ndb.StringProperty()
    emoji = ndb.StringProperty()
    language_tags = ndb.StringProperty(repeated=True)
    selected_tags = ndb.BooleanProperty(repeated=True) #0 reserved for none
    last_message_id = ndb.IntegerProperty()

def getTmpUserTranslationTag(chat_id):
    return Tmp_UserTranslationTag.get_by_id(str(chat_id))

def addTmpUserTranslationTag(chat_id, en_tag, emoji, language_tags, selected_tags, message_id):
    t = Tmp_UserTranslationTag(
        id=str(chat_id),
        en_tag = en_tag,
        emoji = emoji,
        language_tags = language_tags,
        selected_tags = selected_tags,
        last_message_id = message_id
    )
    t.put()
    return t

def deleteTmpUserTranslationTag(chat_id):
    t = Tmp_UserTranslationTag.get_by_id(str(chat_id))
    if t:
        t.key.delete()


###################
# MAIN CLASS TranslationTag
###################

SKIPPED_CONST_VALUE = '**SKIPPED**'

class UserTranslationTag(ndb.Model):
    timestamp = ndb.DateTimeProperty(auto_now=True)
    chat_id = ndb.IntegerProperty()
    language = ndb.StringProperty()
    emoji = ndb.StringProperty()
    en_tag = ndb.StringProperty()
    translation_tags = ndb.StringProperty(repeated=True, write_empty_list=True) #language specific translation, empty if none

def addTranslation(chat_id, language, emoji, en_tag, translation_tags):
    t = UserTranslationTag(
        chat_id = chat_id,
        language = language,
        emoji = emoji,
        en_tag = en_tag,
        translation_tags = translation_tags
    )
    t.put()

def wasEmojiTranslatedByPerson(person, emoji):
    emoji_uni = emoji.decode('utf-8')
    #logging.debug('Checking previous translation for {0} regarding language {1} and emoji {2}'
    #              .format(str(person.chat_id), person.getLanguage(), emoji))
    match = UserTranslationTag.query(UserTranslationTag.chat_id == person.chat_id,
                                     UserTranslationTag.language == person.language,
                                     UserTranslationTag.emoji == emoji_uni).get()
    alreadyTranslated = match!=None
    """
    if not alreadyTranslated:
        qry = match = TranslationTag.query(TranslationTag.chat_id == person.chat_id,
                                 TranslationTag.language == person.language)
        for e in qry:
            logging.debug('- No match in table for emoji {0}-{1}: {2} {3} {4}'.
                          format(emoji, e.emoji.encode('utf-8'),
                                 str(e.chat_id==person.chat_id),
                                 str(e.language==person.language),
                                 str(e.emoji==emoji_uni)))
    """
    return alreadyTranslated

def getNumberOfTranslationByPersonLanguage(person):
    return UserTranslationTag.query(UserTranslationTag.chat_id == person.chat_id,
                                    UserTranslationTag.language == person.language).count()

def getTranslationStats(person, emoji_uni, en_tag):
    dict_answers = defaultdict(int)
    count = 0
    qry = UserTranslationTag.query(UserTranslationTag.language == person.language,
                                   UserTranslationTag.emoji == emoji_uni,
                                   UserTranslationTag.en_tag == en_tag)
    for e in qry:
        translation_tag = e.translation_tags[0].encode('utf-8')
        if translation_tag == SKIPPED_CONST_VALUE:
            continue
        count += 1
        dict_answers[translation_tag] += 1
    return count, dict_answers
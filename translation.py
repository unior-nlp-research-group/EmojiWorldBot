# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key

###################
# HELPER CLASS
###################

class Tmp_UserTranslationTag(ndb.Model):
    #id = str(chat_id)
    last_mod = ndb.DateTimeProperty(auto_now=True)
    en_tag = ndb.StringProperty()
    emoji = ndb.StringProperty()
    language_tags = ndb.StringProperty(repeated=True)
    selected_tags = ndb.BooleanProperty(repeated=True) #0 reserved for none

def getTmpUserTranslationTag(chat_id):
    return Tmp_UserTranslationTag.get_by_id(str(chat_id))

def addTmpUserTranslationTag(chat_id, en_tag, emoji, language_tags, selected_tags):
    t = Tmp_UserTranslationTag(
        id=str(chat_id),
        en_tag = en_tag,
        emoji = emoji,
        language_tags = language_tags,
        selected_tags = selected_tags
    )
    t.put()
    return t

def deleteTmpUserTranslationTag(chat_id):
    Tmp_UserTranslationTag.get_by_id(str(chat_id)).key.delete()


###################
# MAIN CLASS
###################

class TranslationTag(ndb.Model):
    chat_id = ndb.IntegerProperty()
    language = ndb.StringProperty()
    emoji = ndb.StringProperty()
    en_tag = ndb.StringProperty()
    language_tags = ndb.StringProperty(repeated=True) #language specific translation, empty if none


def addTranslation(chat_id, language, emoji, en_tag, translation_tags):
    t = TranslationTag(
        chat_id = chat_id,
        language = language,
        emoji = emoji,
        en_tag = en_tag,
        translation_tags = translation_tags
    )
    t.put()

def deleteTranslation(chat_id, emoji, language):
    translation = TranslationTag.query(TranslationTag.chat_id == chat_id,
                                 TranslationTag.emoji == emoji,
                                 TranslationTag.language == language).get()
    translation.key.delete()

def wasEmojiTranslatedByPerson(chat_id, emoji, language):
    match = TranslationTag.query(TranslationTag.chat_id == chat_id,
                                 TranslationTag.emoji == emoji,
                                 TranslationTag.language == language).get()
    return match!=None

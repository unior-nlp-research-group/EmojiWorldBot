# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key

class Search(ndb.Model):
    chat_id = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now=True)
    language = ndb.StringProperty()
    searched_string = ndb.StringProperty()
    #returned_string_list = ndb.StringProperty(repeated=True)
    is_searched_emoji = ndb.BooleanProperty()
    inline_query = ndb.BooleanProperty()
    found_translation = ndb.BooleanProperty()


def addSearch(chat_id, language, searched_string, is_searched_emoji, inline_query, found_translation):
    s = Search(
        chat_id = chat_id,
        language = language,
        searched_string=searched_string,
        is_searched_emoji = is_searched_emoji,
        inline_query = inline_query,
        found_translation = found_translation
    )
    s.put()

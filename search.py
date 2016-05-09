# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key

class Search(ndb.Model):
    chat_id = ndb.IntegerProperty()
    date = ndb.DateTimeProperty(auto_now=True)
    language = ndb.StringProperty()
    searched_string = ndb.StringProperty()
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

def fixInlineQueryValues():
    qry = Search.query()
    totalCount = 0
    count = 0
    listOfUpdatedEntities = []
    for s in qry:
        if s.inline_query == None:
            s.inline_query = False
            listOfUpdatedEntities.append(s)
            count += 1
            totalCount += 1
        if (count == 200):
            ndb.put_multi(listOfUpdatedEntities)
            listOfUpdatedEntities = []
            count = 0
    ndb.put_multi(listOfUpdatedEntities)
    logging.debug('fixInlineQueryValues: updated elements ' + str(totalCount))
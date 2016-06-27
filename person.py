# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key
import languages
import json, jsonUtil

class Person(ndb.Model):
    chat_id = ndb.IntegerProperty()
    state = ndb.IntegerProperty(default=-1, indexed=True)
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    username = ndb.StringProperty()
    enabled = ndb.BooleanProperty(default=True)
    lang_code = ndb.StringProperty(default='eng')  # language code
    last_seen = ndb.DateTimeProperty(auto_now=True)

    def getFirstName(self):
        return self.name.encode('utf-8')

    def getLastName(self):
        return self.last_name.encode('utf-8')

    def getUserInfoString(self):
        info = self.getFirstName()
        if self.last_name:
            info += ' ' + self.getLastName()
        if self.username:
            info += ' @' + self.username
        info += ' ({0})'.format(str(self.chat_id))
        return info

    def getLanguageCode(self):
        return self.lang_code.encode('utf-8')

    def getLanguageName(self):
        #return self.language.encode('utf-8')
        return languages.getLanguageName(self.getLanguageCode())

    def setState(self, newstate, put=True):
        self.state = newstate
        if put:
            self.put()

    def setEnabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

    def setLanguageAndLangCode(self, index, put=False):
        self.lang_code = languages.ALL_LANG_CODES[index]
        self.language = languages.ALL_LANGUAGES[index]
        #logging.debug("changing language to {0} {1}".format(self.getLanguageCode(),self.getLanguageName()))
        if put:
            self.put()

    def updateUsername(self, username, put=False):
        if (self.username != username):
            self.username = username
            if put:
                self.put()


## --- end of class Person

def addPerson(chat_id, name, last_name, username, put=True):
    p = Person(
        id=str(chat_id),
        chat_id=chat_id,
        name=name,
        last_name = last_name,
        username = username
    )
    if put:
        p.put()
    return p

def getPersonByChatId(chat_id):
    return Person.get_by_id(str(chat_id))

def updateLanguageToDefault():
    toUpdate = Person.query().fetch()
    for ent in toUpdate:
        ent.language = 'English'
    ndb.put_multi(toUpdate)

def exportAllToJson(file):
    structure = []
    for e in Person.query().fetch():
        structure.append({
            "chat_id": e.chat_id,
            "name": e.name.encode('utf-8'),
            "last_name": e.last_name.encode('utf-8') if e.last_name else None,
            "username": e.username.encode('utf-8') if e.username else None
        })
    with open(file, 'w') as f:
        json.dump(structure, f, indent=4, ensure_ascii=False)
    print "Exported elements: " + str(len(structure))

def importAllFromJson(file):
    toAdd = []
    with open(file) as f:
        structure = jsonUtil.json_load_byteified(f)
        for e in structure:
            if Person.get_by_id(str(e['chat_id']))==None: #if not present
                print(str(e))
                toAdd.append(addPerson(e['chat_id'], e['name'], e['last_name'], e['username'], put = False))
    ndb.put_multi(toAdd)
    print "Added elements: " + str(len(toAdd))
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import logging
import key

class Person(ndb.Model):
    chat_id = ndb.IntegerProperty()
    state = ndb.IntegerProperty(default=-1, indexed=True)
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    username = ndb.StringProperty()
    enabled = ndb.BooleanProperty(default=True)
    #language_family = ndb.StringProperty() # to delete
    language = ndb.StringProperty()

    def getName(self):
        return self.name.encode('utf-8')

    def getLastName(self):
        return self.last_name.encode('utf-8')

    def getUserInfoString(self):
        info = self.getName()
        if self.last_name:
            info += ' ' + self.getLastName()
        if self.username:
            info += ' @' + self.username
        return info

    def getLanguage(self):
        return self.language.encode('utf-8')

    def setState(self, newstate, put=True):
        self.last_state = self.state
        self.state = newstate
        if put:
            self.put()

    def setEnabled(self, enabled, put=False):
        self.enabled = enabled
        if put:
            self.put()

    def setLanguage(self, language, put=False):
        self.language = language
        if put:
            self.put()

    def updateUsername(self, username, put=False):
        if (self.username != username):
            self.username = username
            if put:
                self.put()


## --- end of class Person

def addPerson(chat_id, name):
    p = Person(
        id=str(chat_id),
        name=name,
        chat_id=chat_id,
    )
    p.put()
    return p

def getPersonByChatId(chat_id):
    return Person.get_by_id(str(chat_id))

def deleteProp(prop_name):
    for ent in Person.query():
        if prop_name in ent._properties:
            del ent._properties[prop_name]
            ent.put()
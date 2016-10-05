# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

import logging
from collections import defaultdict

import time_util
from time import sleep

QUIZ_MANAGER_ID = "QUIZ_MANAGER"

class QuizManager(ndb.Model):
    quizOpen = ndb.BooleanProperty(default=False)
    quizManagerId = ndb.IntegerProperty()
    questionIndex = ndb.IntegerProperty(default=0)
    acceptingAnswers = ndb.BooleanProperty(default=False)
    questionStartTimestamps = ndb.PickleProperty()
    userAnswersTable = ndb.PickleProperty()

def initQuizManager():
    quizManager = QuizManager(id=QUIZ_MANAGER_ID)
    quizManager.put()
    return quizManager

def getQuizManager():
    return QuizManager.get_by_id(QUIZ_MANAGER_ID)

def startQuiz(quizManagerId):
    quizManager = getQuizManager()
    quizManager.quizManagerId = quizManagerId
    quizManager.quizOpen = True
    quizManager.questionIndex = 0
    quizManager.acceptingAnswers = False
    quizManager.questionStartTimestamps = []
    quizManager.userAnswersTable = {} #'name (chat_id)': {'correct': x, 'ellapsed': y, 'chat_id': id}
    quizManager.put()
    deleteAllAnswers()

def stopQuiz():
    quizManager = getQuizManager()
    quizManager.quizOpen = False
    quizManager.put()

def isQuizOpen():
    return getQuizManager().quizOpen

def getQuizAdminId():
    return getQuizManager().quizManagerId

def getQuizAdminName():
    import person
    quizManagerId = getQuizAdminId
    assert quizManagerId
    return person.getPersonByChatId(quizManagerId).getFirstName()


def addQuestion():
    quizManager = getQuizManager()
    quizManager.questionStartTimestamps.append(time_util.nowUnixTime())
    quizManager.acceptingAnswers = True
    quizManager.put()

def stopAcceptingAnswers():
    quizManager = getQuizManager()
    quizManager.acceptingAnswers = False
    quizManager.put()

def getCurrentQuestionStartTimestamps():
    quizManager = getQuizManager()
    timestamps = quizManager.questionStartTimestamps
    index = quizManager.questionIndex
    assert index < len(timestamps)
    return timestamps[quizManager.questionIndex]

def getUserAnswersTable():
    quizManager = getQuizManager()
    return quizManager.userAnswersTable

def getUserAnswersTableKey(name_utf, chat_id):
    return "{} ({})".format(name_utf, chat_id)

def getUserAnswersTableSorted(top_N = 5):
    quizManager = getQuizManager()
    userAnswersTable = quizManager.userAnswersTable
    # sort users by correct (reverse) and ellapsed time
    sortedUsers = sorted(userAnswersTable,
                         key=lambda k: (
                             -userAnswersTable[k]['correct'],
                             userAnswersTable[k]['ellapsed'])
                         )
    firstN_keys = sortedUsers[:top_N]
    firstN_chat_id = [userAnswersTable[x]['chat_id'] for x in firstN_keys]
    listEnum = list(enumerate(firstN_keys, start=1))
    summary = "Total questions: {}\n\n".format(quizManager.questionIndex)
    if len(firstN_keys)==0:
        summary += "Nobody has answered correctly to any question."
    else:
        summary += '\n'.join([
            '{} - {} - Correct: {} - Ellapsed: {}'.format(
                pos,
                name_chat_id,
                userAnswersTable[name_chat_id]['correct'],
                userAnswersTable[name_chat_id]['ellapsed']) for pos, name_chat_id in listEnum
        ])
    return firstN_chat_id, summary

def getUserScoreEllapsed(person, userAnswersTable):
    tableKey = getUserAnswersTableKey(person.getFirstLastName(), person.chat_id)
    if tableKey in userAnswersTable:
        value = userAnswersTable[tableKey]
        return value['correct'], value['ellapsed']
    else:
        return 0, 0

############################################
############################################
############################################

class UserAnswer(ndb.Model):
    # id = chat_id questionIndex
    chat_id = ndb.IntegerProperty()
    questionIndex = ndb.IntegerProperty()
    name = ndb.StringProperty()
    answer = ndb.StringProperty()
    correct = ndb.BooleanProperty()
    ellapsedSeconds = ndb.IntegerProperty()

    def getName(self):
        return self.name.encode('utf-8')

def getAnswerID(chat_id, questionIndex):
    return "{} {}".format(chat_id, questionIndex)

#---------------------
# RETURNS questionNumber, ellapsedSeconds where
# ellapsedSeconds >=0 if successful
# ellapsedSeconds == -1 if answers are not currently accepted
# ellapsedSeconds == -2 if user already answered to the question
#---------------------
def addAnswer(person, answer, answerTimestamp):
    quizManager = getQuizManager()
    questionIndex = quizManager.questionIndex
    questionNumber = questionIndex + 1
    if not quizManager.acceptingAnswers:
        return questionNumber, -1
    answerID = getAnswerID(person.chat_id, questionIndex)
    if UserAnswer.get_by_id(answerID)!=None:
        return questionNumber, -2
    questionTimestamp = quizManager.questionStartTimestamps[quizManager.questionIndex]
    ellapsedSeconds = answerTimestamp-questionTimestamp
    assert ellapsedSeconds >= 0
    answerEntry = UserAnswer(
        chat_id = person.chat_id,
        name = person.name,
        questionIndex = questionIndex,
        id=answerID,
        answer=answer,
        ellapsedSeconds=ellapsedSeconds
    )
    answerEntry.put()
    return questionNumber, ellapsedSeconds

def validateAnswers(correctAnswer):
    logging.debug("Validating answers")
    quizManager = getQuizManager()
    questionIndex = quizManager.questionIndex
    answers = UserAnswer.query(UserAnswer.questionIndex==questionIndex).fetch()
    userAnswersTable = quizManager.userAnswersTable
    resultTable = {} # chat_id: true|false
    correctNamesTime = {}
    for a in answers:
        a.correct = a.answer == correctAnswer
        logging.debug("{} {}".format(a.getName(), a.correct))
        resultTable[a.chat_id] = a.correct
        if a.correct:
            correctNamesTime[a.getName()] = a.ellapsedSeconds
            tableKey = getUserAnswersTableKey(a.getName(), a.chat_id)
            if tableKey in userAnswersTable.keys():
                userTotalCounts = userAnswersTable[tableKey]
            else:
                userTotalCounts = {'correct': 0, 'ellapsed': 0, 'chat_id': a.chat_id}
                userAnswersTable[tableKey] = userTotalCounts
            userTotalCounts['correct'] += 1
            userTotalCounts['ellapsed'] += a.ellapsedSeconds
    ndb.put_multi(answers)
    quizManager.questionIndex += 1
    quizManager.put()
    correctNamesTimeSortedKey = sorted(correctNamesTime, key=correctNamesTime.get)
    correctNamesTimeSorted = ["{} ({} sec)".format(k,correctNamesTime[k]) for k in correctNamesTimeSortedKey]
    #return resultTable, correctNamesTimeSorted
    return correctNamesTimeSorted

def deleteAllAnswers():
    delete_futures = ndb.delete_multi_async(
        UserAnswer.query().fetch(keys_only=True)
    )
    ndb.Future.wait_all(delete_futures)
    #assert UserAnswer.query().count()==0

def test():
    return
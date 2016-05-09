# -*- coding: utf-8 -*-

import logging
import urllib
import urllib2
import datetime
from datetime import datetime
from time import sleep
import re

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.ext import deferred

import json
import os
from collections import defaultdict
from random import randint

import key

import person
from person import Person

import search

import translation
from translation import Tmp_UserTranslationTag, TranslationTag

import util
import emojiUtil
import string
import unicodedata

import webapp2

# ================================
WORK_IN_PROGRESS = False
# ================================

BASE_URL = 'https://api.telegram.org/bot' + key.TOKEN + '/'

STATES = {
    1: 'Initial state - select language',
    3: 'Select text to emoji or emoji to text',
    4: 'Text to Emoji',
    5: 'Emoji to Text'
}

CANCEL = u'\U0000274C'.encode('utf-8')
CHECK = u'\U00002705'.encode('utf-8')
LEFT_ARROW = u'\U00002B05'.encode('utf-8')
RIGHT_ARROW = u'\U000027A1'.encode('utf-8')
UNDER_CONSTRUCTION = u'\U0001F6A7'.encode('utf-8')
FROWNING_FACE = u'\U0001F641'.encode('utf-8')
LETTERS = u'\U0001F520'.encode('utf-8')
SMILY = u'\U0001F60A'.encode('utf-8')
INFO = u'\U00002139'.encode('utf-8')

LETTERS_TO_EMOJI = LETTERS + ' ' + RIGHT_ARROW + ' ' + SMILY
EMOJI_TO_LETTERS = SMILY + ' ' + RIGHT_ARROW +  ' ' + LETTERS

BUTTON_ACCEPT = CHECK + " Accetta"
BUTTON_CONFIRM = CHECK + " CONFERMA"
BUTTON_CANCEL = CANCEL + " Annulla"
BUTTON_BACK = LEFT_ARROW + " Back"
BUTTON_BACK_CHANGE_LANGUAGE = LEFT_ARROW + " Change Language"
BUTTON_ESCI = CANCEL + " Exit"
BUTTON_INFO = INFO + " Info"
BUTTON_START = "🌎 START 🌍"
BUTTON_ALL_LANGUAGES = "🌏 ALL LANGUAGES 🌍"
BUTTON_INVITE_FRIEND = '👪 INVITE A FRIEND'

BUTTON_MATCHING_GAME = 'MATCHING GAME'

INFO = \
"""
@EmojiWorldBot is a multilingual dictionary that uses Emoji as a pivot for contributors among dozens of diverse languages.
Currently we support emoji-to-word and word-to-emoji for 72 languages imported from the unicode tables (see http://www.unicode.org/cldr/charts/29/annotations).

This is just a start!

Future releases will enable you to help us:
1. Add new languages
2. Add new terms for current languages (including country names for national flags)
3. Match language-to-language: using this bot to crowdsource (via gamification techniques) very accurate bilingual dictionaries between any two languages

EmojiWorldBot is a free public service produced by Federico Sangati (Netherlands), Martin Benjamin and Sina Mansour at Kamusi Project International and EPFL (Switzerland), Francesca Chiusaroli at University of Macerata (Italy), and Johanna Monti at University of Naples “L’Orientale” (Italy).

@EmojiWorldBot version 0.92
"""

TERMS_OF_SERVICE = \
"""
TERMS OF SERVICE:

You are invited to use and share @EmojiWorldBot at your pleasure. Through your use of the service, you agree that:

1. We make no guarantees about the accuracy of the data, and we are not liable for any problems you encounter from using the words you find here. We hope we are giving you good information, but you use it at your own risk.

2. We may keep records of your searches and contributions. We understand privacy and value it as highly as you do. We promise not to sell or share information that can be associated with your name, other than acknowledging any contributions you make to improving our data. We use the log files to learn from you and produce the best possible service. For example, if you search for a term that we don’t have, the log files let us know that we should consider adding it.

3. This is an interactive application that may send you messages from time to time. Messages might include service alerts such as feature updates, or contributor queries such as asking you to translate a new word to your language. We will do our best not to be annoying.

4. Any information you provide about your favorite languages is given freely and voluntarily, with no claims of copyright or ownership on your part, and no expectation of payment. We are free to use the data you share in any way we see fit (and thank you for it!).

If you don’t agree to our terms of service, please delete the bot from your telegram contacts and you’ll never hear from us again (unless you decide to come back 😉). If you are cool with the conditions stated above, please enjoy!

--

"""

INVITE_FRIEND_INSTRUCTION = \
"""
To invite your friends, please copy the following short note🗒and paste it into your chats, or forward ⏩ it directly (for instructions click on /howToForward):
"""

HOW_TO_FORWARD_A_MESSAGE = \
"""
How to forward a message on Telegram:

1 (Browser): left click on message and press 'forward' at screen bottom
1 (Desktop): right click on timestamp next to message and press 'forward'
1 (Mobile): long tap on a message

2: select the user you want to forward it to

"""

MESSAGE_FOR_FRIENDS = \
"""
Hi, I’ve been enjoying a cool new tool that helps me find emoji in _LANGUAGE_.
I think you’ll love 💕 it too.
Just click on @EmojiWorldBot to start!
"""

# ================================
# AUXILIARY FUNCTIONS
# ================================


def char_range(c1, c2):
    """Generates the characters from `c1` to `c2`, inclusive."""
    for c in xrange(ord(c1), ord(c2)+1):
        yield chr(c)

latin_letters= {}

def is_latin(uchr):
    try: return latin_letters[uchr]
    except KeyError:
         return latin_letters.setdefault(uchr, 'LATIN' in unicodedata.name(uchr))

def only_roman_chars(unistr):
    return all(is_latin(uchr)
           for uchr in unistr
           if uchr.isalpha()) # isalpha suggested by John Machin

manualNormChar = {
    u'ß': u'ss',
    u'æ': u'ae',
    u'Æ': u'ae',
    u'œ': u'oe',
    u'Œ': u'oe',
    u'ð': u'd',
    u'Ð': u'd',
    u'đ': u'd',
    u'ø': u'o',
    u'Ø': u'o',
    u'þ': u'th',
    u'Þ': u'th',
    u'ƒ': u'f',
    u'ı': u'i',
}

def replaceManualChars(text):
    return ''.join(manualNormChar[x] if x in manualNormChar.keys() else x for x in text)

def remove_accents_roman_chars(text):
    text_uni = text.decode('utf-8')
    if not only_roman_chars(text_uni):
        return text
    text_uni = replaceManualChars(text_uni)
    msg = ''.join(x for x in unicodedata.normalize('NFKD', text_uni) if (x==' ' or x in string.ascii_letters))
    return msg.encode('utf-8')

def normalizeString(text):
    return remove_accents_roman_chars(text.lower()).lower()

# ================================
# BUILDING DICTIONARIES
# ================================

EMOJI_TO_TEXT_DICTIONARIES = {}

for lang_file_json in os.listdir("EmojiLanguages"):
    if not lang_file_json.startswith("_"):
        with open("EmojiLanguages/"+lang_file_json) as f:
            EMOJI_TO_TEXT_DICTIONARIES[lang_file_json[:-5]] = {
                key.encode('utf-8'): [x.encode('utf-8') for x in value]
                for key, value in json.load(f).iteritems()
                }

with open("EmojiLanguages/_emojiDesc.json") as f:
    EMOJI_DESCRIPTIONS = {
        key.encode('utf-8'): value.encode('utf-8')
        for key, value in json.load(f).iteritems()
    }

with open("EmojiLanguages/_langFamLangFlag.json") as f:
    EMOJI_FAM_LANG_FLAG = json.load(f)


ALL_EMOJIS = EMOJI_DESCRIPTIONS.keys()

TEXT_TO_EMOJI_DICTIONARIES = {}

for lang, dict in EMOJI_TO_TEXT_DICTIONARIES.iteritems():
    lang_dictionary = defaultdict(lambda: [])
    for emoji, tags in dict.iteritems():
        for t in tags:
            t_norm = normalizeString(t)
            #t_norm = t.lower()
            lang_dictionary[t_norm].append(emoji) # adding the tag (could be multiple words)
            tagSplit = t_norm.split(' ')
            if len(tagSplit)>1:
                for word_tag in tagSplit:
                    lang_dictionary[word_tag].append(emoji) # adding each word in the tag
    TEXT_TO_EMOJI_DICTIONARIES[lang] = lang_dictionary

#list of list
ALL_LANGUAGES = [[l.encode('utf-8') for l in langDict.keys()] for langDict in EMOJI_FAM_LANG_FLAG.values()]
ALL_LANGUAGES = sorted([item for sublist in ALL_LANGUAGES for item in sublist])

ALL_LANGUAGES_LOWERCASE = [l.lower() for l in ALL_LANGUAGES]

ALL_LANGUAGES_COMMANDS = ['/' + item for item in ALL_LANGUAGES]
ALL_LANGUAGES_COMMANDS_LOWERCASE = [l.lower() for l in ALL_LANGUAGES_COMMANDS]
ALL_LANGUAGES_COMMANDS_AC = ['/' + item for item in ALL_LANGUAGES if item[0] in char_range('A','C')]
ALL_LANGUAGES_COMMANDS_DJ = ['/' + item for item in ALL_LANGUAGES if item[0] in char_range('D','J')]
ALL_LANGUAGES_COMMANDS_KP = ['/' + item for item in ALL_LANGUAGES if item[0] in char_range('K','P')]
ALL_LANGUAGES_COMMANDS_RZ = ['/' + item for item in ALL_LANGUAGES if item[0] in char_range('R','Z')]


#++++++++++++++++++++
# RANDOM FUNCTIONS
#++++++++++++++++++++

def getRandomTerm(emoji_text_dict):
    emoji = getRandomEmoji(emoji_text_dict)
    terms = emoji_text_dict[emoji]
    if not terms:
        return getRandomTerm(emoji_text_dict)
    else:
        return terms[randint(0, len(terms) - 1)]

def getRandomEmoji(emoji_text_dict):
    return emoji_text_dict.keys()[randint(0, len(emoji_text_dict) - 1)]


# ================================
# AUXILIARY FUNCTIONS
# ================================

def init_user(p, name, last_name, username):
    p.name = name
    p.last_name = last_name
    p.username = username
    p.enabled = True
    p.put()


def broadcast(msg, restart_user=False):
    qry = Person.query()
    count = 0
    for p in qry:
        if (p.enabled):
            count += 1
            if restart_user:
                restart(p)
            tell(p.chat_id, msg)
    logging.debug('broadcasted to people ' + str(count))


def getInfoCount():
    c = Person.query().count()
    msg = "We are " + str(c) + " people subscribed to EmojiWorldBot! "
    return msg


def tell_masters(msg):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg)

def tell(chat_id, msg, kb=None, markdown=False, inlineKeyboardMarkup=False):
    replyMarkup = {}
    replyMarkup['resize_keyboard'] = True
    if kb:
        if inlineKeyboardMarkup:
            replyMarkup['inline_keyboard'] = kb
        else:
            replyMarkup['keyboard'] = kb

    try:
        resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
            'chat_id': chat_id,
            'text': msg,  # .encode('utf-8'),
            'disable_web_page_preview': 'true',
            'parse_mode': 'Markdown' if markdown else '',
            # 'reply_to_message_id': str(message_id),
            'reply_markup': json.dumps(replyMarkup),
        })).read()
        logging.info('send response: ')
        logging.info(resp)
        sleep(0.050)  # no more than 20 messages per second
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = person.getPersonByChatId(chat_id)
            p.setEnabled(False)
            #logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))


##################################
# START OF STATE FUNCTIONS
##################################


# ================================
# RESTART
# ================================
def restart(p, msg=None):
    goToState1(p, msg)


# ================================
# GO TO STATE 1: initial state (select language family)
# ================================

def goToState1(p, input=None, setState=True):
    giveInstruction = input is None
    if giveInstruction:
        if WORK_IN_PROGRESS:
            tell(p.chat_id, UNDER_CONSTRUCTION + "Warning Master, system under maintanence.")
        reply_txt = 'Click button to list available languages, or be adventurous and type a language name (e.g., Swahili)'
        kb = [
            [ 'A-C', 'D-J', 'K-P', 'R-Z'],
            [BUTTON_ALL_LANGUAGES],
            [BUTTON_INVITE_FRIEND, BUTTON_INFO]
        ]
        tell(p.chat_id, reply_txt, kb)
        if setState:
            p.setState(1)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == 'A-C':
            allLanguagesCommmandsStr = ' '.join(ALL_LANGUAGES_COMMANDS_AC)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == 'D-J':
            allLanguagesCommmandsStr = ' '.join(ALL_LANGUAGES_COMMANDS_DJ)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == 'K-P':
            allLanguagesCommmandsStr = ' '.join(ALL_LANGUAGES_COMMANDS_KP)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == 'R-Z':
            allLanguagesCommmandsStr = ' '.join(ALL_LANGUAGES_COMMANDS_RZ)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == BUTTON_ALL_LANGUAGES:
            allLanguagesCommmandsStr = ' '.join(ALL_LANGUAGES_COMMANDS)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == BUTTON_INFO:
            tell(p.chat_id, INFO)
        elif input == BUTTON_INVITE_FRIEND:
            tell(p.chat_id, INVITE_FRIEND_INSTRUCTION)
            replaceWith = p.getLanguage() + ' and 70 other languages' if p.language else 'more than 70 languages'
            #logging.debug(replaceWith)
            msg = MESSAGE_FOR_FRIENDS.replace("_LANGUAGE_", replaceWith)
            tell(p.chat_id, msg)
        elif input == '/howToForward':
            tell(p.chat_id, HOW_TO_FORWARD_A_MESSAGE)
        else:
            if input.lower() in ALL_LANGUAGES_COMMANDS_LOWERCASE:
                p.setLanguage(ALL_LANGUAGES[ALL_LANGUAGES_COMMANDS_LOWERCASE.index(input.lower())])
                goToState2(p)
            elif input.lower() in ALL_LANGUAGES_LOWERCASE:
                p.setLanguage(ALL_LANGUAGES[ALL_LANGUAGES_LOWERCASE.index(input.lower())])
                goToState2(p)
            elif p.chat_id in key.MASTER_CHAT_ID:
                if input.startswith('/broadcast ') and len(input) > 11:
                    msg = input[11:]
                    logging.debug("Starting to broadcast " + msg)
                    deferred.defer(broadcast, msg, restart_user=False)
                elif input.startswith('/restartBroadcast ') and len(input) > 18:
                    msg = input[18:]
                    logging.debug("Starting to broadcast " + msg)
                    deferred.defer(broadcast, msg, restart_user=True)
                elif input.startswith('/normalize') and len(input) > 10:
                    tell(p.chat_id, 'Normalized: ' + normalizeString(input[10:]))
                elif input == '/fixInlineQueryValues':
                    deferred.defer(search.fixInlineQueryValues)
                    tell(p.chat_id, "FixInlineQuryValues procedure activated")
                elif input == '/getInfoCount':
                    tell(p.chat_id, getInfoCount())
                else:
                    tell(p.chat_id, FROWNING_FACE + " Sorry Master, I don't understand.")
            else:
                tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand.")

# ================================
# GO TO STATE 2: [text/emoji] -> [emoji/text]
# ================================

def goToState2(p, input=None, setState=True):
    giveInstruction = input is None
    text_emoji_dict = TEXT_TO_EMOJI_DICTIONARIES[p.getLanguage()]
    emoji_text_dict = EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
    if giveInstruction:
        randomTerm = getRandomTerm(emoji_text_dict)
        randomEmoji = getRandomEmoji(emoji_text_dict)
        reply_txt = 'Ok, you have chosen ' + p.getLanguage() + ".\n"
        reply_txt += 'Please insert a single emoji, e.g., ' + randomEmoji + ' '
        reply_txt += 'or a term (one or more words), e.g., ' + randomTerm
        kb = [[BUTTON_BACK_CHANGE_LANGUAGE]]
        #if not p.getLanguage().startswith('English'):
        #    kb.insert(0, [BUTTON_MATCHING_GAME])
        tell(p.chat_id, reply_txt, kb)
        if setState:
            p.setState(2)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == BUTTON_BACK_CHANGE_LANGUAGE:
            goToState1(p)
        #elif input == BUTTON_MATCHING_GAME and not p.getLanguage().startswith('English'):
        #    p.setState(3)
        #    goToState3(p, firstCall=True)
        else:
            input_norm = input
            if input not in emoji_text_dict.keys():
                input_norm = emojiUtil.getNormalizedEmoji(input)
            if input_norm in ALL_EMOJIS: #emoji_text_dict.keys():
                termList = set(emoji_text_dict[input_norm])
                if termList:
                    terms = ", ".join(termList)
                    tell(p.chat_id, "Found the following terms for " + input + ":\n" + terms)
                    logging.info(str(p.chat_id) + " searching emoji " + input_norm + " and getting terms " + terms)
                    search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=True, inline_query=False, found_translation=True)
                else:
                    tell(p.chat_id, "No terms found for the given emoji.")
                    logging.info(str(p.chat_id) + " searching emoji" + input_norm + " and getting #no_terms#")
                    search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=True, inline_query=False, found_translation=False)
            else:
                input_norm = normalizeString(input)
                if input_norm in text_emoji_dict.keys():
                    emojiList = set(text_emoji_dict[input_norm])
                    emojis = ", ".join(emojiList)
                    tell(p.chat_id, "Found the following emojis for '" + input + "':\n" + emojis)
                    logging.info(str(p.chat_id) + " searching term '" + input + "' and getting emojis " + emojis)
                    search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=False, inline_query=False, found_translation=True)
                else:
                    msg = "No emojis found for the given term, try again " \
                          "(the input has been recognized as a term, " \
                          "if you have entered an emoji it is not a standard one)."
                    tell(p.chat_id, msg)
                    logging.info(str(p.chat_id) + " searching term '" + input + "' and getting #no_emojis#")
                    search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=False, inline_query=False, found_translation=False)

# ================================
# GO TO STATE 3: trnslation matching game
# ================================

BUTTON_ZERO_NONE = '0 (NONE)'
BUTTON_EXIT_GAME = LEFT_ARROW + ' EXIT GAME'

def goToState3(p, input=None, firstCall = False):
    emoji_text_dict_eng = EMOJI_TO_TEXT_DICTIONARIES['English']
    emoji_text_dict = EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
    giveInstruction = input is None
    if giveInstruction:
        if firstCall:
            emoji, en_tag, language_tags = getEmojiTag(p, emoji_text_dict_eng, emoji_text_dict)
            language_tags.insert(0, 'NONE')
            selected_tags = [False] * len(language_tags)
            translation.addTmpUserTranslationTag(p.chat_id, en_tag, emoji, language_tags, selected_tags)
        else:
            tmp_t = translation.getTmpUserTranslationTag(p.chat_id)
            emoji = tmp_t.emoji.encode('utf-8')
            en_tag = tmp_t.en_tag.encode('utf-8')
            language_tags = [x.encode('utf-8') for x in tmp_t.language_tags]
            selected_tags = tmp_t.selected_tags
        reply_txt = 'Thanks for playing with us and helping matching English terms associated to emojis into ' + p.getLanguage() + ".\n\n"
        reply_txt += 'We have selected the following emoji ' + emoji + " and the associated English term '" + en_tag + "'\n\n"
        reply_txt += 'Please select all the ' + p.getLanguage() + " terms that are correct translations of '" + en_tag + "' or press on 'NONE' if none applies.\n\n"
        options = ['/' + str(n) + ' ' + x + ' ' + getActivationMark(selected_tags, n) for n, x in enumerate(language_tags, 0)]
        logging.debug('options: ' + str(options))
        reply_txt += '\n'.join(options)
        kb = util.distributeElementMaxSize([str(x) + ' ' + getActivationMark(selected_tags, x) for x in range(1,len(language_tags))])
        kb.insert(0, [BUTTON_ZERO_NONE + ' ' + getActivationMark(selected_tags, 0)])
        if (sum(selected_tags)>0):
            kb.append([BUTTON_CONFIRM])
        kb.append([BUTTON_EXIT_GAME])
        tell(p.chat_id, reply_txt, kb)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == BUTTON_EXIT_GAME:
            translation.deleteTmpUserTranslationTag(p.chat_id)
            goToState1(p)
        elif input == BUTTON_CONFIRM:
            tmp_t = translation.getTmpUserTranslationTag(p.chat_id)
            translation_tags = [tmp_t.language_tags[i] for i in range(0,len(tmp_t.language_tags)) if tmp_t.selected_tags[i]]
            translation.addTranslation(p.chat_id, p.getLanguage(), tmp_t.emoji, tmp_t.en_tag, translation_tags)
            translation.deleteTmpUserTranslationTag(p.chat_id)
        else:
            if input.startswith(BUTTON_ZERO_NONE):
                input = str(0)
            if input.startswith('/'):
                numberStr = input[1:]
            else:
                numberStr = input.split(' ')[0]
            tmp_t = translation.getTmpUserTranslationTag(p.chat_id)
            if util.representsIntBetween(numberStr, 0, len(tmp_t.language_tags)):
                number = int(numberStr)
                if number == 0:
                    tmp_t.selected_tags = [False] * len(tmp_t.language_tags)
                else:
                    tmp_t.selected_tags[0] = False
                tmp_t.selected_tags[number] = not tmp_t.selected_tags[number]
                tmp_t.put()
                goToState3(p, firstCall=False)
            else:
                tell(p.chat_id, "Not a valid index. The number should be between 0 and " + str(len(tmp_t.language_tags)))


def getEmojiTag(p, emoji_text_dict_eng, emoji_text_dict):
    while(True):
        randomEmoji = getRandomEmoji(emoji_text_dict_eng)
        lang_tag_set = emoji_text_dict[randomEmoji]
        if not lang_tag_set:
            continue # language doesn't have tags for that emoji
        if translation.wasEmojiTranslatedByPerson(p.chat_id, emoji, p.getLanguage()):
            continue
        en_tags = [x.encode('utf-8') for x in emoji_text_dict_eng[randomEmoji]]
        chosen_en_tag = en_tags[randint(0, len(en_tags)-1)].encode('utf-8')
        return randomEmoji, chosen_en_tag, lang_tag_set

def getActivationMark(bool_list, num):
    #return CHECK if bool_list[num] else CANCEL
    return CHECK if bool_list[num] else ''
    #return 'V' if bool_list[num] else 'X'

# ================================
# ================================
# ================================


class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(
                json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


# ================================
# INLINE QUERY
# ================================

EMOJI_PNG_URL = 'https://dl.dropboxusercontent.com/u/12016006/Emoji/png_one/'

def getEmojiThumbnailUrl(e):
    codePoints = '_'.join([str(hex(ord(c)))[2:] for c in e.decode('utf-8')])
    return EMOJI_PNG_URL + codePoints + ".png"

def createInlineQueryResultArticle(p, id, input_norm, query_offset):
    language = p.getLanguage() if p.language else 'English'
    text_emoji_dict = TEXT_TO_EMOJI_DICTIONARIES[language]
    #logging.debug('Replying to inline query for tag ' + tag)
    if input_norm in text_emoji_dict.keys():
        emojiList = list(set(text_emoji_dict[input_norm]))
        result = []
        i = 0
        query_offset_int = int(query_offset) if query_offset else 0
        start_index = 50 * query_offset_int
        end_index = start_index + 50
        hasMore = len(emojiList) > end_index
        emojiList = emojiList[start_index:end_index]
        for e in emojiList:
            result.append(
                {
                    'type': "article",
                    'id': str(id) + '/' + str(i),
                    'title': e,
                    'message_text': e,
                    'hide_url': True,
                    'thumb_url': getEmojiThumbnailUrl(e),
                }
            )
            i += 1
        next_offset = str(query_offset_int + 1) if hasMore else ''
        return next_offset, True, result
    else:
        result = [{
            'type': "article",
            'id': str(id) + '/0',
            'title': 'No emoji found for this tag in ' + language,
            'message_text': 'No emoji found for this tag in ' + language,
            'hide_url': True,
        }]
        return '', False, result


def answerInlineQuery(query_id, inlineQueryResults, next_offset):
    my_data = {
        'inline_query_id': query_id,
        'results': json.dumps(inlineQueryResults),
        'is_personal': True,
        'cache_time': 0, #default 300
        'next_offset': next_offset
    }
    resp = urllib2.urlopen(BASE_URL + 'answerInlineQuery',
                           urllib.urlencode(my_data)).read()
    logging.info('send response: ')
    logging.info(resp)


def dealWithInlineQuery(body):
    inline_query = body['inline_query']
    query_text = inline_query['query'].encode('utf-8').strip()
    if len(query_text)>0:
        query_id = inline_query['id']
        query_offset = inline_query['offset']
        chat_id = inline_query['from']['id']
        p = person.getPersonByChatId(chat_id)
        input_norm = normalizeString(query_text)
        next_offset, validQry, query_results = createInlineQueryResultArticle(p, query_id, input_norm, query_offset)
        answerInlineQuery(query_id, query_results, next_offset)
        if validQry and not query_offset:
            search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=False,
                             inline_query=True, found_translation=True)


# ================================
# ================================
# ================================

class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        # update_id = body['update_id']
        if 'inline_query' in body:
            dealWithInlineQuery(body)
        if 'message' not in body:
            return
        message = body['message']
        # message_id = message.get('message_id')
        # date = message.get('date')
        if "chat" not in message:
            return
        # fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']
        if "first_name" not in chat:
            return
        text = message.get('text').encode('utf-8') if "text" in message else ''
        name = chat["first_name"].encode('utf-8')
        last_name = chat["last_name"].encode('utf-8') if "last_name" in chat else None
        username = chat["username"] if "username" in chat else None
        location = message["location"] if "location" in message else None
        contact = message["contact"] if "contact" in message else None

        # u'contact': {u'phone_number': u'393496521697', u'first_name': u'Federico', u'last_name': u'Sangati',
        #             u'user_id': 130870321}
        # logging.debug('location: ' + str(location))

        def reply(msg=None, kb=None, markdown=False, inlineKeyboardMarkup=False):
            tell(chat_id, msg, kb, markdown, inlineKeyboardMarkup)

        p = ndb.Key(Person, str(chat_id)).get()

        if p is None:
            # new user
            logging.info("Text: " + text)
            if text == '/help':
                reply(INFO)
            elif text.startswith("/start"):
                p = person.addPerson(chat_id, name)
                reply("Hi " + name + ", " + "welcome to EmojiWorldBot!\n" + TERMS_OF_SERVICE)
                init_user(p, name, last_name, username)
                tell_masters("New user: " + p.getUserInfoString())
                restart(p)
            else:
                reply("Please press START or type /start")
                #reply("Something didn't work... please press START or type /startcontact @kercos")
        else:
            # known user
            p.updateUsername(username)
            if text == '/state':
                if p.state in STATES:
                    reply("You are in state " + str(p.state) + ": " + STATES[p.state])
                else:
                    reply("You are in state " + str(p.state))
            elif text in ["/start", "START"]:
                reply("Hi " + name + ", " + "welcome back to EmojiWorldBot!\n" + TERMS_OF_SERVICE)
                if not p.enabled:
                    p.setEnabled(True, put=False)
                restart(p)
            elif WORK_IN_PROGRESS and p.chat_id not in key.MASTER_CHAT_ID:
                reply(UNDER_CONSTRUCTION + " The system is under maintanance, please try later.")
            elif p.state == 1:
                goToState1(p, input=text)
            elif p.state == 2:
                goToState2(p, input=text)
            elif p.state == 3:
                goToState3(p, input=text)
            else:
                reply("There has been a problem (" + str(p.state).encode('utf-8') +
                      "). Please send a message to @kercos" + '\n' +
                      "You will be redirected to the initial screen.")
                restart(p)


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    #    ('/_ah/channel/connected/', DashboardConnectedHandler),
    #    ('/_ah/channel/disconnected/', DashboardDisconnectedHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)

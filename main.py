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
from random import randint, shuffle

import key

import util
import emojiUtil
import emojiTables
import languages

import person
from person import Person

import search

import translation
import tagging
import parameters

import webapp2

# ================================
WORK_IN_PROGRESS = False
# ================================

BASE_URL = 'https://api.telegram.org/bot' + key.TOKEN + '/'

STATES = {
    0:  'Change language',
    1:  'Home screen',
    2:  'Select text to emoji or emoji to text',
    3:  'Translation Game',
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

BUTTON_TEXT_TOFROM_EMOJI = '🔠 ↔ 😊'

BUTTON_ACCEPT = CHECK + " Accetta"
BUTTON_CONFIRM = "✔️ CONFIRM"
BUTTON_CANCEL = CANCEL + " Annulla"
BUTTON_BACK = LEFT_ARROW + " Back"
BUTTON_ESCI = CANCEL + " Exit"
BUTTON_INFO = INFO + " Info"
BUTTON_START = "🌎 START 🌍"
BUTTON_INVITE_FRIEND = '👪 INVITE A FRIEND'

BUTTON_TRANSLATION_GAME = '🕹 TRANSLATION'
BUTTON_TAGGING_GAME = '🕹 TAGGING'

BUTTON_CHANGE_LANGUAGE = "🌏 CHANGE LANGUAGE 🌍"
BUTTON_BACK_HOME_SCREEN = "⬅️ Back to 🏠🖥 home screen"

BULLET_POINT = '🔸'

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
Hi, I’ve been enjoying a cool new tool that helps me find emoji in *{0}* and 70 other languages.
I think you’ll love 💕 it too.
Just click on @EmojiWorldBot to start!
"""


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
            sleep(0.050)  # no more than 20 messages per second
    logging.debug('broadcasted to people ' + str(count))


def getInfoCount():
    c = Person.query().count()
    msg = "We are {0} people subscribed to EmojiWorldBot! ".format(str(c))
    return msg


def tell_masters(msg, markdown=False):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg, markdown=markdown)

def tell(chat_id, msg, kb=None, markdown=False, inlineKeyboardMarkup=False, hide_keyboard = False):
    replyMarkup = {}
    replyMarkup['resize_keyboard'] = True
    replyMarkup['hide_keyboard'] = hide_keyboard
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
        resp_json = json.loads(resp)
        return resp_json['result']['message_id']
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = person.getPersonByChatId(chat_id)
            p.setEnabled(False)
            #logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))

def tell_update(chat_id, msg, update_message_id, inline_kb=None, markdown=False):
    replyMarkup = {}

    if inline_kb:
        replyMarkup['inline_keyboard'] = inline_kb

    try:
        logging.debug("Sending update message: " + str(update_message_id))
        resp = urllib2.urlopen(BASE_URL + 'editMessageText', urllib.urlencode({
            'chat_id': chat_id,
            'message_id': update_message_id,
            'text': msg,  # .encode('utf-8'),
            'disable_web_page_preview': 'true',
            'parse_mode': 'Markdown' if markdown else '',
            'reply_markup': json.dumps(replyMarkup),
        })).read()
        logging.info('send response: ')
        logging.info(resp)
        logging.debug("Resp: " + resp)
    except urllib2.HTTPError, err:
        if err.code == 403:
            p = person.getPersonByChatId(chat_id)
            p.setEnabled(False)
            # logging.info('Disabled user: ' + p.name.encode('utf-8') + ' ' + str(chat_id))

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

INTRO_INSTRUCTIONS = \
"""
Your current language is set to *{0}*
Press on 🕹 for fun quizzes that will help grow the dictionary for your language!
Please insert a single emoji, e.g., {1} or a term (one or more words), e.g., *{2}*
"""

def goToState1(p, input=None, setState=True):
    giveInstruction = input is None
    if giveInstruction:
        if WORK_IN_PROGRESS:
            tell(p.chat_id, "🚧 Warning Master, system under maintanence.")
        emoji_text_dict = emojiTables.EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
        randomTerm = getRandomTerm(emoji_text_dict)
        randomEmoji = getRandomEmoji(emoji_text_dict)
        msg = INTRO_INSTRUCTIONS.format(p.getLanguage(), randomEmoji, randomTerm)
        kb = [[BUTTON_CHANGE_LANGUAGE]]
        kb_second_line = [BUTTON_TAGGING_GAME]
        if p.getLanguage()!='English':
            kb_second_line.append(BUTTON_TRANSLATION_GAME)
        kb.append(kb_second_line)
        kb.append([BUTTON_INVITE_FRIEND, BUTTON_INFO])
        markdown = '*' not in randomEmoji and '*' not in randomTerm
        tell(p.chat_id, msg, kb, markdown=markdown)
        if setState:
            p.setState(1)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == BUTTON_CHANGE_LANGUAGE:
            goToState0(p)
        #elif input == BUTTON_TEXT_TOFROM_EMOJI:
        #    goToState2(p)
        elif input == BUTTON_TRANSLATION_GAME and p.getLanguage()!='English':
            p.setState(3)
            logging.debug("Sending user to state 3")
            goToState3(p)
        elif input == BUTTON_TAGGING_GAME and p.getLanguage():
            p.setState(4)
            goToState4(p)
        elif input == BUTTON_INFO:
            tell(p.chat_id, INFO)
        elif input == BUTTON_INVITE_FRIEND:
            tell(p.chat_id, INVITE_FRIEND_INSTRUCTION)
            msg = MESSAGE_FOR_FRIENDS.format(p.getLanguage())
            tell(p.chat_id, msg)
        elif input == '/howToForward':
            tell(p.chat_id, HOW_TO_FORWARD_A_MESSAGE)
        #elif changeLanguageFromString(p, input):
        #    goToState1(p)
        elif p.chat_id in key.MASTER_CHAT_ID:
            dealWithMasterCommands(p, input)
        else:
            dealWithInputWordOrEmoji(p, input)


def dealWithMasterCommands(p, input):
    if input.startswith('/broadcast ') and len(input) > 11:
        msg = input[11:]
        logging.debug("Starting to broadcast " + msg)
        deferred.defer(broadcast, msg, restart_user=False)
    elif input.startswith('/restartBroadcast ') and len(input) > 18:
        msg = input[18:]
        logging.debug("Starting to broadcast " + msg)
        deferred.defer(broadcast, msg, restart_user=True)
    elif input.startswith('/normalize') and len(input) > 10:
        tell(p.chat_id, 'Normalized: ' + util.normalizeString(input[10:]))
    elif input == '/fixInlineQueryValues':
        deferred.defer(search.fixInlineQueryValues)
        tell(p.chat_id, "FixInlineQuryValues procedure activated")
    elif input == '/getInfoCount':
        tell(p.chat_id, getInfoCount())
    else:
        dealWithInputWordOrEmoji(p, input)

# ================================
# GO TO STATE 0: change language
# ================================
#http://www-01.sil.org/iso639-3/iso-639-3_Name_Index.tab

BUTTON_ACTIVE_LANGUAGES = "ACTIVE LANGUAGES"
BUTTON_ADD_LANGUAGES = "ADD LANGUAGE"

LANGUAGE_LIST_URL = "http://www-01.sil.org/iso639-3/iso-639-3_Name_Index.tab"

ADD_LANGUAGE_INSTRUCTIONS = \
"""
Can you help build the dictionary for a language you don't see on our list? \
Please find its name and *3 letter code* on the list \
in this [language code list]({0}), and then type

*/activate [code]*

For example, if your language is "Zuni", type */activate zun*, \
and we will get back to you with more information.
""".format(LANGUAGE_LIST_URL)

def goToState0(p, input=None, setState=True):
    giveInstruction = input is None
    if giveInstruction:
        reply_txt = 'Your current language is *{0}*\n'.format(p.getLanguage())
        reply_txt += 'Click button to list available languages, or be adventurous and type a language name (e.g., Swahili)'
        kb = [
            [ 'A-C', 'D-J', 'K-P', 'R-Z'],
            [BUTTON_ACTIVE_LANGUAGES, BUTTON_ADD_LANGUAGES],
            [BUTTON_BACK_HOME_SCREEN]
        ]
        tell(p.chat_id, reply_txt, kb, markdown=True)
        if setState:
            p.setState(0)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == 'A-C':
            allLanguagesCommmandsStr = ' '.join(languages.ALL_LANGUAGES_COMMANDS_AC)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == 'D-J':
            allLanguagesCommmandsStr = ' '.join(languages.ALL_LANGUAGES_COMMANDS_DJ)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == 'K-P':
            allLanguagesCommmandsStr = ' '.join(languages.ALL_LANGUAGES_COMMANDS_KP)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == 'R-Z':
            allLanguagesCommmandsStr = ' '.join(languages.ALL_LANGUAGES_COMMANDS_RZ)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == BUTTON_ACTIVE_LANGUAGES:
            allLanguagesCommmandsStr = ' '.join(languages.ALL_LANGUAGES_COMMANDS)
            tell(p.chat_id, allLanguagesCommmandsStr)
        elif input == BUTTON_ADD_LANGUAGES:
            tell(p.chat_id, ADD_LANGUAGE_INSTRUCTIONS, markdown=True)
        elif input == BUTTON_BACK_HOME_SCREEN:
            goToState1(p)
        elif input.startswith("/activate"):
            if len(input)!=13:
                tell(p.chat_id, "Sorry you didn't insert a 3 letter code", markdown=True)
            else:
                new_language_code = input[9:].strip()
                if len(new_language_code)!=3:
                    tell(p.chat_id, "Sorry you didn't insert a 3 letter code", markdown=True)
                else:
                    msg_user = "Thanks {0} for your help, will be back to you with " \
                          "more info about the language you would like to see in @EmojiWorldBot".format(p.getName())
                    tell(p.chat_id, msg_user, markdown=True)
                    msg_masters = "The user {0} has requested to inser language {1}. Please go to " \
                                  "[language code list]({2}).".format(p.getUserInfoString(), new_language_code, LANGUAGE_LIST_URL)
                    tell_masters(msg_masters, markdown=True)
        else:
            if changeLanguageFromString(p, input):
                goToState1(p)
            else:
                tell(p.chat_id, FROWNING_FACE +
                     " Sorry, I don't recognize this as a name of a language, please contact @kercos for support.")

def changeLanguageFromString(p, input):
    normInput = util.normalizeString(input)
    if normInput in languages.ALL_LANGUAGES_COMMANDS_LOWERCASE:
        p.setLanguage(languages.ALL_LANGUAGES[languages.ALL_LANGUAGES_COMMANDS_LOWERCASE.index(normInput)])
        return True
    if normInput in languages.ALL_LANGUAGES_LOWERCASE:
        p.setLanguage(languages.ALL_LANGUAGES[languages.ALL_LANGUAGES_LOWERCASE.index(normInput)])
        return True
    return False


# ================================
# GO TO STATE 2: [text/emoji] -> [emoji/text]
# ================================

def goToState2(p, input=None, setState=True):
    giveInstruction = input is None
    logging.debug("p language: " + str(p.language))
    if giveInstruction:
        emoji_text_dict = emojiTables.EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
        randomTerm = getRandomTerm(emoji_text_dict)
        randomEmoji = getRandomEmoji(emoji_text_dict)
        reply_txt = 'Your current language is set to ' + p.getLanguage() + ".\n"
        reply_txt += 'Please insert a single emoji, e.g., ' + randomEmoji + ' '
        reply_txt += 'or a term (one or more words), e.g., ' + randomTerm
        kb = [[BUTTON_BACK_HOME_SCREEN]]
        tell(p.chat_id, reply_txt, kb)
        if setState:
            p.setState(2)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == BUTTON_BACK_HOME_SCREEN:
            goToState1(p)
        else:
            dealWithInputWordOrEmoji(p, input)

def dealWithInputWordOrEmoji(p, input):
    text_emoji_dict = emojiTables.TEXT_TO_EMOJI_DICTIONARIES[p.getLanguage()]
    emoji_text_dict = emojiTables.EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
    input_norm = input
    if input not in emoji_text_dict.keys():
        input_norm = emojiUtil.getNormalizedEmoji(input)
    if input_norm in emojiTables.ALL_EMOJIS:  # emoji_text_dict.keys():
        termList = emoji_text_dict[input_norm]
        userTagsForEmojiDict = tagging.getUserTagsForEmoji(p.getLanguage(), input_norm)
        if userTagsForEmojiDict:
            termList.extend(userTagsForEmojiDict.keys())
        if termList:
            terms = ", ".join(termList)
            tell(p.chat_id, "Found the following terms for " + input + ":\n" + terms)
            #logging.info(str(p.chat_id) + " searching emoji " + input_norm + " and getting terms " + terms)
            search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=True, inline_query=False,
                             found_translation=True)
        else:
            tell(p.chat_id, "No terms found for the given emoji.")
            #logging.info(str(p.chat_id) + " searching emoji" + input_norm + " and getting #no_terms#")
            search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=True, inline_query=False,
                             found_translation=False)
    else:
        input_norm = util.normalizeString(input)
        tagsList = text_emoji_dict.keys()
        userEmojisForTagDict = tagging.getUserEmojisForTag(p.getLanguage(), input_norm)
        if userEmojisForTagDict:
            tagsList.extend(userEmojisForTagDict.keys())
        if input_norm in tagsList:
            emojiList = set(text_emoji_dict[input_norm])
            emojis = ", ".join(emojiList)
            tell(p.chat_id, "Found the following emojis for '" + input + "':\n" + emojis)
            #logging.info(str(p.chat_id) + " searching term '" + input + "' and getting emojis " + emojis)
            search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=False, inline_query=False,
                             found_translation=True)
        else:
            msg = "No emojis found for the given term, try again " \
                  "(the input has been recognized as a term, " \
                  "if you have entered an emoji it is not a standard one)."
            tell(p.chat_id, msg)
            #logging.info(str(p.chat_id) + " searching term '" + input + "' and getting #no_emojis#")
            search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=False, inline_query=False,
                             found_translation=False)


# ================================
# GO TO STATE 3: trnslation matching game updatede mode single answer
# ================================

BUTTON_NONE = '✖️ NONE of the options'
BUTTON_EXIT_GAME = LEFT_ARROW + ' EXIT GAME'
BUTTON_SKIP_GAME = RIGHT_ARROW + " SKIP"
BUTTON_PLAY_AGAIN = 'PLAY AGAIN'

TRANSLATION_GAME_INSTRUCTIONS = \
"""
⭐⭐⭐⭐⭐
Thanks for playing with us and helping to translate English terms associated with emojis into {0}.

We have selected the following emoji {1} and the associated English term *{2}*.

Please select the {0} term that is the EXACT TRANSLATION of *{2}* or 'NONE of the options' if you \
think that none of them is correct. If you think there are more equally correct answers, choose one of them.

What is the correct translation of *{2}*?
"""

def goToState3(p, input=None, inlineButtonText=None, userTranslationTagEntry = None, resend=False, newMessage = False):
    #logging.debug("goToState3 input={0} inlinebuttonText={1} userTranslationTagEntry={2} resend={3}".
    #              format(input, inlineButtonText, str(userTranslationTagEntry), str(resend)))
    giveInstruction = input is None and inlineButtonText is None
    #logging.debug("goToState3 giveInstruction={0}".format(str(giveInstruction)))
    if giveInstruction:
        newMessage = newMessage or userTranslationTagEntry is None
        emoji_text_dict_src = emojiTables.EMOJI_TO_TEXT_DICTIONARIES['English']
        emoji_text_dict_dst = emojiTables.EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
        if not userTranslationTagEntry:
            userTranslationTagEntry = translation.getOrInsertUserTranslationTagEntry(p, src_language='English')
            numTranslations = 0
        else:
            numTranslations = userTranslationTagEntry.getNumberOfTranslatedEmoji()
        if (numTranslations >= parameters.MAX_EMOJI_FOR_ANNOTATION_PER_PERSON_PER_LANGUAGE):
            msg = "You have provided all the tagging we needed for {0}!\n" \
                  "Thanks a lot for your help! 🙏\n".format(p.getLanguage())
            tell(p.chat_id, msg)
            sleep(2)
            goToState1(p)
            return
        if resend:
            emoji = userTranslationTagEntry.last_emoji.encode('utf-8')
            chosen_src_tag = userTranslationTagEntry.last_src_tag.encode('utf-8')
            dst_tag_set = emoji_text_dict_dst[emoji]
        else:
            emoji, chosen_src_tag, dst_tag_set, random = getNextEmojiForTranslation(
                emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry)
            #logging.debug("Emoji: {0} src_tag: {1} dst_tag: {2} random: {3}".
            #            format(emoji, chosen_src_tag, str(dst_tag_set), str(random)))
            userTranslationTagEntry.setLastEmojiAndSrcTag(emoji, chosen_src_tag, random)
        shuffle(dst_tag_set)
        userTranslationTagEntry.dst_tag_set = dst_tag_set # set destination tag set
        markdown = '*' not in emoji and '*' not in chosen_src_tag
        reply_txt = TRANSLATION_GAME_INSTRUCTIONS.format(p.getLanguage(), emoji, chosen_src_tag)
        options = [BULLET_POINT + ' ' + str(n) + ': ' + x for n, x in enumerate(dst_tag_set, 1)]
        #logging.debug('options: ' + str(options))
        reply_txt += '\n'.join(options)
        kb = util.distributeElementMaxSize([str(x) for x in range(1,len(dst_tag_set)+1)])
        kb.insert(0, [BUTTON_NONE])
        kb.append([BUTTON_SKIP_GAME])
        kb_inline = convertKeyboardToInlineKeyboard(kb)
        if newMessage:
            tell(p.chat_id, "Preparing the game...", kb=[[BUTTON_EXIT_GAME]])
        if newMessage or resend:
            last_message_id = tell(p.chat_id, reply_txt, kb_inline, inlineKeyboardMarkup=True, markdown=markdown)
            userTranslationTagEntry.last_message_id = last_message_id # set last message id
        else:
            last_message_id = userTranslationTagEntry.last_message_id
            tell_update(p.chat_id, reply_txt, last_message_id, kb_inline, markdown=markdown)
        userTranslationTagEntry.put()
    else:
        userTranslationTagEntry = translation.getUserTranslationEntry(p)
        if not userTranslationTagEntry:
            tell(p.chat_id, "Sorry, something went wrong, if the problem persists contact @kercos")
            return
        elif inlineButtonText:
            logging.debug('Receiving inlineButtonText')
            if inlineButtonText == BUTTON_SKIP_GAME:
                userTranslationTagEntry.addTranslationToLastEmojiSrcTag(None)
                translation.addInAggregatedEmojiTranslations(userTranslationTagEntry)
                goToState3(p, userTranslationTagEntry=userTranslationTagEntry)
            else:
                if inlineButtonText == BUTTON_NONE:
                    inlineButtonText = str(0)
                number = int(inlineButtonText)
                if number>0:
                    translation_tag = userTranslationTagEntry.dst_tag_set[number - 1].encode('utf-8')
                else:
                    translation_tag = ''
                msg = "Thanks for your input! 🙏\n" + \
                      translation.getStatsFeedbackForTranslation(userTranslationTagEntry, translation_tag)
                userTranslationTagEntry.addTranslationToLastEmojiSrcTag(translation_tag)
                translation.addInAggregatedEmojiTranslations(userTranslationTagEntry)
                tell_update(p.chat_id, msg, userTranslationTagEntry.last_message_id)
                sleep(3)
                goToState3(p, userTranslationTagEntry=userTranslationTagEntry, newMessage= True)
        elif input == BUTTON_EXIT_GAME:
            tell_update(p.chat_id, "Thanks for your help!", userTranslationTagEntry.last_message_id)
            sleep(2)
            goToState1(p)
        else:
            tell_update(p.chat_id, "Game interrupted", userTranslationTagEntry.last_message_id)
            tell(p.chat_id, "Not a valid input, please use only the buttons.")
            sleep(2)
            goToState1(p)
            #goToState3(p, userTranslationTagEntry=userTranslationTagEntry, resend=True)


def getNextEmojiForTranslation(emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry, forceRandom=False):
    emoji = ''
    if not forceRandom and not userTranslationTagEntry.hasSeenEnoughKnownEmoji():
        emoji, chosen_src_tag = translation.getPrioritizedEmojiSrcTagForUser(userTranslationTagEntry)
        if emoji is None:
            return getNextEmojiForTranslation(
                emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry, forceRandom=True)
        random = False
    else:
        random = True
        while True:
            emoji = getRandomEmoji(emoji_text_dict_dst)
            alreadyTranslated = userTranslationTagEntry.wasEmojiTranslated(emoji)
            if not alreadyTranslated:
                src_tag_set = emoji_text_dict_src[emoji]
                chosen_src_tag = src_tag_set[randint(0, len(src_tag_set) - 1)]
                break
    dst_tag_set = emoji_text_dict_dst[emoji]
    if not dst_tag_set:
        return getNextEmojiForTranslation(
            emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry, forceRandom=True)
    return emoji, chosen_src_tag, dst_tag_set, random

def makeCallbackQueryButton(text):
    return {
        'text': text,
        'callback_data': text,
    }

def convertKeyboardToInlineKeyboard(kb):
    result = []
    for l in kb:
        result.append([makeCallbackQueryButton(b) for b in l])
    return result


# ================================
# GO TO STATE 4: tagging game
# ================================

BUTTON_OR_TYPE_SKIP_GAME = RIGHT_ARROW + " SKIP (or type /skip)"

def goToState4(p, input=None, userTaggingEntry=None):
    emoji_text_dict = emojiTables.EMOJI_TO_TEXT_DICTIONARIES[p.getLanguage()]
    giveInstruction = input is None
    if giveInstruction:
        if not userTaggingEntry:
            userTaggingEntry = tagging.getOrInsertUserTaggingEntry(p)
            numTagging = 0
        else:
            numTagging = userTaggingEntry.getNumberOfTaggedEmoji()
        if (numTagging >= parameters.MAX_EMOJI_FOR_ANNOTATION_PER_PERSON_PER_LANGUAGE):
            msg = "You have provided all the tagging we needed for {0}!\n" \
                  "Thanks a lot for your help! 🙏\n".format(p.getLanguage())
            tell(p.chat_id, msg)
            sleep(1)
            goToState1(p)
            return
        emoji, random = getNextEmojiForTagging(emoji_text_dict, userTaggingEntry)
        userTaggingEntry.setLastEmoji(emoji, random)
        language_tags = emoji_text_dict[emoji]
        english_tags = emojiTables.ENGLISH_EMOJI_TO_TEXT_DICTIONARY[emoji]
        language_tags_str = ', '.join(language_tags)
        english_tags_str = ', '.join(english_tags)
        language_tags_markdown = ["*{0}*".format(t) for t in language_tags]
        english_tags_markdown = ["*{0}*".format(t) for t in english_tags]
        shuffle(language_tags_markdown)
        shuffle(english_tags_markdown)
        language_tags_markeddown_str = ', '.join(language_tags_markdown)
        english_tags_markeddown_str = ', '.join(english_tags_markdown)
        markdown = '*' not in emoji and '*' not in language_tags_str and '*' not in english_tags_str
        if p.getLanguage()=='English':
            english_tags_markeddown_str = None
        reply_txt = getTaggingGameInstruction(p.getLanguage(), emoji,
                                              language_tags_markeddown_str, english_tags_markeddown_str)
        kb= [[BUTTON_OR_TYPE_SKIP_GAME],[BUTTON_EXIT_GAME]]
        tell(p.chat_id, reply_txt, kb, markdown=markdown)
    else:
        userTaggingEntry = tagging.getUserTaggingEntry(p)
        if not userTaggingEntry:
            tell(p.chat_id, "Sorry, something got wrong, if the problem persists contact @kercos")
            return
        if input==BUTTON_OR_TYPE_SKIP_GAME or input.lower()=="/skip":
            userTaggingEntry.addTagsToLastEmoji([])
            tagging.addInAggregatedEmojiTags(userTaggingEntry)
            tell(p.chat_id, "🤔 Sending you a new emoji ...")
            sleep(1)
            goToState4(p, userTaggingEntry=userTaggingEntry)
        elif input == BUTTON_EXIT_GAME:
            tell(p.chat_id, "Thanks for your help 🙏, hope you had a good time! 🎉")
            sleep(1)
            goToState1(p)
        else:
            proposedTags = [i.strip() for i in input.split(',')]
            currentTags = emoji_text_dict[userTaggingEntry.getLastEmoji()]
            newTags = list(set(proposedTags) - set(currentTags))
            if '' in newTags:
                newTags.remove('')
            if newTags:
                newTagsStr = ', '.join(newTags)
                newTagsStrMarkdown = ', '.join(["*{0}*".format(t) for t in newTags])
                markdown = '*' not in newTagsStr
                msg = "You proposed the following new terms: {0}\n".format(newTagsStrMarkdown)
                msg += "Thanks for your input! 🙏\n" + \
                      tagging.getStatsFeedbackForTagging(userTaggingEntry, newTags)
                tell(p.chat_id, msg, markdown=markdown)
                userTaggingEntry.addTagsToLastEmoji(newTags)
                tagging.addInAggregatedEmojiTags(userTaggingEntry)
                tagging.addInAggregatedTagEmojis(userTaggingEntry)
                sleep(1)
                goToState4(p, userTaggingEntry=userTaggingEntry)
            else:
                userTaggingEntry.addTagsToLastEmoji([])
                tagging.addInAggregatedEmojiTags(userTaggingEntry)
                tell(p.chat_id, "😒 You input doesn't contain any new term.")
                sleep(1)
                goToState4(p, userTaggingEntry=userTaggingEntry)

def getTaggingGameInstruction(language, emoji, language_tags_markeddown_str, english_tags_markeddown_str):
    msg = "⭐⭐⭐⭐⭐\n"
    msg += "Thanks for playing with us and helping to tag emoji in {0}.\n\n".format(language)
    msg += "We have selected the following emoji {0}.\n".format(emoji)
    if language_tags_markeddown_str:
        msg += "It is currently associated with the following {0} terms: {1}, " \
               "which you cannot reuse.\n".format(language, language_tags_markeddown_str)
    else:
        msg += "Currently, there are no official terms associated with this emoji.\n"
    if english_tags_markeddown_str:
        msg += "You can get inspired by the English terms: {0}\n".format(english_tags_markeddown_str)
    msg += "\nCan you think of new {0} terms that other people would associate to {1}? ".format(language, emoji)
    msg += "Please type your suggested terms separated by comma [,] e.g., *term1*, *term2*, *term3*."
    return msg

def getNextEmojiForTagging(emoji_text_dict, userTaggingEntry):
    if not userTaggingEntry.hasSeenEnoughKnownEmoji():
        emoji = tagging.getPrioritizedEmojiForUser(userTaggingEntry)
        if emoji:
            return emoji, False
    while True:
        randomEmoji = getRandomEmoji(emoji_text_dict)
        if userTaggingEntry.wasEmojiTagged(randomEmoji):
            continue
        return randomEmoji, True


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
    text_emoji_dict = emojiTables.TEXT_TO_EMOJI_DICTIONARIES[language]
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
        input_norm = util.normalizeString(query_text)
        next_offset, validQry, query_results = createInlineQueryResultArticle(p, query_id, input_norm, query_offset)
        answerInlineQuery(query_id, query_results, next_offset)
        if validQry and not query_offset:
            search.addSearch(p.chat_id, p.language, input_norm, is_searched_emoji=False,
                             inline_query=True, found_translation=True)

# ================================
# CALLBACK QUERY
# ================================

def dealWithCallbackQuery(body):
    callback_query = body['callback_query']
    data = callback_query['data'].encode('utf-8')
    chat_id = callback_query['from']['id']
    p = person.getPersonByChatId(chat_id)
    goToState3(p, inlineButtonText=data)

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
        if 'callback_query' in body:
            dealWithCallbackQuery(body)
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
        #location = message["location"] if "location" in message else None
        #contact = message["contact"] if "contact" in message else None

        # u'contact': {u'phone_number': u'393496521697', u'first_name': u'Federico', u'last_name': u'Sangati',
        #             u'user_id': 130870321}
        # logging.debug('location: ' + str(location))

        def reply(msg=None, kb=None, markdown=False, inlineKeyboardMarkup=False):
            tell(chat_id, msg, kb, markdown, inlineKeyboardMarkup)

        p = person.getPersonByChatId(chat_id)
        #ndb.Key(Person, str(chat_id)).get()

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
                reply("Please press START or type /start or contact @kercos for support")
                #reply("Something didn't work... please press START or type /startcontact @kercos")
        else:
            # known user
            #logging.debug("Name {0} state {1}".format(p.getName(), str(p.chat_id)))
            p.updateUsername(username)
            if WORK_IN_PROGRESS and p.chat_id not in key.DEV_CHAT_ID:
                reply(UNDER_CONSTRUCTION + " The system is under maintanance, please try later.")
            elif text == '/state':
                if p.state in STATES:
                    reply("You are in state " + str(p.state) + ": " + STATES[p.state])
                else:
                    reply("You are in state " + str(p.state))
            elif text in ["/start", "START"]:
                reply("Hi " + name + ", " + "welcome back to EmojiWorldBot!\n" + TERMS_OF_SERVICE)
                if not p.enabled:
                    p.setEnabled(True, put=False)
                restart(p)
            elif p.state == 0:
                goToState0(p, input=text)
            elif p.state == 1:
                goToState1(p, input=text)
            elif p.state == 2:
                goToState2(p, input=text)
            elif p.state == 3:
                goToState3(p, input=text)
            elif p.state == 4:
                goToState4(p, input=text)
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

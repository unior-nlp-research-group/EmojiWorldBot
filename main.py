# -*- coding: utf-8 -*-

# Set up requests
# see https://cloud.google.com/appengine/docs/standard/python/issue-requests#issuing_an_http_request
import requests_toolbelt.adapters.appengine
requests_toolbelt.adapters.appengine.monkeypatch()
#disable warnings
import requests
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.contrib.appengine.AppEnginePlatformWarning
)

import logging
from time import sleep

# standard app engine imports
from google.appengine.ext import deferred
from google.appengine.ext.db import datastore_errors

import json
from random import shuffle
import requests

import key

import utility
import emojiUtil
import emojiTables
import languages

import person
from person import Person

import search
import translation
import userTagging
import parameters
import quizGame

import webapp2

# ================================
WORK_IN_PROGRESS = False
FUTURO_REMOTO_ON = False and key.TEST_MODE == False
# ================================

BASE_URL = 'https://api.telegram.org/bot' + key.TOKEN + '/'

STATES = {
    0:  'Change language',
    1:  'Home screen',
    2:  'Select text to emoji or emoji to text',
    3:  'Translation Game',
    4:  'Tagging Game',
    50: 'Futuro Remoto',
    51:   'Quiz Participants',
    52:   'Quiz Admin'
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
INVISIBLE_CHAR = u"\u2063".encode('utf-8')
#INVISIBLE_CHAR = b'\xE2\x81\xA3'
BULLET_BLUE = '🔹'
BULLET_ORANGE = '🔸'

BUTTON_TEXT_TOFROM_EMOJI = '🔠 ↔ 😊'

BUTTON_ACCEPT = CHECK + " Accetta"
BUTTON_CONFIRM = "✔️ CONFIRM"
BUTTON_CANCEL = CANCEL + " Annulla"
BUTTON_BACK = LEFT_ARROW + " Back"
BUTTON_ESCI = CANCEL + " Exit"
BUTTON_INFO = INFO + " INFO"
BUTTON_START = "🌎 START 🌍"
BUTTON_INVITE_FRIEND = '👪 INVITE A FRIEND'

BUTTON_TAGGING_GAME = 'PLAY 🐣'
BUTTON_TRANSLATION_GAME = 'PLAY 🐥🐥🐥'

"""
BUTTON_TRANSLATION_GAME = '🕹 '
BUTTON_TAGGING_GAME = '🕹 TAGGING'
"""

BUTTON_CHANGE_LANGUAGE = "🌏 Change Language 🌍"
BUTTON_BACK_HOME_SCREEN = "⬅️ Back to 🏠🖥 home screen"

BUTTON_OR_TYPE_SKIP_GAME = RIGHT_ARROW + " SKIP (or type /skip)"
BUTTON_EXIT_GAME = LEFT_ARROW + ' EXIT GAME'
BUTTON_SKIP_GAME = RIGHT_ARROW + " SKIP"

BUTTON_FUTURO_REMOTO = "FUTURO REMOTO"
BUTTON_QUIZ = "QUIZ"
BUTTON_START_QUIZ = "START QUIZ"
BUTTON_REFRESH = "REFRESH"

BULLET_POINT = '🔸'

#[unicode tables](http://www.unicode.org/cldr/charts/29/annotations) \
#Future releases will enable you to help us:
#1. Add new languages
#2. Add new tags for current languages (including country names for national flags)
#3. Match language-to-language: using this bot to crowdsource (via gamification techniques) very accurate bilingual dictionaries between any two languages

INFO = utility.unindent(
    """
    @EmojiWorldBot version 1.0

    @EmojiWorldBot is a *multilingual emoji dictionary* that uses
    emojis as a pivot for contributors among dozens of diverse languages.

    Currently we support *emoji-to-word* and *word-to-emoji* for more than 70 languages.
    The bot features a *tagging game* 🐣 for people to contribute to the expansion of these dictionaries \
    or the creation of new ones for any additional language.

    @EmojiWorldBot is a free public service produced by \
    Federico Sangati (Netherlands), Martin Benjamin and Sina Mansour \
    at Kamusi Project International and EPFL (Switzerland), \
    Francesca Chiusaroli at University of Macerata (Italy), \
    and Johanna Monti at University of Naples “L’Orientale” (Italy). \
    If you need to get in touch with us, please send a message to @kercos.

    *Acknowledgements*:
    🔹 Default tags for 72 languages were obtained from the [Unicode Consortium](http://www.unicode.org/cldr/charts/29/annotations)
    🔹 Emoji images are freely provided by [Emoji One](http://emojione.com)
    """
)

TERMS_OF_SERVICE = utility.unindent(
    """
    TERMS OF SERVICE:

    You are invited to use and share @EmojiWorldBot at your pleasure. \
    Through your use of the service, you agree that:

    1. We make no guarantees about the accuracy of the data, and we are not liable \
    for any problems you encounter from using the words you find here. \
    We hope we are giving you good information, but you use it at your own risk.

    2. We may keep records of your searches and contributions. \
    We understand privacy and value it as highly as you do. \
    We promise not to sell or share information that can be associated with your name, \
    other than acknowledging any contributions you make to improving our data. \
    We use the log files to learn from you and produce the best possible service. \
    For example, if you search for a tag that we don’t have, \
    the log files let us know that we should consider adding it.

    3. This is an interactive application that may send you messages from time to time. \
    Messages might include service alerts such as feature updates, \
    or contributor queries such as asking you to translate a new word to your language. \
    We will do our best not to be annoying.

    4. Any information you provide about your favorite languages is given freely and voluntarily, \
    with no claims of copyright or ownership on your part, and no expectation of payment. \
    We are free to use the data you share in any way we see fit (and thank you for it!).

    If you don’t agree to our terms of service, please delete the bot from your telegram contacts \
    and you’ll never hear from us again (unless you decide to come back 😉). \
    If you are cool with the conditions stated above, please enjoy!

    """
)

INVITE_FRIEND_INSTRUCTION = utility.unindent(
    """
    To invite your friends, please copy the following short note🗒and paste it into your chats, or forward ⏩ it directly (for instructions click on /howToForward):
    """
)

HOW_TO_FORWARD_A_MESSAGE = utility.unindent(
    """
    How to forward a message on Telegram:

    1 (Browser): left click on message and press 'forward' at screen bottom
    1 (Desktop): right click on timestamp next to message and press 'forward'
    1 (Mobile): long tap on a message

    2: select the user you want to forward it to

    """
)

MESSAGE_FOR_FRIENDS = utility.unindent(
    """
    Hi, I’ve been enjoying a cool new tool that helps me find emoji in *{0}* \
    and more than 120 other languages.
    I think you’ll love 😎 it too.
    Just click on @EmojiWorldBot to start!
    """
)

# ================================
# AUXILIARY FUNCTIONS
# ================================

# ================================
# Telegram Send Request
# ================================
def sendRequest(url, data, recipient_chat_id, debugInfo):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    try:
        resp = requests.post(url, data)
        logging.info('Response: {}'.format(resp.text))
        success = resp.status_code==200 #respJson['ok']
        if success:
            return True
            #p.setEnabled(True, put=True)
        else:
            respJson = json.loads(resp.text)
            status_code = resp.status_code
            error_code = respJson['error_code']
            description = respJson['description']
            p = person.getPersonByChatId(recipient_chat_id)
            if error_code == 403:
                # Disabled user
                p.setEnabled(False, put=True)
                #logging.info('Disabled user: ' + p.getFirstNameLastNameUserName())
            elif error_code == 400 and description == "INPUT_USER_DEACTIVATED":
                p = person.getPersonByChatId(recipient_chat_id)
                p.setEnabled(False, put=True)
                debugMessage = '❗ Input user disactivated: ' + p.getFirstNameLastNameUserName()
                logging.debug(debugMessage)
                tell(key.FEDE_CHAT_ID, debugMessage, markdown=False)
            else:
                debugMessage = '❗ Raising unknown err ({}).' \
                          '\nStatus code: {}\nerror code: {}\ndescription: {}.'.format(
                    debugInfo, status_code, error_code, description)
                logging.error(debugMessage)
                #logging.debug('recipeint_chat_id: {}'.format(recipient_chat_id))
                logging.debug('Telling to {} who is in state {}'.format(p.chat_id, p.state))
                tell(key.FEDE_CHAT_ID, debugMessage, markdown=False)
    except:
        report_exception()

def broadcast(sender, msg, restart_user=False, curs=None, enabledCount = 0):
    #return

    BROADCAST_COUNT_REPORT = utility.unindent(
        """
        Mesage sent to {} people
        Enabled: {}
        Disabled: {}
        """
    )

    try:
        users, next_curs, more = Person.query().fetch_page(50, start_cursor=curs)
    except datastore_errors.Timeout:
        sleep(1)
        deferred.defer(broadcast, sender, msg, restart_user, curs, enabledCount)
        return

    for p in users:
        if p.enabled:
            enabledCount += 1
            if restart_user:
                restart(p)
            tell(p.chat_id, msg, sleepDelay=True)

    if more:
        deferred.defer(broadcast, sender, msg, restart_user, next_curs, enabledCount)
    else:
        total = Person.query().count()
        disabled = total - enabledCount
        msg_debug = BROADCAST_COUNT_REPORT.format(str(total), str(enabledCount), str(disabled))
        tell(sender.chat_id, msg_debug)


def tell_masters(msg, markdown=False, one_time_keyboard=False):
    for id in key.MASTER_CHAT_ID:
        tell(id, msg, markdown=markdown, one_time_keyboard = one_time_keyboard, sleepDelay=True)


def tell(chat_id, msg, kb=None, markdown=False, inlineKeyboardMarkup=False,
         one_time_keyboard=False, sleepDelay=False):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    replyMarkup = {
        'resize_keyboard': True,
        'one_time_keyboard': one_time_keyboard
    }
    if kb:
        if inlineKeyboardMarkup:
            replyMarkup['inline_keyboard'] = kb
        else:
            replyMarkup['keyboard'] = kb
    try:
        data = {
            'chat_id': chat_id,
            'text': msg,
            'disable_web_page_preview': 'true',
            'parse_mode': 'Markdown' if markdown else '',
            'reply_markup': json.dumps(replyMarkup),
        }
        resp = requests.post(BASE_URL + 'sendMessage', data)
        logging.info('Response: {}'.format(resp.text))
        #logging.info('Json: {}'.format(resp.json()))
        respJson = json.loads(resp.text)
        success = respJson['ok']
        if success:
            if sleepDelay:
                sleep(0.1)
            return True
        else:
            status_code = resp.status_code
            error_code = respJson['error_code']
            description = respJson['description']
            if error_code == 403:
                # Disabled user
                p = person.getPersonByChatId(chat_id)
                p.setEnabled(False, put=True)
                logging.info('Disabled user: ' + p.getUserInfoString())
            elif error_code == 400 and description == "INPUT_USER_DEACTIVATED":
                p = person.getPersonByChatId(chat_id)
                p.setEnabled(False, put=True)
                debugMessage = '❗ Input user disactivated: ' + p.getUserInfoString()
                logging.debug(debugMessage)
                tell(key.FEDE_CHAT_ID, debugMessage, markdown=False)
            else:
                debugMessage = '❗ Raising unknown err in tell() when sending msg={} kb={}.' \
                          '\nStatus code: {}\nerror code: {}\ndescription: {}.'.format(
                    msg, kb, status_code, error_code, description)
                logging.error(debugMessage)
                tell(key.FEDE_CHAT_ID, debugMessage, markdown=False)
    except:
        report_exception()

def sendImageFileFromUrlOrId(chat_id, url_id):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    try:
        data = {
            'chat_id': chat_id,
            'photo': url_id,
        }
        resp = requests.post(key.BASE_URL + 'sendPhoto', data)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()

def sendImageFileFromData(chat_id, img_data):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    try:
        img = [('photo', ('emoji.png', img_data, 'image/png'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.BASE_URL + 'sendPhoto', data=data, files=img)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()

def sendStickerFileFromData(chat_id, img_data):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    try:
        img = [('sticker', ('emoji.webp', img_data, 'image/webp'))]
        data = {
            'chat_id': chat_id,
        }
        resp = requests.post(key.BASE_URL + 'sendSticker', data=data, files=img)
        logging.info('Response: {}'.format(resp.text))
    except:
        report_exception()

def tell_person(chat_id, msg, markdown=False):
    tell(chat_id, msg, markdown=markdown)
    p = person.getPersonByChatId(chat_id)
    if p and p.enabled:
        return True
    return False


def sendTextImage(chat_id, text):
    text = text.replace(' ','+')
    # see https://developers.google.com/chart/image/docs/gallery/dynamic_icons
    #img_url = "http://chart.apis.google.com/chart?chst=d_text_outline&chld=000000|40|h|FFFFFF|_|" + text
    img_url = "http://chart.apis.google.com/chart?chst=d_fnote&chld=sticky_y|2|0088FF|h|" + text
    sendImageFileFromUrlOrId(chat_id, img_url)



##################################
# START OF STATE FUNCTIONS
##################################


# ================================
# RESTART
# ================================
def restart(p, msg=None):
    if msg:
        tell(p.chat_id, msg)
    redirectToState(p, 1)

# ================================
# SWITCH TO STATE
# ================================
def redirectToState(p, new_state, **kwargs):
    if p.state != new_state:
        logging.debug("In redirectToState. current_state:{0}, new_state: {1}".format(str(p.state),str(new_state)))
        p.setState(new_state)
    repeatState(p, **kwargs)

# ================================
# REPEAT STATE
# ================================
def repeatState(p, **kwargs):
    methodName = "goToState" + str(p.state)
    method = possibles.get(methodName)
    if not method:
        tell(p.chat_id, "A problem has occured (" + methodName +
              "). Please forward this message to @kercos" + '\n' +
              "You will be now redirected to the home screen.")
        restart(p)
    else:
        method(p, **kwargs)



# ================================
# GO TO STATE 1: initial state (select language family)
# ================================

INTRO_INSTRUCTIONS_WITH_TAG_AND_EMOJI = utility.unindent(
    """
    Your current language is set to *{0}*. This is what you can do:

    🔹 *Ask me a tag* (one or more words), e.g., type *{2}* to get all emojis with that tag, \
    or *give me a single emoji*, e.g., {1} to get its tags.

    🔹 Press on 🐣 for a *fun quiz-game* that will help grow the dictionary for your language! 😀

    🔹 I'm also an *inline 🤖  bot*! In your other Telegram chats with your friends, \
    *type my name and an emoji tag* in {0}. I'll send them the emoji you choose.
    📲 For instance, try to type this: @EmojiWorldBot {2}
    """
)

INTRO_INSTRUCTIONS_SIMPLE = utility.unindent(
    """
    Your current language is set to *{0}*.

    We are just getting started with {0} - we need your 🤔 tags.
    Please press on 🐣  for a *fun quiz-game* \
    that will help introduce new tags for your language! \
    Don't forget to invite your friends to help grow the dictionary for your language! 😀
    """
)

def goToState1(p, input=None, **kwargs):
    giveInstruction = input is None
    if giveInstruction:
        if WORK_IN_PROGRESS:
            tell(p.chat_id, "🚧 Warning Master, system under maintanence.")
        lang_code = p.getLanguageCode()
        randomEmoji = emojiTables.getRandomEmojiHavingTags(lang_code)
        if randomEmoji:
            randomTag = emojiTables.getRandomTag(lang_code)
            msg = INTRO_INSTRUCTIONS_WITH_TAG_AND_EMOJI.format(p.getLanguageName(), randomEmoji, randomTag)
            markdown = '*' not in randomEmoji and '*' not in randomTag
        else:
            msg = INTRO_INSTRUCTIONS_SIMPLE.format(p.getLanguageName())
            markdown = True
        kb_games = [BUTTON_TAGGING_GAME, BUTTON_FUTURO_REMOTO] if FUTURO_REMOTO_ON else [BUTTON_TAGGING_GAME]
        #if p.getLanguageCode()!= 'eng':
        #    kb_games.append(BUTTON_TRANSLATION_GAME)
        kb = [kb_games, [BUTTON_CHANGE_LANGUAGE]]
        kb.append([BUTTON_INVITE_FRIEND, BUTTON_INFO])

        tell(p.chat_id, msg, kb, markdown=markdown, one_time_keyboard=False)
    else:
        if input == '':
            tell(p.chat_id, "Sorry, I don't understand what you input")
        elif input == BUTTON_CHANGE_LANGUAGE:
            redirectToState(p, 0)
        #elif input == BUTTON_TRANSLATION_GAME and p.getLanguageCode()!= 'eng':
        #    logging.debug("Sending user to state 3")
        #    redirectToState(p, 3)
        elif input == BUTTON_TAGGING_GAME and p.getLanguageCode():
            redirectToState(p, 4)
        elif input == BUTTON_FUTURO_REMOTO and FUTURO_REMOTO_ON:
            redirectToState(p, 50)
        elif input == BUTTON_INFO:
            tell(p.chat_id, INFO, markdown=True)
        elif input == BUTTON_INVITE_FRIEND:
            tell(p.chat_id, INVITE_FRIEND_INSTRUCTION)
            msg = MESSAGE_FOR_FRIENDS.format(p.getLanguageName())
            tell(p.chat_id, msg)
        elif input == '/howToForward':
            tell(p.chat_id, HOW_TO_FORWARD_A_MESSAGE)
        elif p.chat_id in key.MASTER_CHAT_ID:
            dealWithMasterCommands(p, input)
        else:
            dealWithInputTagOrEmoji(p, input)


def dealWithMasterCommands(p, input):
    splitCommandOnSpace = input.split(' ')
    commandBodyStartIndex = len(splitCommandOnSpace[0])+1
    if input.startswith('/broadcast ') and len(input) > commandBodyStartIndex:
        msg = input[commandBodyStartIndex:]
        logging.debug("Starting to broadcast " + msg)
        deferred.defer(broadcast, p, msg, restart_user=False)
    elif input.startswith('/restartBroadcast ') and len(input) > commandBodyStartIndex:
        msg = input[commandBodyStartIndex:]
        logging.debug("Starting to broadcast " + msg)
        deferred.defer(broadcast, p, msg, restart_user=True)
    elif input=='/generateException':
        tell(p.chat_id, "è".encode('utf-8'))
    #elif input.startswith('/addLanguageNameVariation ') and len(input) > commandBodyStartIndex:
    #    if len(splitCommandOnSpace)==3:
    #        success, msg = languages.addLanguageVariation(splitCommandOnSpace[1], splitCommandOnSpace[2])
    #        tell(p.chat_id, msg)
    #    else:
    #        tell(p.chat_id, "Wrong command format. Please type /addLanguageNameVariation  [lang_code] [new variation]")
    #elif input.startswith('/removeLanguageNameVariation ') and len(input) > commandBodyStartIndex:
    #    if len(splitCommandOnSpace) == 3:
    #        success, msg = languages.removeLanguageVariation(splitCommandOnSpace[1], splitCommandOnSpace[2])
    #        tell(p.chat_id, msg)
    #    else:
    #        tell(p.chat_id, "Wrong command format. Please type /addLanguageNameVariation  [lang_code] [new variation]")
    elif input.startswith('/testNormalize') and len(input) > commandBodyStartIndex:
        tell(p.chat_id, 'Normalized: ' + utility.normalizeString(input[commandBodyStartIndex:]))
    elif input == '/getPeopleCount':
        tell(p.chat_id, person.getPeopleCount())
    elif input.startswith('/testEmojiImg'):
        input_array = input.split(' ')
        emoji = input_array[1] if len(input_array)>1 else '⭐'
        image_url = emojiUtil.getEmojiPngUrl(emoji)
        sendImageFileFromUrlOrId(p.chat_id, image_url)
    elif input.startswith('/testEmojiSticker'):
        input_array = input.split(' ')
        emoji = input_array[1] if len(input_array) > 1 else '⭐'
        sticker_data = emojiUtil.getEmojiStickerDataFromUrl(emoji)
        sendStickerFileFromData(p.chat_id, sticker_data)
    elif input == '/testTextImg':
        sendTextImage(p.chat_id, 'text example')
    elif input.startswith('/sendText'):
        dealWithsendTextCommand(p, input, markdown=False)
    else:
        dealWithInputTagOrEmoji(p, input)

def dealWithsendTextCommand(p, sendTextCommand, markdown=False):
    split = sendTextCommand.split()
    if len(split)<3:
        tell(p.chat_id, 'Commands should have at least 2 spaces')
        return
    if not split[1].isdigit():
        tell(p.chat_id, 'Second argumnet should be a valid chat_id')
        return
    id = int(split[1])
    sendTextCommand = ' '.join(split[2:])
    if tell_person(id, sendTextCommand, markdown=markdown):
        user = person.getPersonByChatId(id)
        tell(p.chat_id, 'Successfully sent text to ' + user.getFirstName())
    else:
        tell(p.chat_id, 'Problems in sending text')

####
# DEAL WITH INPUT TAG OR EMOJI
####

def dealWithInputTagOrEmoji(p, input):
    if len(input)>200:
        tell(p.chat_id, "Sorry, your input is too long.")
        return
    lang_code = p.getLanguageCode()
    emoji_norm = emojiUtil.checkIfEmojiAndGetNormalized(input)
    if emoji_norm:
        # input is an emoji
        tagList = emojiTables.getTagList(lang_code, emoji_norm)
        if len(tagList)>0:
            tagsStr = ", ".join(tagList)
            tell(p.chat_id, "Found the following tags for {0}: \n *{1}*".format(
                input, tagsStr), markdown=utility.markdownSafe(tagsStr))
            # logging.info(str(p.chat_id) + " searching emoji " + input_norm + " and getting tags " + tags)
            search.addSearch(p.chat_id, lang_code, emoji_norm, is_searched_emoji=True, inline_query=False,
                             found_translation=True)
        else:
            tell(p.chat_id, "🤔  *No tags found* for the given emoji.", markdown=True)
            # logging.info(str(p.chat_id) + " searching emoji" + input_norm + " and getting #no_tags#")
            search.addSearch(p.chat_id, lang_code, emoji_norm, is_searched_emoji=True, inline_query=False,
                             found_translation=False)
    else:
        # input is a tag
        #input_norm = utility.normalizeString(input)
        emojiList = emojiTables.getEmojiList(lang_code, input)
        if len(emojiList)>0:
            emojis = " ".join(emojiList)
            tell(p.chat_id, "Found the following emojis for *{0}*:\n{1}".format(
                input, emojis), markdown=utility.markdownSafeList([input, emojis]))
            # logging.info(str(p.chat_id) + " searching tag '" + input + "' and getting emojis " + emojis)
            search.addSearch(p.chat_id, lang_code, input, is_searched_emoji=False, inline_query=False,
                             found_translation=True)
        else:
            msg = "🤔  *No emojis found for the given tag*, try again " \
                  "(the input has been recognized as a tag, " \
                  "if you have entered an emoji it is a flag or a non-standard one)."
            tell(p.chat_id, msg, markdown=True)
            # logging.info(str(p.chat_id) + " searching tag '" + input + "' and getting #no_emojis#")
            search.addSearch(p.chat_id, lang_code, input, is_searched_emoji=False, inline_query=False,
                             found_translation=False)


# ================================
# GO TO STATE 0: change language
# ================================

BUTTON_ACTIVE_LANGUAGES = "ACTIVE LANGUAGES"
BUTTON_ADD_LANGUAGES = "ADD LANGUAGE"

ADD_LANGUAGE_INSTRUCTIONS = utility.unindent(
    """
    Can you help build the dictionary for a language you don't see on our list? \
    Please type:

    */activate [language]*

    For example, if your language is "Zuni", type */activate Zuni*, \
    and we will get back to you with more information.
    """
)

CHANGE_LANGUAGE_INSTRUCTIONS = utility.unindent(
    """
    Your current language is *{0}*.

    Press on a button to list the available languages, or be adventurous and type a language name (e.g., Swahili).
    """
)

def goToState0(p, input=None, **kwargs):
    giveInstruction = input is None
    if giveInstruction:
        reply_txt = CHANGE_LANGUAGE_INSTRUCTIONS.format(p.getLanguageName())
        kb = [
            [ 'A-C', 'D-J', 'K-P', 'R-Z'],
            [BUTTON_ACTIVE_LANGUAGES, BUTTON_ADD_LANGUAGES],
            [BUTTON_BACK_HOME_SCREEN]
        ]
        tell(p.chat_id, reply_txt, kb, markdown=True, one_time_keyboard=False)
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
            redirectToState(p, 1)
        elif input.startswith("/activate"):
            new_language_code = input[9:].strip()
            if len(new_language_code)<3:
                tell(p.chat_id, "Sorry the language should be at least 3 characters long.", markdown=True)
            elif changeLanguageFromString(p, new_language_code):
                tell(p.chat_id, "The language you have requested is already present, switching to it now.")
                redirectToState(p, 1)
            else:
                msg_user = "Thanks {0} for your help, will be back to you with " \
                      "more info about the language you would like to see in @EmojiWorldBot".format(p.getFirstName())
                tell(p.chat_id, msg_user, markdown=True)
                msg_masters = "The user *{0}* has requested to inser language *{1}*. " \
                              "Please get back to him/her.".format(p.getUserInfoString(), new_language_code)
                tell_masters(msg_masters, markdown=True)
        else:
            if changeLanguageFromString(p, input):
                redirectToState(p,1)
            else:
                tell(p.chat_id, FROWNING_FACE +
                     " Sorry, I don't recognize this as a name of a language. \n" + ADD_LANGUAGE_INSTRUCTIONS,
                     markdown = True)

def changeLanguageFromString(p, input):
    logging.debug('input: ' + input)
    normInput = utility.normalizeString(input)
    #slash is removed
    if input.startswith('/'):
        normInput = '/' + normInput
    #logging.debug('norm input: ' + normInput)
    index = None
    if input in languages.ALL_LANGUAGES_COMMANDS:
        index = languages.ALL_LANGUAGES_COMMANDS.index(input)
    elif normInput in languages.ALL_LANGUAGES_LOWERCASE:
        index = languages.ALL_LANGUAGES_LOWERCASE.index(normInput)
    else:
        lang_code = languages.getLanguageCodeByLanguageVariation([normInput, input])
        if lang_code:
            index = languages.ALL_LANG_CODES.index(lang_code)
    if index != None:
        p.setLanguageAndLangCode(index)
        return True
    return False


# # ================================
# # GO TO STATE 3: translation matching game updatede mode single answer
# # ================================
#
# BUTTON_NONE = '✖️ NONE of the options'
# BUTTON_PLAY_AGAIN = 'PLAY AGAIN'
#
# TRANSLATION_GAME_INSTRUCTIONS_1 = \
# """
# ⭐⭐⭐⭐⭐
# Thanks for playing with us and helping to translate English tags associated with emojis into {0}.
# """
#
# TRANSLATION_GAME_INSTRUCTIONS_2 = \
# """
# We have selected the following emoji {1} and the associated English tag *{2}*.
#
# Please select the {0} tag that is the EXACT TRANSLATION of *{2}* or 'NONE of the options' if you \
# think that none of them is correct. If you think there are more equally correct answers, choose one of them.
#
# """
#
# TRANSLATION_GAME_INSTRUCTIONS_3 = \
# """
# What is the correct translation of *{0}*?
# """
#
#
#
# def goToState3(p, input=None, userTranslationTagEntry = None, resend=False, **kwargs):
#     giveInstruction = input is None
#     if giveInstruction:
#         emoji_text_dict_src = emojiTables.EMOJI_TO_TEXT_DICTIONARIES['eng']
#         emoji_text_dict_dst = emojiTables.EMOJI_TO_TEXT_DICTIONARIES[p.getLanguageCode()]
#         if not userTranslationTagEntry:
#             userTranslationTagEntry = translation.getOrInsertUserTranslationTagEntry(p, src_language='eng')
#             numTranslations = 0
#         else:
#             numTranslations = userTranslationTagEntry.getNumberOfTranslatedEmoji()
#         if (numTranslations >= parameters.MAX_EMOJI_FOR_ANNOTATION_PER_PERSON_PER_LANGUAGE):
#             msg = "You have provided all the tagging we needed for {0}!\n" \
#                   "Thanks a lot for your help! 🙏\n".format(p.getLanguageCode())
#             tell(p.chat_id, msg)
#             sleep(2)
#             redirectToState(p,1)
#             return
#         emoji = userTranslationTagEntry.getLastEmoji()
#         if resend or emoji:
#             chosen_src_tag = userTranslationTagEntry.getLastSrcTag()
#             dst_tag_set = emoji_text_dict_dst[emoji]
#         else:
#             emoji, chosen_src_tag, dst_tag_set, random = getNextEmojiForTranslation(
#                 emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry)
#             userTranslationTagEntry.setLastEmojiAndSrcTag(emoji, chosen_src_tag, random)
#         shuffle(dst_tag_set)
#         userTranslationTagEntry.dst_tag_set = dst_tag_set # set destination tag set
#         markdown = '*' not in emoji and '*' not in chosen_src_tag
#
#         msg1 = TRANSLATION_GAME_INSTRUCTIONS_1.format(p.getLanguageCode())
#         tell(p.chat_id, msg1, markdown=markdown, sleepDelay=True)
#
#         sendEmojiImage(p.chat_id, emoji)
#
#         msg2 = TRANSLATION_GAME_INSTRUCTIONS_2.format(p.getLanguageCode(), emoji, chosen_src_tag)
#         tell(p.chat_id, msg2, markdown=markdown, sleepDelay=True)
#
#         sendTextImage(p.chat_id, chosen_src_tag, sleepDelay=True)
#
#         msg3 = TRANSLATION_GAME_INSTRUCTIONS_3.format(chosen_src_tag)
#
#         options = [BULLET_POINT + ' ' + str(n) + ': ' + x for n, x in enumerate(dst_tag_set, 1)]
#         msg3 += '\n'.join(options)
#         number_buttons = [str(x) for x in range(1,len(dst_tag_set)+1)]
#         kb = utility.distributeElementMaxSize(number_buttons)
#         kb.insert(0, [BUTTON_NONE, BUTTON_SKIP_GAME])
#         kb.append([BUTTON_EXIT_GAME])
#         tell(p.chat_id, msg3, kb, markdown=markdown, sleepDelay=True)
#
#         userTranslationTagEntry.put()
#     else:
#         userTranslationTagEntry = translation.getUserTranslationEntry(p)
#         if not userTranslationTagEntry:
#             tell(p.chat_id, "Sorry, something went wrong, if the problem persists contact @kercos")
#             return
#         if input == BUTTON_EXIT_GAME:
#             tell(p.chat_id, "Thanks for your help!")
#             userTranslationTagEntry.removeLastEmoji(True)
#             sleep(2)
#             redirectToState(p,1)
#         elif input == BUTTON_SKIP_GAME:
#             userTranslationTagEntry.addTranslationToLastEmojiSrcTag(None)
#             translation.addInAggregatedEmojiTranslations(userTranslationTagEntry)
#             userTranslationTagEntry.removeLastEmoji(True)
#             redirectToState(p, 3, userTranslationTagEntry=userTranslationTagEntry)
#         else:
#             translation_tag = None
#             if input == BUTTON_NONE:
#                 translation_tag = ''
#             elif utility.representsIntBetween(input, 0, len(userTranslationTagEntry.dst_tag_set)):
#                 number = int(input)
#                 translation_tag = userTranslationTagEntry.dst_tag_set[number - 1]  # .encode('utf-8')
#             if translation_tag != None:
#                 msg = "Thanks for your input! 🙏\n" + \
#                       translation.getStatsFeedbackForTranslation(userTranslationTagEntry, translation_tag)
#                 if userTranslationTagEntry.addTranslationToLastEmojiSrcTag(translation_tag):
#                     translation.addInAggregatedEmojiTranslations(userTranslationTagEntry)
#                     userTranslationTagEntry.removeLastEmoji(True)
#                     tell(p.chat_id, msg)
#                     sleep(3)
#                     redirectToState(p, 3, userTranslationTagEntry=userTranslationTagEntry)
#                 else:
#                     tell(p.chat_id, "You have already answered!")
#             else:
#                 tell(p.chat_id, "Not a valid input, try again.")
#
#
# def getNextEmojiForTranslation(emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry, forceRandom=False):
#     emoji = ''
#     if not forceRandom and not userTranslationTagEntry.hasSeenEnoughKnownEmoji():
#         emoji, chosen_src_tag = translation.getPrioritizedEmojiSrcTagForUser(userTranslationTagEntry)
#         if emoji is None:
#             return getNextEmojiForTranslation(
#                 emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry, forceRandom=True)
#         random = False
#     else:
#         random = True
#         while True:
#             emoji = emojiTable.getRandomEmoji(emoji_text_dict_dst)
#             alreadyTranslated = userTranslationTagEntry.wasEmojiTranslated(emoji)
#             if not alreadyTranslated:
#                 src_tag_set = emoji_text_dict_src[emoji]
#                 chosen_src_tag = src_tag_set[randint(0, len(src_tag_set) - 1)]
#                 break
#     dst_tag_set = emoji_text_dict_dst[emoji]
#     if not dst_tag_set:
#         return getNextEmojiForTranslation(
#             emoji_text_dict_src, emoji_text_dict_dst, userTranslationTagEntry, forceRandom=True)
#     return emoji, chosen_src_tag, dst_tag_set, random
#
# def makeCallbackQueryButton(text):
#     return {
#         'text': text,
#         'callback_data': text,
#     }
#
# def convertKeyboardToInlineKeyboard(kb):
#     result = []
#     for l in kb:
#         result.append([makeCallbackQueryButton(b) for b in l])
#     return result


# ================================
# GO TO STATE 4: tagging game
# ================================

DISABLE_DIACRITIC_WARNING_MSG = "/disableWarningSpecialChars"

def goToState4(p, input=None, userTaggingEntry=None, **kwargs):
    giveInstruction = input is None
    if giveInstruction:
        if not userTaggingEntry:
            userTaggingEntry = userTagging.getOrInsertUserTaggingEntry(p)
            numTagging = 0
        else:
            numTagging = userTaggingEntry.getNumberOfTaggedEmoji()
        if (numTagging >= parameters.MAX_EMOJI_FOR_ANNOTATION_PER_PERSON_PER_LANGUAGE):
            msg = "You have provided all the tags we needed for {0}!\n" \
                  "Thanks a lot for your help! 🙏\n".format(p.getLanguageCode())
            tell(p.chat_id, msg)
            sleep(1)
            redirectToState(p,1)
            return
        emoji = userTaggingEntry.getLastEmoji()
        if not emoji:
            emoji, random = getNextEmojiForTagging(userTaggingEntry)
            userTaggingEntry.setLastEmoji(emoji, random)
        userLang = p.getLanguageCode()
        langTags = emojiTables.getTagList(userLang, emoji)
        logging.debug("Lang: {} Emoji: {} Tags: {}".format(userLang, emoji, langTags))
        engTags = emojiTables.getTagList('eng', emoji)
        useMarkdown = not any((utility.containsMarkdown(emoji),
                               utility.containsMarkdownList(langTags),
                               utility.containsMarkdownList(engTags)))
        langShuffledTagMarkdownStr = getShuffledTagsMarkdownStr(langTags, useMarkdown)
        engShuffledTagMarkdownStr = getShuffledTagsMarkdownStr(engTags, useMarkdown)
        if p.getLanguageCode()== 'eng':
            engShuffledTagMarkdownStr = None
        # SENDING INSTRUCTIONS
        msg1, msg2 = getTaggingGameInstruction(p, userTaggingEntry, langShuffledTagMarkdownStr,
                                               engShuffledTagMarkdownStr, useMarkdown)
        tell(p.chat_id, msg1, markdown=useMarkdown)

        #image_data = emojiUtil.getEmojiImageDataFromUrl(emoji)
        #sendImageFileFromData(p.chat_id, image_data)

        sticker_data = emojiUtil.getEmojiStickerDataFromUrl(emoji)
        sendStickerFileFromData(p.chat_id, sticker_data)

        kb= [[BUTTON_OR_TYPE_SKIP_GAME],[BUTTON_EXIT_GAME]]
        tell(p.chat_id, msg2, kb, markdown=useMarkdown)
    else:
        userTaggingEntry = userTagging.getUserTaggingEntry(p)
        if not userTaggingEntry:
            tell(p.chat_id, "Sorry, something got wrong, if the problem persists contact @kercos")
            return
        if input==DISABLE_DIACRITIC_WARNING_MSG:
            userTaggingEntry.setDisableDiacriticsWarning(value=True, put=True)
            tell(p.chat_id, "👍 The warning has been disabled!")
            sleep(1)
            repeatState(p, userTaggingEntry=userTaggingEntry)
        elif input==BUTTON_OR_TYPE_SKIP_GAME or input.lower()=="/skip":
            userTaggingEntry.addTagsToLastEmoji([])
            userTagging.addInAggregatedEmojiTags(userTaggingEntry)
            userTaggingEntry.removeLastEmoji(put = True)
            tell(p.chat_id, "🤔 Sending you a new emoji ...")
            sleep(1)
            repeatState(p, userTaggingEntry=userTaggingEntry)
        elif input == BUTTON_EXIT_GAME:
            userTaggingEntry.removeLastEmoji()
            tell(p.chat_id, "Thanks for your help 🙏, hope you had a good time! 🎉")
            sleep(1)
            redirectToState(p,1)
        elif input == BUTTON_TAGGING_GAME:
            tell(p.chat_id, "😒  The input is not valid, try again.")
        else:
            proposedTag = input.strip()
            if proposedTag == '':
                tell(p.chat_id, "😒  The input is not valid, try again.")
            else:
                emoji = userTaggingEntry.getLastEmoji()
                currentTags = emojiTables.getTagList(p.getLanguageCode(), emoji)
                currentTagsLower = [x.lower() for x in currentTags]
                proposedTagLower = proposedTag.lower()
                oldTag = proposedTagLower in currentTagsLower
                useMarkdown = not utility.containsMarkdown(proposedTagLower)
                msg = "You proposed *{0}* as a new tag.\n".format(proposedTagLower)
                if oldTag:
                    langShuffledTagMarkdownStr = getShuffledTagsMarkdownStr(currentTags, useMarkdown)
                    msg += "😒 The tag you have input is already present in the list: {0}. " \
                           "Please try again or press SKIP.".format(langShuffledTagMarkdownStr)
                    tell(p.chat_id, msg, markdown= useMarkdown)
                else:
                    statsFeedback = userTagging.getStatsFeedbackForTagging(userTaggingEntry, proposedTagLower)
                    msg += "Thanks for your input! 🙏\n" + statsFeedback
                    useMarkdown = not utility.containsMarkdownList(proposedTagLower) and not utility.containsMarkdownList(statsFeedback)
                    tell(p.chat_id, msg, markdown=useMarkdown)
                    userTaggingEntry.updateUpperCounts(proposedTagLower)
                    userTaggingEntry.addTagsToLastEmoji([proposedTagLower])
                    #tagging.addInAggregatedTagEmojis(userTaggingEntry)
                    userTagging.addInAggregatedEmojiTags(userTaggingEntry)
                    userTaggingEntry.removeLastEmoji(put = True)
                    sleep(1)
                    repeatState(p, userTaggingEntry=userTaggingEntry)

def getShuffledTagsMarkdownStr(tags, useMarkdown):
    tagsMarkDown = ["*{0}*".format(t) for t in tags] if useMarkdown else [t for t in tags]
    shuffle(tagsMarkDown)
    tagsMarkDownStr = ', '.join(tagsMarkDown)
    return tagsMarkDownStr

UPPER_CASE_SOFT_MESSAGE = utility.unindent(
    """
    ❗  Please be aware that 'car' ≠ 'Car', so use upper case letters only if needed.\
    """
)

UPPER_CASE_SHOCK_MESSAGE = utility.unindent(
    """
    ❗⚠ It looks like your phone automatically capitalized your word. \
    Please make sure to use upper case letters only when needed (e.g. 🐠 fish,  but 🗻 Mount Fuji) \
    """
)

UPPER_CASE_MESSAGE_LEVELS = ['',UPPER_CASE_SOFT_MESSAGE, UPPER_CASE_SHOCK_MESSAGE]

DIACRITICS_MESSAGE = utility.unindent(
    """
    Your language contains special characters (e.g., accents), \
    it is VERY important that you use the settings on your device \
    to select the correct keyboard for your language. \
    To disable this message press on {0}
    """.format(DISABLE_DIACRITIC_WARNING_MSG)
)

def getTaggingGameInstruction(p, userTaggingEntry, language_tags_markeddown_str,
                              english_tags_markeddown_str, useMarkdown):
    language = p.getLanguageName()
    emoji = userTaggingEntry.getLastEmoji()
    #tagUpperCountLevel = userTaggingEntry.tagUpperCountLevel()
    #showDiacriticWarning = not userTaggingEntry.disableDiacriticsWarning and userTaggingEntry.currentLanguageHasDiacritics()
    msg1 = "⭐⭐⭐⭐⭐\n"
    msg1 += "Thanks for playing and helping tag emojis in *{0}*.\n\n".format(language)
    msg1 += "We have a new emoji for you: {0}\n".format(emoji)
    if language_tags_markeddown_str:
        msg1 += "It is currently associated with the following {0} tags: {1}, " \
               "which you cannot reuse. ".format(language, language_tags_markeddown_str)
    else:
        msg1 += "This emoji still does not have any official tags in {0}.".format(language)

    if useMarkdown:
        msg2 = "\nCan you think of *a single new* {0} tag for {1}?".format(language, emoji)
    else:
        msg2 = "\nCan you think of a single new {0} tag for {1}?".format(language, emoji)
    if english_tags_markeddown_str:
        msg2 += "\nYou can get inspired by the English tags: {0}.".format(english_tags_markeddown_str)

    msg2 += '\n'
    #msg2 += UPPER_CASE_MESSAGE_LEVELS[tagUpperCountLevel]
    #if showDiacriticWarning:
    #    msg2 += DIACRITICS_MESSAGE
    return msg1, msg2.strip()

def getNextEmojiForTagging(userTaggingEntry):
    if not userTaggingEntry.hasSeenEnoughKnownEmoji():
        #logging.debug("Person has not seen enough knwon emoji: " + str(userTaggingEntry.ongoingAlreadyTaggedEmojis))
        emoji = userTagging.getPrioritizedEmojiForUser(userTaggingEntry)
        if emoji:
            #logging.debug("Send new emoji: " + emoji)
            return emoji, False
    while True:
        randomEmoji = emojiUtil.getRandomEmoji()
        if userTaggingEntry.wasEmojiTagged(randomEmoji):
            continue
        #logging.debug("Sendin random emoji: " + randomEmoji)
        emojiTables.addEmojiLangInTableIfNotExists(userTaggingEntry.lang_code, randomEmoji)
        return randomEmoji, True



# ================================
# GO TO STATE 50: FUTURO REMOTO
# ================================

def goToState50(p, input=None, **kwargs):
    giveInstruction = input is None
    quizOpen = quizGame.isQuizOpen()
    quizAdmin = quizGame.getQuizAdminId() if quizOpen else None
    if giveInstruction:
        msg = utility.unindent(
            """
            Welcome to Futuro Remoto!
            From this screen you will be able to access to the live quiz!
            Below you will see a button {} once the QUIZ is open, if you want to refresh the screen press {}.
            """.format(BUTTON_QUIZ, BUTTON_REFRESH)
        )
        kb = [[BUTTON_BACK]]
        if quizOpen:
            kb.insert(0, [BUTTON_QUIZ])
        elif p.isAdmin():
            kb.insert(0, [BUTTON_START_QUIZ])
            msg = "Press {} if you want to start the quiz.".format(BUTTON_START_QUIZ)
        else:
            kb.insert(0, [BUTTON_REFRESH])
        tell(p.chat_id, msg, kb)
    else:
        if input == BUTTON_BACK:
            restart(p)
        elif input == BUTTON_REFRESH:
            repeatState(p)
        elif input == BUTTON_START_QUIZ and p.isAdmin():
            if quizGame.isQuizOpen():
                if quizAdmin == p.chat_id:
                    redirectToState(p, 52)
                else:
                    msg = 'The quiz has been already activated by {}\n' \
                          'You are now a participant'.format(quizGame.getQuizAdminName())
                    tell(p.chat_id, msg)
                    redirectToState(p, 50)
            else:
                quizGame.startQuiz(p.chat_id)
                redirectToState(p, 52)
        elif input == BUTTON_QUIZ:
            if quizGame.isQuizOpen():
                if quizAdmin == p.chat_id:
                    msg = 'Back in the quiz as an administrator'
                    tell(p.chat_id, msg)
                    redirectToState(p, 52)
                else:
                    redirectToState(p, 51)
            else:
                msg = 'The quiz is no longer active'
                tell(p.chat_id, msg)
                repeatState(p)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand what you input")

# ================================
# GO TO STATE 51: Futuro Remoto Participants
# ================================
ANSWER_BUTTONS = ['A','B','C','D']

def goToState51(p, input=None, **kwargs):
    giveInstruction = input is None
    if giveInstruction:
        msg = "Hi {}, welcome to the live quiz!".format(p.getFirstName())
        kb = [ANSWER_BUTTONS]
        tell(p.chat_id, msg, kb, sleepDelay=True, one_time_keyboard=False)
    else:
        message_timestamp = kwargs['message_timestamp']
        if input in ANSWER_BUTTONS:
            #tell(p.chat_id, "You sent the message at: {}".format(message_timestamp))
            questionNumber, ellapsedSeconds = quizGame.addAnswer(p, input, message_timestamp)
            if ellapsedSeconds == -1:
                # answers are not currently accepted
                msg = FROWNING_FACE + ' Sorry, answered are not accepted right now.'
                tell(p.chat_id, msg, sleepDelay=True, one_time_keyboard=False)
            elif ellapsedSeconds == -2:
                # user already answered to the question
                msg = FROWNING_FACE + ' Sorry, you already answered to question {}.'.format(questionNumber)
                tell(p.chat_id, msg, sleepDelay=True, one_time_keyboard=False)
            else: # >0
                msg = utility.unindent(
                    """
                    Thanks!  😊
                    You have answered in {} seconds.
                    You answer ({}) to question {} has been recorded.
                    """.format(ellapsedSeconds, input, questionNumber)
                )
                tell(p.chat_id, msg, sleepDelay=True, one_time_keyboard=False)
        else:
            tell(p.chat_id, FROWNING_FACE + " Sorry, I don't understand. Please press on A, B, C or D.")

# ================================
# GO TO STATE 52: Futuro Remoto ADMIN
# ================================

def goToState52(p, input=None, **kwargs):
    NEXT_QUESTION_BUTTON = 'NEXT QUESTION'
    STOP_ANSWERS_BUTTON = 'STOP ANSWERS'
    END_QUIZ_BUTTON = 'END QUIZ'
    PEOPLE_IN_QUIZ_BUTTON = 'PEOPLE IN QUIZ'
    GLOBAL_STATS_BUTTON = 'GLOBAL STATS'
    RESTART_QUIZ_BUTTON = 'RESTART QUIZ'
    WINNING_MSG = [
        "🎉🎉🎉 CONGRATULATIONS, YOU WON THE QUIZ!\nCOME TO COLLECT YOUR PRIZE!  🎉🎉🎉",
        "🎉🎉🎉 CONGRATULATIONS, YOU WON THE 2ND PLACE!\nCOME TO COLLECT YOUR PRIZE! 🎉🎉🎉",
        "🎉🎉🎉 CONGRATULATIONS, YOU WON THE 3RD PLACE!\nCOME TO COLLECT YOUR PRIZE! 🎉🎉🎉",
    ]
    giveInstruction = input is None
    if giveInstruction:
        kb = [
            [NEXT_QUESTION_BUTTON],
            [PEOPLE_IN_QUIZ_BUTTON, GLOBAL_STATS_BUTTON],
            [END_QUIZ_BUTTON, RESTART_QUIZ_BUTTON]
        ]
        msg = "You are the admin of the live quiz!"
        tell(p.chat_id, msg, kb, sleepDelay=True, one_time_keyboard=False)
    else:
        if input == END_QUIZ_BUTTON:
            userAnswersTable = quizGame.getUserAnswersTable()
            firstN_chat_id, summary = quizGame.getUserAnswersTableSorted(3)
            tell(p.chat_id, summary, sleepDelay=True, one_time_keyboard=False)
            enuList = list(enumerate(firstN_chat_id))
            deferred.defer(broadcast_quiz_final_msg, p.chat_id, 51, userAnswersTable, restart_user=True)
            sleep(3)
            for i, id in enuList:
                tell(id, WINNING_MSG[i])
            sleep(1)
            quizGame.stopQuiz()
            restart(p)
        elif input == PEOPLE_IN_QUIZ_BUTTON:
            c = person.getPeopleCountInState(51)
            msg = 'There are {} people in the quiz.'.format(c)
            tell(p.chat_id, msg, sleepDelay=True, one_time_keyboard=False)
        elif input == RESTART_QUIZ_BUTTON:
            quizGame.startQuiz(p.chat_id)
            msg = 'Quiz resetted successfully.'
            tell(p.chat_id, msg, sleepDelay=True, one_time_keyboard=False)
        elif input == NEXT_QUESTION_BUTTON:
            quizGame.addQuestion()
            kb = [[STOP_ANSWERS_BUTTON]]
            msg = 'Ask your question (live) and when you want to stop the answers press on {}.'.format(STOP_ANSWERS_BUTTON)
            tell(p.chat_id, msg, kb, sleepDelay=True, one_time_keyboard=False)
        elif input == STOP_ANSWERS_BUTTON:
            quizGame.stopAcceptingAnswers()
            kb = [ANSWER_BUTTONS]
            msg = 'Answers have been blocked. Please, provide the correct answer..'
            tell(p.chat_id, msg, kb, sleepDelay=True, one_time_keyboard=False)
        elif input in ANSWER_BUTTONS:
            correctNamesTimeSorted = quizGame.validateAnswers(input)
            correctNamesStr = ', '.join([x for x in correctNamesTimeSorted])
            msg = 'The answers have been validated. \n' \
                  'The people who answered the last question correctly are {}: {}'.format(
                len(correctNamesTimeSorted), str(correctNamesStr))
            kb = [
                [NEXT_QUESTION_BUTTON],
                [PEOPLE_IN_QUIZ_BUTTON, GLOBAL_STATS_BUTTON],
                [END_QUIZ_BUTTON, RESTART_QUIZ_BUTTON]
            ]
            tell(p.chat_id, msg, kb, sleepDelay=True, one_time_keyboard=False)
        elif input == GLOBAL_STATS_BUTTON:
            firstN_chat_id, summary = quizGame.getUserAnswersTableSorted()
            tell(p.chat_id, summary, sleepDelay=True, one_time_keyboard=False)
        else:
            tell(p.chat_id, FROWNING_FACE + "Sorry, I don't understand what you input")

def broadcast_quiz_final_msg(sender_id, state, userAnswersTable, restart_user=False, markdown=False, curs=None):
    users, next_curs, more = Person.query(Person.state == state).fetch_page(50, start_cursor=curs)
    try:
        for p in users:
            if p.enabled:
                if restart_user:
                    restart(p)
                score, ellapsed = quizGame.getUserScoreEllapsed(p, userAnswersTable)
                if score == 0:
                    msg = "You have correctly answered 0 questions."
                else:
                    msg = utility.unindent(
                        """
                        You have correctly answered {} questions in {} seconds in total.
                        Thanks to have participated to the quiz!
                        """.format(score, ellapsed)
                    )
                tell(p.chat_id, msg, sleepDelay=True)
    except datastore_errors.Timeout:
        sleep(1)
        deferred.defer(broadcast_quiz_final_msg, sender_id, state, userAnswersTable, restart_user, markdown, curs)
        return
    if more:
        deferred.defer(broadcast_quiz_final_msg, sender_id, state, userAnswersTable, restart_user, markdown, next_curs)
    else:
        msg_debug = "The final message has been sent to all participants."
        tell(sender_id, msg_debug)



# ================================
# ================================
# ================================


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        #urlfetch.set_default_fetch_deadline(60)
        allowed_updates = ["message", "inline_query", "chosen_inline_result", "callback_query"]
        data = {
            'url': key.WEBHOOK_URL,
            'allowed_updates': json.dumps(allowed_updates),
        }
        resp = requests.post(key.BASE_URL + 'setWebhook', data)
        logging.info('SetWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)

class GetWebhookInfo(webapp2.RequestHandler):
    def get(self):
        #urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'getWebhookInfo')
        logging.info('GetWebhookInfo Response: {}'.format(resp.text))
        self.response.write(resp.text)

class DeleteWebhook(webapp2.RequestHandler):
    def get(self):
        #urlfetch.set_default_fetch_deadline(60)
        resp = requests.post(key.BASE_URL + 'deleteWebhook')
        logging.info('DeleteWebhook Response: {}'.format(resp.text))
        self.response.write(resp.text)


# ================================
# INLINE QUERY
# ================================


def createInlineQueryResultArticle(p, id, query_text, query_offset):
    lang_code = p.getLanguageCode() if p.lang_code else 'eng'
    language = p.getLanguageName() if p.lang_code else 'English'
    #query_text = utility.normalizeString(query_text)
    emojiList = emojiTables.getEmojiList(lang_code, query_text)
    if len(emojiList) > 0:
        #logging.debug('Replying to inline query for tag ' + tag)
        result = []
        i = 0
        query_offset_int = int(query_offset) if query_offset else 0
        start_index = 50 * query_offset_int
        end_index = start_index + 50
        hasMore = len(emojiList) > end_index
        emojiList = emojiList[start_index:end_index]
        for e in emojiList:
            msg = e
            if parameters.ADD_TEXT_TO_EMOJI_IN_INLINE_QUERY:
                msg += ' ({0} in {1})'.format(query_text, language) \
                    if parameters.ADD_LANGUAGE_TO_TEXT_IN_INLINE_QUERY \
                    else ' ({0})'.format(query_text)
            result.append(
                {
                    'type': "article",
                    'id': str(id) + '/' + str(i),
                    'title': e,
                    'message_text': msg,
                    'hide_url': True,
                    'thumb_url': emojiUtil.getEmojiPngUrl(e),
                }
            )
            i += 1
        next_offset = str(query_offset_int + 1) if hasMore else ''
        return next_offset, True, result
    else:
        msg = 'No emoji found for {0} in {1}'.format(query_text, language)
        result = [{
            'type': "article",
            'id': str(id) + '/0',
            'title':  msg,
            'message_text': msg,
            'hide_url': True,
        }]
        return '', False, result


def answerInlineQuery(query_id, inlineQueryResults, next_offset):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    data = {
        'inline_query_id': query_id,
        'results': json.dumps(inlineQueryResults),
        'is_personal': True,
        'cache_time': 0, #default 300
        'next_offset': next_offset
    }
    logging.debug('send inline query data: ' + str(data))
    resp = requests.post(BASE_URL + 'answerInlineQuery', data)
    logging.info('Response: {}'.format(resp.text))


def dealWithInlineQuery(body):
    inline_query = body['inline_query']
    query_text = inline_query['query'].encode('utf-8').strip()
    if len(query_text)>0:
        query_id = inline_query['id']
        query_offset = inline_query['offset']
        chat_id = inline_query['from']['id']
        p = person.getPersonByChatId(chat_id)
        if p:
            next_offset, validQry, query_results = createInlineQueryResultArticle(p, query_id, query_text, query_offset)
            answerInlineQuery(query_id, query_results, next_offset)
            if validQry and not query_offset:
                search.addSearch(p.chat_id, p.getLanguageCode(), query_text, is_searched_emoji=False,
                                 inline_query=True, found_translation=True)

# ================================
# CALLBACK QUERY
# ================================

def dealWithCallbackQuery(body):
    callback_query = body['callback_query']
    data = callback_query['data'].encode('utf-8')
    chat_id = callback_query['from']['id']
    p = person.getPersonByChatId(chat_id)
    #redirectToState(p, 3, inlineButtonText=data)

# ================================
# ================================
# ================================

class SafeRequestHandler(webapp2.RequestHandler):
    def handle_exception(self, exception, debug_mode):
        report_exception()


def updateUser(p, name, last_name, username):
    modified = False
    if p.getFirstName() != name:
        p.name = name
        modified = True
    if p.getLastName() != last_name:
        p.last_name = last_name
        modified = True
    if p.username != username:
        p.username = username
        modified = True
    if not p.enabled:
        p.enabled = True
        modified = True
    if modified:
        p.put()

class WebhookHandler(SafeRequestHandler):

    def post(self):
        #urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        # update_id = body['update_id']
        if 'inline_query' in body:
            dealWithInlineQuery(body)
        #if 'callback_query' in body:
        #    dealWithCallbackQuery(body)
        if 'message' not in body:
            return
        message = body['message']
        message_timestamp = int(message['date'])
        # message_id = message.get('message_id')
        if "chat" not in message:
            return
        # fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']
        if "first_name" not in chat:
            return
        text = message.get('text').encode('utf-8').strip() if "text" in message else ''
        name = chat["first_name"].encode('utf-8')
        last_name = chat["last_name"].encode('utf-8') if "last_name" in chat else None
        username = chat["username"] if "username" in chat else None
        #location = message["location"] if "location" in message else None
        #contact = message["contact"] if "contact" in message else None

        # u'contact': {u'phone_number': u'393496521697', u'first_name': u'Federico', u'last_name': u'Sangati',
        #             u'user_id': 130870321}
        # logging.debug('location: ' + str(location))

        def reply(msg=None, kb=None, markdown=True, inlineKeyboardMarkup=False):
            tell(chat_id, msg, kb=kb, markdown=markdown, inlineKeyboardMarkup=inlineKeyboardMarkup)

        p = person.getPersonByChatId(chat_id)
        #ndb.Key(Person, str(chat_id)).get()

        if p is None:
            # new user
            logging.info("Text: " + text)
            if text == '/help':
                reply(INFO)
            elif text.startswith("/start"):
                new_count = person.getPeopleCount(increment=True)
                p = person.addPerson(chat_id, name, last_name, username)
                reply("Hi {0},  welcome to EmojiWorldBot!\n".format(name) + TERMS_OF_SERVICE)
                restart(p)
                tell_masters("New user #{} : {}".format(new_count, p.getUserInfoString()))
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
                updateUser(p, name, last_name, username)
                restart(p)
            else:
                logging.debug("Sending {0} to state {1} with input '{2}'".format(p.getFirstName(), str(p.state), text))
                repeatState(p, input=text, message_timestamp = message_timestamp)

class ServeEmojiImage(webapp2.RequestHandler):
    def get(self, code_points):
        #logging.debug("Starting serving emoji image {}".format(code_points))
        image_data = emojiUtil.getEmojiImageDataFromSprite(code_points=code_points)
        if image_data:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.headers['Content-Length'] = len(image_data)
            self.response.out.write(image_data)
        else:
            self.response.set_status(400)


def report_exception():
    import traceback
    msg = "❗ Detected Exception: " + traceback.format_exc()
    tell(key.FEDE_CHAT_ID, msg, markdown=False)
    logging.error(msg)


app = webapp2.WSGIApplication([
    ('/set_webhook', SetWebhookHandler),
    ('/get_webhook_info', GetWebhookInfo),
    ('/delete_webhook', DeleteWebhook),
    (key.WEBHOOK_PATH, WebhookHandler),
    ('/getEmojiImg/([^/]+)?', ServeEmojiImage),
    ('/translationUserTable/([^/]+)?', translation.TranslationUserTableHandler),
    ('/translationAggregatedTable/([^/]+)?', translation.TranslationAggregatedTableHandler),
    ('/taggingUserTable/([^/]+)?', userTagging.TaggingUserTableHandler),
    ('/taggingAggregatedTable/([^/]+)?', userTagging.TaggingAggregatedTableHandler),
    ('/taggingLanguagageStats', emojiTables.LanguageUserTagsStatsHandler),
], debug=False)

possibles = globals().copy()
possibles.update(locals())

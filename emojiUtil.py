# -*- coding: utf-8 -*-


import logging
import jsonUtil
import random
import requests

# imported from https://github.com/iamcal/emoji-data/blob/master/emoji_pretty.json
EMOJI_JSON_FILE = 'EmojiData/emoji_pretty.json'
EMOJI_INFO = jsonUtil.json_load_byteified_file(EMOJI_JSON_FILE)
EMOJI_INFO_NO_OBSOLETE = [entry for entry in EMOJI_INFO if entry.get("obsoleted_by",None)==None]


def getEmojiFromCodePoint(code_point, separator='-'):
    codes = code_point.split(separator)
    emoji_uni = ''.join(unichr(int(c,16)) for c in codes)
    emoji_utf = emoji_uni.encode('utf-8')
    return emoji_utf

def getCodePointUpper(e, separator='-', addExtraZeros=True):
    codePoints = [str(hex(ord(c)))[2:] for c in e.decode('utf-8')]
    if addExtraZeros:
        codePoints = [x if len(x)>2 else "00" + x for x in codePoints]
    result = separator.join(codePoints)
    return result.upper()

ALL_EMOJIS = [getEmojiFromCodePoint(entry['unified']) for entry in EMOJI_INFO_NO_OBSOLETE]
NON_QUALIFIED_CODE_POINTS = [entry['non_qualified'] for entry in EMOJI_INFO_NO_OBSOLETE]

UNIFICATION_CODE = "FE0F"
UNIFICATION_CODE_LOWER = UNIFICATION_CODE.lower()

SKIN_TONES = ['🏻', '🏾', '🏿', '🏼', '🏽']
SKIN_TONES_CODE_POINT = [getCodePointUpper(x) for x in SKIN_TONES]

def getAlphaName(emoji):
    code_point = getCodePointUpper(emoji)
    matched_entry = next((entry
                         for entry in EMOJI_INFO_NO_OBSOLETE
                         if entry['unified']==code_point
                         or entry['non_qualified']==code_point),None)
    if matched_entry:
        return matched_entry['short_name']
    return None

def makeCodePointUnified(code_point):
    entry = [x for x in EMOJI_INFO if x['non_qualified']==code_point]
    if len(entry)==1:
        return entry[0]['unified']
    return None

def removeSkinTones(emoji_text):
    for st in SKIN_TONES:
        emoji_text = emoji_text.replace(st, '')
    return emoji_text

def makeCodePointDeObsoleted(code_point):
    try:
        entry = next(x for x in EMOJI_INFO if x['unified']==code_point)
    except StopIteration:
        try:
            entry = next(x for x in EMOJI_INFO if x['non_qualified'] == code_point)
        except StopIteration:
            return None
    return entry.get("obsoleted_by", None)


def checkIfEmojiAndGetNormalized(e):
    if e in ALL_EMOJIS:
        return e
    code_point = getCodePointUpper(e)
    if code_point in NON_QUALIFIED_CODE_POINTS:
        fixed_code_point = makeCodePointUnified(code_point)
        e = getEmojiFromCodePoint(fixed_code_point)
        return e
    emoji_without_skin_tones = removeSkinTones(e)
    if emoji_without_skin_tones != e and emoji_without_skin_tones in ALL_EMOJIS:
        return emoji_without_skin_tones
    renwed_code_point = makeCodePointDeObsoleted(code_point)
    if renwed_code_point:
        renewed_emoji = getEmojiFromCodePoint(renwed_code_point)
        return renewed_emoji
    return None


def getRandomEmoji():
    return random.choice(ALL_EMOJIS)

####################################
# EMOJI IMG UTIL FUNCTIONS
####################################

#EMOJI_PNG_URL = 'https://dl.dropboxusercontent.com/u/12016006/Emoji/png_one_64/'
#EMOJI_PNG_URL = 'https://s3.eu-central-1.amazonaws.com/kercos/png_one_64/'
#EMOJI_PNG_URL = 'http://emojiworldbot.appspot.com/getEmojiImg/'
EMOJI_PNG_URL_GIT_TWITTER_IAMCAL = 'https://github.com/iamcal/emoji-data/raw/master/img-twitter-72/'
EMOJI_PNG_URL_GIT_APPLE_IAMCAL = 'https://github.com/iamcal/emoji-data/raw/master/img-apple-160/'
#EMOJI_PNG_URL_EMOJIPEDIA = 'https://emojipedia-us.s3.amazonaws.com/thumbs/240/twitter/131/'
EMOJI_PNG_URL_GIT_LOICPIREZ = 'https://github.com/loicpirez/EmojiExtractor/raw/master/emojipedia.org/twitter/' # 1f385_1f3fe.png no fe0f
EMOJI_ONE_WIKIMEDIA = 'https://github.com/emojione/emojione/raw/2.2.7/assets/png_128x128/{}.png' #0023-20e3

def hasImageApple(code_point):
    try:
        entry = next(x for x in EMOJI_INFO if x['unified']==code_point)
    except StopIteration:
        return False
    return entry.get("has_img_apple", False)

def getEmojiUrlFromEmojione(e):
    codePointUpper = getCodePointUpper(e, separator='-', addExtraZeros=True)
    if UNIFICATION_CODE in codePointUpper:
        points = codePointUpper.split('-')
        points.remove(UNIFICATION_CODE)
        codePointUpper = '-'.join(points)
    emojiUrl = EMOJI_ONE_WIKIMEDIA.format(codePointUpper.lower())
    logging.debug('Requesting emoj url: ' + emojiUrl)
    return emojiUrl

def getEmojiUrlFromGitLoicpirez(e):
    codePointUpper = getCodePointUpper(e, separator='_', addExtraZeros=False)
    codePointUpper = codePointUpper.split('_fe0f')[0]
    # try:
    #     entry = next(e for e in EMOJI_INFO if e['unified']==codePointUpper)
    # except StopIteration:
    #     return None
    # title = entry['short_name'].replace('_','-')
    # emojiUrl = EMOJI_PNG_URL + '{}_{}'.format(title,entry['image'])
    emojiUrl = EMOJI_PNG_URL_GIT_LOICPIREZ + '{}.png'.format(codePointUpper.lower())
    logging.debug('Requesting emoj url: ' + emojiUrl)
    return emojiUrl

def getEmojiUrlFromGitIamcalTwitter(e):
    codePointUpper = getCodePointUpper(e, separator='-')
    if codePointUpper in NON_QUALIFIED_CODE_POINTS:
        logging.debug('Detected non qualified emoji in getEmojiUrlFromGitIamcal: {}'.format(codePointUpper))
        codePointUpper = makeCodePointUnified(codePointUpper)
    emojiUrl = EMOJI_PNG_URL_GIT_TWITTER_IAMCAL + '{}.png'.format(codePointUpper.lower())
    logging.debug('Requesting emoj url: ' + emojiUrl)
    return emojiUrl

def getEmojiUrlFromGitIamcalApple(e):
    codePointUpper = getCodePointUpper(e, separator='-')
    if codePointUpper in NON_QUALIFIED_CODE_POINTS:
        logging.debug('Detected non qualified emoji in getEmojiUrlFromGitIamcal: {}'.format(codePointUpper))
        codePointUpper = makeCodePointUnified(codePointUpper)
    emojiUrl = EMOJI_PNG_URL_GIT_APPLE_IAMCAL + '{}.png'.format(codePointUpper.lower())
    logging.debug('Requesting emoj url: ' + emojiUrl)
    return emojiUrl


def getEmojiPngUrl(e):
    codePointUpper = getCodePointUpper(e, separator='-')
    if hasImageApple(codePointUpper):
        url = getEmojiUrlFromGitIamcalApple(e)
    else:
        url = getEmojiUrlFromGitIamcalTwitter(e)
    logging.debug("Sending emoji image. Emoji: {} Codepoints: {} Url: {}".format(e,getCodePointUpper(e), url))
    return url

def getEmojiPngDataFromUrl(e):
    from google.appengine.api import urlfetch
    urlfetch.set_default_fetch_deadline(20)
    png_url = getEmojiPngUrl(e)
    assert png_url
    try:
        r = requests.get(png_url)
        png_data = r.content
        return png_data
    except requests.ConnectionError:
        from time import sleep
        sleep(1)
        return getEmojiPngDataFromUrl(e)



def getEmojiStickerDataFromUrl(e):
    png_data = getEmojiPngDataFromUrl(e)
    assert png_data
    from google.appengine.api import images
    sticker_data = images.crop(image_data=png_data, left_x=0.0, top_y=0.0,
        right_x=1.0, bottom_y=1.0, output_encoding=images.WEBP)
    return sticker_data


# =============================
# Check Emoji image Files and Url
# =============================

def checkAllEmojiUrl():
    total = 0
    error = 0
    for e in ALL_EMOJIS:
        total += 1
        url = getEmojiUrlFromEmojione(e)
        status_code = requests.get(url).status_code
        if status_code==200:
            print("ok: " + url)
        else:
            error += 1
            print("error: " + url)
    print("{0}/{1}".format(str(error),str(total)))
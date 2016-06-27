# -*- coding: utf-8 -*-

"""
import sys
sys.path.append('/usr/local/google_appengine/')
sys.path.append('/usr/local/google_appengine/lib/yaml/lib/')
if 'google' in sys.modules:
    del sys.modules['google']
import os.path
"""

import logging
from emoji_unicode import Emoji
from emoji_unicode.utils import code_point_to_unicode, unicode_to_code_point
from emojiTables import ALL_EMOJIS
import urllib2


def getNormalizedEmoji(text):
    textuni = text.decode('utf-8')
    emoji = Emoji(textuni)
    norm = u''
    for e in emoji.as_map():
       norm += code_point_to_unicode(e[1]) #e[0] #
    return norm.encode('utf-8')

# =============================
# Emoji image Url
# =============================

EMOJI_PNG_URL = 'https://dl.dropboxusercontent.com/u/12016006/Emoji/png_one_64/'

def getCodePoint(e):
    codePoints = [str(hex(ord(c)))[2:] for c in e.decode('utf-8')]
    codePoints = [x if len(x)>2 else "00" + x for x in codePoints]
    result = '_'.join(codePoints)
    return result

def getEmojiImageUrl(e):
    codePoints = getCodePoint(e)
    emojiUrl = EMOJI_PNG_URL + codePoints + ".png"
    logging.debug('Requesting emoj url: ' + emojiUrl)
    return emojiUrl

def getEmojiImageFilePath(e):
    codePoints = getCodePoint(e)
    return 'png_one_64/{0}.png'.format(codePoints)


"""
emojiFileIdEntry = emojiTables.getEmojiFileIdEntry(emoji)
if emojiFileIdEntry:
    file_id = emojiFileIdEntry.file_id
    sendImageFile(chat_id, file_id = file_id)
else:
    img_url = getEmojiImageUrl(emoji)
    file_id = sendImageFile(chat_id, img_url = img_url)
    emojiTables.addEmojiFileId(emoji, file_id)
"""

# =============================
# Check Emoji image Files and Url
# =============================

def checkAllEmojiUrl():
    total = 0
    error = 0
    for e in ALL_EMOJIS:
        total += 1
        url = getEmojiImageUrl(e)
        try:
            urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            print(str(e.code) + ": " + url)
            error += 1
            continue
        except urllib2.URLError, e:
            print(str(e.args) + ": " + url)
            error += 1
            continue
        #print("ok: " + url)
    print("{0}/{1}".format(str(error),str(total)))

def checkAllEmojiFile():
    path = "/Users/fedja/Dropbox/Public/Emoji/png_one_64/"
    total = 0
    error = 0
    for e in ALL_EMOJIS:
        total += 1
        codePoints = getCodePoint(e)
        file = path + codePoints + ".png"
        if not os.path.isfile(file):
            print("not found: " + file)
            error += 1
    print("{0}/{1}".format(str(error), str(total)))
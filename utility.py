# -*- coding: utf-8 -*-

import string
import unicodedata
from google.appengine.ext import ndb
import re
import textwrap

# ================================
# AUXILIARY FUNCTIONS for strings
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

def contains_roman_chars(unistr):
    return any(is_latin(uchr)
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
    msg = ''.join(x for x in unicodedata.normalize('NFKD', text_uni) if (x in [' ','_'] or x in string.ascii_letters))
    return msg.encode('utf-8')

# remove accents and make lower
def normalizeString(text):
    return remove_accents_roman_chars(text.lower()).lower()

def representsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def representsIntBetween(s, low, high):
    if not representsInt(s):
        return False
    sInt = int(s)
    if sInt>=low and sInt<=high:
        return True
    return False

def escapeMarkdown(text):
    for char in '*_`[':
        text = text.replace(char, '\\'+char)
    return text

def containsMarkdown(text):
    for char in '*_`[':
        if char in text:
            return True
    return False

def markdownSafe(text):
    return not containsMarkdown(text)

def markdownSafeList(list):
    return all(markdownSafe(x) for x in list)

def containsMarkdownList(list):
    return any(containsMarkdown(x) for x in list)


# ================================
# comma and semicolun delimiter
# see:
# #http://unicode-search.net/unicode-namesearch.pl?term=COMMA
# #http://unicode-search.net/unicode-namesearch.pl?term=SEMICOLON
# ================================

ALL_DELIMITERS_UNI = [
    u'\u002C', #COMMA
    u'\u055D', #ARMENIAN COMMA
    u'\u060C', #ARABIC COMMA
    u'\u07F8', #NKO COMMA
    u'\u1363', #ETHIOPIC COMMA
    u'\u1802', #MONGOLIAN COMMA
    u'\u1808', #MONGOLIAN MANCHU COM­MA
    u'\u236A', #APL FUNCTIONAL SYMBOL COMMA BAR
    u'\uFE50', #SMALL COM­MA
    u'\uFE51', #SMALL IDEO­GRAPHIC COM­MA
    u'\uFF0C', #FULLWIDTH COM­MA
    u'\uFF64', #HALFWIDTH IDEO­GRAPHIC COM­MA
    u'\u003B', #SEMICOLON
    u'\u061B', #ARABIC SEMICOLON
    u'\u1364', #ET­HI­O­PIC SEMICOLON
    u'\u204F', #RE­VER­SED SEMICOLON
    u'\u236E', #APL FUNCTIONAL SYMBOL SEMICOLON UNDERBAR
    u'\uFE14', #PRE­SEN­TA­TI­ON FORM FOR VER­TI­CAL SEMICOLON
    u'\uFE54', #SMALL SEMICOLON
    u'\uFF1B', #FULLWIDTH SEMICOLON
]

ALL_DELIMITERS_UTF = [x.encode('utf-8') for x in ALL_DELIMITERS_UNI]

# ================================
# AUXILIARY FUNCTIONS for array (keyboard)
# ================================

def makeArray2D(data_list, length=2):
    return [data_list[i:i+length] for i in range(0, len(data_list), length)]

def distributeElementMaxSize(seq, maxSize=5):
    lines = len(seq) / maxSize
    if len(seq) % maxSize > 0:
        lines += 1
    avg = len(seq) / float(lines)
    out = []
    last = 0.0
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    return out


def segmentArrayOnMaxChars(array, maxChar=20, ignoreString=None):
    #logging.debug('selected_tokens: ' + str(selected_tokens))
    result = []
    lineCharCount = 0
    currentLine = []
    for t in array:
        t_strip = t.replace(ignoreString, '') if ignoreString and ignoreString in t else t
        t_strip_size = len(t_strip.decode('utf-8'))
        newLineCharCount = lineCharCount + t_strip_size
        if not currentLine:
            currentLine.append(t)
            lineCharCount = newLineCharCount
        elif newLineCharCount > maxChar:
            #logging.debug('Line ' + str(len(result)+1) + " " + str(currentLine) + " tot char: " + str(lineCharCount))
            result.append(currentLine)
            currentLine = [t]
            lineCharCount = t_strip_size
        else:
            lineCharCount = newLineCharCount
            currentLine.append(t)
    if currentLine:
        #logging.debug('Line ' + str(len(result) + 1) + " " + str(currentLine) + " tot char: " + str(lineCharCount))
        result.append(currentLine)
    return result

def unindent(s):
    return re.sub('[ ]+', ' ', textwrap.dedent(s))

#####################
# VERY DANGEREOUS OPERATIONS
#####################

def deleteData(language=None):
    deleteTagging(language)
    #deleteTranslation(language)

def deleteTagging(language=None):
    import tagging
    ndb.delete_multi(tagging.UserTagging.query().fetch(keys_only=True))
    ndb.delete_multi(tagging.AggregatedEmojiTags.query().fetch(keys_only=True))


def deleteProperty(model, prop_name):
    toUpdate = model.query().fetch()
    for ent in toUpdate:
        if prop_name in ent._properties:
            del ent._properties[prop_name]
    ndb.put_multi(toUpdate)


"""
def deleteTagging(language=None):
    import tagging
    if language:
        ndb.delete_multi(
            tagging.UserTagging.query(tagging.UserTagging.language==language).fetch(keys_only=True))
        ndb.delete_multi(
            tagging.AggregatedEmojiTags.query(tagging.AggregatedEmojiTags.language==language).fetch(keys_only=True))
        ndb.delete_multi(
            tagging.AggregatedTagEmojis.query(tagging.AggregatedTagEmojis.language==language).fetch(keys_only=True))
    else:
        ndb.delete_multi(tagging.UserTagging.query().fetch(keys_only=True))
        ndb.delete_multi(tagging.AggregatedEmojiTags.query().fetch(keys_only=True))
        ndb.delete_multi(tagging.AggregatedTagEmojis.query().fetch(keys_only=True))
"""

"""
def deleteTranslation(language=None):
    import translation
    if language:
        ndb.delete_multi(
            translation.UserTranslationTag.query(
                translation.UserTranslationTag.dst_language==language).fetch(keys_only=True))
        ndb.delete_multi(
            translation.AggregatedEmojiTranslations.query(
                translation.AggregatedEmojiTranslations.dst_language==language).fetch(keys_only=True))
    else:
        ndb.delete_multi(translation.UserTranslationTag.query().fetch(keys_only=True))
        ndb.delete_multi(translation.AggregatedEmojiTranslations.query().fetch(keys_only=True))
"""



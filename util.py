# -*- coding: utf-8 -*-

import string
import unicodedata

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


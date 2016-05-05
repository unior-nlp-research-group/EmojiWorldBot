# -*- coding: utf-8 -*-

from emoji_unicode import Emoji, normalize
from emoji_unicode.utils import code_point_to_unicode, unicode_to_code_point

def getNormalizedEmoji(text):
    textuni = text.decode('utf-8')
    emoji = Emoji(textuni)
    norm = u''
    for e in emoji.as_map():
       norm += code_point_to_unicode(e[1]) #e[0] #
    return norm.encode('utf-8')

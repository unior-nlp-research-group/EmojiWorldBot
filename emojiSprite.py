# -*- coding: utf-8 -*-
import jsonUtil
from PIL import Image
import StringIO
import jsonUtil
from emojiUtil import getCodePoint
import logging


EMOJI_JSON_FILE = 'EmojiData/emoji_pretty.json'
EMOJI_INFO = jsonUtil.json_load_byteified_file(EMOJI_JSON_FILE)
EMOJI_SIZE = 64
EMOJI_SPRITE_FILE = 'EmojiData/sheet_twitter_{}_indexed_128.png'.format(EMOJI_SIZE)
EMOJI_SPRITE_IMAGE = Image.open(EMOJI_SPRITE_FILE)
EMOJI_SPRITE_WIDTH, EMOJI_SPRITE_HEIGHT = EMOJI_SPRITE_IMAGE.size
SPRITE_IMG_STR = open(EMOJI_SPRITE_FILE, 'r').read()

def getEmojiBoxInSprite(e=None, code_points=None):
    assert e!=None or code_points!=None
    init_space = 1
    inbetween_space = 2
    if code_points is None:
        code_points = getCodePoint(e).upper()
    #logging.debug('codePoints: {}'.format(code_points))
    emoji_entry = [x for x in EMOJI_INFO if x['unified'] == code_points or x['non_qualified'] == code_points]
    if emoji_entry:
        x = emoji_entry[0]["sheet_x"]
        y = emoji_entry[0]["sheet_y"]
        x_left = x * (EMOJI_SIZE + inbetween_space) + init_space
        y_top = y * (EMOJI_SIZE + inbetween_space) + init_space
        x_right = x_left + EMOJI_SIZE
        y_bottom = y_top + EMOJI_SIZE
        # print("{} {} {} {}".format(x_left, y_top, x_right, y_bottom))
        box = (x_left, y_top, x_right, y_bottom)
        return box
    logging.debug('Emoji {} with codepoints {} not found in table'.format(e, code_points))
    return None

def getEmojiImageDataFromSprite(e=None, code_points=None, show=False):
    # someshow PIL returns a pixelated image
    '''
    box = getEmojiBoxInSprite(e,code_points)
    assert box
    region = EMOJI_SPRITE_IMAGE.crop(box)
    cropped_image = Image.new("RGBA", (EMOJI_SIZE, EMOJI_SIZE), (0, 0, 0, 0))
    cropped_image.paste(region, (0, 0))
    imgData = StringIO.StringIO()
    cropped_image.save(imgData, format="PNG", quality=100)
    if show:
        cropped_image.show()
    return imgData.getvalue()
    '''
    from google.appengine.api import images
    box = getEmojiBoxInSprite(e, code_points)
    assert box
    x_left = float(box[0]) / EMOJI_SPRITE_WIDTH
    y_top = float(box[1]) / EMOJI_SPRITE_HEIGHT
    x_right = float(box[2]) / EMOJI_SPRITE_WIDTH
    y_bottom = float(box[3]) / EMOJI_SPRITE_HEIGHT
    sticker_data = images.crop(
        image_data=SPRITE_IMG_STR, left_x=x_left, top_y=y_top,
        right_x=x_right, bottom_y=y_bottom, output_encoding=images.PNG)
    return sticker_data


def getEmojiStickerFromSprite(e):
    from google.appengine.api import images
    box = getEmojiBoxInSprite(e)
    assert box
    x_left = float(box[0]) / EMOJI_SPRITE_WIDTH
    y_top = float(box[1]) / EMOJI_SPRITE_HEIGHT
    x_right = float(box[2]) / EMOJI_SPRITE_WIDTH
    y_bottom = float(box[3]) / EMOJI_SPRITE_HEIGHT
    sticker_data = images.crop(
        image_data=SPRITE_IMG_STR, left_x=x_left, top_y=y_top,
        right_x=x_right, bottom_y=y_bottom, output_encoding=images.WEBP)
    return sticker_data
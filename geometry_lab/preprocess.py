"""Deterministic foreground preprocessing; no segmentation model or external upload."""
import math

from PIL import Image


def foreground(image,occupancy=.85,size=512):
    if image.mode!='RGBA' or not .5<=occupancy<=.95 or not 128<=size<=1024:
        raise ValueError('RGBA mask, bounded occupancy and output size required')
    alpha=image.getchannel('A')
    if alpha.getextrema()[0]==255 or alpha.getbbox() is None:
        raise ValueError('A nonempty isolated foreground with transparent background is required')
    box=alpha.getbbox()
    crop=image.crop(box)
    side=math.ceil(max(crop.size)/occupancy)
    canvas=Image.new('RGBA',(side,side),(128,128,128,255))
    canvas.alpha_composite(crop,((side-crop.width)//2,(side-crop.height)//2))
    return canvas.convert('RGB').resize((size,size),Image.Resampling.LANCZOS),dict(
        crop_box=list(box),square_side=side,occupancy=occupancy,size=size,background_rgb=[128,128,128])

import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('PIL'),'Geometry environment includes Pillow')
class ForegroundTests(unittest.TestCase):
    def test_alpha_is_composited_on_gray_and_input_is_preserved(self):
        from PIL import Image
        from geometry_lab.preprocess import foreground
        image=Image.new('RGBA',(80,80),(0,0,0,0))
        for x in range(25,55):
            for y in range(15,65):
                image.putpixel((x,y),(255,0,0,255))
        before=image.tobytes()
        result,info=foreground(image,occupancy=.5,size=128)
        self.assertEqual(result.mode,'RGB')
        self.assertEqual(result.getpixel((0,0)),(128,128,128))
        self.assertEqual(result.getpixel((64,64)),(255,0,0))
        self.assertEqual(info['crop_box'],[25,15,55,65])
        self.assertEqual(image.tobytes(),before)

    def test_opaque_or_empty_masks_fail_without_segmentation_guessing(self):
        from PIL import Image
        from geometry_lab.preprocess import foreground
        for image in (Image.new('RGBA',(4,4),(0,0,0,255)),Image.new('RGBA',(4,4),(0,0,0,0))):
            with self.assertRaises(ValueError):
                foreground(image)

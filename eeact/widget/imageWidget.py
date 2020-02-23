import os
import ueberzug.lib.v0 as ueberzug
from .widget import Widget

class ImageWidget(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.path = ""
      self.focusable = False
      self.img = None
      self.covered = False

   #pylint: disable=arguments-differ
   def _init(self, *args):
      super()._init(*args)
      self.img = self.manager["ueber"].create_placement(
         self.name,
         scaler=ueberzug.ScalerOption.FIT_CONTAIN.value
      )

   def _covered(self, covered):
      super()._covered(covered)
      self.touch()
      self.covered = covered

   def set_image(self, path):
      if not os.path.isfile(path):
         return
      self.path = path
      self.touch()

   def clear_image(self):
      self.path = ""
      self.touch()

   def draw(self, win):
      if self.path and not self.covered:
         with self.manager["ueber"].lazy_drawing:
            self.img.x = self.x
            self.img.y = self.y
            self.img.width = self.w
            self.img.height = self.h
            self.img.path = self.path
            self.img.visibility = ueberzug.Visibility.VISIBLE
      else:
         self.img.visibility = ueberzug.Visibility.INVISIBLE

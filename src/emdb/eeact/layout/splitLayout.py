from enum import Enum, auto
from .layout import Layout
from ..widget import Widget

class SplitLayout(Layout):
   class Alignment(Enum):
      VERTICAL = auto()
      HORIZONTAL = auto()

   def __init__(self, name, alignment, *args):
      super().__init__(name)
      self.alignment = alignment
      self.ratio = []
      self.widgets = []

      for i,w in enumerate(args):
         if i % 2 == 0:
            if not isinstance(w, Widget):
               raise Exception("SplitLayout expected widget on index {}".format(i))
            self.widgets.append(w)
         else:
            if not isinstance(w, float) and not isinstance(w, int):
               raise Exception("SplitLayout expected float on index {}".format(i))
            self.ratio.append(w)

      if len(self.widgets) != len(self.ratio):
         raise Exception("SplitLayout needs one ratio per widget")
      if len([x for x in self.ratio if x == 0.0]) != 1:
         raise Exception("SplitLayout needs exactly one floating zero as ratio")

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      list(
         map(
            lambda wd: wd[0]._init(*wd[1], manager, self),
            zip(self.widgets, self._get_dimensions())
         )
      )

   def _get_dimensions(self):
      floats = [f for f in self.ratio if isinstance(f, float)]
      ints = [i for i in self.ratio if isinstance(i, int)]
      constantspace = sum(ints)
      if self.alignment == self.Alignment.VERTICAL:
         previousx = self.y
         dimension = self.h - constantspace
      else:
         previousx = self.x
         dimension = self.w - constantspace

      widths = [int(dimension * f) for f in floats]
      widths[widths.index(0.0)] = dimension - sum(widths)

      res = []
      for r in self.ratio:
         if isinstance(r, int):
            w = ints.pop(0)
         else:
            w = widths.pop(0)
         res.append((previousx, self.y, w, self.h))
         previousx += w

      # transform if vertical
      if self.alignment == self.Alignment.VERTICAL:
         res = [(self.x, x, self.w, w) for (x, _, w, _) in res]

      return res

   #pylint: disable=protected-access,fixme
   def _resize(self, stdx, stdy, stdw, stdh):
      # FIXME: self.resize is called before the children are updated, might be a problem
      super()._resize(stdx, stdy, stdw, stdh)
      list(
         map(
            lambda wd: wd[0]._resize(*wd[1]),
            zip(self.widgets, self._get_dimensions())
         )
      )

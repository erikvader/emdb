import curses
import curses.ascii as ca
import random
from ..StringFormatter import ice
from .widget import Widget

class ListWidget(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.list = []
      self.selected = 0
      self.highlighted = set()
      self._index_list = []
      self._list_top = 0
      self._last_filter_fun = lambda _: True

      from functools import cmp_to_key
      self._last_sort_fun = cmp_to_key(lambda a,b: True)

   def _select(self, index):
      self.touch()
      if not self.list:
         return
      self.selected = index

      if self.selected >= len(self._index_list):
         self.selected = len(self._index_list) - 1

      if self.selected < 0:
         self.selected = 0

   def next(self, step=1):
      self._select(self.selected + step)

   def prev(self, step=1):
      self._select(self.selected - step)

   def goto_first(self):
      self._select(0)

   def goto_last(self):
      self._select(len(self._index_list) - 1)

   def goto_random(self):
      self._select(random.randrange(len(self._index_list)))

   def highlight(self):
      if not self._index_list:
         return

      i = self._index_list[self.selected]
      if i in self.highlighted:
         self.highlighted.remove(i)
      else:
         self.highlighted.add(i)
      self.touch()

   def clear_highlighted(self):
      self.highlighted.clear()

   def highlight_by(self, pred):
      self.highlighted = {i for i,x in enumerate(self.list) if pred(x)}
      self.touch()

   def set_list(self, l):
      self.list = l
      self.clear_filter()
      self.clear_highlighted()

   def add(self, a, select_new=True):
      self.list.append(a)
      if select_new:
         self._index_list.append(len(self.list) - 1)
         self.selected = len(self._index_list) - 1
      self.refresh()

   def _remove_index(self, i):
      del self.list[i]
      def fix(x):
         return (h if h < i else h-1 for h in x if h != i)
      self.highlighted = set(fix(self.highlighted))
      self._index_list = list(fix(self._index_list))
      self._select(self.selected)

   def remove_selected(self):
      if not self._index_list:
         return
      self._remove_index(self._index_list[self.selected])

   def filter_by(self, pred):
      if not self.list:
         return
      self._index_list = [i for i,x in enumerate(self.list) if pred(x)]
      self._select(self.selected)
      self._last_filter_fun = pred
      self.touch()

   def clear_filter(self):
      self.filter_by(lambda _: True)

   def sort_by(self, keyfun):
      if not self.list:
         return

      dec = [(l, i) for i,l in enumerate(self.list)]
      old_selected = self._index_list[self.selected]

      dec.sort(key=lambda tup: keyfun(tup[0]))

      self.list = [l for l,_ in dec]
      self.highlighted = {i for i,(_,h) in enumerate(dec) if h in self.highlighted}
      self._index_list = [i for i,(_,il) in enumerate(dec) if il in self._index_list]

      new_selected = [a for _,a in dec].index(old_selected)
      self.selected = self._index_list.index(new_selected)

      self._last_sort_fun = keyfun
      self.touch()

   def get_selected(self):
      if self._index_list:
         return self.list[self._index_list[self.selected]]
      else:
         return None

   def get_visible(self):
      return [self.list[i] for i in self._index_list]

   # in no particular order
   def get_highlighted(self):
      return [x for i,x in enumerate(self.list) if i in self.highlighted]

   def key_event(self, key):
      if key == curses.KEY_DOWN or key == ord('j'):
         self.next()
      elif key == curses.KEY_UP or key == ord('k'):
         self.prev()
      elif key == ca.SP:
         self.highlight()
      elif key == ord('g'):
         self.goto_first()
      elif key == ord('G'):
         self.goto_last()
      else:
         return False
      return True

   def refresh(self):
      self.sort_by(self._last_sort_fun)
      self.filter_by(self._last_filter_fun)
      self.touch()

   def _str_of(self, i, width):
      obj = self.list[i]
      if hasattr(obj, "widgetFormat"):
         return obj.widgetFormat(width)
      return str(obj)

   def draw(self, win):
      win.erase()
      todraw = self._index_list
      if not todraw:
         return

      if self.selected < self._list_top:
         self._list_top = self.selected
      elif self.selected > self._list_top + self.h - 1:
         self._list_top = self.selected - self.h + 1

      for l,i in enumerate(todraw[self._list_top:]):
         self.format_draw(win, 0, l, self._str_of(i, self.w), dots=True)
         attr = 0
         if l + self._list_top == self.selected:
            attr = curses.A_REVERSE
         if i in self.highlighted:
            attr |= self.manager.get_attr("list_highlight")
         ice(win.chgat, l, 0, attr)

class FancyListWidget(ListWidget):
   def draw(self, win):
      win.erase()
      mid = int(self.h / 2)

      win.addstr(mid, 0, "-> ", self.manager.get_attr("fancy_list_arrow"))

      todraw = self._index_list
      if not todraw:
         return

      startx = 3
      linewidth = self.w - startx

      def draw_these(ran):
         for l,item in ran:
            self.format_draw(win, startx, l, self._str_of(item, linewidth), dots=True)
            if item in self.highlighted:
               ice(win.chgat, l, startx, self.manager.get_attr("list_highlight"))

      draw_these(zip(range(mid, self.h), todraw[self.selected:]))
      draw_these(zip(reversed(range(0, mid)), reversed(todraw[:self.selected])))

      win.chgat(mid, startx, curses.A_REVERSE)

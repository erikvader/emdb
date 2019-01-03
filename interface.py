import curses
import curses.panel as cp
import curses.ascii as ca
from enum import Enum, auto
import os
import subprocess as S
from PIL import Image
import struct
import sys
import fcntl
import termios
from time import sleep, monotonic_ns
from threading import Thread, Lock
from collections import deque
from . import StringFormatter
from .StringFormatter import ice

class Widget():
   def __init__(self, name):
      self.x = 0
      self.y = 0
      self.w = 0
      self.h = 0
      self.redraw = True
      self.is_focused = False
      self.panel = None
      self.is_layout = False
      self.resized = False
      self.parent = None
      self.manager = None
      self.name = name
      self.focusable = True
      self.initialized = False

   def _init(self, x, y, w, h, manager, parent):
      self.x = x
      self.y = y
      self.w = w
      self.h = h
      if not self.is_layout:
         self.panel = cp.new_panel(curses.newwin(self.h, self.w, self.y, self.x))
      else:
         self.panel = None
      self.parent = parent
      self.manager = manager
      self.manager.widgets[self.name] = self
      self.init()
      self.initialized = True

   def init(self):
      pass

   def _draw(self):
      self.draw(self.panel.window())
      self.redraw = False
      self.resized = False

   def draw(self, win):
      pass

   def format_draw(self, win, x, y, string, **kwargs):
      return StringFormatter.draw(win, x, y, string, self.manager, **kwargs)

   def _key_event(self, key):
      return self.key_event(key)

   def key_event(self, _key):
      return False

   def touch(self):
      self.redraw = True

   def untouch(self):
      self.redraw = False

   def _resize(self, stdx, stdy, stdw, stdh):
      if self.panel:
         self.panel.window().resize(stdh, stdw)
         self.panel.move(stdy, stdx)

      self.x = stdx
      self.y = stdy
      self.w = stdw
      self.h = stdh

      self.touch()
      self.resized = True
      self.resize(stdx, stdy, stdw, stdh)

   def resize(self, stdx, stdy, stdw, stdh):
      pass

   #pylint: disable=protected-access
   def focus(self):
      if not self.focusable:
         raise Exception("can't focus anything non-focusable")

      self._focus()
      if self.parent:
         self.parent._focus_child(self)

   def onfocus(self):
      pass

   def _focus_child(self, _child):
      if not self.is_layout:
         raise Exception("can't focus child on a widget")

   def _unfocus(self):
      self.is_focused = False
      self.touch()

   def _focus(self):
      self.is_focused = True
      self.manager.current_focus = self
      self.touch()
      self.onfocus()

   def _hide(self):
      if self.panel:
         self.panel.hide()

   def _show(self):
      if self.panel:
         self.panel.show()

   def is_hidden(self):
      if self.panel:
         return self.panel.hidden()
      raise Exception("this widget doesn't have a panel")

   def map_focused(self, f, *args, **kwargs):
      if kwargs["top_down"]:
         if self.parent:
            self.parent.map_focused(f, *args, **kwargs)
         f(self, *args, **kwargs)
      else:
         f(self, *args, **kwargs)
         if self.parent:
            self.parent.map_focused(f, *args, **kwargs)

class Layout(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.widgets = []
      self.focused = 0
      self.is_layout = True
      self.focusable = False

   #pylint: disable=protected-access
   def _show(self):
      for w in self.widgets:
         w._show()

   #pylint: disable=protected-access
   def _hide(self):
      for w in self.widgets:
         w._hide()

   #pylint: disable=protected-access
   def is_hidden(self):
      for w in self.widgets:
         if not w.is_hidden():
            return False
      return True

   #pylint: disable=protected-access
   def _focus_child(self, child):
      super()._focus_child(child)
      for i,w in enumerate(self.widgets):
         if w == child:
            self.change_focus(i, dofocus=False)
            break
      else:
         raise Exception("didn't find any child to focus")

      if self.parent:
         self.parent._focus_child(self)

   def _unfocus(self):
      self.widgets[self.focused]._unfocus()

   def _focus(self):
      self.widgets[self.focused]._focus()

   def change_focus(self, to, dofocus=True):
      newfocus = to % len(self.widgets)
      if newfocus != self.focused:
         self.widgets[self.focused]._unfocus()
         self.focused = newfocus
         if dofocus:
            self.widgets[self.focused]._focus()

   # pylint: disable=protected-access
   def _key_event(self, key):
      if not self.widgets[self.focused]._key_event(key):
         return self.key_event(key)
      return True

   #pylint: disable=protected-access
   def _draw(self):
      self.redraw = True
      self.resized = False
      for w in self.widgets:
         if w.redraw:
            w._draw()

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

class InputWidget(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.value = []
      self.cursor = 0
      self._offset = 0

   def clear(self):
      self.value = []
      self.cursor = 0
      self._offset = 0

   def get_input(self):
      return "".join(self.value)

   def set_initial_input(self, initial):
      self.value = list(initial)
      self.cursor = min(len(self.value), self.w - 1)
      self._offset = len(self.value) - self.cursor

   def _fix_single_move(self):
      if self.cursor >= self.w:
         self.cursor -= 1
         self._offset += 1
      elif self.cursor < 0:
         self.cursor += 1
         self._offset -= 1

   def _shift_cursor_to_middle(self):
      m = self.w // 2
      to_move = m - self.cursor
      if to_move < 0:
         raise Exception("wrong side of the middle, implement later")
      to_move = min(to_move, self._offset)
      self._offset -= to_move
      self.cursor += to_move

   def key_event(self, key):
      if ca.isalnum(key) or key == ord(' '):
         self.value.insert(self._offset + self.cursor, chr(key))
         self.cursor += 1
         self._fix_single_move()
         self.changed()
      elif key == curses.KEY_LEFT:
         if self.cursor + self._offset > 0:
            self.cursor -= 1
            self._fix_single_move()
      elif key == curses.KEY_RIGHT:
         if self.cursor + self._offset < len(self.value):
            self.cursor += 1
            self._fix_single_move()
      elif key == ca.BS or key == curses.KEY_BACKSPACE:
         if self.cursor + self._offset > 0:
            del self.value[self._offset + self.cursor-1]
            self.cursor -= 1
            if self.cursor == 0:
               self._shift_cursor_to_middle()
            self.changed()
      else:
         return False
      self.touch()
      return True

   def changed(self):
      pass

   def draw(self, win):
      win.erase()
      x = 0
      for c in self.value[self._offset:]:
         if x > self.w:
            break
         ice(win.addch, 0, x, c)
         x += 1
      ice(win.chgat, 0, self.cursor, 1, self.manager.get_attr("input_cursor"))

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
      if not self.list:
         return
      self.selected = index

      if self.selected >= len(self._index_list):
         self.selected = len(self._index_list) - 1

      if self.selected < 0:
         self.selected = 0

      self.touch()

   def next(self, step=1):
      self._select(self.selected + step)

   def prev(self, step=1):
      self._select(self.selected - step)

   def goto_first(self):
      self._select(0)

   def goto_last(self):
      self._select(len(self._index_list) - 1)

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

   def add(self, a):
      self.list.append(a)
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
      self._index_list = [i for i,x in enumerate(self.list) if pred(x)]
      self._select(self.selected)
      self._last_filter_fun = pred
      self.touch()

   def clear_filter(self):
      self.filter_by(lambda _: True)

   def sort_by(self, keyfun):
      dec = [(l, i in self._index_list, i in self.highlighted) for i,l in enumerate(self.list)]
      self.highlighted.clear()
      self._index_list.clear()

      dec.sort(key=lambda tup: keyfun(tup[0]))

      self.list = [l for l,_,_ in dec]
      self.highlighted = {i for i,(_,_,h) in enumerate(dec) if h}
      self._index_list = [i for i,(_,il,_) in enumerate(dec) if il]

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
      self.filter_by(self._last_filter_fun)
      self.sort_by(self._last_sort_fun)
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

class ImageWidget(Widget):
   def __init__(self, name):
      super().__init__(name)
      self.path = ""
      self.img_h = 0
      self.img_w = 0
      self.cw = 0
      self.ch = 0
      self.focusable = False
      self.w3mpath = "/usr/lib/w3m/w3mimgdisplay"
      self.w3m = None
      self.in_idle_queue = False

   #pylint: disable=protected-access,arguments-differ
   def _init(self, *args):
      super()._init(*args)
      self.cw, self.ch = self._get_font_dimensions()
      self.w3m = S.Popen([self.w3mpath], stdin=S.PIPE, stdout=S.PIPE, universal_newlines=True)

   def set_image(self, path):
      assert(os.path.isfile(path))
      self.path = path
      self.touch()

   def clear_image(self):
      self.path = ""
      self.touch()

   def _get_font_dimensions(self):
      # NOTE: stolen from ranger
      # Get the height and width of a character displayed in the terminal in
      # pixels.
      farg = struct.pack("HHHH", 0, 0, 0, 0)
      fd_stdout = sys.stdout.fileno()
      fretint = fcntl.ioctl(fd_stdout, termios.TIOCGWINSZ, farg)
      rows, cols, xpixels, ypixels = struct.unpack("HHHH", fretint)
      if xpixels == 0 and ypixels == 0:
         process = S.Popen([self.w3mpath, "-test"], stdout=S.PIPE, universal_newlines=True)
         output, _ = process.communicate()
         output = output.split()
         xpixels, ypixels = int(output[0]), int(output[1])
         # adjust for misplacement
         xpixels += 2
         ypixels += 2

      return (xpixels // cols), (ypixels // rows)

   def draw(self, win):
      # win.erase()
      # TODO: should probably run w3m clear if path is empty
      if self.path and not self.in_idle_queue:
         self.in_idle_queue = True
         self.manager.start_idle_job(self.post_draw)

   def post_draw(self, _man):
      self.in_idle_queue = False
      if not self.path:
         return False

      im = Image.open(self.path)
      self.img_w, self.img_h = im.size
      im.close()

      aspect = self.img_w / self.img_h
      windoww = self.w * self.cw
      windowh = self.h * self.ch
      dw = windoww - 3
      dh = int(dw / aspect)
      if dh > windowh:
         dh = windowh
         dw = int(dh * aspect)
      windowx = self.x * self.cw
      windowy = self.y * self.cw + 5

      # clear, draw, sync, sync draw
      inp = '6;{};{};{};{}\n0;1;{};{};{};{};;;;;{}\n4;\n3;\n'.format(
         windowx,
         windowy,
         windoww,
         windowh + 5,
         windowx,
         windowy,
         dw,
         dh,
         self.path
      )
      # sleep(0.02)
      self.w3m.stdin.write(inp)
      self.w3m.stdin.flush()
      self.w3m.stdout.readline()
      return False

class PopupLayout(Layout):
   def __init__(self, name, base, popup):
      super().__init__(name)
      self.widgets = [base, popup]

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(x, y, w, h, manager, self)
      self.widgets[1]._init(x, y, w, h, manager, self)
      self.hide_popup()

   def show_popup(self):
      self.widgets[1]._show()
      # self.widgets[1]._top()
      self.widgets[1].touch()
      self.change_focus(1)

   def hide_popup(self):
      self.widgets[1]._hide()
      self.change_focus(0)

   def is_popupped(self):
      return not self.widgets[1].is_hidden()

   def toggle(self):
      if not self.is_popupped():
         self.show_popup()
      else:
         self.hide_popup()

   #pylint: disable=protected-access,fixme
   def _resize(self, stdx, stdy, stdw, stdh):
      # FIXME: self.resize is called before the children are updated, might be a problem
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(stdx, stdy, stdw, stdh)
      self.widgets[1]._resize(stdx, stdy, stdw, stdh)

   #pylint: disable=protected-access
   def _focus_child(self, child):
      super()._focus_child(child)
      if self.focused == 1:
         self.show_popup()
      else:
         self.hide_popup()

class TabbedLayout(Layout):
   def __init__(self, name, *widgets):
      super().__init__(name)
      self.widgets = widgets

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      for wi in self.widgets:
         wi._init(x, y, w, h, manager, self)

      for wi in self.widgets[1:]:
         wi._hide()

   def _tab_to(self, index):
      self.widgets[self.focused]._hide()
      self.change_focus(index)
      self.widgets[self.focused]._show()
      self.widgets[self.focused].touch()

   def show_next(self):
      self._tab_to(self.focused + 1)

   def show_prev(self):
      self._tab_to(self.focused - 1)

   #pylint: disable=protected-access,fixme
   def _resize(self, stdx, stdy, stdw, stdh):
      # FIXME: self.resize is called before the children are updated, might be a problem
      super()._resize(stdx, stdy, stdw, stdh)
      for w in self.widgets:
         w._resize(stdx, stdy, stdw, stdh)

   #pylint: disable=protected-access
   def _focus_child(self, child):
      oldfocus = self.focused
      super()._focus_child(child)
      if self.focused != oldfocus:
         self.widgets[oldfocus]._hide()
         self.widgets[self.focused]._show()
         # self.widgets[self.focused].touch()

class WrapperLayout(Layout):
   def __init__(self, name, widget):
      super().__init__(name)
      self.widgets.append(widget)

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(x, y, w, h, manager, self)

   def _resize(self, stdx, stdy, stdw, stdh):
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(stdx, stdy, stdw, stdh)

class ConstraintLayout(Layout):
   def __init__(self, widget, maxw=None, maxh=None):
      super().__init__("constraint_{}".format(widget.name))
      self.widgets.append(widget)
      self.maxw = maxw
      self.maxh = maxh

   def _get_size(self):
      pw = min(self.w, self.maxw) if self.maxw else self.w
      ph = min(self.h, self.maxh) if self.maxh else self.h
      px = self.x + int((self.w - pw) / 2)
      py = self.y + int((self.h - ph) / 2)
      return (px, py, pw, ph)

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(*self._get_size(), manager, self)

   def _resize(self, stdx, stdy, stdw, stdh):
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(*self._get_size())

class BorderWrapperLayout(Layout):
   def __init__(self, edges, widget):
      super().__init__("border_{}".format(widget.name))
      self.widgets.append(widget)
      self.edges = edges

   def _show(self):
      self.panel.show()
      super()._show()

   def _hide(self):
      self.panel.hide()
      super()._hide()

   def _get_child_size(self):
      x = self.x
      y = self.y
      w = self.w
      h = self.h
      if 'l' in self.edges:
         x += 1
         w -= 1
      if 'r' in self.edges:
         w -= 1
      if 't' in self.edges:
         y += 1
         h -= 1
      if 'b' in self.edges:
         h -= 1
      return x, y, w, h

   #pylint: disable=protected-access
   def _init(self, x, y, w, h, manager, parent):
      self.is_layout = False
      super()._init(x, y, w, h, manager, parent)
      self.widgets[0]._init(*self._get_child_size(), manager, self)
      self.is_layout = True
      self.resized = True

   def _resize(self, stdx, stdy, stdw, stdh):
      super()._resize(stdx, stdy, stdw, stdh)
      self.widgets[0]._resize(*self._get_child_size())

   def _draw(self):
      if self.resized:
         win = self.panel.window()
         win.erase()
         if 't' in self.edges:
            ice(win.hline, 0, 0, curses.ACS_HLINE, self.w)
         if 'b' in self.edges:
            ice(win.hline, self.h - 1, 0, curses.ACS_HLINE, self.w)
         if 'l' in self.edges:
            ice(win.vline, 0, 0, curses.ACS_VLINE, self.h)
         if 'r' in self.edges:
            ice(win.vline, 0, self.w - 1, curses.ACS_VLINE, self.h)
         if 'l' in self.edges and 't' in self.edges or '1' in self.edges:
            ice(win.addch, 0, 0, curses.ACS_ULCORNER)
         if 'l' in self.edges and 'b' in self.edges or '3' in self.edges:
            ice(win.addch, self.h - 1, 0, curses.ACS_LLCORNER)
         if 'r' in self.edges and 't' in self.edges or '2' in self.edges:
            ice(win.addch, 0, self.w - 1, curses.ACS_URCORNER)
         if 'r' in self.edges and 'b' in self.edges or '4' in self.edges:
            ice(win.addch, self.h - 1, self.w - 1, curses.ACS_LRCORNER)
      super()._draw()

class InfoPopup(PopupLayout):
   INFO = 1
   WARNING = 2
   ERROR = 3

   class InfoWidget(Widget):
      def __init__(self, name):
         super().__init__(name)
         self.msg = ""
         self.yesno = False
         self.ok_yes_callback = lambda _: None
         self.no_callback = lambda _: None
         self.kind = InfoPopup.INFO

      def set_yesno(self, msg, yes_call, no_call):
         self.msg = msg
         self.ok_yes_callback = yes_call
         self.no_callback = no_call
         self.yesno = True
         self.touch()

      def set_ok(self, msg, ok_call, kind):
         self.msg = msg
         self.kind = kind
         self.yesno = False
         self.ok_yes_callback = ok_call
         self.no_callback = lambda _: None
         self.touch()

      def _get_kind_text(self):
         if self.kind == InfoPopup.INFO:
            return "${info_info}Info$0"
         elif self.kind == InfoPopup.WARNING:
            return "${info_warning}Warning$0"
         elif self.kind == InfoPopup.ERROR:
            return "${info_error}Error$0"

      def draw(self, win):
         win.erase()
         if not self.yesno:
            self.format_draw(win, 0, 0, self._get_kind_text())
            mid = (self.h-1) // 2
         else:
            mid = self.h // 2
         self.format_draw(win, 0, mid, self.msg, centered=True)

      def key_event(self, key):
         if self.yesno:
            if key == ord('y'):
               self.ok_yes_callback(self.manager)
            elif key == ord('n'):
               self.no_callback(self.manager)
         else:
            if key == ord('y') or key == ca.NL:
               self.ok_yes_callback(self.manager)
         return True

   def __init__(self, name, base, popmaxw, popmaxh):
      self.infoWidget = self.InfoWidget("{}_InfoWidget".format(name))
      super().__init__(
         name,
         base,
         ConstraintLayout(
            BorderWrapperLayout("rltb", self.infoWidget),
            maxw=popmaxw,
            maxh=popmaxh
         )
      )

   def _def_pop_callback(self, _man):
      self.hide_popup()

   def show_info(self, msg, kind=INFO, ok_call=None):
      self.infoWidget.set_ok(
         msg,
         ok_call if ok_call else lambda man: self._def_pop_callback(man),
         kind
      )
      self.show_popup()

   def show_question(self, msg, yes_call=None, no_call=None):
      self.infoWidget.set_yesno(
         msg,
         yes_call if yes_call else lambda man: self._def_pop_callback(man),
         no_call  if no_call  else lambda man: self._def_pop_callback(man)
      )
      self.show_popup()

# pylint: disable=protected-access
class Manager():
   def __init__(self, layout):
      self.running = True
      self.attr_names = {"0": 0}
      self.attr_override = []
      self.layout = layout
      self.widgets = {}
      self.global_hook = []
      self.current_focus = None
      self.global_vars = {}
      self.stdscr = None
      self.event_queue = deque()
      self.event_lock = Lock()
      self.bg_jobs = []
      self.curses_blocking = True
      self.idle_jobs = []

   def __getitem__(self, key):
      return self.global_vars[key]

   def __setitem__(self, key, value):
      self.global_vars[key] = value

   def __delitem__(self, key):
      del self.global_vars[key]

   def __enter__(self):
      os.environ.setdefault('ESCDELAY', '0')
      self.stdscr = curses.initscr()
      curses.noecho()
      curses.cbreak()
      self.stdscr.keypad(True)
      try:
         curses.start_color()
         curses.use_default_colors()
      except:
         pass
      return self

   def __exit__(self, _exc_type, _exc_value, _traceback):
      if self.stdscr:
         self.stdscr.keypad(0)
         curses.echo()
         curses.nocbreak()
         curses.endwin()
      return False

   def on_any_event(self, f):
      self.global_hook.append(f)

   def get_widget(self, name):
      if name not in self.widgets:
         raise Exception("can't find widget with name {}".format(name))
      return self.widgets[name]

   def init_color(self, index, fg, bg):
      curses.init_pair(index, fg, bg)

   def add_color(self, name, index):
      self.add_attr(name, curses.color_pair(index))

   def add_attr(self, name, attr):
      self.attr_names[name] = attr

   def get_attr(self, name):
      for o in reversed(self.attr_override):
         if name == o[0]:
            return o[1]
      return self.attr_names.get(name, 0)

   def push_attr_override(self, name, attr):
      self.attr_override.append((name, attr))

   def pop_attr_override(self):
      if not self.attr_override:
         raise Exception("override stack is empty")
      self.attr_override.pop()

   def map_focused(self, f, *args, top_down=True, **kwargs):
      self.current_focus.map_focused(f, *args, top_down=top_down, **kwargs)

   def get_focused(self):
      return self.current_focus

   def start_bg_job(self, f, *args):
      fixed_args = (self.event_lock, self.event_queue)
      t = Thread(daemon=True, target=f, args=(*fixed_args, *args))
      t.start()
      self.bg_jobs.append(t)

   def start_idle_job(self, f, *args):
      self.idle_jobs.append(f)

   def start(self):
      self._main_fun(self.stdscr)

   def stop(self):
      self.running = False

   def _main_fun(self, stdscr):
      curses.curs_set(False)
      stdscr.immedok(False)

      maxy, maxx = stdscr.getmaxyx()
      self.layout._init(0, 0, maxx, maxy, self, None)

      self.get_widget("MAIN").focus()

      while self.running:

         for f in self.global_hook:
            f(self)

         self.layout._draw()

         cp.update_panels()
         curses.doupdate()

         self._get_event(stdscr)

   def _get_event(self, stdscr):
      start = monotonic_ns()
      while True:
         self.bg_jobs = [j for j in self.bg_jobs if j.is_alive()]
         with self.event_lock:
            update = False
            while self.event_queue:
               update |= self.event_queue.popleft()(self)

            if update:
               break

         if self.idle_jobs and monotonic_ns() - start > 40*1000000:
            update = False
            while self.idle_jobs:
               update |= self.idle_jobs.pop()(self)

            if update:
               break

         if not self.bg_jobs and not self.idle_jobs:
            if not self.curses_blocking:
               stdscr.timeout(-1)
               self.curses_blocking = True
         else:
            if self.curses_blocking:
               stdscr.timeout(50)
               self.curses_blocking = False

         k = stdscr.getch()
         if k == -1:
            continue
         elif k == curses.KEY_RESIZE:
            maxy, maxx = stdscr.getmaxyx()
            self.layout._resize(0, 0, maxx, maxy)
            break
         else:
            if self.layout._key_event(k):
               break

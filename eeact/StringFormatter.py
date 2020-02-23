import _curses

# Ignore Curses Error
def ice(f, *args):
   try:
      f(*args)
   except _curses.error:
      pass

def _parse_string(string, manager):
   escon = False
   word = ""
   from itertools import zip_longest
   for c,h in zip_longest(string, string[1:], fillvalue=" "):
      if escon:
         if c == '{':
            pass
         elif c == '}':
            escon = False
            yield manager.get_attr(word)
         elif c == '0':
            yield 0
            escon = False
         else:
            word += c
      elif c == '$' and (h == '{' or h == '0'):
         escon = True
         word = ""
      else:
         yield c

def _parse(stringorlist, manager):
   if isinstance(stringorlist, str):
      stringorlist = [stringorlist]

   for l in stringorlist:
      yield True
      for c in _parse_string(l, manager):
         yield c

def parse_and_len(stringorlist, manager):
   parsed = list(_parse(stringorlist, manager))
   return sum(1 for x in parsed if isinstance(x, str)), parsed

def _draw_dots(win, x, y):
   for _ in range(3):
      if x < 0:
         break
      ice(win.addch, y, x, '.')
      x -= 1

def calc_centered_pos(string_len, win_len):
   return max(0, (win_len - string_len) // 2)

def draw(win, x, y, stringorlist, manager, centered=False, wrap=False, dots=False):
   _, w = win.getmaxyx()
   if centered:
      lenn, parsed = parse_and_len(stringorlist, manager)
      x = calc_centered_pos(lenn, w)
   else:
      parsed = _parse(stringorlist, manager)
   return draw_parsed(win, x, y, parsed, wrap=wrap, dots=dots)

def draw_parsed(win, x, y, parsed, wrap=False, dots=False):
   h, w = win.getmaxyx()
   attr = 0
   for c in parsed:
      if y >= h:
         break
      if x >= w:
         if dots:
            _draw_dots(win, x-1, y)
         break

      if isinstance(c, str):
         ice(win.addch, y, x, c)
         if attr != 0:
            ice(win.chgat, y, x, 1, attr)
         x += 1
      elif not isinstance(c, bool):
         attr = c

   return (x, y)

import curses.ascii as ca
from .popupLayout import PopupLayout
from ...widget.widget import Widget
from ..borderWrapperLayout import BorderWrapperLayout
from ..constraintLayout import ConstraintLayout

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

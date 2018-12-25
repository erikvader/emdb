import interface
import database

class TextWidget(interface.Widget):
   def __init__(self, name):
      super().__init__(name)
      self.value = "hejsan"

   def draw(self, win):
      if self.resized:
         win.erase()
      # if self.is_focused:
      #    win.attrset(interface.curses.color_pair(1))
      # win.border()

      # win.attrset(0)
      win.addstr(0, 0, self.value)

   def key_event(self, key):
      if interface.ca.isalnum(key) or key == ord(' '):
         self.value += chr(key)
         self.touch()
      else:
         return False
      return True

class GlobalBindings(interface.WrapperLayout):
   def key_event(self, key):
      if key == interface.ca.TAB:
         pop = self.manager.get_widget("popup")
         pop.toggle()
         if pop.is_popupped():
            self.manager.get_widget("img").clear_image()
      elif key == interface.ca.ESC:
         self.manager.stop()

class SelectorWidget(interface.FancyListWidget):
   def init(self):
      self.set_list(["hej{}".format(i)*5 + "a" for i in range(0, 100)])
      self.filter_by([i for i in range(0, len(self.get_indexlist())) if i % 2 == 0])

class ImgWidget(interface.ImageWidget):
   def init(self):
      self.set_image("/home/erik/Pictures/PFUDOR_2.jpg")

def main():
   l = GlobalBindings(
      "globals",
      interface.PopupLayout(
         "popup",
         interface.SplitLayout(
            "mainlayout",
            interface.SplitLayout.Alignment.HORIZONTAL,
            SelectorWidget("MAIN"), 0.3,
            interface.BorderWrapperLayout("rb", TextWidget("img"))
         ),
         TextWidget("popup_inner"),
         50,
         50
      )
   )
   man = interface.Manager(l)
   man.add_color(1, interface.curses.COLOR_RED, -1)
   man.start()

if __name__ == "__main__":
   main()

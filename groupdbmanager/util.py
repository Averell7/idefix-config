from gi.repository import Gtk


def askyesno(title, string):
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION,
                               Gtk.ButtonsType.NONE, title)
    dialog.add_button(Gtk.STOCK_YES, True)
    dialog.add_button(Gtk.STOCK_NO, False)
    dialog.format_secondary_text(string)
    dialog.set_keep_above(True)
    rep = dialog.run()
    dialog.destroy()
    return rep

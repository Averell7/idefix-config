import sys

from gi.repository import Gtk


def message_dialog(title, message):
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO, Gtk.ButtonsType.OK_CANCEL, title)
    dialog.format_secondary_text(message)
    dialog.set_keep_above(True)
    dialog.run()
    dialog.destroy()


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


def ask_text(parent, message, default=''):
    """
    Display a dialog with a text entry.
    Returns the text, or None if canceled.
    """
    d = Gtk.MessageDialog(parent,
                          Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                          Gtk.MessageType.QUESTION,
                          Gtk.ButtonsType.OK_CANCEL,
                          message)
    entry = Gtk.Entry()
    entry.set_text(default)
    entry.show()
    d.vbox.pack_end(entry, True, True, 0)
    entry.connect('activate', lambda _: d.response(Gtk.ResponseType.OK))
    d.set_default_response(Gtk.ResponseType.OK)

    r = d.run()
    text = entry.get_text()
    if sys.version_info[0] == 2:
        text = text.decode('utf8')
    d.destroy()
    if r == Gtk.ResponseType.OK:
        return text
    else:
        return None

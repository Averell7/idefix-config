from gi.repository import Gtk

from util import showwarning


class GroupManager:
    groups_store = None
    groups_changed = False
    buffer = None
    widgets = {}

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

    def show(self):
        widgets = Gtk.Builder()
        widgets.add_from_file('./groups_manager.glade')
        widgets.connect_signals(self)
        self.widgets = {}
        for z in widgets.get_objects():
            try:
                name = Gtk.Buildable.get_name(z)
                self.widgets[name] = z
                z.name = name
            except:
                pass
        self.widgets['groups_window'].show()
        self.groups_store = self.widgets['groups_store']
        self.action_edit_groups(None)
        self.groups_changed = False
        self.buffer = None

    def hide(self, *args):
        self.widgets['groups_window'].hide()

    def save_groups(self, *args):
        """Update the group"""
        self.controller.groups_store.clear()
        for row in self.groups_store:
            self.controller.groups_store.append((row[0], row[1]))
        self.hide()

    """ Signals """

    def selection_changed(self, widget):
        if self.groups_changed:
            showwarning(_("Save"), _("Don't forget to save"), 2)
            self.groups_changed = False

        model, iter = widget.get_selected()

        self.buffer = Gtk.TextBuffer()
        self.buffer.set_text(model.get_value(iter, 1))
        self.buffer.connect('changed', self.set_groups_dirty)
        self.widgets['groups_view'].set_buffer(self.buffer)

    def set_groups_dirty(self, widget):
        """Mark that the group entry was edited and update it"""
        self.groups_changed = True
        model, iter = self.widgets['groups_tree'].get_selection().get_selected()
        model.set_value(iter, 1, self.buffer.get_text(
            self.buffer.get_start_iter(),
            self.buffer.get_end_iter(),
            False
        ))

    def action_edit_groups(self, widget):
        """Show the groups in the tree view to allow the user to edit """
        self.groups_store.clear()
        for row in self.controller.groups_store:
            self.groups_store.append((row[0], row[1]))

    def action_import_groups(self, widget):
        pass

    def action_update_groups(self, widget):
        pass

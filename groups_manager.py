from gi.repository import Gtk

from myconfigparser import myConfigParser
from util import showwarning, askyesno


class GroupManager:
    groups_store = None
    groups_changed = False
    buffer = None
    widgets = {}
    imported_groups = False

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
        self.imported_groups = False

    def hide(self, *args):
        self.widgets['groups_window'].hide()

    def save(self, *args):
        self.save_groups()
        self.hide()

    def save_groups(self, *args):
        """Update the group"""
        self.controller.groups_store.clear()
        for row in self.groups_store:
            self.controller.groups_store.append((row[0], row[1]))

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
        if self.imported_groups or self.groups_changed:
            if askyesno(_("Save Changes"), _("Do you want to save your changes?")):
                self.save_groups()

        self.imported_groups = False
        self.groups_changed = False

        self.groups_store.clear()
        for row in self.controller.groups_store:
            self.groups_store.append((row[0], row[1]))

    def action_import_groups(self, widget):
        if self.groups_changed:
            if askyesno(_("Save Changes"), _("Do you want to save your changes?")):
                self.save_groups()

        self.groups_changed = False

        dialog = Gtk.FileChooserDialog(
            _("Import File"),
            self.widgets['groups_window'],
            Gtk.FileChooserAction.OPEN,
            (_("Import"), Gtk.ResponseType.ACCEPT),
        )
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern('*.ini')
        dialog.set_filter(file_filter)

        self.groups_store.clear()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:

            parser = myConfigParser()
            data1 = parser.read(dialog.get_filename(), "groups", comments=True)['groups']
            for key in data1:
                tooltip = "\n".join(data1[key].get('dest_domain', ''))
                if data1[key].get('dest_ip', ''):
                    if tooltip:
                        tooltip += '\n'
                    tooltip += "\n".join(data1[key].get('dest_ip', ''))
                self.groups_store.append([key, tooltip])

            self.imported_groups = True

        dialog.destroy()

    def action_export_groups(self, widget):
        pass

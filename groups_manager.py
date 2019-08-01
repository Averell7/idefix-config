import os
from collections import OrderedDict
from urllib.parse import urlparse, urljoin

from gi.repository import Gtk, Gdk

from myconfigparser import myConfigParser
from repository import fetch_repository_list, download_group_file
from util import showwarning, askyesno, ask_text, ip_address_test

IMPORT_COLUMN_SELECTED = 0
IMPORT_COLUMN_NAME = 1
IMPORT_COLUMN_PATH = 2
IMPORT_COLUMN_INCONSISTENT = 3


class GroupManager:
    groups_store = None
    groups_changed = False
    buffer = None
    widgets = {}
    imported_groups = False

    # If we encounter a group that already exists
    # if None - ask the user what to do
    # True - Merge
    # False - Replace
    merge_in_group = None

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

    def show(self):
        widgets = Gtk.Builder()
        widgets.set_translation_domain("confix")
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
        self.widgets['import_tree'].get_model().set_sort_column_id(IMPORT_COLUMN_NAME, Gtk.SortType.ASCENDING)
        self.widgets['groups_tree'].get_model().set_sort_column_id(0, Gtk.SortType.ASCENDING)

    def hide(self, *args):
        self.groups_changed = False
        self.imported_groups = False
        self.widgets['groups_window'].hide()

    def save(self, *args):
        if self.imported_groups:
            dialog = Gtk.Dialog()
            dialog.set_transient_for(self.widgets['groups_window'])
            dialog.add_button(_("Merge"), Gtk.ResponseType.APPLY)
            dialog.add_button(_("Replace"), Gtk.ResponseType.ACCEPT)
            dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
            label = Gtk.Label(_("Do you want to merge groups or replace existing?"))
            dialog.get_content_area().add(label)
            dialog.show_all()
            result = dialog.run()
            dialog.hide()
            if result == Gtk.ResponseType.APPLY:
                # Merge case
                if not self.merge():
                    return
            elif result == Gtk.ResponseType.ACCEPT:
                # Replace
                self.save_groups()
        else:
            self.save_groups()

        self.hide()

    def ask_merge(self, name):
        dialog = Gtk.Dialog()
        dialog.set_transient_for(self.widgets['groups_window'])
        dialog.add_button(_("Replace"), Gtk.ResponseType.APPLY)
        dialog.add_button(_("Replace all"), Gtk.ResponseType.ACCEPT)
        dialog.add_button(_("Merge"), Gtk.ResponseType.OK)
        dialog.add_button(_("Merge all"), Gtk.ResponseType.YES)
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.get_content_area().add(Gtk.Label(_("Duplicate group %s found") % name))
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result == Gtk.ResponseType.APPLY:
            return False
        elif result == Gtk.ResponseType.ACCEPT:
            self.merge_in_group = False
            return False
        elif result == Gtk.ResponseType.OK:
            return True
        elif result == Gtk.ResponseType.YES:
            self.merge_in_group = True
            return True
        else:
            return None

    @staticmethod
    def merge_group(new, original):
        """Merge contents of new and original"""
        values = set()
        values.update(new)
        values.update(original)
        return list(values)

    def merge(self):
        """Go through each item in our store vs the controller store and look for differences"""
        groups = {}

        original_groups = {}
        for row in self.controller.groups_store:
            original_groups[row[0]] = row[1].split('\n')

        new_groups = {}
        for row in self.groups_store:
            new_groups[row[0]] = row[1].split('\n')

        for key in new_groups:
            if key not in original_groups:
                groups[key] = new_groups[key]
            else:
                # What is our merge strategy?
                if self.merge_in_group is None:
                    # Ask the user what to do
                    merge = self.ask_merge(key)
                    if merge is None:
                        return
                else:
                    merge = self.merge_in_group

                if merge is True:
                    # Merge within the group
                    groups[key] = self.merge_group(new_groups[key], original_groups[key])
                elif merge is False:
                    # Replace
                    groups[key] = new_groups[key]

                original_groups.pop(key)

        # Now go through the original group
        for key in original_groups:
            groups[key] = original_groups[key]

        # And finally write
        self.controller.groups_store.clear()
        for key, value in groups.items():
            self.controller.groups_store.append((key, '\n'.join(value)))

        return True

    def read_config_data(self, data):
        """Read ini config data from an ini file into the group manager's groups store"""
        for key in data:
            tooltip = "\n".join(data[key].get('dest_domain', ''))
            if data[key].get('dest_ip', ''):
                if tooltip:
                    tooltip += '\n'
                tooltip += "\n".join(data[key].get('dest_ip', ''))
            self.groups_store.append([key, tooltip])

    def save_groups(self, *args):
        """Update the group"""
        self.controller.groups_store.clear()
        for row in self.groups_store:
            self.controller.groups_store.append((row[0], row[1]))

    def selection_changed(self, widget):
        if self.groups_changed:
            showwarning(_("Save"), _("Don't forget to save"), 2)
            self.groups_changed = False

        self.buffer = Gtk.TextBuffer()
        self.widgets['groups_view'].set_buffer(self.buffer)
        model, iter = widget.get_selected()
        if not iter:
            return

        self.buffer.set_text(model.get_value(iter, 1))
        self.buffer.connect('changed', self.set_groups_dirty)

    def set_groups_dirty(self, widget):
        """Mark that the group entry was edited and update it"""
        self.groups_changed = True
        model, iter = self.widgets['groups_tree'].get_selection().get_selected()

        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()  # Get actual model

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

        self.widgets['add_group_menu'].show()

        self.groups_store.clear()
        self.buffer = Gtk.TextBuffer()
        self.widgets['groups_view'].set_buffer(self.buffer)
        for row in self.controller.groups_store:
            self.groups_store.append((row[0], row[1]))

    def action_import_groups(self, widget):
        """Imports groups from an ini file, first adds them into the tree view for later merging/replacing"""
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

        self.buffer = Gtk.TextBuffer()
        self.widgets['groups_view'].set_buffer(self.buffer)
        self.groups_store.clear()
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:

            parser = myConfigParser()
            data1 = parser.read(dialog.get_filename(), "groups", comments=True)['groups']
            self.read_config_data(data1)
            self.imported_groups = True

        dialog.destroy()

    def action_export_groups(self, widget):
        """Export the groups in the main group store into an ini file"""

        dialog = Gtk.FileChooserDialog(
            _("Export File"),
            self.widgets['groups_window'],
            Gtk.FileChooserAction.SAVE,
            (_("Export"), Gtk.ResponseType.ACCEPT),
        )
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern('*.ini')
        dialog.set_filter(file_filter)

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:

            data = ''

            for row in self.controller.groups_store:
                data += '\n[%s]\n' % row[0]
                for domain in row[1].split('\n'):
                    if ip_address_test(domain):
                        data += 'dest_ip = %s\n' % domain
                    else:
                        data += 'dest_domain = %s\n' % domain

            with open(dialog.get_filename(), 'w', encoding="utf-8-sig", newline="\n") as f:
                f.write(data)

        dialog.destroy()

    def action_import_repository(self, widget):
        if self.imported_groups or self.groups_changed:
            if askyesno(_("Save Changes"), _("Do you want to save your changes?")):
                self.save_groups()

        self.imported_groups = False
        self.groups_changed = False

        self.widgets['add_group_menu'].hide()

        # Get repository file from server
        data = fetch_repository_list()
        if not data:
            showwarning(_("Repository"), _("Could not get files from server"))
            return

        self.widgets['repository_store'].clear()

        path_iters = {
            '/': None
        }

        for path, files in data:
            directory = urlparse(path).path
            if directory.endswith('/'):
                directory = directory[:-1]

            parent_path, name = os.path.split(directory)
            if not name:
                name = 'all'

            if parent_path not in path_iters:
                path_iters[parent_path] = self.widgets['repository_store'].append(None)
                self.widgets['repository_store'].set_value(
                    path_iters[parent_path],
                    IMPORT_COLUMN_NAME, os.path.split(parent_path)[1])
                self.widgets['repository_store'].set_value(
                    path_iters[parent_path],
                    IMPORT_COLUMN_PATH, "")

            parent = self.widgets['repository_store'].append(path_iters[parent_path])
            path_iters[directory] = parent

            self.widgets['repository_store'].set_value(parent, IMPORT_COLUMN_NAME, name)
            self.widgets['repository_store'].set_value(parent, IMPORT_COLUMN_PATH, "")
            for file in files:
                if file.endswith('.json'):
                    # Only import ini files for now
                    continue

                iter = self.widgets['repository_store'].append(parent)

                full_path = urljoin(path, file)
                name, ext = os.path.splitext(file)

                self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_NAME, name)
                self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_PATH, full_path)

        self.widgets['import_window'].show_all()

    def action_cancel_repository(self, widget):
        self.widgets['import_window'].hide()

    def walk_repository_tree(self, iterchildren):
        """Return the paths of any bottom most children which have been selected"""
        results = []
        for child in iterchildren:
            if not child[IMPORT_COLUMN_SELECTED] and not child[IMPORT_COLUMN_INCONSISTENT]:
                continue
            children = child.iterchildren()
            if children.iter:
                # Continue walking
                results.extend(self.walk_repository_tree(children))
            else:
                # We are at the base
                results.append((child[IMPORT_COLUMN_PATH], child[IMPORT_COLUMN_NAME]))
        return results

    def action_start_repository_import(self, widget):
        """Process the user selection and import the proxy groups"""
        download_files = []

        for row in self.widgets['repository_store']:
            if not row[IMPORT_COLUMN_SELECTED] and not row[IMPORT_COLUMN_INCONSISTENT]:
                continue

            # Get to the bottom level
            children = row.iterchildren()
            download_files = self.walk_repository_tree(children)

        parser = myConfigParser()
        groups = OrderedDict()
        for file, name in download_files:
            #file = file.replace("http://", "https://")
            ini_data = ('[%s]\n' % name) + download_group_file(file).decode("utf-8-sig")
            data = parser.read(ini_data.split('\n'), "groups", isdata=True, comments=True)
            groups.update(data['groups'])

        self.buffer = Gtk.TextBuffer()
        self.widgets['groups_view'].set_buffer(self.buffer)
        self.groups_store.clear()
        self.read_config_data(groups)
        self.imported_groups = True
        self.widgets['import_window'].hide()

    def show_context(self, widget, event):
        if event.type != Gdk.EventType.BUTTON_RELEASE or event.button != 3:
            return
        self.widgets["context_menu"].popup(None, None, None, None, event.button, event.time)

    def add_item(self, widget):
        """Add a new group"""
        value = ask_text(self.widgets['groups_window'], _("Add Group"), "")
        if not value:
            return
        iter = self.widgets['groups_store'].append()
        self.widgets['groups_store'].set_value(iter, 0, value)
        self.widgets['groups_store'].set_value(iter, 1, '')

        # Select the new group
        sort_model = self.widgets['groups_tree'].get_model()
        model, sort_iter = sort_model.convert_child_iter_to_iter(iter)
        self.widgets['groups_tree'].set_cursor(sort_model.get_path(sort_iter))

        # Set focus to the text area
        self.widgets['groups_view'].grab_focus()

    def rename_item(self, widget):
        """Rename an entry"""
        model, iter = self.widgets['groups_tree'].get_selection().get_selected()
        name = model.get_value(iter, 0)
        value = ask_text(self.widgets['groups_window'], _("Rename Group"), name)

        iter = model.convert_iter_to_child_iter(iter)
        model.get_model().set_value(iter, 0, value)
        self.groups_changed = True

    def delete_item(self, widget):
        """Delete an entry"""
        model, iter = self.widgets['groups_tree'].get_selection().get_selected()
        name = model.get_value(iter, 0)
        if askyesno(_("Delete Group"), _("Do you want to delete %s?" % name)):
            iter = model.convert_iter_to_child_iter(iter)
            model.get_model().remove(iter)
            self.groups_changed = True

    def propagate_status(self, iter, value):
        """Update the value all the way down the children tree"""
        self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_SELECTED, value)
        self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_INCONSISTENT, False)

        child = self.widgets['repository_store'].iter_children(iter)
        while child is not None:
            self.propagate_status(child, value)
            child = self.widgets['repository_store'].iter_next(child)

    def check_children_status_same(self, iter, value):
        """Return if all the children values (all the way down) are the same"""
        child = self.widgets['repository_store'].iter_children(iter)
        while child is not None:
            if self.widgets['repository_store'].get_value(child, IMPORT_COLUMN_INCONSISTENT):
                return False
            if self.widgets['repository_store'].get_value(child, IMPORT_COLUMN_SELECTED) != value:
                return False
            if not self.check_children_status_same(child, value):
                return False
            child = self.widgets['repository_store'].iter_next(child)
        return True

    def update_import_selection(self, widget: Gtk.CellRendererToggle, path):
        """Update the checkbox across the whole tree view"""

        # Transform from sort path to actual path
        iter = self.widgets['import_tree'].get_model().get_iter(path)
        iter = self.widgets['import_tree'].get_model().convert_iter_to_child_iter(iter)

        value = not widget.get_active()
        self.propagate_status(iter, value)  # Get children and set appropriately

        # Get parents and set appropriately
        parent = self.widgets['repository_store'].iter_parent(iter)

        inconsistent = False
        while parent:
            if inconsistent:
                self.widgets['repository_store'].set_value(parent, IMPORT_COLUMN_INCONSISTENT, True)
                parent = self.widgets['repository_store'].iter_parent(parent)
                continue

            child = self.widgets['repository_store'].iter_children(parent)
            same = True
            while child:
                # Some children have differing options
                if self.widgets['repository_store'].get_value(child, IMPORT_COLUMN_INCONSISTENT):
                    same = False
                    break

                # Children have different values
                if self.widgets['repository_store'].get_value(child, IMPORT_COLUMN_SELECTED) != value:
                    same = False
                    break

                child = self.widgets['repository_store'].iter_next(child)

            # All children have the same value
            if same:
                self.widgets['repository_store'].set_value(parent, IMPORT_COLUMN_SELECTED, value)
                self.widgets['repository_store'].set_value(parent, IMPORT_COLUMN_INCONSISTENT, False)
            else:
                parent_value = self.widgets['repository_store'].get_value(parent, IMPORT_COLUMN_SELECTED)
                # Check if any child != parent_value
                inconsistent = not self.check_children_status_same(parent, parent_value)
                self.widgets['repository_store'].set_value(parent, IMPORT_COLUMN_INCONSISTENT, inconsistent)

            parent = self.widgets['repository_store'].iter_parent(parent)

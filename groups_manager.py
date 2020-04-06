import json
import os
from collections import defaultdict, OrderedDict

from gi.repository import Gtk, Gdk

from repository import fetch_repository_categories, search_repository_groups, upload_group
from util import showwarning, askyesno, ask_text, name_sorter

IMPORT_COLUMN_SELECTED = 0
IMPORT_COLUMN_NAME = 1
IMPORT_COLUMN_ID = 2
IMPORT_COLUMN_INCONSISTENT = 3
IMPORT_COLUMN_DOMAINS = 4
IMPORT_COLUMN_PARENT_ID = 5
IMPORT_COLUMN_TYPE = 6
IMPORT_COLUMN_CATEGORY = 7
IMPORT_COLUMN_GROUP = 8
CATEGORY_TYPE = 0
GROUP_TYPE = 1

"""
The groups manager uses a Json format to export and import groups. The format is:
{
   "groups": [{
      "group": "GROUPNAME",             # Name of the group being imported
      "group_id": "GROUPID",            # This is optional and may be None
      "dest": ["domain", "domain2"],    # List of destination domains/ips
   }]
}

There is also a simple way to import groups using a text file. If the user selects a .txt file then
it will import with the group name equal to that of the file (ie: My Group.txt --> My Group). Each line
of the text file will be a domain.

"""


class GroupManager:
    groups_store = None
    groups_changed = False
    buffer = None
    widgets = {}
    imported_groups = False

    _cached_categories = {}
    _cached_groups = {}
    _cached_groups_by_category_id = {}

    group_results = []
    categories_in_results = []

    # If we encounter a group that already exists
    # if None - ask the user what to do
    # True - Merge
    # False - Replace
    merge_in_group = None

    subcategories = defaultdict(list)

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
        self.widgets['groups_tree'].get_model().set_default_sort_func(name_sorter)
        self.widgets['import_tree'].get_model().get_model().set_sort_column_id(
            IMPORT_COLUMN_NAME, Gtk.SortType.ASCENDING
        )
        self.widgets['import_tree'].get_model().set_visible_func(self.filter_groups)
        self.subcategories = defaultdict(list)

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
        """Read json data from file into the group manager's groups store"""

        for item in data.get('groups', []):
            key = item.get('group')
            domains = item.get('dest', [])
            tooltip = "\n".join(domains)
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
        """Imports groups from a json file, first adds them into the tree view for later merging/replacing"""
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
        file_filter.add_pattern('*.json')
        file_filter.add_pattern('*.txt')
        dialog.set_filter(file_filter)

        self.buffer = Gtk.TextBuffer()
        self.widgets['groups_view'].set_buffer(self.buffer)
        self.groups_store.clear()
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            with open(dialog.get_filename(), 'r', encoding='utf-8-sig', newline='\n') as f:
                if dialog.get_filename().lower().endswith('txt'):
                    # Load the simple group format
                    path, ext = os.path.splitext(dialog.get_filename())
                    data = {
                        'groups': [{
                            'group': os.path.basename(path).title(),
                            'group_id': '',
                            'dest': [line.strip() for line in f.read().split('\n')]
                        }]
                    }
                else:
                    data = json.load(f, object_pairs_hook=OrderedDict)

            self.read_config_data(data)
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
        file_filter.add_pattern('*.json')
        dialog.set_filter(file_filter)

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:

            data = {
                'groups': []
            }
            groups = data['groups']

            for row in self.controller.groups_store:
                groups.append({
                    'group': row[0],
                    'group_id': None,
                    'dest': row[1].split('\n')
                })

            with open(dialog.get_filename(), 'w', encoding='utf-8-sig', newline='\n') as f:
                json.dump(data, f, indent=3)

        dialog.destroy()

    def action_export_repository(self, widget):
        """Create a new unverified group"""
        smodel, siter = self.widgets['groups_tree'].get_selection().get_selected()
        if not siter:
            return

        if self.imported_groups or self.groups_changed:
            if askyesno(_("Save Changes"), _("Do you want to save your changes?")):
                self.save_groups()

        iter = smodel.convert_iter_to_child_iter(siter)
        model = smodel.get_model()

        if askyesno(_("Export Group"), _("Are you sure you want to send this group to the repository?")):
            if upload_group(model.get_value(iter, 0), model.get_value(iter, 1).split('\n')):
                showwarning(_("Exported"), _("Thank you for sending us the group details"))
            else:
                showwarning(_("Error"), _("Please try again"), 4)

    def action_import_repository(self, widget):
        if self.imported_groups or self.groups_changed:
            if askyesno(_("Save Changes"), _("Do you want to save your changes?")):
                self.save_groups()

        self.imported_groups = False
        self.groups_changed = False

        self.widgets['add_group_menu'].hide()

        # Get the categories from the server
        data = fetch_repository_categories()
        if not data:
            showwarning(_("Repository"), _("Could not get files from server"))
            return

        self._cached_categories = {}
        self._cached_groups = {}
        self._cached_groups_by_category_id = {}

        self.group_results = []
        self.categories_in_results = []

        self.widgets['repository_store'].clear()

        category_iters = {
            None: None
        }

        # Always make sure parent id is at the top
        data.sort(key=lambda x: x['parent_id'] is None, reverse=True)

        for category in data:
            self._cached_categories[int(category['id'])] = category
            category_id = int(category['id'])

            if category.get('parent_id'):
                parent_id = int(category['parent_id'])
            else:
                parent_id = None

            category_iters[category_id] = iter = self.widgets['repository_store'].append(category_iters.get(parent_id))
            self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_NAME, category['name'])
            self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_ID, category_id)
            self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_PARENT_ID, parent_id)
            self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_TYPE, CATEGORY_TYPE)
            self.widgets['repository_store'].set_value(iter, IMPORT_COLUMN_CATEGORY, True)
            self._cached_categories[int(category['id'])]['path'] = self.widgets['repository_store'].get_path(iter)

        for group in search_repository_groups():
            self.add_group_to_store(group)

        self.widgets['import_window'].show_all()

    def add_group_to_store(self, group):
        if group.get('category_id') not in self._cached_groups_by_category_id:
            self._cached_groups_by_category_id[group.get('category_id')] = []

        if group not in self._cached_groups_by_category_id[group.get('category_id')]:
            self._cached_groups_by_category_id[group.get('category_id')].append(group)

        self._cached_groups[group['id']] = group

        # Get the iter that the group must be stored to
        try:
            iter = self.widgets['repository_store'].get_iter(self._cached_categories[int(group['category_id'])]['path'])
        except KeyError:
            iter = None

        group_iter = self.widgets['repository_store'].append(iter)
        self.widgets['repository_store'].set_value(group_iter, IMPORT_COLUMN_NAME, group['name'])
        self.widgets['repository_store'].set_value(group_iter, IMPORT_COLUMN_ID, int(group['id']))
        self.widgets['repository_store'].set_value(group_iter, IMPORT_COLUMN_PARENT_ID, group.get('category_id'))
        self.widgets['repository_store'].set_value(group_iter, IMPORT_COLUMN_TYPE, GROUP_TYPE)
        self.widgets['repository_store'].set_value(group_iter, IMPORT_COLUMN_GROUP, True)
        domains = ''
        for domain in group.get('domains', []):
            domains += 'dest_domains = %s\n' % domain
        self.widgets['repository_store'].set_value(group_iter, IMPORT_COLUMN_DOMAINS, domains)

    def import_selection_changed(self, widget):
        """Check if we must load items"""
        if self.widgets['import_search_entry'].get_text():
            return

        filter_model, filter_iter = widget.get_selected()

        sort_iter = filter_model.convert_iter_to_child_iter(filter_iter)
        sort_model = filter_model.get_model()
        iter = sort_model.convert_iter_to_child_iter(sort_iter)
        model = sort_model.get_model()

        if model.get_value(iter, IMPORT_COLUMN_TYPE) == GROUP_TYPE:
            buf = Gtk.TextBuffer()
            self.widgets['import_group_domains_view'].set_buffer(buf)
            data = model.get_value(iter, IMPORT_COLUMN_DOMAINS).split('\n')
            domains = ''
            for row in data:
                if not row:
                    continue
                domains += row.split(' = ', 1)[1] + '\n'
            buf.set_text(domains)
        else:
            buf = Gtk.TextBuffer()
            self.widgets['import_group_domains_view'].set_buffer(buf)

        if model.get_value(iter, IMPORT_COLUMN_TYPE) != CATEGORY_TYPE:
            return

        category_id = model.get_value(iter, IMPORT_COLUMN_ID)

        # Have we loaded any items?
        if category_id in self._cached_groups_by_category_id:
            return

        # Get items from the api
        groups = search_repository_groups(category_id)
        for group in groups:
            self.add_group_to_store(group)

        if category_id not in self._cached_groups_by_category_id:
            self._cached_groups_by_category_id[category_id] = []
            return

    def action_cancel_repository(self, widget):
        self.widgets['import_window'].hide()

    def toggle_search(self, enabled=True):
        self.widgets['import_search_entry'].set_sensitive(enabled)
        self.widgets['import_search_button'].set_sensitive(enabled and self.widgets['import_search_entry'].get_text())

        self.search_groups()

    def filter_groups(self, model, iter, data):
        if not self.widgets['import_search_entry'].get_text():
            return True

        if model.get_value(iter, IMPORT_COLUMN_TYPE) == GROUP_TYPE:
            # Check if our id is in the results
            group_id = model.get_value(iter, IMPORT_COLUMN_ID)
            return group_id in self.group_results
        else:
            # Category
            category_id = model.get_value(iter, IMPORT_COLUMN_ID)

            if category_id in self.categories_in_results:
                return True

    def search_groups(self, *args):
        """Query the database for results"""
        if self.widgets['import_search_entry'].get_text():
            query = self.widgets['import_search_entry'].get_text()
        else:
            query = None

        self.categories_in_results = set()
        self.group_results = []

        if not query:
            self.widgets['import_tree'].get_model().refilter()
            return

        for result in search_repository_groups(None, query):
            if not result.get('name'):
                continue

            if result['id'] not in self._cached_groups:
                self.add_group_to_store(result)

            category_id = int(result.get('category_id'))
            while category_id:
                self.categories_in_results.add(category_id)
                try:
                    category_id = int(self._cached_categories.get(category_id, {}).get('parent_id'))
                except TypeError:
                    category_id = None

            self.group_results.append(int(result['id']))

        self.widgets['import_tree'].get_model().refilter()

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
                results.append((child[IMPORT_COLUMN_ID], child[IMPORT_COLUMN_NAME], child[IMPORT_COLUMN_DOMAINS]))
        return results

    def action_start_repository_import(self, widget):
        """Process the user selection and import the proxy groups"""

        data = {
            'groups': []
        }
        groups = data['groups']
        for row in self.widgets['repository_store']:
            for group_id, group_name, domains in self.walk_repository_tree(row.iterchildren()):
                groups.append({
                    "group": group_name,
                    "group_id": group_id,
                    "dest": domains.split('\n'),
                })

        self.buffer = Gtk.TextBuffer()
        self.widgets['groups_view'].set_buffer(self.buffer)
        self.groups_store.clear()
        self.read_config_data(data)
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

    def update_import_selection(self, widget, path):
        """Update the checkbox across the whole tree view"""

        # Transform from sort path to actual path
        filter_iter = self.widgets['import_tree'].get_model().get_iter(path)
        sort_iter = self.widgets['import_tree'].get_model().convert_iter_to_child_iter(filter_iter)
        sort_model = self.widgets['import_tree'].get_model().get_model()

        iter = sort_model.convert_iter_to_child_iter(sort_iter)

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

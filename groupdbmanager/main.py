import argparse
import configparser

from gi.repository import Gtk, Gdk

from db import Database
from util import askyesno, ask_text, message_dialog

COLUMN_NAME = 0
COLUMN_DATA = 1
COLUMN_ID = 2
COLUMN_TYPE = 3
COLUMN_VERIFIED = 4
TYPE_CATEGORY = 0
TYPE_GROUP = 1

COLUMN_DIFF_DOMAIN = 0
COLUMN_DIFF_MERGE = 1
COLUMN_DIFF_COLOUR = 2
COLUMN_DIFF_ACTION = 3

ADD_ACTION = 0
DELETE_ACTION = 1


def diff_sort(model, iter_a, iter_b, _data=None):
    domain_a = model.get_value(iter_a, COLUMN_DIFF_DOMAIN)
    if domain_a:
        domain_a = domain_a.replace('*.', '')
    else:
        domain_a = ''

    domain_b = model.get_value(iter_b, COLUMN_DIFF_DOMAIN)
    if domain_b:
        domain_b = domain_b.replace('*.', '')
    else:
        domain_b = ''

    if domain_a > domain_b:
        return 1
    elif domain_a < domain_b:
        return -1
    else:
        return 0


class DatabaseManager:

    category_iters = {}
    group_iters = {}

    new_item = False
    verified_dirty = False
    unverified_dirty = False

    def __init__(self, config_file='config.ini'):
        widgets = Gtk.Builder()
        widgets.set_translation_domain("confix")
        widgets.add_from_file('./main.glade')
        widgets.connect_signals(self)
        self.widgets = {}
        for z in widgets.get_objects():
            try:
                name = Gtk.Buildable.get_name(z)
                self.widgets[name] = z
                z.name = name
            except:
                pass
        self.widgets['main_window'].show()

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(config_file)

        self.store = self.widgets['group_store']
        self.widgets['verified_treeview'].get_model().set_visible_func(self.filter_verified)
        self.widgets['unverified_treeview'].get_model().set_visible_func(self.filter_unverified)
        self.widgets['unverified_buffer'] = self.widgets['unverified_textview'].get_buffer()
        self.widgets['verified_buffer'] = self.widgets['verified_textview'].get_buffer()

        self.database = Database(
            self.config['database']['host'],
            self.config.getint('database', 'port', fallback=3306),
            self.config['database']['username'],
            self.config['database']['password'],
            self.config['database']['database'],
        )

        self.widgets['verified_treeview'].enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.COPY
        )
        self.widgets['verified_treeview'].drag_dest_set(Gtk.DestDefaults.DROP, [], Gdk.DragAction.COPY)
        self.widgets['verified_treeview'].drag_source_add_text_targets()
        self.widgets['verified_treeview'].drag_dest_add_text_targets()
        self.widgets['verified_treeview'].connect("drag-data-get", self.drag_data_get)
        self.widgets['verified_treeview'].connect("drag-data-received", self.drag_data_received)

        self.widgets['unverified_treeview'].enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.MOVE
        )
        self.widgets['unverified_treeview'].drag_source_add_text_targets()
        self.widgets['unverified_treeview'].connect("drag-data-get", self.drag_data_get)

        self.widgets['diff_view'].get_model().set_default_sort_func(diff_sort)

    def drag_data_get(self, widget, drag_context, data, info, time):
        (model, iter) = widget.get_selection().get_selected()
        if iter:
            path = model.get_string_from_iter(iter)
            data.set_text(widget.get_name() + ',' + path, -1)

    def drag_data_received(self, widget, drag_context, x, y, data, info, etime):
        """Drag and drop items in the treeviews, allows for:
         - Moving groups from unverified list to verified list
         - Moving groups from one category to another
         - Moving categories from one category to another
        """

        src_widget_name, path = data.get_text().split(',')

        dest_path, position = self.widgets['verified_treeview'].get_dest_row_at_pos(x, y)
        dest_iter = self.widgets['verified_treeview'].get_model().get_iter(dest_path)

        if src_widget_name == 'unverified_treeview':
            # Unverified --> Verified
            model = self.widgets[src_widget_name].get_model()
            source_iter = model.get_iter(path)
            if not source_iter:
                return True
            # Make the item verified
            if model.get_value(source_iter, COLUMN_TYPE) == TYPE_GROUP:
                group_id = model.get_value(source_iter, COLUMN_ID)

                dest_model = self.widgets['verified_treeview'].get_model()

                if not dest_iter:
                    category_id = None
                elif dest_model.get_value(dest_iter, COLUMN_TYPE) == TYPE_CATEGORY:
                    category_id = dest_model.get_value(dest_iter, COLUMN_ID)
                elif dest_model.get_value(dest_iter, COLUMN_TYPE) == TYPE_GROUP:
                    parent_iter = dest_model.iter_parent(dest_iter)
                    category_id = dest_model.get_value(parent_iter, COLUMN_ID)
                else:
                    category_id = None

                self.database.update_group(group_id, category_id=category_id, verified=True)
                self.refresh_database()
        elif src_widget_name == 'verified_treeview':
            # Update verified
            model = self.widgets[src_widget_name].get_model()
            source_iter = model.get_iter(path)
            if not source_iter:
                return True

            if model.get_value(source_iter, COLUMN_TYPE) == TYPE_GROUP:
                if not dest_iter:
                    return True

                group_id = model.get_value(source_iter, COLUMN_ID)

                if model.get_value(dest_iter, COLUMN_TYPE) == TYPE_CATEGORY:
                    category_id = model.get_value(dest_iter, COLUMN_ID)
                else:
                    parent_iter = model.iter_parent(dest_iter)
                    category_id = model.get_value(parent_iter, COLUMN_ID)
                self.database.update_group(group_id, category_id=category_id)
                self.refresh_database()
            else:
                if not model.iter_parent(dest_iter) and position in (
                        Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.AFTER
                ):
                    category_id = ''
                elif not dest_iter:
                    category_id = ''
                elif model.get_value(dest_iter, COLUMN_TYPE) == TYPE_CATEGORY:
                    category_id = model.get_value(dest_iter, COLUMN_ID)
                else:
                    parent_iter = model.iter_parent(dest_iter)
                    category_id = model.get_value(parent_iter, COLUMN_ID)
                self.database.update_category(model.get_value(source_iter, COLUMN_ID), parent_id=category_id)
                self.refresh_database()

        return True

    def ask_verified_save_changes(self):
        """Asks the user if they want to save their changes"""
        if self.verified_dirty:
            return askyesno("Save Changes?", "Do you want to save your changes first?")

    def add_new_group(self, widget):
        """Create a new group entry"""
        if self.ask_verified_save_changes():
            # Do save?
            self.updated_verified(widget)

        name = ask_text(self.widgets['main_window'], "Enter the group name")
        if name:
            self.verified_dirty = True
            self.new_item = True
            self.widgets['verified_entry_name'].set_text(name)
            self.widgets['verified_entry_checkbox'].set_active(True)
            self.widgets['verified_buffer'].set_text("")
            self.widgets['verified_textview'].grab_focus()

    def add_new_category(self, widget):
        """Create a new category entry"""
        name = ask_text(self.widgets['main_window'], "Please enter the category name")
        if not name:
            return

        parent_id = None

        model, iter = self.widgets['verified_treeview'].get_selection().get_selected()
        if iter:
            iter = model.convert_iter_to_child_iter(iter)
            model = model.get_model()

            if model.get_value(iter, COLUMN_TYPE) == TYPE_CATEGORY:
                parent_id = model.get_value(iter, COLUMN_ID)

        ok, err = self.database.create_category(name, parent_id)
        if not ok:
            message_dialog("Error", err)
        self.refresh_database()

    def filter_verified(self, model, iter, data=None):
        """Return true if the iter is verified."""
        if model.get_value(iter, COLUMN_TYPE) == TYPE_GROUP:
            return model.get_value(iter, COLUMN_VERIFIED)
        else:
            child = model.iter_children(iter)
            while child:
                if not self.filter_verified(model, child):
                    return False
                child = model.iter_next(child)
            return True

    def filter_unverified(self, model, iter, data=None):
        """Return true if the iter is verified. Also hides categories that don't have any groups"""
        if model.get_value(iter, COLUMN_TYPE) == TYPE_GROUP:
            return not model.get_value(iter, COLUMN_VERIFIED)
        else:
            child = model.iter_children(iter)
            while child:
                if self.filter_unverified(model, child):
                    return True
                child = model.iter_next(child)
            return False

    def verified_selected(self, widget):
        model, iter = widget.get_selected()
        if not iter:
            return
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        if model.get_value(iter, COLUMN_TYPE) == TYPE_GROUP:
            self.widgets['verified_entry_name'].set_text(model.get_value(iter, COLUMN_NAME))
            self.widgets['verified_entry_checkbox'].set_active(model.get_value(iter, COLUMN_VERIFIED))

            self.widgets['verified_buffer'].set_text(model.get_value(iter, COLUMN_DATA))
        else:
            self.widgets['verified_entry_name'].set_text('')
            self.widgets['verified_entry_checkbox'].set_active(False)
            self.widgets['verified_textview'].get_buffer().set_text('')

        self.new_item = False
        self.diff_group_domains()

    def unverified_selected(self, widget):
        model, iter = widget.get_selected()
        if not iter:
            return
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        if model.get_value(iter, COLUMN_TYPE) == TYPE_GROUP:
            self.widgets['unverified_entry_name'].set_text(model.get_value(iter, COLUMN_NAME))
            self.widgets['unverified_entry_checkbox'].set_active(model.get_value(iter, COLUMN_VERIFIED))
            self.widgets['unverified_buffer'].set_text(model.get_value(iter, COLUMN_DATA))

            # Try to find the corresponding verified group (if one exists)
            name = model.get_value(iter, COLUMN_NAME)
            selected_id = model.get_value(iter, COLUMN_ID)
            for item_iter, item in self.group_iters.items():
                if item['name'] == name and item['id'] != selected_id:
                    # Select this item
                    filtered_model = self.widgets['verified_treeview'].get_model()
                    found, select_iter = filtered_model.convert_child_iter_to_iter(item_iter)
                    if found:
                        path = filtered_model.get_path(select_iter)
                        self.widgets['verified_treeview'].expand_to_path(path)
                        self.widgets['verified_treeview'].set_cursor(path)

        else:
            self.widgets['unverified_entry_name'].set_text('')
            self.widgets['unverified_entry_checkbox'].set_active(False)
            self.widgets['unverified_textview'].get_buffer().set_text('')

        self.diff_group_domains()

    def diff_group_domains(self):
        """Highlight differences in domains between unverified and verified"""

        self.widgets['diff_store'].clear()

        buf = self.widgets['unverified_buffer']
        unverified_data = buf.get_text(
            buf.get_start_iter(), buf.get_end_iter(), True
        ).lower()
        unverified_list = unverified_data.split('\n')

        buf = self.widgets['verified_buffer']
        verified_data = buf.get_text(
            buf.get_start_iter(), buf.get_end_iter(), True
        ).lower()
        verified_list = verified_data.split('\n')

        for line in unverified_list:
            if not len(line) or not line:
                continue

            if line in verified_list:
                start_pos = unverified_data.find(line)
                end_pos = start_pos + len(line)
                start_iter = self.widgets['unverified_buffer'].get_iter_at_offset(start_pos)
                end_iter = self.widgets['unverified_buffer'].get_iter_at_offset(end_pos)
                self.widgets['unverified_buffer'].apply_tag_by_name('existingdomain', start_iter, end_iter)
            else:
                start_pos = unverified_data.find(line)
                end_pos = start_pos + len(line)
                start_iter = self.widgets['unverified_buffer'].get_iter_at_offset(start_pos)
                end_iter = self.widgets['unverified_buffer'].get_iter_at_offset(end_pos)
                diff_iter = self.widgets['diff_store'].append()

                if line:
                    self.widgets['unverified_buffer'].apply_tag_by_name('newdomain', start_iter, end_iter)
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_DOMAIN, line)
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_MERGE, False)
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_COLOUR, 'light green')
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_ACTION, ADD_ACTION)

        for line in verified_list:
            if not len(line) or not line:
                continue

            if line not in unverified_list:
                start_pos = verified_data.find(line)
                end_pos = start_pos + len(line)
                start_iter = self.widgets['verified_buffer'].get_iter_at_offset(start_pos)
                end_iter = self.widgets['verified_buffer'].get_iter_at_offset(end_pos)
                self.widgets['verified_buffer'].apply_tag_by_name('deletedomain', start_iter, end_iter)

                if line:
                    diff_iter = self.widgets['diff_store'].append()
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_DOMAIN, line)
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_MERGE, False)
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_COLOUR, 'light coral')
                    self.widgets['diff_store'].set_value(diff_iter, COLUMN_DIFF_ACTION, DELETE_ACTION)

    def toggle_diff_merge(self, widget, path):
        path = Gtk.TreePath.new_from_string(path)
        store_path = self.widgets['diff_view'].get_model().convert_path_to_child_path(path)
        store_iter = self.widgets['diff_store'].get_iter(store_path)
        v = self.widgets['diff_store'].get_value(store_iter, COLUMN_DIFF_MERGE)
        self.widgets['diff_store'].set_value(store_iter, COLUMN_DIFF_MERGE, not v)

    def merge_diff(self, widget):
        """Merge the selected items in the diff store"""

        model, iter = self.widgets['verified_treeview'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        domains = set(model.get_value(iter, COLUMN_DATA).split('\n'))

        for item in self.widgets['diff_store']:
            domain, merge, col, action = item
            if not merge:
                continue
            if action == DELETE_ACTION:
                domains.discard(domain)
            elif action == ADD_ACTION:
                domains.add(domain)

        self.widgets['verified_buffer'].set_text('\n'.join(domains))
        self.updated_verified()

    def updated_unverified(self, widget):
        """Update the selected group"""
        model, iter = self.widgets['unverified_treeview'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        if model.get_value(iter, COLUMN_TYPE) == TYPE_CATEGORY:
            return

        # Get the id
        id = model.get_value(iter, COLUMN_ID)

        # Update with the entry data
        buffer = self.widgets['unverified_textview'].get_buffer()
        data = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            False
        )
        name = self.widgets['unverified_entry_name'].get_text()
        verified = self.widgets['unverified_entry_checkbox'].get_active()

        self.database.update_group(
            int(id),
            verified,
            name,
            data.split('\n')
        )
        self.refresh_database()
        self.unverified_dirty = False

    def updated_verified(self, widget=None):
        """Update the selected group"""

        model, iter = self.widgets['verified_treeview'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        category_id = None
        id = None

        if not self.new_item:
            if model.get_value(iter, COLUMN_TYPE) == TYPE_CATEGORY:
                return

            # Get the id
            id = model.get_value(iter, COLUMN_ID)
        else:
            while iter and model.get_value(iter, COLUMN_TYPE) != TYPE_CATEGORY:
                iter = model.parent_iter(iter)
            category_id = model.get_value(iter, COLUMN_ID)

        # Update with the entry data
        buffer = self.widgets['verified_textview'].get_buffer()
        data = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            False
        )
        name = self.widgets['verified_entry_name'].get_text()
        verified = self.widgets['verified_entry_checkbox'].get_active()

        if self.new_item:
            self.database.create_group(
                True,
                name,
                data.split('\n'),
                category_id
            )
        else:
            self.database.update_group(
                int(id),
                verified,
                name,
                data.split('\n')
            )
        self.refresh_database()
        self.verified_dirty = False
        self.new_item = False

    def delete_unverified(self, widget):
        """Delete an unverified group"""

        model, iter = self.widgets['unverified_treeview'].get_selection().get_selected()
        if not iter:
            return
        iter = model.convert_iter_to_child_iter(iter)
        if not iter:
            return
        model = model.get_model()

        if model.get_value(iter, COLUMN_TYPE) == TYPE_CATEGORY:
            return

        name = model.get_value(iter, COLUMN_NAME)

        if askyesno("Delete Unverified Group", "Delete %s?" % name):
            self.database.delete_group(int(model.get_value(iter, COLUMN_ID)))
            self.refresh_database()
            self.unverified_dirty = False

    def delete_verified(self, widget):
        """Delete a verified group"""

        model, iter = self.widgets['verified_treeview'].get_selection().get_selected()
        if not iter:
            return
        iter = model.convert_iter_to_child_iter(iter)
        if not iter:
            return
        model = model.get_model()

        if model.get_value(iter, COLUMN_TYPE) == TYPE_CATEGORY:
            return

        name = model.get_value(iter, COLUMN_NAME)

        if askyesno("Delete Verified Group", "Delete %s?" % name):
            self.database.delete_group(int(model.get_value(iter, COLUMN_ID)))
            self.refresh_database()
            self.verified_dirty = False

    def connect_database(self, widget):
        if not self.database.connected:
            self.database.connect()
            self.refresh_database()
        else:
            self.database.disconnect()

    def refresh_database(self, widget=None):
        """Refresh the tree views"""

        if not self.database.connected:
            return

        self.store.clear()
        self.category_iters = {}
        self.group_iters = {}

        for row in self.database.get_categories():
            iter = self.store.append(
                self.category_iters.get(row['parent_id'], None),
                None
            )

            self.category_iters[row['id']] = iter
            self.store.set_value(iter, COLUMN_ID, str(row['id']))
            self.store.set_value(iter, COLUMN_VERIFIED, True)
            self.store.set_value(iter, COLUMN_TYPE, TYPE_CATEGORY)
            self.store.set_value(iter, COLUMN_NAME, row['name'])

        for row in self.database.get_groups():
            parent_iter = self.category_iters.get(row['category_id'])

            iter = self.store.append(parent_iter)
            self.store.set_value(iter, COLUMN_ID, str(row['id']))
            self.store.set_value(iter, COLUMN_VERIFIED, not row['unverified'])
            self.store.set_value(iter, COLUMN_NAME, row['name'])
            self.store.set_value(iter, COLUMN_TYPE, TYPE_GROUP)
            self.store.set_value(iter, COLUMN_DATA, row['domains'])

            self.group_iters[iter] = row

    def quit(self, *args):
        if self.database.connected:
            self.database.disconnect()
        Gtk.main_quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', default='config.ini')
    args = parser.parse_args()
    manager = DatabaseManager(args.config_file)
    Gtk.main()

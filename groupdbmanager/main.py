import configparser

from gi.repository import Gtk

from db import Database

COLUMN_NAME = 0
COLUMN_DATA = 1
COLUMN_ID = 2
COLUMN_TYPE = 3
COLUMN_VERIFIED = 4
TYPE_CATEGORY = 0
TYPE_GROUP = 1


class DatabaseManager:

    category_iters = {}
    group_iters = {}

    def __init__(self):
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
        self.config.read('config.ini')

        self.store = self.widgets['group_store']
        self.widgets['verified_treeview'].get_model().set_visible_func(self.filter_verified)
        self.widgets['unverified_treeview'].get_model().set_visible_func(self.filter_unverified)

        self.database = Database(
            self.config['database']['host'],
            self.config.getint('database', 'port', fallback=3306),
            self.config['database']['username'],
            self.config['database']['password'],
            self.config['database']['database'],
        )

    def filter_verified(self, model, iter, data=None):
        """Return true if the iter is verified. Also hides categories that don't have any groups"""
        if model.get_value(iter, COLUMN_TYPE) == TYPE_GROUP:
            return model.get_value(iter, COLUMN_VERIFIED)
        else:
            child = model.iter_children(iter)
            while child:
                if self.filter_verified(model, child):
                    return True
                child = model.iter_next(child)
            return False

    def filter_unverified(self, model, iter, data=None):
        """Return true if the iter is verified"""
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
            buffer = Gtk.TextBuffer()
            buffer.set_text(model.get_value(iter, COLUMN_DATA))
            self.widgets['verified_textview'].set_buffer(buffer)
        else:
            self.widgets['verified_entry_name'].set_text('')
            self.widgets['verified_entry_checkbox'].set_active(False)
            self.widgets['verified_textview'].get_buffer().set_text('')

    def unverified_selected(self, widget):
        model, iter = widget.get_selected()
        if not iter:
            return
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        if model.get_value(iter, COLUMN_TYPE) == TYPE_GROUP:
            self.widgets['unverified_entry_name'].set_text(model.get_value(iter, COLUMN_NAME))
            self.widgets['unverified_entry_checkbox'].set_active(model.get_value(iter, COLUMN_VERIFIED))
            buffer = Gtk.TextBuffer()
            buffer.set_text(model.get_value(iter, COLUMN_DATA))
            self.widgets['unverified_textview'].set_buffer(buffer)

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

    def updated_unverified(self, widget):
        """Update the selected group"""
        model, iter = self.widgets['unverified_treeview'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

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

    def updated_verified(self, widget):
        """Update the selected group"""
        model, iter = self.widgets['verified_treeview'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        # Get the id
        id = model.get_value(iter, COLUMN_ID)

        # Update with the entry data
        buffer = self.widgets['verified_textview'].get_buffer()
        data = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            False
        )
        name = self.widgets['verified_entry_name'].get_text()
        verified = self.widgets['verified_entry_checkbox'].get_active()

        self.database.update_group(
            int(id),
            verified,
            name,
            data.split('\n')
        )
        self.refresh_database()

    def connect_database(self, widget):
        if not self.database.connected:
            self.database.connect()
            self.refresh_database()
        else:
            self.database.disconnect()

    def refresh_database(self, widget=None):
        """Refresh the tree views"""
        self.store.clear()
        self.category_iters = {}
        self.group_iters = {}

        for row in self.database.get_categories():

            iter = self.store.append(self.category_iters.get(row['id'], None))

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
    manager = DatabaseManager()
    Gtk.main()

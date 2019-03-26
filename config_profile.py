import configparser

from gi.repository import Gdk

from util import askyesno, ask_text

COLUMN_NAME = 0
COLUMN_MODE = 1
COLUMN_USERNAME = 2
COLUMN_PASSWORD = 3
COLUMN_SERVER = 4


class ConfigProfile:
    """Read and write different configuration profiles"""

    mode_iters = {}
    block_signals = False

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller
        self.window = self.arw['profiles_window']
        self.profiles_store = self.arw['profiles_store']

        self.arw['profile_context_menu'].attach_to_widget(self.arw['profiles_tree'])

        mode_iter = self.arw['profile_mode_store'].get_iter_first()
        while mode_iter:
            self.mode_iters[self.arw['profile_mode_store'].get_value(mode_iter, 0)] = mode_iter
            mode_iter = self.arw['profile_mode_store'].iter_next(mode_iter)

    def list_configuration_profiles(self):
        """Update the list view with all the configuration profiles found"""
        self.profiles_store.clear()
        for key, config in self.controller.idefix_config['conf'].items():
            new_iter = self.profiles_store.append()
            self.profiles_store.set_value(new_iter, COLUMN_NAME, key)
            self.profiles_store.set_value(new_iter, COLUMN_MODE, config['mode'][0])
            self.profiles_store.set_value(new_iter, COLUMN_USERNAME, config['login'][0])
            self.profiles_store.set_value(new_iter, COLUMN_PASSWORD, config['pass'][0])
            self.profiles_store.set_value(new_iter, COLUMN_SERVER, config['server'][0])

    def profile_open_window(self, *args):
        """Show the profiles window"""
        self.window.show_all()

    def profile_close_window(self, *args):
        """Close the profile window"""
        self.window.hide()
        return True

    def profile_selection_updated(self, widget):
        """Update the text entries when the selection changes"""
        self.block_signals = True
        model, selected_iter = widget.get_selected()

        self.arw['profile_name_entry'].set_text(model.get_value(selected_iter, COLUMN_NAME))
        self.arw['profile_username_entry'].set_text(model.get_value(selected_iter, COLUMN_USERNAME) or '')
        self.arw['profile_password_entry'].set_text(model.get_value(selected_iter, COLUMN_PASSWORD) or '')
        self.arw['profile_server_entry'].set_text(model.get_value(selected_iter, COLUMN_SERVER) or '')
        self.arw['profile_mode_combo'].set_active_iter(self.mode_iters[model.get_value(selected_iter, COLUMN_MODE)])
        self.block_signals = False

    def profile_update_data(self, widget):
        """Update the store with data from the widget"""

        if self.block_signals:
            return

        model, selected_iter = self.arw['profiles_tree'].get_selection().get_selected()

        if widget.name == 'profile_mode_combo':
            value = self.arw['profile_mode_store'].get_value(widget.get_active_iter(), 0)
            model.set_value(selected_iter, COLUMN_MODE, value)
        else:
            column = {
                'profile_name_entry': COLUMN_NAME,
                'profile_username_entry': COLUMN_USERNAME,
                'profile_password_entry': COLUMN_PASSWORD,
                'profile_server_entry': COLUMN_SERVER,
            }[widget.name]
            model.set_value(selected_iter, column, widget.get_text())

    def profile_list_show_context_menu(self, widget, event):
        """Show a context menu to add or delete items"""
        if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 3:
            self.arw["profile_context_menu"].popup(None, None, None, None, event.button, event.time)

    def profile_add_new(self, widget):
        """Add a new configuration"""
        profile_name = ask_text(self.window, "Enter name for profile")
        if profile_name:
            new_iter = self.profiles_store.append()
            self.profiles_store.set_value(new_iter, COLUMN_NAME, profile_name)
            self.profiles_store.set_value(new_iter, COLUMN_MODE, 'local')
            self.arw['profiles_tree'].get_selection().select_iter(new_iter)

    def profile_delete_selected(self, widget):
        """Delete an existing configuration"""

        model, selected_iter = self.arw['profiles_tree'].get_selection().get_selected()

        if askyesno("Delete Profile", "Really delete %s?" % model.get_value(selected_iter, COLUMN_NAME)):
            model.remove(selected_iter)

    def profile_save_config(self, widget):
        """Update the cfg file with the currently stored configuration"""
        config = configparser.ConfigParser(interpolation=None)
        for row in self.profiles_store:
            config[row[COLUMN_NAME]] = {
                'server': row[COLUMN_SERVER],
                'login': row[COLUMN_USERNAME],
                'pass': row[COLUMN_PASSWORD],
                'mode': row[COLUMN_MODE]
            }
        with open('idefix-config.cfg', 'w') as f:
            config.write(f)

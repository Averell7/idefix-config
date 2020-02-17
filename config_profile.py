import binascii
import os
# from myconfigparser import myConfigParser
from configparser import ConfigParser
from copy import deepcopy

from gi.repository import Gdk

import pyaes
from util import askyesno, ask_text, get_config_path, alert

COLUMN_NAME = 0
COLUMN_MODE = 1
COLUMN_USERNAME = 2
COLUMN_PASSWORD = 3
COLUMN_SERVER = 4

DEFAULT_KEY = "idefix-config"


# AES CTR encryption using user supplied password or default password
# Pads the key with \0 if it is too short and pads the data with \0
# to ensure a minimum length of 16. Assumes both the key and the password
# does not contain \0.


def _get_aes_key(key):
    """Return a padded key in the correct format"""
    if len(key) % 16 != 0:
        key += '\0' * (16 - (len(key) % 16))
    if isinstance(key, str):
        return key.encode('utf-8')
    return key


def decrypt_password(password, key=DEFAULT_KEY):
    """Decrypt a password with the given key"""
    if password.startswith('$aes$'):
        ctx = pyaes.AESModeOfOperationCTR(_get_aes_key(key))
        try:
            p = ctx.decrypt(bytes.fromhex(password[5:])).decode('utf-8')
            return p.replace('\0', '')  # Quick way to remove any padding
        except UnicodeDecodeError:
            return None
    else:
        return password


def encrypt_password(password, key=DEFAULT_KEY):
    """Encrypt a password with the given key"""
    if not password:
        return ''

    if password.startswith('$aes'):
        return password

    ctx = pyaes.AESModeOfOperationCTR(_get_aes_key(key))
    if len(password) % 16 != 0:
        # Pad with \0
        password += '\0' * (16 - (len(password) % 16))
    return '$aes$' + binascii.hexlify(ctx.encrypt(password.encode('utf-8'))).decode("ascii")


def decrypt_config(cfg, password):
    for key, value in cfg.items():
        if 'pass' in value:
            cfg[key]['pass'] = decrypt_password(value['pass'], password)

    return cfg


def get_config(filename, password=DEFAULT_KEY):
    """Get the configuration for the given filename and decrypt any passwords. Optionally will return
     a default configuration if one does not already exist"""
    parser = ConfigParser(interpolation=None, default_section='__DEFAULT')
    parser.read(filename)
    if not parser.has_section('__options'):
        parser.add_section('__options')

    return decrypt_config(parser, password)


class ConfigProfile:
    """Read and write different configuration profiles"""

    mode_iters = {}
    block_signals = False

    def __init__(self, arw, controller, filename=None, password=DEFAULT_KEY):
        self.arw = arw
        self.controller = controller
        self.password = password
        if not filename:
            filename = get_config_path('confix.cfg')
        self.filename = filename

        self.window = self.arw['profiles_window']
        self.profiles_store = self.arw['profiles_store']

        self.arw['profile_context_menu'].attach_to_widget(self.arw['profiles_tree'])

        mode_iter = self.arw['profile_mode_store'].get_iter_first()
        while mode_iter:
            self.mode_iters[self.arw['profile_mode_store'].get_value(mode_iter, 0)] = mode_iter
            mode_iter = self.arw['profile_mode_store'].iter_next(mode_iter)

        self.config = get_config(self.filename, self.password)
        self.config_found = os.path.exists(self.filename)

    def refresh_saved_profiles(self):
        """Read the config file again and update the configuration profiles"""
        self.config = get_config(self.filename, self.password)
        self.config_found = os.path.exists(self.filename)

    def list_configuration_profiles(self):
        """Update the list view with all the configuration profiles found"""
        self.profiles_store.clear()
        for key, config in self.config.items():
            if key.startswith('__'):
                continue
            new_iter = self.profiles_store.append()
            self.profiles_store.set_value(new_iter, COLUMN_NAME, key)
            if 'mode' in config:
                self.profiles_store.set_value(new_iter, COLUMN_MODE, config['mode'])
            if 'login' in config:
                self.profiles_store.set_value(new_iter, COLUMN_USERNAME, config['login'])
            if 'pass' in config:
                self.profiles_store.set_value(new_iter, COLUMN_PASSWORD, config['pass'])
            if 'server' in config:
                self.profiles_store.set_value(new_iter, COLUMN_SERVER, config['server'])

    def profile_open_window(self, *args):
        """Show the profiles window"""
        self.window.show_all()

    def profile_close_window(self, *args):
        """Close the profile window"""
        self.window.hide()
        self.refresh_saved_profiles()
        return True

    def profile_selection_updated(self, widget):
        """Update the text entries when the selection changes"""
        self.block_signals = True
        model, selected_iter = widget.get_selected()
        if not selected_iter:
            alert("There is no configuration selected. \nPlease, select a configuration before editing.")
        self.arw['profile_name_entry'].set_text(model.get_value(selected_iter, COLUMN_NAME))
        self.arw['profile_username_entry'].set_text(model.get_value(selected_iter, COLUMN_USERNAME) or '')
        self.arw['profile_password_entry'].set_text(model.get_value(selected_iter, COLUMN_PASSWORD) or '')
        self.arw['profile_server_entry'].set_text(model.get_value(selected_iter, COLUMN_SERVER) or '')
        #self.arw['profile_mode_combo'].set_active_iter(self.mode_iters[model.get_value(selected_iter, COLUMN_MODE)])
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

    def profile_save_config(self, widget=None):
        """Update the cfg file with the currently stored configuration"""

        c = deepcopy(self.config)

        for row in self.profiles_store:
            c[row[COLUMN_NAME]] = {
                'server': row[COLUMN_SERVER],
                'login': row[COLUMN_USERNAME] or '',
                'pass': encrypt_password(row[COLUMN_PASSWORD] or '', self.password)
            }

##            # update self.config
##            edit = self.config['conf'][row[COLUMN_NAME]]
##            edit['server'] = row[COLUMN_SERVER]
##            edit['login']  = row[COLUMN_USERNAME]
##            edit['pass']   = row[COLUMN_PASSWORD]
##            edit['mode']   = row[COLUMN_MODE]
        with open(self.filename, 'w') as f:
            c.write(f)

        #self.config = get_config(self.filename, self.password)


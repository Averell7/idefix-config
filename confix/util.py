import configparser
import os
import re
import sys
import traceback

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import elib_intl3

gtk = Gtk


class SignalHandler:
    def __init__(self, classes):
        self.classes = classes

    def __getattr__(self, name):
        for c in self.classes:
            if not hasattr(c, name):
                continue
            return getattr(c, name)
        else:
            raise AttributeError("Signal Not Found: %s", name)


class AskForConfig:

    def __init__(self, idefix_config):
        # dialog = gtk.Dialog(title=None, parent=None, flags=0, buttons=None)
        self.dialog = gtk.Dialog(title='Configuration choice', parent=None, flags=gtk.DialogFlags.MODAL,
                                 buttons=("OK", 1, "Cancel", 0))
        self.combo = gtk.ComboBoxText()
        self.label = gtk.Label()
        message =  "Please, choose the <b>Idefix module</b> or the <b>FTP site</b>\n"
        message += "to which you want to be connected\nand press OK\n"
        message += "or Cancel to close the program"
        self.label.set_markup(message)
        alignment = gtk.Align(1)
        self.label.set_halign(alignment)

        for key in idefix_config:
            if key.startswith('__'):
                continue
            self.combo.append_text(key)
        self.combo.set_active(0)
        self.button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Normal (for LAN 1)")
        self.button2 = Gtk.RadioButton.new_with_label_from_widget(self.button1, "for LAN 2")
        self.button3 = Gtk.RadioButton.new_with_label_from_widget(self.button1, "for LAN 3")
        self.dialog.vbox.pack_start(self.label, 0, 0, 0)
        self.dialog.vbox.pack_start(self.combo, 0, 0, 0)
        self.dialog.vbox.pack_start(self.button1, True, True, 0)
        self.dialog.vbox.pack_start(self.button2, True, True, 0)
        self.dialog.vbox.pack_start(self.button3, True, True, 0)
        self.dialog.show_all()

    def run(self):
        x = self.dialog.run()
        configname = self.combo.get_active_text()
        self.dialog.destroy()
        if self.button1.get_active() == True:
            eth = 1
        elif self.button2.get_active() == True:
            eth = 2
        elif self.button3.get_active() == True:
            eth = 3
        if x == 1:
            return configname, eth
        else:
            return ""


class PasswordDialog:
    def __init__(self):
        # dialog = gtk.Dialog(title=None, parent=None, flags=0, buttons=None)
        self.dialog = gtk.Dialog(title='Config Password', parent=None, flags=gtk.DialogFlags.MODAL,
                                 buttons=("OK", gtk.ResponseType.OK, "Cancel", gtk.ResponseType.CANCEL))
        self.entry = gtk.Entry()
        self.entry.set_visibility(False)
        self.dialog.vbox.pack_start(
            Gtk.Label(_("Your configuration is password protected.\nPlease enter password below:")), 0, 0, 0
        )
        self.dialog.vbox.pack_start(self.entry, 0, 0, 0)
        self.dialog.show_all()

    def run(self):
        self.dialog.show_all()
        self.entry.set_text('')
        r = self.dialog.run()
        if r == gtk.ResponseType.CANCEL:
            return None
        data = self.entry.get_text()
        self.dialog.hide()
        return data

    def destroy(self):
        self.dialog.destroy()


def print_except(info = False):
    a, b, c = sys.exc_info()
    text = ""
    for d in traceback.format_exception(a, b, c):
        try:
            print(d, end=' ')
        except:
            print(d.encode("cp850", "ignore"))
        text += d
    if info:
        return text


def parse_date_format_to_squid(value):
    """Translate numerical day of week to Squid day of week"""
    n = {
        '1': "M",
        '2': "T",
        '3': "W",
        '4': "H",
        '5': "F",
        '6': "A",
        '7': "S"
    }
    try:
        return ''.join([n[c] for c in value])
    except KeyError:
        return ''


def parse_date_format_from_squid(value):
    """Translate squid day of week to numerical day of week"""
    n = {
        'M': '1',
        'T': '2',
        'W': '3',
        'H': '4',
        'F': '5',
        'A': '6',
        'S': '7',
    }
    try:
        return ''.join([n[c] for c in value])
    except KeyError:
        return ''


def mac_address_test(value):
    """Check that a MAC Address is valid"""

    value = value.split("#")[0].strip()  # strip comment
    result = re.search(r'^([+\-]@)?([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$', value, re.I)
    return result is not None


def ip_address_test(value):
    """Check IP Address is valid"""

    value = value.split("#")[0].strip()  # strip comment
    result = re.search(r'^([+\-]@)?((2[0-5]|1[0-9]|[0-9])?[0-9]\.){3}((2[0-5]|1[0-9]|[0-9])?[0-9])$', value, re.I)
    return result is not None


def get_ip_address(value):
    """Get the first IP Address found in a string"""

    return re.search(r'((2[0-5]|1[0-9]|[0-9])?[0-9]\.){3}((2[0-5]|1[0-9]|[0-9])?[0-9])', value, re.I)

def get_mac_address(value):
    """Check that a MAC Address is valid"""
    return re.search(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', value, re.I)

def bool_test(value):
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            if value.strip().lower() == "true":
                return True
            else:
                return False

    return bool(value)


def alert(message, type_=0):
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING,
                               Gtk.ButtonsType.CLOSE, message)
    dialog.set_keep_above(True)
    dialog.run()
    dialog.destroy()


def showwarning(title, message, msgtype=1):
    """
      type 1 = INFO,
      type 2 = WARNING,
      type 3 = QUESTION,
      type 4 = ERROR,
      type 5 = OTHER
    """
    types = [Gtk.MessageType.INFO,
             Gtk.MessageType.WARNING,
             Gtk.MessageType.QUESTION,
             Gtk.MessageType.ERROR,
             Gtk.MessageType.OTHER]

    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, types[msgtype - 1],
                               Gtk.ButtonsType.CLOSE, title)
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


def ask_text(parent, message, default='', password=False):
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
    entry.set_visibility(not password)
    entry.show()
    d.vbox.pack_end(entry, True, True, 0)
    entry.connect('activate', lambda _: d.response(Gtk.ResponseType.OK))
    d.set_default_response(Gtk.ResponseType.OK)
    d.set_keep_above(True)

    r = d.run()
    text = entry.get_text()
    if sys.version_info[0] == 2:
        text = text.decode('utf8')
    d.destroy()
    if r == Gtk.ResponseType.OK:
        return text
    else:
        return None


def ask_choice(parent, message, default='', password=False):
    """
    Display a dialog with radio buttons.
    Returns the text, or None if canceled.
    """
    d = Gtk.MessageDialog(parent,
                          Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                          Gtk.MessageType.QUESTION,
                          Gtk.ButtonsType.OK_CANCEL,
                          message)
    button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Normal (for LAN 1")
    button2 = Gtk.RadioButton.new_with_label_from_widget(button1, "for LAN 2")
    button3 = Gtk.RadioButton.new_with_label_from_widget(button1, "for LAN 3")
    d.vbox.pack_start(button1, True, True, 0)
    d.vbox.pack_start(button2, True, True, 0)
    d.vbox.pack_start(button3, True, True, 0)
    d.vbox.show_all()
    #entry.connect('activate', lambda _: d.response(Gtk.ResponseType.OK))
    #d.set_default_response(Gtk.ResponseType.OK)
    d.set_keep_above(True)

    r = d.run()
    d.destroy()
    if button1.get_active() == True:
        return 1
    elif button2.get_active() == True:
        return 2
    elif button3.get_active() == True:
        return 3




def format_line(key, line1):
    text = ""
    key += " = "

    list1 = line1.split("\n")
    if "any" in list1:
        return key + "any\n"

    for value in list1:
        if value.strip() != "":
            text += key + value + "\n"
    return text


def format_comment(line1):
    text = ""
    for value in line1.split("\n"):
        if value.strip() == "":
            continue
        if value.strip() == "#":
            continue
        if value.strip()[0:1] != "#":
            text += "# " + value + "\n"
        else:
            text += value + "\n"
    return text


def format_time(line1):
    # Check if time range overlaps 24:00
    # if yes, returns two ranges.
    if line1.strip() == "":
        return [""]
    tc0 = line1.strip()
    elements = re.search("([0-9]*)\s([0-9:]*)-([0-9:]*)", tc0.strip())
    if not elements:
        elements = re.search("([0-9:]*)-([0-9:]*)", tc0.strip())
        if not elements:
            return [line1]
        else:
            days = ""
            start = elements.group(1)
            stop = elements.group(2)
    else:
        days = elements.group(1)
        days = parse_date_format_to_squid(days)
        start = elements.group(2)
        stop = elements.group(3)
    start_i = int(start.replace(":", ""))
    stop_i = int(stop.replace(":", ""))
    if stop_i < start_i:
        tc1 = days + " " + start + "-24:00"
        tc2 = days + " 00:00-" + stop
        return [tc1, tc2]
    else:
        return [days + " " + start + "-" + stop]


def format_directive(list1):
    out = "action = " + list1[0] + "\n"
    for line in list1[1:]:
        out += "ports = " + line + "\n"
    return out + "\n"


def format_userline(dummy, line1):
    # separate domains and ips
    text = ""
    for value in line1.split("\n"):
        if value.strip() != "":
            if len(re.findall("[:]", value)) == 5:  # five : means this is a mac address
                # TODO  check that the mac address is valid
                key = "users"
            else:
                key = "user"
            text += key + " = " + value + "\n"
    return text


def format_domainline(dummy, line1):
    # separate domains and ips
    text = ""
    for value in line1.split("\n"):
        if value.strip() != "":
            if ip_address_test(value):
                key = "dest_ip"
            else:
                key = "dest_domains"
            text += key + " = " + value + "\n"
    return text


def format_name(name):
    return name.replace(" ", "_")


EMPTY_STORE = gtk.ListStore(str)


def get_config_path(filename):
    """Return the full path for the configuration (if it exists)"""

    directory, filename = os.path.split(filename)

    if sys.platform.startswith('win'):
        # step 1: roaming
        roaming = os.path.join(os.getenv('APPDATA'), 'Confix', directory)
        if not os.path.exists(os.path.join(roaming, filename)):
            os.makedirs(roaming, exist_ok=True)
        # for dev mode
        if not os.path.isdir(os.path.join(roaming, "dev")):
            os.makedirs(roaming + "/dev", exist_ok=True)
        path = roaming
    else:
        # step 1: ~/.local/share/confix/
        roaming = os.path.join(os.path.expanduser('~/.local/confix'), directory)
        if os.path.exists(os.path.join(roaming, filename)):
            path = roaming
        else:
            os.makedirs(roaming, exist_ok=True)
            path = roaming

    return os.path.join(path, filename)


def write_default_config():
    """Write the default configuration to the roaming directory"""

    if sys.platform.startswith('win'):
        roaming = os.path.join(os.getenv('APPDATA'), 'confix')
    else:
        roaming = os.path.expanduser('~/.local/confix')

    # Create the directory structure
    os.makedirs(roaming, exist_ok=True)

    with open(os.path.join(roaming, 'confix.cfg'), 'w') as f:
        if os.path.isfile('./confix.cfg') :
            with open('./confix.cfg', 'r') as f2:
                data1 = f2.read()
                f.write(data1)
        elif os.path.isfile('./idefix-config.cfg') :
            with open('./idefix-config.cfg', 'r') as f2:
                data1 = f2.read()
                f.write(data1)
        else:
            config = configparser.ConfigParser(interpolation=None)
            config['default'] = {
                'mode': 'local',
                'server': '192.168.84.184',
                'login': 'rock64',
                'pass': 'rock64'
            }
            config.write(f)

    return os.path.join(roaming, 'confix.cfg')


###########################################################################
# LOCALISATION ############################################################
###########################################################################
elib_intl3.install("confix", "share/locale")


def name_sorter(model, a, b, data):
    namea = model.get_value(a, 0)
    nameb = model.get_value(b, 0)

    if namea == nameb:
        return 0
    elif namea and nameb and namea > nameb:
        return 1
    else:
        return -1


def cleanhtml(html):
    return re.sub(r'<.*?>', '', html)

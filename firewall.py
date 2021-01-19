from collections import OrderedDict

from gi.repository import Gtk, Gdk

from util import (
    askyesno, ask_text, ip_address_test, mac_address_test, format_comment, format_line, format_directive,
    get_config_path
)


class Firewall:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller

        # 2 - firewall
        """
        0 : section
        1 : "active",
        2 : "action",
        3 : "ports",
        4 : "time_condition",
        5 : "#comments",
        6 : "user",
        7 : "users",
        8 :
        9 :
        10 : (int)
        11 : checkbox visible (0/1)
        12 : checkbox3
        13 : checkbox1   (0/1)
        14 : checkbox2   (0/1)
        15 : color1
        16 : color2


        """

        self.firewall_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, int, int, int, int, int,
                                            str, str)  #
        self.cell2 = Gtk.CellRendererText()

        self.check3 = Gtk.CellRendererToggle(activatable=True)
        # self.check.set_property('xalign', 0.0)
        self.check3.connect('toggled', self.controller.toggle_col13, self.firewall_store, "firewall")
        self.check4 = Gtk.CellRendererToggle(activatable=True, xalign=0.5)
        self.check4.connect('toggled', self.toggle_col14, self.firewall_store)
        # self.check6 = gtk.CellRendererToggle(activatable = True, xalign = 0.5)
        # self.check6.connect( 'toggled', self.toggle_col12_firewall, self.firewall_store )

        self.treeview2 = self.arw["treeview2"]
        self.treeview2.set_model(self.firewall_store)
        self.treeview2.connect("button-press-event", self.firewall_user)

        self.tvcolumn = Gtk.TreeViewColumn(_('Key'), self.cell2, text=0, foreground=15, background=16)
        # self.tvcolumn.pack_start(self.cell2, False)
        # self.tvcolumn.add_attribute(self.cell2, "text", 0)
        self.treeview2.append_column(self.tvcolumn)

        self.tvcolumn = Gtk.TreeViewColumn(_('Accept/Drop'), self.check3, active=13, visible=11)
        self.treeview2.append_column(self.tvcolumn)

        self.tvcolumn = Gtk.TreeViewColumn(_('On/Off'), self.check4, active=14, visible=11)
        self.treeview2.append_column(self.tvcolumn)

        """
        def sorter(a, b):
            return self.arw['ports_list_sort'].get_value(a, 0) > self.arw['ports_list_sort'].get_value(b, 0)

        self.arw['ports_list_sort'].set_default_sort_func(sorter)
        """
        self.arw['ports_tree'].get_model().set_sort_column_id(0, Gtk.SortType.ASCENDING)

    def populate_ports(self):
        if not self.controller.config.get('ports'):
            self.controller.config['ports'] = OrderedDict()

        self.arw['ports_list'].clear()
        for key, value in self.controller.config['ports'].items():
            iter = self.arw['ports_list'].append()
            self.arw['ports_list'].set_value(iter, 0, key)
            self.arw['ports_list'].set_value(iter, 1, '\n'.join(value.get('port', [])))

    def ports_open_window(self, widget=None):
        """Opens the ports window from the developer menu"""

        self.arw['ports_window'].show_all()
        buf = Gtk.TextBuffer()
        self.arw['ports_buffer'] = buf
        self.arw['ports_view'].set_buffer(buf)
        self.ports_selection_changed(self.arw['ports_tree'].get_selection())

    def cancel_ports_window(self, widget):
        self.arw['ports_window'].hide()
        self.arw['ports_buffer'] = Gtk.TextBuffer()
        self.arw['ports_view'].set_buffer(self.arw['ports_buffer'])
        self.populate_ports()

    def ports_selection_changed(self, widget):
        model, iter = widget.get_selected()

        if not iter:
            return
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        value = model.get_value(iter, 1)
        buf = Gtk.TextBuffer()
        buf.set_text(value)
        buf.connect('changed', self.update_ports)
        self.arw['ports_buffer'] = buf
        self.arw['ports_view'].set_buffer(self.arw['ports_buffer'])

    def update_ports(self, widget):
        model, iter = self.arw['ports_tree'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()

        model.set_value(iter, 1, self.arw['ports_buffer'].get_text(
            self.arw['ports_buffer'].get_start_iter(),
            self.arw['ports_buffer'].get_end_iter(),
            False
        ))

    def save_ports(self, widget):
        """Write the tree list to the ports store"""
        model = self.arw['ports_tree'].get_model()
        self.controller.config['ports'] = OrderedDict()
        for row in model:
            self.controller.config['ports'][row[0]] = {
                'port': row[1].split('\n'),
            }

        self.arw['ports_window'].hide()

    def ports_new_group(self, widget):
        """Create a new port group"""
        name = ask_text(self.arw['ports_window'], _('Enter group name'))
        if not name:
            return
        iter = self.arw['ports_list'].append([name, ''])
        valid, iter = self.arw['ports_tree'].get_model().convert_child_iter_to_iter(iter)
        self.arw['ports_tree'].get_selection().select_iter(iter)

    def ports_delete_group(self, widget):
        """Delete the selected ports group"""
        model, iter = self.arw['ports_tree'].get_selection().get_selected()
        name = model.get_value(iter, 0)

        if not askyesno(_('Delete %s') % name, _('Are you sure you want to delete port group?')):
            return

        model, iter = self.arw['ports_tree'].get_selection().get_selected()
        iter = model.convert_iter_to_child_iter(iter)
        model = model.get_model()
        model.remove(iter)

    def ports_show_menu(self, widget, event=None):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:  # right click, runs the context menu
                self.arw["ports_menu"].popup(None, None, None, None, event.button, event.time)
        return

    def toggle_col12_firewall(self, cellrenderer, row, treestore):  # unused
        # callback of ?
        # col 12 = open access state; col 16 = background color
        if treestore[row][12] == 0:
            treestore[row][12] = 1
            treestore[row][3] = "any"
            treestore[row][16] = "#ffff88"
        else:
            treestore[row][12] = 0
            treestore[row][3] = ""
            treestore[row][16] = "#ffffff"

    def toggle_col14(self, cellrenderer, row, treestore):
        # callback of the on/off checkbox in proxy tab.
        # col 14 = on/off state; col 15 = text color
        if treestore[row][14] == 0:
            treestore[row][14] = 1
            treestore[row][1] = "on"
            if treestore[row][13] == 1:
                treestore[row][15] = "#009900"
            else:
                treestore[row][15] = "#ff0000"
        else:
            treestore[row][14] = 0
            treestore[row][1] = "off"
            treestore[row][15] = "#bbbbbb"

    def firewall_user(self, widget, event):
        # Loads user data when a user is selected in the list
        path = widget.get_path_at_pos(event.x, event.y)
        if path is None:
            return
        iter1 = self.firewall_store.get_iter(path[0])
        self.controller.iter_firewall = iter1

        # TODO
        self.arw["firewall_time_from"].set_text(self.firewall_store[iter1][4])
        # time conditions
        data1 = self.firewall_store[iter1][4].strip()
        if data1 == "":
            # self.arw["firewall_time_days"].set_text("")
            self.arw["firewall_time_from"].set_text("")
            self.arw["firewall_time_to"].set_text("")

        elif len(data1) > 8:
            try:
                # tmp1 = data1.split()
                tmp2 = data1.split("-")
                # days = tmp1[0].strip()
                time_from = tmp2[0].strip()
                time_to = tmp2[1].strip()

                # self.arw["firewall_time_days"].set_text(days)
                self.arw["firewall_time_from"].set_text(time_from)
                self.arw["firewall_time_to"].set_text(time_to)
            except:
                print("Error handling firewall time condition :", data1)

        # add comments
        data1 = self.firewall_store[iter1][5]
        self.arw["firewall_comments"].get_buffer().set_text(data1)

        # add ports
        data1 = self.firewall_store[iter1][3]
        self.arw["firewall_ports"].get_buffer().set_text(data1)

        # add users
        data1 = self.firewall_store[iter1][6]
        # TODO problème ici
        # add mac, if any
        data1 += self.firewall_store[iter1][7]
        self.firewall_store[iter1][7] = ""
        self.arw["firewall_users"].get_buffer().set_text(data1)

    def populate_firewall(self):
        self.firewall_store.clear()
        data1 = self.controller.config["firewall"]
        keys = ["active", "action", "ports", "time_condition", "#comments", "user", "users"]
        for section in data1:
            data2 = [section]
            if section[0:2] == "__":  # for sections generated from the users data, don't load data here
                self.firewall_store.append([section] + [""] * 9 + [0] * 5 + ["", ""])
                continue
            for key in keys:
                if key in data1[section]:
                    data2.append("\n".join(data1[section][key]))
                else:
                    data2.append("")
            data2 += ["", "", 1]  # reserved
            if section[0:2] == "__":
                data2 += [0]
            else:
                data2 += [1]
            data2 += [1]  # reserved
            data2 += [1, 1, "#009900", "#ffffff"]  # check boxes and colors (green on white)
            self.firewall_store.append(data2)

    def add_user_below3(self, widget):
        (model, node) = self.arw["treeview2"].get_selection().get_selected()
        x = ask_text(self.arw["window1"], "Name of the new user :", "")
        if x is None:
            return
        else:
            x = self.controller.format_name(x)
            address = ask_text(self.arw['window1'], "Enter address of the user", "")
            if ip_address_test(address) or mac_address_test(address):
                self.controller.maclist[x] = [address]
            self.firewall_store.insert_after(node, [x] + [""] * 9 + [0, 1, 0, 0, 0, "", "#ffffff"])

    def delete_user3(self, widget):
        (model, node) = self.arw["treeview2"].get_selection().get_selected()
        name = model.get_value(node, 0)
        if askyesno("Remove rule", "Do you want to remove %s?" % name):
            self.firewall_store.remove(node)

    def edit_user3(self, widget):
        (model, node) = self.arw["treeview2"].get_selection().get_selected()
        name = model.get_value(node, 0)
        x = ask_text(self.arw["window1"], "Name of the user :", name)
        if x is None:
            return
        else:
            x = self.controller.format_name(x)
            self.firewall_store.set(node, [0], [x])


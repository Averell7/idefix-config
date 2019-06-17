from collections import OrderedDict

from gi.repository import Gtk

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

    def ports_open_window(self, widget):
        self.arw['ports_window'].show_all()
        for key, value in self.controller.config['ports'].items():
            iter = self.arw['ports_list'].append()
            self.arw['ports_list'].set_value(iter, 0, key)
            self.arw['ports_list'].set_value(iter, 1, '\n'.join(value['port']))

    def cancel_ports_window(self, widget):
        self.arw['ports_window'].hide()
        self.arw['ports_buffer'] = Gtk.TextBuffer()
        self.arw['ports_view'].set_buffer(self.arw['ports_buffer'])
        self.arw['ports_list'].clear()

    def ports_selection_changed(self, widget):
        model, iter = widget.get_selected()
        value = model.get_value(iter, 1)
        buf = Gtk.TextBuffer()
        buf.set_text(value)
        buf.connect('changed', self.update_ports)
        self.arw['ports_buffer'] = buf
        self.arw['ports_view'].set_buffer(self.arw['ports_buffer'])

    def update_ports(self, widget):
        model, iter = self.arw['ports_tree'].get_selection().get_selected()
        model.set_value(iter, 1, self.arw['ports_buffer'].get_text(
            self.arw['ports_buffer'].get_start_iter(),
            self.arw['ports_buffer'].get_end_iter(),
            False
        ))

    def save_ports(self, widget):
        self.controller.config['ports'] = OrderedDict()
        for item in self.arw['ports_list']:
            key, value = item
            self.controller.config['ports'][key] = {
                'port': value.split('\n')
            }
        self.cancel_ports_window(widget)

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

    def build_firewall_ini(self):
        out = {}
        sections = []
        # "active", "action", "ports", "time_condition", "#comments", "user", "users"

        for row in self.firewall_store:
            section = row[0]
            if section[0:2] == "__":  # This section was generated, skip
                continue
            sections.append(section)

            tmp1 = ""
            tmp1 += "\n[%s]\n" % section
            tmp1 += format_comment(row[5])  # comments
            tmp1 += format_line("active", row[1])
            tmp1 += format_line("action", row[2])
            tmp1 += format_line("ports", row[3])
            tmp1 += format_line("time_condition", row[4])
            tmp1 += format_line("user", row[6])
            tmp1 += format_line("users", row[7])
            # print(tmp1)
            out[section] = tmp1

        # data from the users tree
        """
        0 : section (level 1)  - user (level 2)
        1 : options (text) (no longer used)
        2 : email time condition
        3 : internet time condition
        4 : email (1/0)
        5 : internet access (1/0)
        6 : filtered (1/0)
        7 : open (1/0)
        """

        for row in self.controller.users_store:
            section = "__" + row[0]
            if not section in sections:
                sections.append(section)
            #print(row[0], row[1], row[2], row[3], row[4])
            tmp2 = "\n[%s]\n" % section
            # set the command lines for the categories
            option = row[1].split("|")

            myoptions = []
            if row[4] == 1:  # email
                myoptions.append("email")
                myoptions.append("ports_techniques")  # TODO problème de traduction
            if row[5] == 1:
                if not "ports_techniques" in myoptions:
                    myoptions.append("ports_techniques")  # TODO problème de traduction
                if row[6] == 1:
                    myoptions.append("ftp")
                elif row[7] == 1:
                    myoptions = "any"

            if len(myoptions) > 0:
                ports = []
                if myoptions == "any":
                    ports = ["any"]
                else :
                    for group in myoptions:
                        if self.controller.config["ports"][group].get("port"):
                            ports += self.controller.config["ports"][group].get("port")
                tmp2 += format_directive(["ACCEPT"] + ports)
            else:
                tmp2 += format_directive(["DROP", "any"])

            tmp2 += format_line("time_condition", row[3])

            for b in row.iterchildren():
                tmp2 += "user = " + b[0] + "\n"
            out[section] = tmp2

        output = ""
        for section in sections:
            output += out[section]

        with open(get_config_path("./tmp/firewall-users.ini"), "w", encoding="utf-8-sig", newline="\n") as f1:
            f1.write(output)

import json
import configparser
from collections import OrderedDict
from io import StringIO

from gi.repository import Gtk
import ipaddress

from ftp_client import ftp_connect
from util import alert, showwarning


class Idefix2Config:
    ddclient_options = {}
    dns_options = {}

    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller
        self.config = {}
        self.block_signals = False
        self.autoddclient_config = None
        self.load_default_options()

    def load_default_options(self):
        self.block_signals = True
        options = configparser.ConfigParser()
        options.read('./defaults/option_values.ini')
        self.arw['idefix2_dns_type_store'].clear()
        self.arw['idefix2_dd_handler_store'].clear()
        self.ddclient_options = {}
        self.dns_options = {}
        for section in options.sections():
            if section.startswith('dns:'):
                value = section.split(':', 1)[1]
                name = options[section].get('name', value)
                self.arw['idefix2_dns_type_store'].append((name, value))
                self.dns_options[value] = options[section]
            elif section.startswith('ddclient:'):
                value = section.split(':', 1)[1]
                name = options[section].get('name', value)
                self.ddclient_options[value] = options[section]
                self.arw['idefix2_dd_handler_store'].append((name, value))
        self.block_signals = False

    def idefix2_show_config(self, *args):
        """Load default configuration"""
        self.autoddclient_config = None
        self.load_default_options()
        self.config = OrderedDict({
            "general": {
                "idefix_id": "version 2.4.1"
            },
            "ports": {
                "lan_ports": "eth1",
                "wan_port": "eth0",
                "wifi_port": "",
            },
            "eth0": {
                "wan_ip_type": "dhcp",
                "wan_ip": "",
                "wan_netmask": "",
                "wan_subnet": "",
                "wan_network": "",
                "wan_broadcast": "",
                "wan_gateway": ""
            },
            "eth1": {
                "lan_used": "yes",
                "lan_ip": "",
                "lan_netmask": "",
                "lan_subnet": "",
                "lan_network": "",
                "lan_broadcast": ""
            },
            "wlan0": {
                "wifi_used": "no",
                "wifi_ip": "",
                "wifi_netmask": "",
                "wifi_subnet": "",
                "wifi_network": "",
                "wifi_broadcast": ""
            },
            "dhcp": {
                "dhcp_begin": "",
                "dhcp_end": "",
                "wifi_dhcp_begin": "",
                "wifi_dhcp_end": "",
            },
            "ftp": {
                "effacement": "false",
                "ftp": "",
                "login": "",
                "password": ""
            },
            "dns": {
                "dns_filtering": "",
                "dns_nameserver1": "",
                "dns_nameserver2": ""
            },
            "ddclient": {
                "ip_type": "static",
                "dyn_ip_handler": "",
                "ddclient_login": "",
                "ddclient_password": "",
                "ddclient_domain": "",
                "ddclient_server": "",
                "ddclient_web": "",
                "protocol": ""
            }
        })
        self.arw['idefix2_config_window'].show_all()
        self.set_text_values()
        self.arw['idefix2_send_idefix_button'].set_sensitive(self.controller.ftp_config is not None)
        self.arw['idefix2_load_idefix_button'].set_sensitive(self.controller.ftp_config is not None)

    def idefix2_load_template(self, *args):
        dialog = Gtk.FileChooserDialog(
            _("Open Template"),
            self.arw['idefix2_config_window'],
            Gtk.FileChooserAction.OPEN,
            (_("Cancel"), Gtk.ResponseType.CLOSE, _("Open"), Gtk.ResponseType.ACCEPT),
        )
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern('*.json')
        dialog.set_filter(file_filter)

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            with open(dialog.get_filename(), 'r', encoding='utf-8-sig', newline='\n') as f:
                self.config = json.load(f, object_pairs_hook=OrderedDict)
            self.set_text_values()
        dialog.destroy()

    def set_text_values(self):
        """Sets the gui entry values based on the config dict"""
        self.block_signals = True
        self.arw['idefix2_wan_ip'].set_text(self.config['eth0']['wan_ip'])
        self.arw['idefix2_wan_subnet'].set_text(self.config['eth0']['wan_netmask'])
        self.arw['idefix2_wan_gateway'].set_text(self.config['eth0']['wan_gateway'])
        for item in self.arw['idefix2_wan_type_store']:
            if item[1] == self.config['eth0']['wan_ip_type']:
                self.arw['idefix2_wan_type'].set_active_iter(item.iter)
                break

        self.arw['idefix2_wan_port'].set_text(self.config.get('ports', {}).get('wan_port', ''))

        self.arw['idefix2_lan_ports'].set_text(self.config.get('ports', {}).get('lan_ports', ''))
        self.arw['idefix2_lan_ip'].set_text(self.config['eth1']['lan_ip'])
        self.arw['idefix2_lan_subnet'].set_text(self.config['eth1']['lan_netmask'])

        self.arw['idefix2_wifi_port'].set_text(self.config.get('ports', {}).get('wifi_port', ''))
        self.arw['idefix2_wifi_ip'].set_text(self.config.get('wlan0', {}).get('wifi_ip', ''))
        self.arw['idefix2_wifi_subnet'].set_text(self.config.get('wlan0', {}).get('wifi_netmask', ''))

        self.arw['idefix2_dhcp_start'].set_text(self.config['dhcp'].get('dhcp_begin', ''))
        self.arw['idefix2_dhcp_end'].set_text(self.config['dhcp'].get('dhcp_end', ''))
        self.arw['idefix2_dhcpwifi_start'].set_text(self.config['dhcp'].get('wifi_dhcp_begin', ''))
        self.arw['idefix2_dhcpwifi_end'].set_text(self.config['dhcp'].get('wifi_dhcp_end', ''))

        self.arw['idefix2_ftp_host'].set_text(self.config['ftp']['ftp'])
        self.arw['idefix2_ftp_username'].set_text(self.config['ftp']['login'])
        self.arw['idefix2_ftp_password'].set_text(self.config['ftp']['password'])

        self.arw['idefix2_dns_ns1'].set_text(self.config['dns']['dns_nameserver1'])
        self.arw['idefix2_dns_ns2'].set_text(self.config['dns']['dns_nameserver2'])
        for item in self.arw['idefix2_dns_type_store']:
            if item[1] == self.config['dns']['dns_filtering']:
                self.arw['idefix2_dns'].set_active_iter(item.iter)
                break

        self.arw['idefix2_dd_login'].set_text(self.config['ddclient']['ddclient_login'])
        self.arw['idefix2_dd_password'].set_text(self.config['ddclient']['ddclient_password'])
        self.arw['idefix2_dd_domain'].set_text(self.config['ddclient']['ddclient_domain'])
        for item in self.arw['idefix2_dd_type_store']:
            if item[1] == self.config['ddclient']['ip_type']:
                self.arw['idefix2_dd_type'].set_active_iter(item.iter)
                break

        for item in self.arw['idefix2_dd_handler_store']:
            if item[1] == self.config['ddclient']['dyn_ip_handler']:
                self.arw['idefix2_dd_handler'].set_active_iter(item.iter)
                break

        self.block_signals = False
        self.idefix2_entry_changed()

    def idefix2_entry_changed(self, *args):
        """Recalculate the configuration"""
        if self.block_signals:
            return

        if 'ports' not in self.config:
            self.config['ports'] = {}

        self.config['ports']['wan_port'] = self.arw['idefix2_wan_port'].get_text()
        self.config['ports']['lan_ports'] = self.arw['idefix2_lan_ports'].get_text()
        self.config['ports']['wifi_port'] = self.arw['idefix2_wifi_port'].get_text()

        iter = self.arw['idefix2_wan_type'].get_active_iter()
        self.config['eth0']['wan_ip_type'] = self.arw['idefix2_wan_type_store'].get_value(iter, 1)
        if self.arw['idefix2_wan_type_store'].get_value(iter, 1) == 'dhcp':
            self.arw['idefix2_wan_ip'].set_text('')
            self.arw['idefix2_wan_ip'].set_sensitive(False)
            self.arw['idefix2_wan_subnet'].set_text('')
            self.arw['idefix2_wan_subnet'].set_sensitive(False)
            self.arw['idefix2_wan_gateway'].set_text('')
            self.arw['idefix2_wan_gateway'].set_sensitive(False)
            self.config['eth0'] = {
                'wan_ip_type': 'dhcp',
                'wan_ip': '',
                'wan_subnet': '',
                'wan_netmask': '',
                'wan_broadcast': '',
                'wan_gateway': '',
                'wan_network': '',
            }
        else:
            self.arw['idefix2_wan_ip'].set_sensitive(True)
            self.arw['idefix2_wan_gateway'].set_sensitive(True)
            self.arw['idefix2_wan_subnet'].set_sensitive(True)
            self.recalculate_ip_settings('eth0', 'wan')

        if self.arw['idefix2_lan_ports'].get_text():
            self.arw['idefix2_lan_ip'].set_sensitive(True)
            self.arw['idefix2_lan_subnet'].set_sensitive(True)
            self.arw['idefix2_dhcp_start'].set_sensitive(True)
            self.arw['idefix2_dhcp_end'].set_sensitive(True)
            if 'eth1' not in self.config:
                self.config['eth1'] = {}
            self.config['eth1']['lan_used'] = 'yes'
            self.recalculate_ip_settings('eth1', 'lan')
        else:
            self.arw['idefix2_lan_ip'].set_sensitive(False)
            self.arw['idefix2_lan_ip'].set_text('')
            self.arw['idefix2_lan_subnet'].set_text('')
            self.arw['idefix2_lan_subnet'].set_sensitive(False)
            self.arw['idefix2_dhcp_start'].set_sensitive(False)
            self.arw['idefix2_dhcp_end'].set_sensitive(False)
            self.config['eth1'] = {
                'lan_used': 'no',
                'lan_ip': '',
                'lan_subnet': '',
                'lan_netmask': '',
                'lan_broadcast': '',
                'lan_network': '',
            }

        if self.arw['idefix2_wifi_port'].get_text():
            self.arw['idefix2_wifi_ip'].set_sensitive(True)
            self.arw['idefix2_wifi_subnet'].set_sensitive(True)
            self.arw['idefix2_dhcpwifi_start'].set_sensitive(True)
            self.arw['idefix2_dhcpwifi_end'].set_sensitive(True)
            if 'wlan0' not in self.config:
                self.config['wlan0'] = {}
            self.config['wlan0']['wifi_used'] = 'yes'
            self.recalculate_ip_settings('wlan0', 'wifi')
        else:
            self.arw['idefix2_dhcpwifi_start'].set_sensitive(False)
            self.arw['idefix2_dhcpwifi_end'].set_sensitive(False)
            self.arw['idefix2_wifi_ip'].set_sensitive(False)
            self.arw['idefix2_wifi_ip'].set_text('')
            self.arw['idefix2_wifi_subnet'].set_text('')
            self.arw['idefix2_wifi_subnet'].set_sensitive(False)
            self.config['wlan0'] = {
                'wifi_used': 'no',
                'wifi_ip': '',
                'wifi_subnet': '',
                'wifi_netmask': '',
                'wifi_network': '',
                'wifi_broadcast': '',
            }

        self.recalculate_dhcp()
        self.recalculate_ftp()
        self.recalculate_dns()
        self.recalculate_ddclient()

    def recalculate_ftp(self):
        ftp_host = self.arw['idefix2_ftp_host'].get_text()
        ftp_username = self.arw['idefix2_ftp_username'].get_text()
        ftp_password = self.arw['idefix2_ftp_password'].get_text()
        self.config['ftp'] = {
            'effacement': 'false',
            'ftp': ftp_host,
            'login': ftp_username,
            'password': ftp_password
        }

    def recalculate_dhcp(self):
        try:
            start_ip = ipaddress.IPv4Address(self.arw['idefix2_dhcp_start'].get_text())
            self.config['dhcp']['dhcp_begin'] = str(start_ip)
        except ipaddress.AddressValueError:
            self.arw['idefix2_dhcp_start'].set_text('')
            self.config['dhcp']['dhcp_begin'] = ''

        try:
            end_ip = ipaddress.IPv4Address(self.arw['idefix2_dhcp_end'].get_text())
            self.config['dhcp']['dhcp_end'] = str(end_ip)
        except ipaddress.AddressValueError:
            self.arw['idefix2_dhcp_end'].set_text('')
            self.config['dhcp']['dhcp_end'] = ''

        try:
            start_ip_wifi = ipaddress.IPv4Address(self.arw['idefix2_dhcpwifi_start'].get_text())
            self.config['dhcp']['wifi_dhcp_begin'] = str(start_ip_wifi)
        except ipaddress.AddressValueError:
            self.arw['idefix2_dhcpwifi_start'].set_text('')
            self.config['dhcp']['wifi_dhcp_begin'] = ''

        try:
            end_ip_wifi = ipaddress.IPv4Address(self.arw['idefix2_dhcpwifi_end'].get_text())
            self.config['dhcp']['wifi_dhcp_end'] = str(end_ip_wifi)
        except ipaddress.AddressValueError:
            self.arw['idefix2_dhcpwifi_end'].set_text('')
            self.config['dhcp']['wifi_dhcp_end'] = ''

    def recalculate_ip_settings(self, interface='eth0', type='wan'):
        ip = '0.0.0.0'
        try:
            ip = ipaddress.IPv4Address(self.arw['idefix2_' + type + '_ip'].get_text())
        except ipaddress.AddressValueError:
            self.arw['idefix2_' + type + '_ip'].set_text('')
        self.config[interface][type + '_ip'] = str(ip)

        subnet = '255.255.255.0'
        try:
            subnet = ipaddress.IPv4Address(self.arw['idefix2_' + type + '_subnet'].get_text())
        except ipaddress.AddressValueError:
            self.arw['idefix2_' + type + '_subnet'].set_text('')

        if type == 'wan':
            gateway = ''
            try:
                gateway = ipaddress.IPv4Address(self.arw['idefix2_' + type + '_gateway'].get_text())
            except ipaddress.AddressValueError:
                self.arw['idefix2_' + type + '_gateway'].set_text('')
            self.config[interface][type + '_gateway'] = str(gateway)

        network = ipaddress.IPv4Interface(str(ip) + '/' + str(subnet))
        self.config[interface][type + '_netmask'] = str(network.netmask)
        self.config[interface][type + '_subnet'] = str(network.network)
        self.config[interface][type + '_network'] = str(network.network.network_address)
        self.config[interface][type + '_broadcast'] = str(network.network.broadcast_address)

    def recalculate_dns(self):
        iter = self.arw['idefix2_dns'].get_active_iter()
        if iter:
            dns_type = self.arw['idefix2_dns_type_store'].get_value(iter, 1)
        else:
            dns_type = 'SafeDNS'

        if dns_type != self.config['dns']['dns_filtering']:
            dns = self.dns_options.get(dns_type, {})
            self.arw['idefix2_dns_ns1'].set_text(dns.get('ns1', ''))
            self.arw['idefix2_dns_ns2'].set_text(dns.get('ns2', ''))
            self.config['dns'] = {
                'dns_filtering': dns.get('value', dns_type),
                'dns_nameserver1': dns.get('ns1', ''),
                'dns_nameserver2': dns.get('ns2', ''),
            }
        else:
            ns1 = ''
            try:
                ns1 = ipaddress.IPv4Address(self.arw['idefix2_dns_ns1'].get_text())
            except ipaddress.AddressValueError:
                self.arw['idefix2_dns_ns1'].set_text('')

            ns2 = ''
            try:
                ns2 = ipaddress.IPv4Address(self.arw['idefix2_dns_ns2'].get_text())
            except ipaddress.AddressValueError:
                self.arw['idefix2_dns_ns2'].set_text('')

            self.config['dns']['dns_nameserver1'] = str(ns1)
            self.config['dns']['dns_nameserver2'] = str(ns2)

    def recalculate_ddclient(self):
        iter = self.arw['idefix2_dd_type'].get_active_iter()
        if iter:
            dd_type = self.arw['idefix2_dd_type_store'].get_value(iter, 1)
        else:
            dd_type = 'dynamic'

        iter = self.arw['idefix2_dd_handler'].get_active_iter()
        if iter:
            dd_handler = self.arw['idefix2_dd_handler_store'].get_value(iter, 1)
        else:
            dd_handler = 'None'

        if dd_handler == 'auto':
            if self.arw['idefix2_ddclient_auto_config_checkbox'].get_active():
                self.arw['idefix2_dd_login'].set_sensitive(True)
                self.arw['idefix2_dd_password'].set_sensitive(True)
                self.arw['idefix2_dd_domain'].set_sensitive(True)
                self.arw['idefix2_dd_handler'].set_sensitive(True)
            else:
                self.arw['idefix2_dd_login'].set_sensitive(False)
                self.arw['idefix2_dd_password'].set_sensitive(False)
                self.arw['idefix2_dd_domain'].set_sensitive(False)
                self.arw['idefix2_dd_type'].set_sensitive(False)
        else:
            self.arw['idefix2_dd_type'].set_sensitive(True)

            if dd_type == 'static':
                self.config['ddclient'] = {
                    'ip_type': 'static',
                    'dyn_ip_handler': '',
                    'ddclient_login': '',
                    'ddclient_password': '',
                    'ddclient_domain': '',
                    'ddclient_server': '',
                    'ddclient_web': '',
                    'protocol': ''
                }
                self.arw['idefix2_dd_login'].set_sensitive(False)
                self.arw['idefix2_dd_password'].set_sensitive(False)
                self.arw['idefix2_dd_domain'].set_sensitive(False)
                return
            else:
                self.arw['idefix2_dd_login'].set_sensitive(True)
                self.arw['idefix2_dd_password'].set_sensitive(True)
                self.arw['idefix2_dd_domain'].set_sensitive(True)

        dd = self.ddclient_options.get(dd_handler, {})

        if self.arw['idefix2_ddclient_auto_config_checkbox'].get_active():
            self.autoddclient_config = {
                'ddclient_login': self.arw['idefix2_dd_login'].get_text(),
                'ddclient_password': self.arw['idefix2_dd_password'].get_text(),
                'ddclient_domain': self.arw['idefix2_dd_domain'].get_text(),
                'ddclient_server': dd.get('server', ''),
                'ddclient_web': dd.get('web', ''),
                'protocol': dd.get('protocol', '')
            }
            self.config['ddclient'] = {
                'ip_type': 'dynamic',
                'dyn_ip_handler': 'auto',
                'ddclient_login': '',
                'ddclient_password': '',
                'ddclient_domain': '',
                'ddclient_server': '',
                'ddclient_web': '',
                'protocol': ''
            }
        else:
            self.autoddclient_config = None
            self.config['ddclient'] = {
                'ip_type': 'dynamic',
                'dyn_ip_handler': dd_handler,
                'ddclient_login': self.arw['idefix2_dd_login'].get_text(),
                'ddclient_password': self.arw['idefix2_dd_password'].get_text(),
                'ddclient_domain': self.arw['idefix2_dd_domain'].get_text(),
                'ddclient_server': dd.get('server', ''),
                'ddclient_web': dd.get('web', ''),
                'protocol': dd.get('protocol', '')
            }

    def validate_config(self):
        """Validate that the config makes sense"""
        # Check WAN settings make sense

        if self.config['eth1'].get('lan_used', 'yes') == 'yes':
            try:
                lan_ip = ipaddress.IPv4Address(self.config['eth1']['lan_ip'])
            except ipaddress.AddressValueError:
                alert(_("LAN IP invalid"))
                return
        else:
            lan_ip = None

        if self.config['wlan0']['wifi_used'] == 'yes':
            try:
                wlan_ip = ipaddress.IPv4Address(self.config['wlan0']['wifi_ip'])
            except ipaddress.AddressValueError:
                alert(_("WAN IP invalid"))
                return
        else:
            wlan_ip = None

        if self.config['eth0']['wan_ip_type'] != 'dhcp':
            wan = ipaddress.IPv4Network(self.config['eth0']['wan_subnet'])
            wan_ip = ipaddress.IPv4Address(self.config['eth0']['wan_ip'])
            if wan.is_unspecified or wan_ip.is_unspecified:
                alert(_("WAN IP must be set"))
                return

            if wan_ip not in wan:
                alert(_("WAN IP address must be in WAN network"))
                return

            try:
                wan_gateway = ipaddress.IPv4Address(self.config['eth0']['wan_gateway'])
            except ipaddress.AddressValueError:
                alert(_("WAN Gateway cannot be blank"))
                return

            if wan_gateway not in wan:
                alert(_("WAN Gateway must be in the WAN network"))
                return

            if lan_ip and lan_ip in wan:
                alert(_("LAN must be in a different network to WAN"))
                return

            if wlan_ip and wlan_ip in wan:
                alert(_("WLAN must be in a different network to WAN"))
                return

        # Check LAN settings make sense
        if lan_ip:
            lan = ipaddress.IPv4Network(self.config['eth1']['lan_subnet'])

            if lan_ip.is_unspecified or lan.is_unspecified:
                alert(_("LAN IP must be set"))
                return

            if lan_ip not in lan:
                alert(_("LAN IP address must be in LAN network"))
                return

        # Check WLAN settings make sense
        if wlan_ip:
            wlan = ipaddress.IPv4Network(self.config['wlan0']['wifi_subnet'])

            if wlan_ip.is_unspecified or wlan.is_unspecified:
                alert(_("WLAN IP must be set"))
                return

            if wlan_ip not in wlan:
                alert(_("WLAN IP address must be in WLAN network"))
                return

        if not lan_ip and not wlan_ip:
            alert(_("Either LAN or WLAN must be enabled"))
            return

        # Check DHCP settings make sense
        if lan_ip:
            try:
                dhcp_start = ipaddress.IPv4Address(self.config['dhcp']['dhcp_begin'])
                dhcp_end = ipaddress.IPv4Address(self.config['dhcp']['dhcp_end'])
            except ipaddress.AddressValueError:
                dhcp_start = None
                dhcp_end = None
            if not dhcp_start or not dhcp_end:
                alert(_("LAN DHCP range must be set"))
                return

            if dhcp_start > dhcp_end:
                alert(_("LAN DHCP Range invalid"))
                return

        if wlan_ip:
            try:
                dhcp_start = ipaddress.IPv4Address(self.config['dhcp']['wifi_dhcp_begin'])
                dhcp_end = ipaddress.IPv4Address(self.config['dhcp']['wifi_dhcp_begin'])
            except ipaddress.AddressValueError:
                dhcp_start = None
                dhcp_end = None

            if not dhcp_start or not dhcp_end:
                alert(_("WLAN DHCP range must be set"))
                return

            if dhcp_start > dhcp_end:
                alert(_("WLAN DHCP Range invalid"))
                return

        if not self.config['ftp']['ftp']:
            alert(_("No FTP Settings"))
            return

        if self.arw['idefix2_ddclient_auto_config_checkbox'].get_active():
            dd_iter = self.arw['idefix2_dd_handler'].get_active_iter()
            if not dd_iter:
                alert(_("DDclient handler must be set for automatic configuration"))
                return
            value = self.arw['idefix2_dd_handler'].get_model().get_value(dd_iter, 1)
            if value in ['auto', 'None']:
                alert(_("DDClient handler must be set for automatic configuration"))
                return

        return True

    def idefix2_create_config(self, *args):
        if not self.validate_config():
            return

        dialog = Gtk.FileChooserDialog(
            _("Export Configuration"),
            self.arw['idefix2_config_window'],
            Gtk.FileChooserAction.SAVE,
            (_("Cancel"), Gtk.ResponseType.CLOSE, _("Export"), Gtk.ResponseType.ACCEPT)
        )
        dialog.set_current_name('idefix2_config.json')
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern('*.json')
        dialog.set_filter(file_filter)

        dialog.show_all()
        response = dialog.run()

        if 'ddclient_options' in self.config:
            del self.config['ddclient_options']

        if response == Gtk.ResponseType.ACCEPT:
            with open(dialog.get_filename(), 'w', encoding='utf-8-sig', newline='\n') as f:
                json.dump(self.config, f, indent=3)
            self.arw['idefix2_config_window'].hide()

            if self.autoddclient_config:
                dialog.destroy()
                dialog = Gtk.FileChooserDialog(
                    _("Export Auto DDClient Configuration"),
                    self.arw['idefix2_config_window'],
                    Gtk.FileChooserAction.SAVE,
                    (_("Cancel"), Gtk.ResponseType.CLOSE, _("Export"), Gtk.ResponseType.ACCEPT)
                )
                dialog.set_current_name('idefix_auto.conf')
                file_filter = Gtk.FileFilter()
                file_filter.add_pattern('*.conf')
                dialog.set_filter(file_filter)

                dialog.show_all()
                response = dialog.run()
                if response == Gtk.ResponseType.ACCEPT:
                    conf = self.get_auto_ddclient_config()
                    with open(dialog.get_filename(), 'w', encoding='utf-8-sig', newline='\n') as f:
                        f.write(conf)
                    self.arw['idefix2_config_window'].hide()

        dialog.destroy()

    def get_auto_ddclient_config(self):
        if not self.autoddclient_config:
            return ''

        parser = configparser.RawConfigParser()
        parser.add_section('default')
        parser['default'] = self.autoddclient_config
        data = ''
        with StringIO() as f:
            parser.write(f)
            f.seek(0)
            data = f.read()
        return '\n'.join(data.split('\n')[1:])

    def idefix2_test_ftp(self, *args):
        valid = ftp_connect(self.config['ftp']['ftp'], self.config['ftp']['login'], self.config['ftp']['password'])
        if not valid:
            alert(_("Could not conect to FTP"))
        else:
            showwarning(_("Test FTP"), _("FTP Connection Success"), 5)

    def idefix2_close_window(self, *args):
        self.arw['idefix2_config_window'].hide()

    def idefix2_load_from_idefix(self, widget=None):
        """Load configuration from idefix (if connected)"""
        data = self.controller.information.get_infos('get_conf')
        conf_list = json.loads(data, object_pairs_hook=OrderedDict)
        if 'idefix2_conf.json' not in conf_list:
            alert(_("No idefix2 config found"))
            return
        self.config = json.loads(conf_list['idefix2_conf.json'], object_pairs_hook=OrderedDict)
        self.set_text_values()

    def idefix2_send_config(self, widget=None):
        """Send configuration to idefix (if connected)"""
        if not self.validate_config():
            return

        auto_conf = None
        if self.autoddclient_config:
            auto_conf = self.get_auto_ddclient_config()

        if 'ddclient_options' in self.config:
            del self.config['ddclient_options']

        self.controller.restore_dialog.import_network(json.dumps(self.config, indent=3), auto_conf)
        alert(_("Sent configuration to idefix"))

    def idefix2_load_default(self, widget=None):
        """Load default configuration from 'defaults' directory"""
        with open('defaults/idefix2_conf.json', 'r') as f:
            self.config = json.load(f, object_pairs_hook=OrderedDict)
        self.set_text_values()

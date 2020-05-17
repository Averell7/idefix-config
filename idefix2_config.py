import json

from gi.repository import Gtk
import ipaddress

from ftp_client import ftp_connect
from util import alert, showwarning

DD_HANDLERS = [
    {
        'name': _('Automatic'),
        'value': 'automatic',
        'server': '',
        'web': '',
        'protocol': '',
    },
    {
        'name': _('NoIP'),
        'value': 'NoIP',
        'server': '',
        'web': '',
        'protocol': '',
    },
    {
        'name': _('SafeDNS'),
        'value': 'SafeDNS',
        'server': 'www.safedns.com',
        'web': 'http://www.safedns.com/nic/myip',
        'protocol': 'dyndns2',
    },
    {
        'name': _('Aucun'),
        'value': 'Aucun',
        'server': '',
        'web': '',
        'protocol': '',
    },
]

DNS_TYPES = [
    {
        'name': _('Automatic'),
        'value': 'automatic',
        'ns1': '',
        'ns2': ''
    },
    {
        'name': _('SafeDNS'),
        'value': 'SafeDNS',
        'ns1': '195.46.39.39',
        'ns2': '195.36.39.40'
    },
    {
        'name': _('OpenDNS'),
        'value': 'OpenDNS',
        'ns1': '208.67.222.222',
        'ns2': '208.67.222.220'
    },
    {
        'name': _('Autre'),
        'value': 'Autre',
        'ns1': '',
        'ns2': ''
    },
    {
        'name': _('Aucun'),
        'value': 'Aucun',
        'ns1': '1.1.1.1',
        'ns2': '8.8.8.8'
    },
]


def get_by_value(options, value):
    for opt in options:
        if opt['value'] == value:
            return opt
    return None


class Idefix2Config:
    def __init__(self, arw, controller):
        self.arw = arw
        self.controller = controller
        self.config = {}
        self.block_signals = False
        for type in DNS_TYPES:
            self.arw['idefix2_dns_type_store'].append((type['name'], type['value']))
        for type in DD_HANDLERS:
            self.arw['idefix2_dd_handler_store'].append((type['name'], type['value']))

    def idefix2_show_config(self, *args):
        """Load default configuration"""
        self.config = {
            "general": {
                "idefix_id": "version 2.4.0"
            },
            "eth0": {
                "wan_ip_type": "dhcp",
                "wan_ip": "10.10.10.11",
                "wan_netmask": "255.255.252.0",
                "wan_subnet": "10.10.8.0/22",
                "wan_network": "10.10.8.0",
                "wan_broadcast": "10.10.11.255",
                "wan_gateway": "10.10.10.100"
            },
            "eth1": {
                "lan_ip": "192.168.84.184",
                "lan_netmask": "255.255.255.0",
                "lan_subnet": "192.168.84.0/24",
                "lan_network": "192.168.84.0",
                "lan_broadcast": "192.168.84.255"
            },
            "wlan0": {
                "wifi_used": "yes",
                "wifi_ip": "10.10.84.1",
                "wifi_netmask": "255.255.255.0",
                "wifi_subnet": "10.10.84.0/24",
                "wifi_network": "10.10.84.0",
                "wifi_broadcast": "10.10.84.255"
            },
            "dhcp": {
                "dhcp_begin": "192.168.84.200",
                "dhcp_end": "192.168.84.253"
            },
            "ftp": {
                "effacement": "false",
                "ftp": "ftp.online.net",
                "login": "",
                "password": ""
            },
            "dns": {
                "dns_filtering": "SafeDNS",
                "dns_nameserver1": "195.46.39.39",
                "dns_nameserver2": "195.46.39.40"
            },
            "ddclient": {
                "ip_type": "dynamic",
                "dyn_ip_handler": "SafeDNS",
                "ddclient_login": "",
                "ddclient_password": "",
                "ddclient_domain": "",
                "ddclient_server": "www.safedns.com",
                "ddclient_web": "http://www.safedns.com/nic/myip",
                "protocol": "dyndns2"
            }
        }
        self.set_text_values()
        self.arw['idefix2_config_window'].show_all()

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

        self.arw['idefix2_lan_ip'].set_text(self.config['eth1']['lan_ip'])
        self.arw['idefix2_lan_subnet'].set_text(self.config['eth1']['lan_netmask'])

        self.arw['idefix2_wifi_enabled'].set_active(self.config['wlan0']['wifi_used'] == 'yes')
        self.arw['idefix2_wifi_ip'].set_text(self.config['wlan0']['wifi_ip'])
        self.arw['idefix2_wifi_subnet'].set_text(self.config['wlan0']['wifi_netmask'])

        self.arw['idefix2_dhcp_start'].set_text(self.config['dhcp']['dhcp_begin'])
        self.arw['idefix2_dhcp_end'].set_text(self.config['dhcp']['dhcp_end'])

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
            }
        else:
            self.arw['idefix2_wan_ip'].set_sensitive(True)
            self.arw['idefix2_wan_gateway'].set_sensitive(True)
            self.arw['idefix2_wan_subnet'].set_sensitive(True)
            self.recalculate_ip_settings('eth0', 'wan')

        self.recalculate_ip_settings('eth1', 'lan')

        if self.arw['idefix2_wifi_enabled'].get_active():
            self.arw['idefix2_wifi_ip'].set_sensitive(True)
            self.arw['idefix2_wifi_subnet'].set_sensitive(True)
            self.config['wlan0']['wifi_used'] = 'yes'
            self.recalculate_ip_settings('wlan0', 'wifi')
        else:
            self.arw['idefix2_wifi_ip'].set_sensitive(False)
            self.arw['idefix2_wifi_ip'].set_text('')
            self.arw['idefix2_wifi_subnet'].set_text('')
            self.arw['idefix2_wifi_subnet'].set_sensitive(False)
            self.config['wlan0'] = {
                'wifi_used': '',
                'wifi_ip': '',
                'wifi_subnet': '',
                'wifi_netmask': '',
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
        start_ip = ''
        try:
            start_ip = ipaddress.IPv4Address(self.arw['idefix2_dhcp_start'].get_text())
            self.config['dhcp']['dhcp_begin'] = str(start_ip)
        except ipaddress.AddressValueError:
            self.arw['idefix2_dhcp_start'].set_text('')
            self.config['dhcp']['dhcp_begin'] = ''

        end_ip = ''
        try:
            end_ip = ipaddress.IPv4Address(self.arw['idefix2_dhcp_end'].get_text())
            self.config['dhcp']['dhcp_end'] = str(end_ip)
        except ipaddress.AddressValueError:
            self.arw['idefix2_dhcp_end'].set_text('')
            self.config['dhcp']['dhcp_end'] = ''

        if not start_ip or not end_ip:
            return

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
        self.config[interface][type + '_broadcast'] = str(network.network.broadcast_address)

    def recalculate_dns(self):
        iter = self.arw['idefix2_dns'].get_active_iter()
        if iter:
            dns_type = self.arw['idefix2_dns_type_store'].get_value(iter, 1)
        else:
            dns_type = 'SafeDNS'

        if dns_type != self.config['dns']['dns_filtering']:
            dns = get_by_value(DNS_TYPES, dns_type)
            self.arw['idefix2_dns_ns1'].set_text(dns['ns1'])
            self.arw['idefix2_dns_ns2'].set_text(dns['ns2'])
            self.config['dns'] = {
                'dns_filtering': dns['value'],
                'dns_nameserver1': dns['ns1'],
                'dns_nameserver2': dns['ns2'],
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

            self.config['dns']['ns1'] = str(ns1)
            self.config['dns']['ns2'] = str(ns2)

    def recalculate_ddclient(self):
        iter = self.arw['idefix2_dd_type'].get_active_iter()
        if iter:
            dd_type = self.arw['idefix2_dd_type_store'].get_value(iter, 1)
        else:
            dd_type = 'dynamic'

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

        self.arw['idefix2_dd_login'].set_sensitive(True)
        self.arw['idefix2_dd_password'].set_sensitive(True)
        self.arw['idefix2_dd_domain'].set_sensitive(True)

        iter = self.arw['idefix2_dd_handler'].get_active_iter()
        if iter:
            dd_handler = self.arw['idefix2_dd_handler_store'].get_value(iter, 1)
        else:
            dd_handler = 'SafeDNS'

        dd = get_by_value(DD_HANDLERS, dd_handler)

        self.config['ddclient'] = {
            'ip_type': 'dynamic',
            'dyn_ip_handler': dd_handler,
            'ddclient_login': self.arw['idefix2_dd_login'].get_text(),
            'ddclient_password': self.arw['idefix2_dd_password'].get_text(),
            'ddclient_domain': self.arw['idefix2_dd_domain'].get_text(),
            'ddclient_server': dd['server'],
            'ddclient_web': dd['web'],
            'protocol': dd['protocol']
        }

    def validate_config(self):
        """Validate that the config makes sense"""
        # Check WAN settings make sense

        try:
            lan_ip = ipaddress.IPv4Address(self.config['eth1']['lan_ip'])
        except ipaddress.AddressValueError:
            alert(_("LAN IP invalid"))
            return

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

            if lan_ip in wan:
                alert(_("LAN must be in a different network to WAN"))
                return

            if self.config['wlan0']['wifi_used'] == 'yes':
                if wlan_ip in wan:
                    alert(_("WLAN must be in a different network to WAN"))
                    return

        # Check LAN settings make sense
        lan = ipaddress.IPv4Network(self.config['eth1']['lan_subnet'])

        if lan_ip.is_unspecified or lan.is_unspecified:
            alert(_("LAN IP must be set"))

        if lan_ip not in lan:
            alert(_("LAN IP address must be in LAN network"))
            return

        # Check WLAN settings make sense
        if self.config['wlan0']['wifi_used'] == 'yes':
            wlan = ipaddress.IPv4Network(self.config['wlan0']['wifi_subnet'])

            if not wlan_ip or not wlan:
                alert(_("WLAN IP must be set"))

            if wlan_ip not in wlan:
                alert(_("WLAN IP address must be in WLAN network"))
                return

        # Check DHCP settings make sense
        dhcp_start = ipaddress.IPv4Address(self.config['dhcp']['dhcp_begin'])
        dhcp_end = ipaddress.IPv4Address(self.config['dhcp']['dhcp_end'])
        if not dhcp_start or not dhcp_end:
            alert(_("DHCP range must be set"))
            return

        if dhcp_start > dhcp_end:
            alert(_("DHCP Range invalid"))
            return

        return True

    def idefix2_create_config(self, *args):
        if not self.validate_config():
            return

        dialog = Gtk.FileChooserDialog(
            _("Export Configuration"),
            self.arw['idefix2_config_window'],
            Gtk.FileChooserAction.SAVE,
            (_("Export"), Gtk.ResponseType.ACCEPT),
        )
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern('*.json')
        dialog.set_filter(file_filter)

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            with open(dialog.get_filename(), 'w', encoding='utf-8-sig', newline='\n') as f:
                json.dump(self.config, f, indent=3)
            self.arw['idefix2_config_window'].hide()

        dialog.destroy()

    def idefix2_test_ftp(self, *args):
        valid = ftp_connect(self.config['ftp']['ftp'], self.config['ftp']['login'], self.config['ftp']['password'])
        if not valid:
            alert(_("Could not conect to FTP"))
        else:
            showwarning(_("Test FTP"), _("FTP Connection Success"), 5)

    def idefix2_close_window(self, *args):
        self.arw['idefix2_config_window'].hide()

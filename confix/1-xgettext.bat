echo off

rem génération de confix.pot
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 confix.py 
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j actions.py assistant.py config_profile.py confix.py 
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -jconnection_information.py Create_rescue.py domain_util.py filter_rules.py
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j firewall.py ftp_client.py http_client.py  
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j groups_manager.py icons.py idefix2_config.py json_config.py
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j proxy_group.py repository.py
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j services.py users.py util.py verify_versions.py
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j -L Glade confix.glade 
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j -L Glade assistant.glade
c:\prog2\gettext014\bin\xgettext.exe -o confix.pot --from-code=UTF-8 -j -L Glade groups_manager.glade


pause






@echo off
echo Adding firewall rule for port 80...
netsh advfirewall firewall add rule name="HTTP 80 for Rails" dir=in action=allow protocol=TCP localport=80
echo Firewall rule has been added.

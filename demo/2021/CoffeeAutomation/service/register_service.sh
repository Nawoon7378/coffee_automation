ServiceName=coffee_automation_service

echo Enter the password:
read varpw

echo $varpw | sudo -kS touch /etc/sudoers.d/user
# { echo $varpw; echo -e "user ALL=(ALL) NOPASSWD:/sbin/ifup, /sbin/ifdown, /sbin/service isc-dhcp-server restart\n"; } | sudo -kS tee -a /etc/sudoers.d/user

echo $varpw | sudo -kS cp $ServiceName\_main_script /etc/
echo $varpw | sudo -kS cp $ServiceName /etc/init.d/
echo $varpw | sudo -kS chmod 775 /etc/init.d/$ServiceName
echo $varpw | sudo -kS chmod 775 /etc/$ServiceName\_main_script

echo $varpw | sudo -kS update-rc.d -f $ServiceName remove
echo $varpw | sudo -kS update-rc.d $ServiceName defaults
echo $varpw | sudo -kS service $ServiceName restart

echo -e '\n'


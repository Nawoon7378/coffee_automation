ServiceName=coffee_automation_service

echo Enter the password:
read varpw

echo $varpw | sudo -kS service $ServiceName stop
echo $varpw | sudo -kS update-rc.d -f $ServiceName remove
echo $varpw | sudo -kS rm /etc/$ServiceName\_main_script
echo $varpw | sudo -kS rm /etc/init.d/$ServiceName
echo -e '\n'

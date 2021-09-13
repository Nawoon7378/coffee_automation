#!/bin/bash
ip=`ifconfig|xargs|awk '{print $7}'|sed -e 's/[a-z]*:/''/'`
jupyter notebook --allow-root --ip=$ip --port=8880 --NotebookApp.password="$(echo nrmk2013 | python3 -c 'from notebook.auth import passwd;print(passwd(input()))')" &
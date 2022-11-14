ps -ef | grep python | grep robobits |awk '{print $2}' | xargs kill -9
nohup /usr/bin/python -u /root/robobits/robobits.py > /root/robobits/logs/robo.log &

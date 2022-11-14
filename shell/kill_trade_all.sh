ps -ef | grep python | grep robobits |awk '{print $2}' | xargs kill -9

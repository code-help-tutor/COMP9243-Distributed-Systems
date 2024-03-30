WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
#!/bin/bash
PROCESSES="dsm share matmul";
for i in $(seq -w 0 09);do
    echo "#### vina$i";
    ssh vina$i "ps aux | grep $USER;
    killall -u $USER $PROCESSES";
done

#!/usr/bin/python3
from configparser import ConfigParser
import subprocess
import time
import datetime
import sys


def main():
    d_cmd = 'start'
    if len(sys.argv) > 1:
        d_cmd = sys.argv[1]
    conf_file = 'pycker.conf'
    if len(sys.argv) > 2:
        conf_file = sys.argv[2]
    cfg = ConfigParser()
    cfg.read(conf_file)
    container_intervals = cfg.get('containers', 'container_interval').strip().split('\n') # one docker instance per line
    the_time = datetime.datetime.now()
    print(f'Command: docker {d_cmd} ...')
    print(f'Start at: {the_time}')
    for temp in container_intervals:
        con_int = temp.strip().split(':') # semicolon as separator, example: docker_instance_name:interval_time
        exe_cmd = f'docker {d_cmd} {con_int[0]}'
        subprocess.call(exe_cmd, shell=True)
        print('processing...')
        if d_cmd == 'stop':
            time.sleep(1)
        else:
            time.sleep(int(con_int[1]))
    the_time2 = datetime.datetime.now()
    print(f'End at: {the_time2}; Duration {the_time2 - the_time}')


if __name__ == "__main__":
    main()

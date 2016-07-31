from subprocess import *
import subprocess
from socket import *
import time
import os
import datetime as dt
import threading
import ssl
import sys

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class MyAdapter(HTTPAdapter):

    def init_poolmanager(self, connections, maxsize, block=False):
        ca_certs = "/etc/ssl/certs/ca-certificates.crt"  
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       cert_reqs='CERT_REQUIRED',
                                       ca_certs=ca_certs, 
                                       ssl_version=ssl.PROTOCOL_SSLv3)


http = requests.Session()
http.mount('https://', MyAdapter())


class Timer:

    def __init__(self):
        self.start = dt.datetime.now()

    def __str__(self):
        return str(dt.datetime.now() - self.start)

    def __repr__(self):
        return str(dt.datetime.now() - self.start)


class bgcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def print_info(str):
    sys.stderr.write(bgcolors.HEADER + str + bgcolors.ENDC)


def print_ok(str):
    sys.stderr.write(bgcolors.OKGREEN + str + bgcolors.ENDC)

def print_fail(str):
    sys.stderr.write(bgcolors.FAIL + str + bgcolors.ENDC)


def ping(host, port):
    s = socket(AF_INET, SOCK_STREAM)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception, e:
        s.close()
        return False


def call_async(func, args):
    t = threading.Thread(target=func, args=args)
    t.daemon = True
    t.start()

    def null():
        pass

    return null


def stream_process_results(p, prefix=''):
    out = ""
    while True:
        line = p.stdout.readline()
        if not line:
            p.poll()
            print_info ("[%s] " % prefix)
            print_ok (line + "\n")
            if p.returncode == 0:
                print_info(prefix + " ")
                print_ok("[0]\n")
            else:
                print_info(prefix + " ")
                print_fail("[%s]" % p.returncode + "\n")
            
            print

def print_process_result(p, prefix='',full=False):
    out = ""
    while True:
        line = p.stdout.readline()
        if not line:
            p.poll()
            if p.returncode == 0:
                print_info(prefix + " ")
                print_ok("[0]\n")
                if full:
                    print out
            else:
                print_info(prefix + " ")
                print_fail("[%s]" % p.returncode + "\n")
                print out
            return out
        out += line + "\n"

def print_process(p, prefix=''):  
    while True:
        line = p.stdout.readline()
        if not line:
            p.poll()
            if p.returncode == 0:
                print_info(prefix + " ")
                print_ok("[0]\n")                
            else:
                print_info(prefix + " ")
                print_fail("[%s]" % p.returncode + "\n")           
            return p.returncode
        print line


def print_response(r):
    if r.status_code >= 200 and r.status_code < 300:
        print_ok(str(r.status_code) + "\n")
    else:
        print_fail("[%s]\n %s\n" % (str(r.status_code), r.text))


def http_post(url, data, headers={}, username=None, password=None, **kwargs):
    try:

        print_info(url + " ..  ")
        headers['User-Agent'] = 'Mozilla'
        r = requests.post(url, data=data, verify=False, auth=(username, password), headers=headers, allow_redirects=False, **kwargs)
        if r.status_code > 300 and r.status_code < 400:
            print_ok(" -> " + r.headers['Location'] + "\n")
            return http_post(r.headers['Location'], data=data, headers=headers, username=username, password=password, **kwargs)
        print_response(r)
        return r
    except Exception, e:
        print_fail(str(e))


def http_get(url, data=None, username=None, password=None, **kwargs):
    try:
        print_info(url + " ..  ")

        r = requests.get(url, params=data, verify=False,
                         headers={"User-Agent": 'Mozilla'},
                         auth=(username, password),
                         allow_redirects=False, **kwargs)

        if r.status_code > 300 and r.status_code < 400:
            print_ok(" -> " + r.headers['Location'] + "\n")
            return http_get(r.headers['Location'], data, username, password, **kwargs)

        print_response(r)

        return r
    except Exception, e:
        print_fail(str(e))


def execute(command, async=False,  env=os.environ):
    print_info("executing ")
    print command

    p = Popen(command, stdout=subprocess.PIPE, shell=True, env=os.environ)
    if async:
        call_async(print_process_result, [p, command])
    else:
        return print_process_result(p, command)

def ansible_playbook(playbook, host,hostname,extra_vars=None,group=None,private_key_file=None,remote_user=None):
    print "running play %s on %s" % (playbook, host)
    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
    inventory = ansible.inventory.Inventory([host])
    inventory.get_host(host).set_variable('hostname', hostname)
    inventory.set_playbook_basedir('egis-cloud')
    if group != None:
        print 'adding ' + group
        _group = ansible.inventory.Group(name=group)
        _group.add_host(inventory.get_host(host))
        inventory.add_group(_group)
    pb = ansible.playbook.PlayBook(
        playbook=playbook, 
        inventory=inventory,
        callbacks=playbook_cb,
        runner_callbacks=runner_cb,
        stats=stats,
        extra_vars=extra_vars
    )

    if private_key_file != None:
        pb.private_key_file = private_key_file
    if remote_user != None:
        pb.remote_user = remote_user

    pb.run()

        


def wait(condition, sleep=1):
    result = condition()
    while result == False:
        result = condition()
        time.sleep(sleep)

def async(func, args):
    t = threading.Thread(target=func,args=args)
    t.daemon = True
    t.start()

    def null(args):
        pass

    return null
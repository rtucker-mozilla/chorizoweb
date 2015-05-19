#!/usr/bin/env python
import sys
sys.path.append("..")

import puka
import time
import datetime
import hashlib
import collections
import json
import os

from flask.ext.script import Manager
from moz_au_web.app import create_app
from threading import Thread
from moz_au_web.settings import ProdConfig, DevConfig
from moz_au_web.system.models import System, SystemUpdate, SystemUpdateLog, SystemPing
from moz_au_web.database import db
from celery_tasks import async_pong

ENV = os.environ.get('ENV', False)
if ENV == 'DEV':
    config_object = DevConfig
else:
    config_object = ProdConfig

app = create_app(DevConfig)

manager = Manager(app)

AMQP_URL = app.config.get("AMQP_URL", "amqp://127.0.0.1/")
print AMQP_URL
EXCHANGE='chorizo'
QUEUE_CNT = 32
BURST_SIZE = 120
QUEUE_SIZE = 1000
BODY_SIZE = 1
PREFETCH_CNT = 1
MSG_HEADERS = {'persistent': False}
PUBACKS = False
running_updates = {}

counter = 0
counter_t0 = time.time()

class AsyncGeneratorState(object):
    def __init__(self, client, gen):
        self.gen = gen
        self.client = client
        self.promises = collections.defaultdict(list)

        self.waiting_for = self.gen.next()
        self.client.set_callback(self.waiting_for, self.callback_wrapper)

    def callback_wrapper(self, t, result):
        self.promises[t].append(result)
        while self.waiting_for in self.promises:
            result = self.promises[self.waiting_for].pop(0)
            if not self.promises[self.waiting_for]:
                del self.promises[self.waiting_for]
            self.waiting_for = self.gen.send(result)
        self.client.set_callback(self.waiting_for, self.callback_wrapper)

def puka_async_generator(method):
    def wrapper(client, *args, **kwargs):
        AsyncGeneratorState(client, method(client, *args, **kwargs))
        return None
    return wrapper

@puka_async_generator
def action_watcher(client):
    # consume a queue for actions injected
    master_q = "action"
    client.queue_declare(queue=master_q, durable=True)

    def callback(arg1, arg2):
        msg = arg2
        print "msg: %s" % (msg)
        client.basic_ack(msg)

    def parse_action(msg):
        try:
            json_obj = json.loads(msg['body'])
        except ValueError:
            return
        try:
            command = str(json_obj['command'])
        except:
            return
        if command == 'ping':
            ping(json_obj)
        elif command == 'start_update':
            start_update(json_obj)

    def ping(json_obj):
        ping_obj = {}
        ping_obj['hash'] = str(json_obj['hash'])
        ping_obj['command'] = 'ping'
        ping_obj['args'] = []
        ping_obj['timestamp'] = str(json_obj['timestamp'])
        try:
            routing_key = "%s.host" % json_obj['host']
        except KeyError:
            client.basic_ack(msg)
            return
        client.basic_ack(msg)
        print json_obj
        print ping_obj
        try:
            client.basic_publish(
                exchange=EXCHANGE,
                routing_key = str(routing_key),
                body = json.dumps(ping_obj)
                )
        except Exception, e:
            pass

    def start_update(json_obj):
        ping_obj = {}
        ping_obj['hash'] = str(json_obj['hash'])
        ping_obj['command'] = 'start_update'
        ping_obj['args'] = []
        ping_obj['timestamp'] = str(json_obj['timestamp'])
        try:
            routing_key = "%s.host" % json_obj['host']
        except KeyError:
            client.basic_ack(msg)
            return
        print routing_key
        client.basic_ack(msg)
        try:
            client.basic_publish(
                exchange=EXCHANGE,
                routing_key = str(routing_key),
                body = json.dumps(ping_obj)
                )
        except Exception, e:
            print "Could not start update"
            pass

    consume_promise = client.basic_consume(queue=master_q)
    while True:
        msg = (yield consume_promise)
        parse_action(msg)

def finish_update(current_update):
    update_log = SystemUpdateLog()
    update_log.system_update_id = current_update.id
    update_log.log_text = "Update Finished"
    update_log.system_id = current_update.system.id
    update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    update_log.save()
    current_update.is_current = False
    current_update.save()

def add_system_update_log(system, log_text, return_code):
    new_update = SystemUpdate(system_id=system.id, is_current=True, created_at=datetime.datetime.utcnow()).save()
    update_log = SystemUpdateLog()
    update_log.system_update_id = new_update.id
    update_log.log_text = log_text
    update_log.system_id = system.id
    update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    update_log.save()

def start_update(system):
    current_update = SystemUpdate.query.filter_by(system_id=system.id).filter_by(is_current=True).order_by('-id').first()
    if current_update:
        finish_update(current_update)
    add_system_update_log(system, 'Update Started', 0)
    return True

def run_updates(channel):
    global running_updates
    for dict_host in running_updates.iterkeys():
        try:
            script_to_run = running_updates[dict_host]['scripts_to_run'][0]
        except (KeyError, IndexError):
            script_to_run = None

        try:
            host = System.get_by_hostname(dict_host)
        except:
            host = None

        if script_to_run and host:
            execute(channel, host, script_to_run)
        elif not script_to_run and host:
            pass

def execute(channel, host, script_to_run):
    current_ms = str(time.time())
    exec_obj = {}
    exec_obj['command'] = "exec"
    exec_obj['args'] = [script_to_run]
    exec_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    exec_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    channel.basic_publish(
        exchange='chorizo',
        routing_key=host.get_routing_key(),
        body=json.dumps(exec_obj)
    )

def logcapture(log_obj, host):
    s = SystemUpdateLog()
    s.return_code = log_obj['ExitCode']
    s.stdout = log_obj['StdOut']
    s.stderr = log_obj['StdErr']
    try:
        s.log_text = log_obj['Message']
    except KeyError:
        pass
    s.created_at = datetime.datetime.utcnow()
    try:
        s.log_text = log_obj['log_text']
    except KeyError:
        pass
    system_update = SystemUpdate.query.filter_by(system_id=host.id).filter_by(is_current=1).first()
    s.system_update_id = system_update.id
    s.save()

def parse_message(msg, channel):
    global running_updates
    try:
        json_obj = json.loads(msg['body'])
    except:
        print 'Cannot parse json'
    host = System.get_by_hostname(json_obj['Hostname'])
    hostname = json_obj['Hostname']
    action = str(json_obj['Command'])
    if action == 'pong':
        ping_hash = str(json_obj['Hash'])
        async_pong(hostname, ping_hash, app.config)
    elif action == "start_update_resp":
        start_update_success = start_update(host)
        hostname = host.hostname
        running_updates[hostname] = {}
        running_updates[hostname]['scripts_to_run'] = [s.script.file_name for s in host.updategroups[0].scripts]
        running_updates[hostname]['scripts_ran'] = []
        run_updates(channel)
    elif action == "exec_response":
        # Get the currently executed script
        # Log the response
        # Remove executed_script from 
        should_continue = True
        try:
            executed_script = json_obj['Args'][0]
        except (KeyError, IndexError):
            should_continue = False
        # remove json

        hostname = json_obj['Hostname']
        script_ran = json_obj['Args'][0]
        try:
            len_scripts_to_run = len(running_updates[hostname]['scripts_to_run'])
        except (KeyError):
            # Somehow got into a weird race condition where there is no local running_updates
            return
        if running_updates[hostname]['scripts_to_run'][0] == script_ran:
            del running_updates[hostname]['scripts_to_run'][0]
            running_updates[hostname]['scripts_ran'].append(script_ran)
            logcapture(json_obj, host)
            if len(running_updates[hostname]['scripts_to_run']) > 0:
                run_updates(channel)
            else:
                current_update = SystemUpdate.query.filter_by(system_id=host.id).order_by('-id').first()
                finish_update(current_update)

@puka_async_generator
def worker(client, q):
    master_q = "master.%s" % (q)
    client.queue_declare(queue=master_q, durable=False)

    def callback(arg1, arg2):
        msg = arg2
        #print "msg: %s" % (msg)
        client.basic_ack(msg)

    consume_promise = client.basic_consume(queue=master_q)
    while True:
        msg = (yield consume_promise)
        client.basic_ack(msg)
        parse_message(msg, client)
        #print msg


average = average_count = 0.0


def get_queue_name_from_hostname(hostname):
    replaced_hostname = hostname.replace('.','-')
    replaced_hostname = str(replaced_hostname)
    return replaced_hostname

@manager.command
def queue_listen():
    client = puka.Client(AMQP_URL, pubacks=PUBACKS)
    promise = client.connect()
    client.wait(promise)
    systems = System.query.all()
    '''
    queues = [
        'robs-macbook-pro',
        'robs-macbook-pro2',
        'update'
    ]
    '''
    queues = [get_queue_name_from_hostname(s.hostname) for s in systems]




    action_watcher(client)
    for q in queues:
        worker(client, q)

    time.sleep(5)
    print ' [*] loop'
    while True:
        client.loop()
    #while True:
        #t0 = time.time()
        #client.loop(timeout=1.0)
        #td = time.time() - t0
        #average_count = max(average_count, 1.0)
        #print "send: %i  avg: %.3fms " % (counter/td,
                                          #(average/average_count)*1000.0)
        #counter = average = average_count = 0

if __name__ == '__main__':
    manager.run()

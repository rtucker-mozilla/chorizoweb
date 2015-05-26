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
from moz_au_web.system.models import System, SystemUpdate, SystemUpdateLog, SystemPing, UpdateGroup
from moz_au_web.database import db
from celery_tasks import async_pong
import logging


ENV = os.environ.get('ENV', False)
if ENV == 'DEV':
    config_object = DevConfig
else:
    config_object = ProdConfig
logging.info("config_object: %s" % (config_object))


app = create_app(config_object)

manager = Manager(app)

AMQP_URL = app.config.get("AMQP_URL", "amqp://127.0.0.1:5671/")
EXCHANGE='chorizo'
QUEUE_CNT = 32
BURST_SIZE = 120
QUEUE_SIZE = 1000
BODY_SIZE = 1
PREFETCH_CNT = 1
MSG_HEADERS = {'persistent': False}
PUBACKS = False
running_group_updates = {}

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
    logging.info("action_watcher: declaring queue: %s" % master_q)
    client.queue_declare(queue=master_q, durable=True)

    def callback(arg1, arg2):
        msg = arg2
        logging.info("action_watcher: msg: %s" % (msg))
        client.basic_ack(msg)

    def parse_action(msg):
        logging.info("action_water.parse_info")
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
        # Send the message to the client system that it should start to update
        ping_obj = {}
        ping_obj['hash'] = str(json_obj['hash'])
        ping_obj['command'] = 'start_update'
        ping_obj['args'] = json_obj['args']
        ping_obj['groupid'] = json_obj['groupid']
        ping_obj['timestamp'] = str(json_obj['timestamp'])
        try:
            routing_key = "%s.host" % json_obj['host']
        except KeyError:
            client.basic_ack(msg)
            return
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

def finish_update(current_update, group_id=None):
    update_log = SystemUpdateLog()
    update_log.system_update_id = current_update.id
    update_log.log_text = "Update Finished"
    update_log.system_id = current_update.system.id
    update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    if not group_id is None:
        update_log.group_id = group_id
    current_update.finished_at = datetime.datetime.utcnow()
    update_log.save()
    current_update.finished_at = datetime.datetime.utcnow()
    current_update.is_current = False
    current_update.save()

def add_system_update_log(system, log_text, return_code, group_id=None):
    new_update = SystemUpdate(
        system_id=system.id,
        is_current=True,
        group_id=group_id,
        created_at=datetime.datetime.utcnow()
    )
    new_update.save()
    update_log = SystemUpdateLog()
    update_log.system_update_id = new_update.id
    update_log.log_text = log_text
    update_log.system_id = system.id
    update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    update_log.save()

def start_update_log(system, group_id=None):
    current_update = SystemUpdate.query.filter_by(system_id=system.id).filter_by(is_current=True).order_by('-id').first()
    if current_update:
        finish_update(current_update)
    add_system_update_log(system, 'Update Started', 0, group_id=group_id)
    return True

def run_updates(channel, update_group):
    global running_group_updates

    if not update_group is None:
        group_name = update_group.group_name
        for dict_host in running_group_updates[group_name].iterkeys():
            try:
                script_to_run = running_group_updates[group_name][dict_host]['scripts_to_run'][0]
            except (KeyError, IndexError):
                script_to_run = None

            try:
                host = System.get_by_hostname(dict_host)
            except:
                host = None

            if script_to_run and host:
                execute(channel, host, script_to_run, group_id=update_group.id)
            elif not script_to_run and host:
                pass

def execute(channel, host, script_to_run, group_id=None):
    current_ms = str(time.time())
    exec_obj = {}
    exec_obj['command'] = "exec"
    exec_obj['args'] = [script_to_run]
    exec_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    exec_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    if not group_id is None:
        exec_obj['groupid'] = group_id
    else:
        exec_obj['group_id'] = ""
    print exec_obj
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
    # These are incoming messages from the client/agent machines
    global running_group_updates
    try:
        json_obj = json.loads(msg['body'])
    except:
        print 'Cannot parse json'
    host = System.get_by_hostname(json_obj['Hostname'])
    hostname = json_obj['Hostname']
    action = str(json_obj['Command'])
    if action == 'pong':
        ping_hash = str(json_obj['Hash'])
        logging.info(ping_hash)
        async_pong(hostname, ping_hash, app.config)
    elif action == "start_update_resp":
        hostname = host.hostname
        try:
            update_group = UpdateGroup.get_by_id(json_obj['GroupId'])
        except:
            # No group_id in Args
            # Use the 1st group
            update_group = None
        try:
            start_update_success = start_update_log(host, update_group.id)
        except:
            return
        group_name = None
        if not update_group is None:
            group_name = update_group.group_name
            running_group_updates[group_name] = {}
            running_group_updates[group_name][hostname] = {}
        else:
            logging.info("group not found by id: %s" % (json_obj['GroupId']))

        if update_group:
            running_group_updates[group_name][hostname]['scripts_to_run'] = [s.script.file_name for s in update_group.scripts]
            if not hostname in running_group_updates[group_name]:
                running_group_updates[group_name][hostname] = {}
            running_group_updates[group_name][hostname]['scripts_to_run'] = [s.script.file_name for s in update_group.scripts]
            running_group_updates[group_name][hostname]['scripts_ran'] = []

        run_updates(channel, update_group)
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
            group_id = json_obj['GroupId']
            if group_id == "":
                group_id = None
        except KeyError:
            group_id = None
        update_group = UpdateGroup.get_by_id(group_id)
        if not update_group is None:
            group_name = update_group.group_name
        elif update_group is None:
            return
        try:
            len_scripts_to_run = len(running_group_updates[group_name][hostname]['scripts_to_run'])
        except (KeyError):
            # Somehow got into a weird race condition where there is no local running_updates
            return

        if running_group_updates[group_name][hostname]['scripts_to_run'][0] == script_ran:
            del running_group_updates[group_name][hostname]['scripts_to_run'][0]
            running_group_updates[group_name][hostname]['scripts_ran'].append(script_ran)
            logcapture(json_obj, host)
            if len(running_group_updates[group_name][hostname]['scripts_to_run']) > 0:
                run_updates(channel, update_group)
            else:
                current_update = SystemUpdate.query.filter_by(system_id=host.id).order_by('-id').first()
                finish_update(current_update, group_id)

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

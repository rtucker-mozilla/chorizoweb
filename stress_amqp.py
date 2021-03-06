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
from chorizo_queue_state import ChorizoQueueState
cqs = ChorizoQueueState()
import logging
EXIT_CODE_REBOOT = 128
ALLOWED_EXIT_CODES = [
    0,
    128
]


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
    master_q = "master.action"
    logging.info("action_watcher: declaring queue: %s" % master_q)
    client.queue_declare(queue=master_q, durable=True)

    def callback(arg1, arg2):
        msg = arg2
        logging.info("action_watcher: msg: %s" % (msg))
        client.basic_ack(msg)

    def parse_action(msg):
        logging.info("action_watcher.parse_info")
        try:
            json_obj = json.loads(msg['body'])
        except ValueError:
            return
        try:
            command = str(json_obj['command'])
        except:
            return
        logging.info("action_watcher::parse_action::command: %s" % command)
        if command == 'ping':
            ping(json_obj)
        elif command == 'start_update':
            start_update(json_obj)
        elif command == 'start_group_update':
            start_group_update(json_obj)
        elif command == 'start_reboot':
            start_reboot(json_obj)
        else:
            print "Unknown Command: %s" % (command)

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
        try:
            client.basic_publish(
                exchange=EXCHANGE,
                routing_key = str(routing_key),
                body = json.dumps(ping_obj)
                )
        except Exception, e:
            pass

    def start_reboot(json_obj):
        ping_obj = {}
        ping_obj['hash'] = str(json_obj['hash'])
        ping_obj['command'] = 'start_reboot'
        ping_obj['args'] = []
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
            pass


    def start_group_update(json_obj):
        # Send the message to the client system that it should start to update
        try:
            group = UpdateGroup.get_by_id(json_obj['group_id'])
        except KeyError:
            # No group_id found in json_obj
            logging.error("No group_id found in json_obj")
            client.basic_ack(msg)
        group_name = group.group_name
        cqs.add_group_if_not_exists(group_name)
        group_systems = group.sorted_systems_list
        if len(group_systems) > 0:
            for system in group_systems:
                try:
                    system_hostname = system['hostname']
                    cqs.add_host_to_group_if_not_exists(group, system_hostname, add_scripts=True)
                except KeyError:
                    pass
        logging.info("run_updates for: %s" % (cqs.running_group_updates))
        run_updates(client, group)

    consume_promise = client.basic_consume(queue=master_q)
    while True:
        msg = (yield consume_promise)
        parse_action(msg)
        client.basic_ack(msg)

def log_reboot(current_update, group_id, host, message=None):
    if message is None:
        message = "Rebooting Host"
    update_log = SystemUpdateLog()
    update_log.system_update_id = current_update.id
    update_log.system_id = current_update.system.id
    update_log.group_id = group_id
    update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    update_log.log_text = message
    if not group_id is None:
        update_log.group_id = group_id
    else:
        logging.info("unable to set group_id")
    update_log.save()
    current_update.status_code = 4
    current_update.save()

def finish_update(current_update, group_id=None, is_error=False, manual_message=None):
    if current_update is None:
        logging.info("creating current_update in finish_update")
    update_log = SystemUpdateLog()
    update_log.system_update_id = current_update.id
    if manual_message is not None:
        update_log.log_text = manual_message
    else:
        update_log.log_text = "Update Finished"
    update_log.system_id = current_update.system.id
    if is_error is True:
        update_log.return_code = 255
    else:
        update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    if not group_id is None:
        update_log.group_id = group_id
    else:
        logging.info("unable to set group_id")
    update_log.save()
    current_update.finished_at = datetime.datetime.utcnow()
    current_update.is_current = False
    if is_error is True:
        current_update.status_code = 2
    else:
        current_update.status_code = 0
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
    update_log.return_code = 1
    update_log.created_at = datetime.datetime.utcnow()
    update_log.save()

def start_update_log(system, group_id=None):
    current_update = SystemUpdate.query.filter_by(system_id=system.id).filter_by(is_current=True).filter_by(group_id=group_id).order_by('-id').first()
    if current_update:
        finish_update(current_update)
    add_system_update_log(system, 'Update Started', 0, group_id=group_id)
    return True

def run_updates(channel, update_group):

    if not update_group is None:
        group_name = update_group.group_name
        host, script_to_run = cqs.get_next_script_to_run(update_group)
        if script_to_run and host:
            execute(channel, host, script_to_run, group_id=update_group.id)

def reboot_host(channel, host, group_id):
    current_ms = str(time.time())
    exec_obj = {}
    exec_obj['command'] = "start_reboot"
    exec_obj['args'] = ''
    exec_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    exec_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    if not group_id is None:
        exec_obj['groupid'] = group_id
    else:
        exec_obj['group_id'] = ""
    channel.basic_publish(
        exchange='chorizo',
        routing_key=host.get_routing_key(),
        body=json.dumps(exec_obj)
    )
    cqs.set_host_rebooted(host, group_id)

def execute(channel, host, script_to_run, group_id=None):
    if not hasattr(host, 'get_routing_key'):
        host = System.query.filter_by(hostname=host).first()
    if not get_current_system_update(host):
        start_update_log(host, group_id)
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
    channel.basic_publish(
        exchange='chorizo',
        routing_key=host.get_routing_key(),
        body=json.dumps(exec_obj)
    )

def get_current_system_update(host, group_id=None):
    if host and group_id is None:
        return SystemUpdate.query.filter_by(system_id=host.id).filter_by(is_current=1).first()
    elif host and not group_id is None:
        return SystemUpdate.query.filter_by(system_id=host.id).filter_by(is_current=1).filter_by(group_id=group_id).first()
    else:
        return None

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
    if not system_update is None:
        s.system_update_id = system_update.id
    else:
        logging.info("Unable to get SystemUpdate by system_id: %s" % (host.id))
    s.save()

def parse_message(msg, channel):
    # These are incoming messages from the client/agent machines
    global running_group_updates
    try:
        json_obj = json.loads(msg['body'])
    except:
        logger.error('Cannot parse json')
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
            group_name = update_group.group_name
        except:
            # No group_id in Args
            # Use the 1st group
            update_group = None
        try:
            start_update_success = start_update_log(host, update_group.id)
        except:
            return

        if not update_group is None:
            cqs.add_host_to_group_if_not_exists(update_group, hostname)
        else:
            logging.info("group not found by id: %s" % (json_obj['GroupId']))

        if update_group:
            for s in update_group.scripts:
                cqs.add_script_to_host_group(s.script.file_name, hostname, update_group)

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
        host = System.get_by_hostname(hostname)
        script_ran = json_obj['Args'][0]
        try:
            group_id = json_obj['GroupId']
            if group_id == "":
                group_id = None
        except KeyError:
            logging.info("GroupId from client is None - Returning")
            group_id = None
        update_group = UpdateGroup.get_by_id(group_id)
        if not update_group is None:
            group_name = update_group.group_name
        elif update_group is None:
            logging.info("update_group is None - Returning")
            return
        # @TODO figure out if the following is necessary
        #if cqs.get_scripts_to_run_len(hostname, group_name) == 0:
        #    # Somehow got into a weird race condition where there is no local running_updates
        #    return

        # Figure out how to confirm the script that is running
        logging.info("cqs.running_group_updates:before %s" % (cqs.running_group_updates))
        cqs.set_script_ran(script_ran, hostname, group_name)
        logging.info("cqs.running_group_updates:after %s" % (cqs.running_group_updates))
        if not get_current_system_update(host):
            start_update_log(host, group_id)
        logcapture(json_obj, host)
        try:
            exit_code = int(json_obj['ExitCode'])
        except:
            exit_code = None
        current_update = get_current_system_update(host, group_id)

        if not exit_code is None:
            if not exit_code in ALLOWED_EXIT_CODES:
                # We have an unknown exit code
                # Immediately die
                cqs.remove_host_from_group(hostname, group_name)
                cqs.remove_group(group_name)
                finish_update(current_update, group_id, is_error=True, manual_message="Received unallowed return code")
                return
            elif exit_code == EXIT_CODE_REBOOT:
                log_reboot(current_update, group_id, host)
                reboot_host(channel, host, group_id)
                return
        execute_if_not_done(host, update_group, current_update, channel)


        return
    elif action == "hello_resp":
        hostname = json_obj['Hostname']
        host = System.get_by_hostname(hostname)
        current_update = get_current_system_update(host, group_id=None)
        try:
            group_id = json_obj['GroupId']
            update_group = UpdateGroup.get_by_id(group_id)
            if group_id == "":
                group_id = None
        except KeyError:
            logging.info("GroupId from client is None - Returning")
            group_id = None
            update_group = None
        execute_if_not_done(host, update_group, current_update, channel)

def execute_if_not_done(host, update_group, current_update, channel):
    # We don't have an update group
    # Host probably rebooted
    if update_group is None:
        group_id = cqs.get_rebooted_group_id_by_host(host)
        update_group = UpdateGroup.get_by_id(group_id)
        if update_group is None:
            return
        cqs.remove_host_rebooted(host)
    group_name = update_group.group_name
    group_id = update_group.id
    hostname = host.hostname
    if cqs.check_if_host_done(hostname, group_name):
        logging.info("cqs.check_if_host_done host::true: %s group_name: %s" % (hostname, group_name))
        #current_update = SystemUpdate.query.filter_by(system_id=host.id).filter_by(group_id=group_id).order_by('-id').first()
        if current_update is None:
            logging.info("Unable to get current_update")
        else:
            finish_update(current_update, group_id)
        cqs.remove_host_from_group(hostname, group_name)
        logging.info("removed host: %s from group: %s" % (hostname, group_name))
        if cqs.check_if_group_done(group_name) is False:
            next_host = cqs.get_next_host_by_group(update_group)
            logging.info("next_host: %s" % (next_host))
            host = System.get_by_hostname(next_host)
            logging.info("host: %s" % (host))
            logging.info("group_id: %s" % (group_id))
            run_updates(channel, update_group)
            logging.info("host: %s started update" % (host))
        else:
            logging.info("Removing group: %s" % (update_group.group_name))
            cqs.remove_group(group_name)
    else:
        host, script_to_run = cqs.get_next_script_to_run(update_group)
        execute(channel, host, script_to_run, group_id=group_id)
        logging.info("cqs.check_if_host_done host::false: %s group_name: %s" % (hostname, group_name))


@puka_async_generator
def worker(client, q):
    master_q = "master.%s" % (q)
    master_q = 'host-action'
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
    #queues = [get_queue_name_from_hostname(s.hostname) for s in systems]
    queues = ['host-action']




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

#!/usr/bin/env python
import pika
import time
import datetime
import logging
import json
import hashlib
import sys
import os
from moz_au_web.settings import ProdConfig, DevConfig
logging.basicConfig()
ENV = os.environ.get('ENV', False)
if ENV == 'DEV':
    config_object = DevConfig
else:
    config_object = ProdConfig

def ping(channel, routing_key):
    current_ms = str(time.time())
    ping_obj = {}
    ping_obj['command'] = "ping"
    ping_obj['args'] = []
    ping_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    ping_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    channel.basic_publish(
        exchange='chorizo',
        routing_key=routing_key,
        body=json.dumps(ping_obj)
    )

def start_update(channel, routing_key):
    current_ms = str(time.time())
    ping_obj = {}
    ping_obj['command'] = "start_update"
    ping_obj['args'] = []
    ping_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    ping_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    channel.basic_publish(
        exchange='chorizo',
        routing_key=routing_key,
        body=json.dumps(ping_obj)
    )

def execute(channel, routing_key, action_args):
    current_ms = str(time.time())
    ping_obj = {}
    ping_obj['command'] = "exec"
    ping_obj['args'] = action_args
    ping_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    ping_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    channel.basic_publish(
        exchange='chorizo',
        routing_key=routing_key,
        body=json.dumps(ping_obj)
    )

def get_queue_name_from_hostname(hostname):
    replaced_hostname = hostname.replace('.','-')
    replaced_hostname = str(replaced_hostname)
    return replaced_hostname

if __name__ == '__main__':
    exchange='chorizo'
    host = sys.argv[1]
    queue = get_queue_name_from_hostname(host)
    action = sys.argv[2]
    action_list = sys.argv[3:]
    routing_key = "%s.host" % (queue)

    connection = pika.BlockingConnection(pika.ConnectionParameters(
                       config_object.RABBITMQ_HOST,
                       config_object.RABBITMQ_PORT
                       )
    )
    channel = connection.channel()
    channel.exchange_declare(exchange=config_object.RABBITMQ_EXCHANGE, type='topic')
    channel.queue_declare(queue, exclusive=False)
    channel.queue_bind(exchange=config_object.RABBITMQ_EXCHANGE, queue=queue, routing_key=routing_key)
    if str(action) == 'ping':
        ping(channel, routing_key)
    elif str(action) == 'start_update':
        start_update(channel, routing_key)
    elif str(action) == 'exec':
        execute(channel, routing_key, action_args = action_list)
    channel.close()

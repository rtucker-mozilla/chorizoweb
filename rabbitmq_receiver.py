#!/usr/bin/env python
import pika
import time
import datetime
import logging
import json
import hashlib
logging.basicConfig()
import sys
from flask.ext.script import Manager
from moz_au_web.app import create_app
from threading import Thread
from moz_au_web.settings import ProdConfig, DevConfig

app = create_app(DevConfig)

manager = Manager(app)
from consumer import ExampleConsumer

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) ' '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
ROUTING_KEYS = [
        {
            'queue': 'master.robs-macbook-pro',
            'routing_key': 'master.robs-macbook-pro.host',
        }
        ]

known_queues = []
queues = [
    'robs-macbook-pro'
]
def bind_queues(consumer, queues):
    global known_queues
    for q in queues:
        if q not in known_queues:
            master_queue_name = "master.%s" % (q)
            master_routing_key = "master.%s.host" % (q)
            consumer.queue_declare(q, exclusive=False)
            consumer.queue_declare(master_queue_name, exclusive=False)
            consumer.queue_bind(exchange="chorizo", queue=master_queue_name, routing_key=master_routing_key)
            consumer.basic_consume(callback,
                        queue=master_queue_name,
                        no_ack=True)
            known_queues.append(q)

def on_connection_open():
    pass

def channel_open():
    return

def on_exchange_declareok(unused_frame):
    """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
    command.

    :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

    """
    LOGGER.info('Exchange declared')
    #self.setup_queue(self.QUEUE, bind_key=self.BIND_KEY, bind=True)

def add_on_channel_close_callback(channel):
    """This method tells pika to call the on_channel_closed method if
    RabbitMQ unexpectedly closes the channel.

    """
    LOGGER.info('Adding channel close callback')
    channel.add_on_close_callback(self.on_channel_closed)

def on_channel_closed(self, channel, reply_code, reply_text):
    """Invoked by pika when RabbitMQ unexpectedly closes the channel.
    Channels are usually closed if you attempt to do something that
    violates the protocol, such as re-declare an exchange or queue with
    different parameters. In this case, we'll close the connection
    to shutdown the object.

    :param pika.channel.Channel: The closed channel
    :param int reply_code: The numeric reason the channel was closed
    :param str reply_text: The text reason the channel was closed

    """
    LOGGER.warning('Channel %i was closed: (%s) %s',
                   channel, reply_code, reply_text)
    self._connection.close()

@manager.command
def queue_listen():
    LOGGER.setLevel(2)
    try:
        conn = pika.SelectConnection(pika.URLParameters('amqp://127.0.0.1:5672/%2F'),
                                     False,
                                     stop_ioloop_on_close=False)
        #example.run()
        #example.setup_exchange('chorizo')
        LOGGER.info('binding')
        channel = conn.channel(channel_open)
        add_on_channel_close_callback(channel)
        channel.exchange_declare(on_exchange_declareok, 'chorizo', 'topic')
        LOGGER.info('getting channel')
        #conn.ioloop.start()
        bind_queues(channel, queues)
        #example.setup_queue('master.robs-macbook-pro')
        #example.start_consuming('master.robs-macbook-pro')
    except KeyboardInterrupt:
        conn.stop()



# Write Queues
#channel.queue_declare('robs-macbook-pro', exclusive=False)
#channel.queue_declare('update', exclusive=False)
#
## Read Queues
#channel.queue_declare('master.update', exclusive=False)
#channel.queue_declare('master.robs-macbook-pro', exclusive=False)
#
#channel.queue_bind(exchange="chorizo", queue='master.update', routing_key='master.update.host')
#channel.queue_bind(exchange="chorizo", queue='master.robs-macbook-pro', routing_key='master.robs-macbook-pro.host')

pings = []

queues = [
    'update',
    'robs-macbook-pro',
]

def declare_queues(channel, queues):
    for q in queues:
        print q
        master_queue_name = "master.%s" % (q)
        master_routing_key = "master.%s.host" % (q)
        channel.queue_declare(q, exclusive=False)
        channel.queue_declare(master_queue_name, exclusive=False)
        channel.queue_bind(exchange="chorizo", queue=master_queue_name, routing_key=master_routing_key)
        channel.basic_consume(callback,
                    queue=master_queue_name,
                    no_ack=True)
    return channel

def pong(json_obj):
    global pings
    try:
        hash = json_obj['Hash']
    except KeyError:
        pass
    pings = [p for p in pings if p['hash'] != hash]
    print "pings", pings

def callback(ch, method, properties, body):
    global pings
    try:
        json_obj = json.loads(body)
        if json_obj['Command'] == 'pong':
            pong(json_obj)
    except:
        pass
    print "Received on Master [x] %r:%r" % (method.routing_key, body,)


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) ' '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
if __name__ == "__main__":
    manager.run()

def ping(channel, routing_key):
    global pings
    current_ms = str(time.time())
    ping_obj = {}
    ping_obj['command'] = "ping"
    ping_obj['args'] = ["arg1", "arg2"]
    ping_obj['hash'] = hashlib.sha1(current_ms).hexdigest()
    ping_obj['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
    pings.append(ping_obj)
    channel.basic_publish(
        exchange='chorizo',
        routing_key=routing_key,
        body=json.dumps(ping_obj)
    )
    print "Pings in ping"
    print pings



#channel.basic_consume(callback,
#                      queue='master.update',
#                      no_ack=True)
#
#channel.basic_consume(callback,
#                      queue='master.robs-macbook-pro',
#                      no_ack=True)
#
#hostname = 'robs-macbook-pro'
#routing_key = "robs-macbook-pro.host"
#channel.queue_bind(exchange="chorizo", queue=hostname, routing_key=routing_key)
#
#for i in range(0,1000):
#    if i % 3 == 0 and i != 0:
#        routing_key = "robs-macbook-pro.host"
#        ping(channel, routing_key)
#
#    else:
#        hostname = 'update'
#        queue = hostname
#        routing_key = "update.host"
#        channel.queue_bind(exchange="chorizo", queue=hostname, routing_key=routing_key)
#
#    #channel.basic_publish(exchange='chorizo',
#    #                            routing_key=routing_key,
#    #                            body='Key: %s - Counter %i' % (routing_key, i))
#    #print "%s: Counter %i" % (routing_key, i)
#    time.sleep(1)
#channel.close()

from celery import Celery
import os
from flask import Flask, current_app
import pika
from moz_au_web.settings import ProdConfig, DevConfig
from moz_au_web.extensions import db
from moz_au_web.system.models import System, SystemPing, SystemPong
import datetime
ENV = os.environ.get('ENV', False)
if ENV == 'DEV':
    config_object = DevConfig
else:
    config_object = ProdConfig

from celery.utils.log import get_task_logger

def init_rabbitmq(config):
    rabbitmq_host = config['RABBITMQ_HOST']
    rabbitmq_port = config['RABBITMQ_PORT']
    rabbitmq_user = config['RABBITMQ_USER']
    rabbitmq_pass = config['RABBITMQ_PASS']
    current_app.logger.info("init_rabbitmq: rabbitmq_host %s" % (rabbitmq_host))
    rabbitmq_exchange = config['RABBITMQ_EXCHANGE']
    queue = 'action'
    routing_key = 'action.host'
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
                       rabbitmq_host,
                       rabbitmq_port,
                       "/",
                       credentials
                       ))
    channel = connection.channel()
    channel.exchange_declare(exchange=rabbitmq_exchange, type='topic')
    channel.queue_declare(queue, exclusive=False, durable=True)
    channel.queue_bind(exchange=rabbitmq_exchange, queue=queue, routing_key=routing_key)
    global_channel = channel

    return channel

def make_celery():
    app = Flask(__name__)
    db.init_app(app)
    app.config.from_object(config_object)
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


celery = make_celery()


@celery.task()
def async_ping(system, config):
    current_app.logger.info("async_ping system: %s" % (system))
    rabbit_channel = init_rabbitmq(config)
    ping_hash = system.ping(rabbit_channel)
    current_app.logger.info("async_ping ping_hash: %s" % (ping_hash))

@celery.task()
def async_pong(hostname, ping_hash, config):
    current_app.logger.info("async_pong hostname: %s" % (hostname))
    current_app.logger.info("async_pong ping_hash: %s" % (ping_hash))
    system = System.get_by_hostname(hostname)
    if system:
        current_app.logger.info("We have system ping object ping_hash: %s" % (ping_hash))
        sp = SystemPong()
        sp.ping_hash = ping_hash
        sp.pong_time = datetime.datetime.now()
        sp.save()
    else:
        current_app.logger.info("No system found by hostname: %s" % (hostname))

@celery.task()
def async_group_start_update(group, config):
    channel = init_rabbitmq(config)
    group.start_update(channel)

@celery.task()
def async_system_start_update(system, config, group_id=None):
    channel = init_rabbitmq(config)
    system.start_update(channel, group_id=group_id)

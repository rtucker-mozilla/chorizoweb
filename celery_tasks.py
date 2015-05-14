from celery import Celery
from flask import Flask
import pika
from moz_au_web.settings import ProdConfig, DevConfig
from moz_au_web.extensions import db
from moz_au_web.system.models import System, SystemPing
import datetime
config_object = ProdConfig
config_object = DevConfig

def init_rabbitmq(config):
    rabbitmq_host = config['RABBITMQ_HOST']
    rabbitmq_port = config['RABBITMQ_PORT']
    rabbitmq_user = config['RABBITMQ_USER']
    rabbitmq_pass = config['RABBITMQ_PASS']
    rabbitmq_user = 'chorizo'
    rabbitmq_pass = 'chorizo'
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
    rabbit_channel = init_rabbitmq(config)
    system.ping(rabbit_channel)

@celery.task()
def async_pong(hostname, ping_hash, config):
    global rabbit_channel
    system = System.query.filter_by(hostname = hostname).first()
    if not system is None:
        sp = SystemPing.query.filter_by(system = system).filter_by(ping_hash=ping_hash).first()
    if not sp is None:
        sp.pong_time = datetime.datetime.now()
        sp.success = True
        sp.save()

@celery.task()
def async_start_update(system, config):
    channel = init_rabbitmq(config)
    system.start_update(channel)

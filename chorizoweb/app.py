# -*- coding: utf-8 -*-
'''The app module, containing the app factory function.'''
from flask import Flask, render_template
import pika
from celery import Celery


from chorizoweb.settings import ProdConfig
from chorizoweb.assets import assets
from chorizoweb.extensions import (
    bcrypt,
    cache,
    db,
    login_manager,
    migrate,
    debug_toolbar,
)
from chorizoweb import public, user, system, api

def create_app(config_object=ProdConfig):
    '''An application factory, as explained here:
        http://flask.pocoo.org/docs/patterns/appfactories/

    :param config_object: The configuration object to use.
    '''
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    return app


def register_extensions(app):
    assets.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    db.session.autocommit = True
    login_manager.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    #init_rabbitmq(app)
    return None

def init_rabbitmq(app):
    rabbitmq_host = app.config['RABBITMQ_HOST']
    rabbitmq_port = app.config['RABBITMQ_PORT']
    rabbitmq_user = app.config['RABBITMQ_USER']
    rabbitmq_pass = app.config['RABBITMQ_PASS']
    rabbitmq_exchange = app.config['RABBITMQ_EXCHANGE']
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
    app.channel = channel

def make_celery(app):
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

def register_blueprints(app):
    app.register_blueprint(public.views.blueprint)
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(system.views.blueprint)
    app.register_blueprint(api.views.blueprint)
    return None


def register_errorhandlers(app):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template("{0}.html".format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None

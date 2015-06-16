#!/usr/bin/env python
import sys
sys.path.append("..")

import pika, datetime, time, datetime, os
from croniter import croniter

from flask.ext.script import Manager
from moz_au_web.app import create_app
from moz_au_web.settings import ProdConfig, DevConfig
from moz_au_web.system.models import UpdateGroup
from celery_tasks import async_pong
import logging

ENV = os.environ.get('ENV', False)
if ENV == 'DEV':
    config_object = DevConfig
else:
    config_object = ProdConfig

app = create_app(config_object)

manager = Manager(app)

def validate_cron_line(cron_line):
    current_minute = datetime.datetime.now()
    current_minute = current_minute.replace(second=0, microsecond=0)
    base = current_minute
    try:
        cron_iter = croniter(cron_line, base)
        return True, "expression validated"
    except Exception, e:
        return False, e


def eval_cron_line(cron_line):
    current_minute = datetime.datetime.now()
    current_minute = current_minute.replace(second=0, microsecond=0)
    base = current_minute - datetime.timedelta(seconds = 1)
    cron_iter = croniter(cron_line, base)
    next_run = cron_iter.next(datetime.datetime)
    if current_minute == next_run:
        return True
    else:
        return False

def get_update_groups():
    ret_groups = []
    for ug in UpdateGroup.query.all():
        cron_content = ug.cronfile
        if cron_content != None and cron_content != '':
            is_valid, message = validate_cron_line(cron_content)
            if is_valid:
                ret_groups.append(ug)

    if len(ret_groups) > 0:
        return ret_groups
    else:
        return False

def get_channel():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
                       config_object.RABBITMQ_HOST,
                       config_object.RABBITMQ_PORT
                       )
    )
    channel = connection.channel()
    return channel

def run_group_update(update_group):
    channel = get_channel()
    update_group.start_update(channel)


@manager.command
def run_group_updates():
    update_groups = get_update_groups()
    if update_groups is False:
        return

    for ug in update_groups:
        run_now = eval_cron_line(ug.cronfile)
        if run_now:
            run_group_update(ug)

if __name__ == '__main__':
    manager.run()

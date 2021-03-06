# -*- coding: utf-8 -*-
import datetime as dt
import time
import hashlib
import json


from chorizoweb.extensions import bcrypt
from chorizoweb.database import (
    Column,
    db,
    Model,
    ReferenceCol,
    relationship,
    SurrogatePK,
)
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.sql import text
import logging
LOG_FORMAT = (
    '\n%(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n\n' +
    '\t%(message)s'
    )
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)


class System(SurrogatePK, Model):

    __tablename__ = 'systems'
    hostname = Column(db.String(80), unique=True, nullable=False)
    created_at = Column(db.DateTime, default=dt.datetime.utcnow())
    cronfile = Column(db.String(80), unique=False, nullable=False)
    
    def __repr__(self):
        return '<System({hostname!r})>'.format(hostname=self.hostname)

    @staticmethod
    def get_by_hostname(hostname):
        # Find a system by it's hostname
        # If a system doesn't exist by it's hostname than create it
        system = System.query.filter_by(hostname=hostname).first()
        if system is None:
            system = System()
            system.hostname = hostname
            system.created_at = datetime.datetime.utcnow()
            system.save()
        return system

    def get_queue_name_from_hostname(self):
        replaced_hostname = self.hostname.replace('.','-')
        replaced_hostname = str(replaced_hostname)
        return replaced_hostname

    def get_master_queue_name_from_hostname(self):
        queue = "master.%s" % (self.get_queue_name_from_hostname())
        return queue

    def get_routing_key(self):
        return "%s.host" % (self.get_queue_name_from_hostname())

    def get_master_routing_key(self):
        return "master.action"

    def mq_default_args(self):
        current_ms = str(time.time())
        hash_string = "%s%s" % (self.hostname, current_ms)
        ret_obj = {}
        ret_obj['hash'] = hashlib.sha1(hash_string).hexdigest()
        ret_obj['host'] = self.hostname
        ret_obj['args'] = []
        ret_obj['timestamp'] = dt.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
        return ret_obj

    def ping(self, channel):
        queue = self.get_queue_name_from_hostname()
        routing_key = self.get_routing_key()
        ping_obj = self.mq_default_args()
        ping_obj['command'] = 'ping'

        res = channel.basic_publish(
            exchange='chorizo',
            routing_key = routing_key,
            body=json.dumps(ping_obj)
        )
        try:
            sp = SystemPing()
            sp.system = self
            sp.ping_hash = ping_obj['hash']
            sp.ping_time = dt.datetime.now()
            sp.save(commit=True)
            return sp.ping_hash
        except Exception ,e:
            print e

        return False




    def start_update(self, channel, group_id=None):
        # Injection point for a system to start updating
        queue = self.get_queue_name_from_hostname()
        routing_key = self.get_routing_key()
        current_ms = str(time.time())
        start_update_obj = self.mq_default_args()
        start_update_obj['command'] = 'start_update'
        start_update_obj['groupid'] = int(group_id)
        logging.info("start_update_obj: %s" % (json.dumps(start_update_obj)))
        logging.info("routing_key: %s" % (routing_key))

        res = channel.basic_publish(
            exchange='chorizo',
            routing_key = routing_key,
            body=json.dumps(start_update_obj)
        )


class SystemPing(SurrogatePK, Model):
    __tablename__ = 'system_pings'
    system_id = Column(db.Integer, db.ForeignKey('systems.id'))
    system = relationship("System", foreign_keys=[system_id], backref="pings")
    ping_hash = Column(db.String(80), unique=True, nullable=False)
    ping_time = Column(db.DateTime)

    @property
    def success(self):
        try:
            pong = SystemPong.query.filter_by(ping_hash=self.ping_hash).first()
            if pong:
                return 1
            else:
                return 0
        except TypeError:
            return 0

    @property
    def pong_time(self):
        try:
            return SystemPong.query.filter_by(ping_hash=self.ping_hash).first().pong_time
        except:
            return ''

class SystemPong(SurrogatePK, Model):
    __tablename__ = 'system_pongs'
    system_id = Column(db.Integer, db.ForeignKey('systems.id'))
    system = relationship("System", foreign_keys=[system_id], backref="pongs")
    ping_hash = Column(db.String(80), unique=True, nullable=False)
    pong_time = Column(db.DateTime)

update_groups = db.Table('update_groups',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('system_id', db.Integer, db.ForeignKey('systems.id')),
    db.Column('update_group_id', db.Integer, db.ForeignKey('update_group.id'))
)

class UpdateGroup(SurrogatePK, Model):
    __tablename__ = 'update_group'
    group_name = Column(db.String(80), unique=True, nullable=False)
    systems = db.relationship('System', secondary=update_groups,
        backref=db.backref('updategroups', lazy='dynamic'), collection_class=ordering_list("id"))
    cronfile = Column(db.String(80), unique=False, nullable=True)

    def get_queue_name_from_hostname(self, hostname):
        replaced_hostname = hostname.replace('.','-')
        replaced_hostname = str(replaced_hostname)
        return replaced_hostname

    def get_master_queue_name_from_hostname(self):
        queue = "master.%s" % (self.get_queue_name_from_hostname())
        return queue

    def get_routing_key(self, hostname):
        return "%s.host" % (self.get_queue_name_from_hostname(hostname))

    def get_master_routing_key(self):
        return "master.action"

    def mq_default_args(self):
        current_ms = str(time.time())
        hash_string = "%s%s" % (self.group_name, current_ms)
        ret_obj = {}
        ret_obj['hash'] = hashlib.sha1(hash_string).hexdigest()
        ret_obj['args'] = []
        ret_obj['timestamp'] = dt.datetime.now().strftime("%Y-%m-%d %H:%I:%s")
        return ret_obj

    @property
    def sorted_systems_list(self):
        ret_list = []
        query = "select id, system_id, update_group_id from update_groups where update_group_id = :id order by id"
        result = db.engine.execute(text(query), id=self.id)
        for system in result:
            system_id = int(system[1])
            tmp = {}
            tmp['id'] = system_id
            try:
                tmp['hostname'] = System.get_by_id(system_id).hostname
            except AttributeError:
                continue
            ret_list.append(tmp)
        return ret_list

    def start_update(self, channel, concurrent=False):
        if concurrent == True:
            for host in self.systems:
                queue = self.get_queue_name_from_hostname(host.hostname)
                routing_key = self.get_routing_key(hostname)
                current_ms = str(time.time())
                start_update_obj = self.mq_default_args()
                start_update_obj['command'] = 'start_update'

                res = channel.basic_publish(
                    exchange='chorizo',
                    routing_key = routing_key,
                    body=json.dumps(start_update_obj)
                )
        else:
            queue = 'action'
            routing_key = 'action.host'
            current_ms = str(time.time())
            start_update_obj = self.mq_default_args()
            start_update_obj['command'] = 'start_group_update'
            start_update_obj['group_id'] = self.id

            res = channel.basic_publish(
                exchange='chorizo',
                routing_key = routing_key,
                body=json.dumps(start_update_obj)
            )


class SystemUpdate(SurrogatePK, Model):
    __tablename__ = 'system_updates'
    system_id = Column(db.Integer, db.ForeignKey('systems.id'))
    system = relationship("System", foreign_keys=[system_id], backref="updates")
    created_at = Column(db.DateTime, default=dt.datetime.utcnow())
    finished_at = Column(db.DateTime)
    group_id = Column(db.Integer, db.ForeignKey('update_group.id'))
    group = relationship("UpdateGroup", foreign_keys=[group_id], backref="recent_updates")
    """
        is_current
        0 = Completed
        1 = Currently running
    """
    is_current = Column(db.Boolean, nullable=False, default=1)
    """
        status_code
        0 = OK
        1 = Warning
        2 = Failed
        3 = Running
        4 = Host Rebooting
    """
    status_code = Column(db.Integer, nullable=False, default=0)

class SystemUpdateLog(SurrogatePK, Model):
    __tablename__ = 'system_update_logs'
    system_update_id = Column(db.Integer, db.ForeignKey('system_updates.id'))
    system_update = relationship("SystemUpdate", foreign_keys=[system_update_id])
    return_code = Column(db.Integer, nullable=True)
    stdout = Column(db.Text, nullable=True)
    stderr = Column(db.Text, nullable=True)
    log_text = Column(db.Text, nullable=True)
    created_at = Column(db.DateTime, default=dt.datetime.utcnow())

class ScriptAvailable(SurrogatePK, Model):
    __tablename__ = 'scripts_available'
    file_name = Column(db.String(80), unique=True, nullable=False)
    description = Column(db.Text, unique=False, nullable=False)
    created_at = Column(db.DateTime, default=dt.datetime.utcnow)
    script_exit_code_reboot = Column(db.BigInteger, default=128)
    """
        is_available
        0 = Disabled
        1 = Enabled
    """
    is_available = Column(db.Boolean, nullable=False, default=1)

class ScriptsInstalled(SurrogatePK, Model):
    __tablename__ = 'scripts_installed'
    group_id = Column(db.Integer, db.ForeignKey('update_group.id'))
    group = relationship("UpdateGroup", foreign_keys=[group_id], backref="scripts")
    script_id = Column(db.Integer, db.ForeignKey('scripts_available.id'))
    script = relationship("ScriptAvailable", foreign_keys=[script_id], backref="script")
    script_order = Column(db.Integer, default=0)
    """
        is_current
        0 = Disabled
        1 = Active
    """
    is_active = Column(db.Boolean, nullable=False, default=1)

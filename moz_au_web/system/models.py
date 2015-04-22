# -*- coding: utf-8 -*-
import datetime as dt


from moz_au_web.extensions import bcrypt
from moz_au_web.database import (
    Column,
    db,
    Model,
    ReferenceCol,
    relationship,
    SurrogatePK,
)


class System(SurrogatePK, Model):

    __tablename__ = 'systems'
    hostname = Column(db.String(80), unique=True, nullable=False)
    created_at = Column(db.DateTime, default=dt.datetime.utcnow())
    cronfile = Column(db.String(80), unique=False, nullable=False)
    
    def __repr__(self):
        return '<System({hostname!r})>'.format(hostname=self.hostname)

class SystemUpdate(SurrogatePK, Model):
    __tablename__ = 'system_updates'
    system_id = Column(db.Integer, db.ForeignKey('systems.id'))
    system = relationship("System", foreign_keys=[system_id], backref="updates")
    created_at = Column(db.DateTime, default=dt.datetime.utcnow())
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
    """
        is_available
        0 = Disabled
        1 = Enabled
    """
    is_available = Column(db.Boolean, nullable=False, default=1)

class ScriptsInstalled(SurrogatePK, Model):
    __tablename__ = 'scripts_installed'
    system_id = Column(db.Integer, db.ForeignKey('systems.id'))
    system = relationship("System", foreign_keys=[system_id], backref="system")
    script_id = Column(db.Integer, db.ForeignKey('scripts_available.id'))
    script = relationship("ScriptAvailable", foreign_keys=[script_id], backref="script")
    script_order = Column(db.Integer, default=0)
    """
        is_current
        0 = Disabled
        1 = Active
    """
    is_active = Column(db.Boolean, nullable=False, default=1)

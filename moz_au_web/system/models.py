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
    def __repr__(self):
        return '<System({hostname!r})>'.format(hostname=self.hostname)

class SystemBackup(SurrogatePK, Model):
    __tablename__ = 'system_backups'
    system_id = Column(db.Integer, db.ForeignKey('systems.id'))
    system = relationship("System", foreign_keys=[system_id], backref="backups")
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

class SystemBackupLog(SurrogatePK, Model):
    __tablename__ = 'system_backup_logs'
    system_backup_id = Column(db.Integer, db.ForeignKey('system_backups.id'))
    system_backup = relationship("SystemBackup", foreign_keys=[system_backup_id])
    return_code = Column(db.Integer, nullable=True)
    stdout = Column(db.Text, nullable=True)
    stderr = Column(db.Text, nullable=True)
    log_text = Column(db.Text, nullable=True)


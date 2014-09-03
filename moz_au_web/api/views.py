# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''
from flask import (Blueprint, request, render_template, flash, url_for,
                    redirect, session, jsonify, make_response)
from flask.ext.login import login_user, login_required, logout_user

from moz_au_web.extensions import login_manager
from moz_au_web.user.models import User
from moz_au_web.public.forms import LoginForm
from moz_au_web.user.forms import RegisterForm
from moz_au_web.utils import flash_errors
from moz_au_web.database import db
from moz_au_web.system.models import System, SystemBackup, SystemBackupLog

blueprint = Blueprint('api', __name__, static_folder="../static", url_prefix='/api')

@login_manager.user_loader
def load_user(id):
    return User.get_by_id(int(id))

@blueprint.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@blueprint.route("/getsystemid/<hostname>/", methods=["GET"])
def getsystemid(hostname):
    ret = []
    system = System.query.filter_by(hostname=hostname).first()
    if not system:
        system = System(hostname=hostname).save()

    s_dict = {}
    s_dict['id'] = system.id
    s_dict['hostname'] = system.hostname
    s_dict['created_at'] = system.created_at
    ret.append(s_dict)
    return jsonify({
        'total_count': 1,
        'limit': 1,
        'offset': 0,
        'system': s_dict}
    )
@blueprint.route("/system/", methods=["GET", "POST"])
def system():
    ret = []
    limit=request.args.get('limit', 100)
    offset=request.args.get('offset', 0)
    hostname=request.args.get('hostname', 0)
    systems = System.query
    total = len(systems.all())
    if hostname:
        systems = systems.filter(System.hostname.like('%' + hostname + '%'))

    systems = systems.limit(limit).offset(offset).all()
    for s in systems:
        s_dict = {}
        s_dict['hostname'] = s.hostname
        s_dict['created_at'] = s.created_at
        ret.append(s_dict)
    return jsonify({
        'total_count': total,
        'limit': limit,
        'offset': offset,
        'systems': ret}
    )

@blueprint.route("/system/<id>/", methods=["GET"])
def read_system(id):
    try:
        id = int(id)
        is_id = True
    except ValueError:
        is_id = False

    if is_id:
        system = System.get_by_id(id)
    else:
        system = System.query.filter_by(hostname=id).first()

    if system == None:
        return make_response(jsonify({'error': 'Cannot find system'}), 404)

    s_dict = {}
    s_dict['id'] = system.id
    s_dict['hostname'] = system.hostname
    s_dict['created_at'] = system.created_at
    return make_response(jsonify({'system': s_dict}), 200)

@blueprint.route("/system/<hostname>/", methods=["POST"])
def create_system(hostname):
    s = System()
    s.hostname = hostname
    s.save()
    s_dict = {}
    s_dict['id'] = s.id
    s_dict['hostname'] = s.hostname
    s_dict['created_at'] = s.created_at
    return make_response(jsonify({'system': ret}), 200)

@blueprint.route("/system/<hostname>/", methods=["PUT"])
def update_system():
    s = System()
    s.hostname = hostname
    s.save()
    s_dict = {}
    s_dict['id'] = s.id
    s_dict['hostname'] = s.hostname
    s_dict['created_at'] = s.created_at
    return make_response(jsonify({'system': ret}), 200)

@blueprint.route("/system/<id>/", methods=["DELETE"])
def delete_system(id):
    s = System.get_by_id(id)
    s.delete()
    return make_response(jsonify({'success': 'success'}), 200)


@blueprint.route("/backups/<hostname>", methods=["GET", "POST"])
def backups(hostname):
    ret = []
    limit=request.args.get('limit', 100)
    offset=request.args.get('offset', 0)
    s_system = System.query.filter_by(hostname=hostname).first()
    backups = SystemBackup.query.filter(SystemBackup.system==s_system).order_by('-created_at').limit(limit).all()
    s_ret = []
    for b in backups:
        tmp = {}
        tmp['id'] = b.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        tmp['hostname'] = hostname
        tmp['current'] = b.is_current
        tmp['status'] = b.status_code
        s_ret.append(tmp)

    total = len(s_system.backups)
    return jsonify({
        'total_count': total,
        'limit': limit,
        'offset': offset,
        'backups': s_ret}
    )
@blueprint.route("/backupdetail/<id>", methods=["GET", "POST"])
def backupdetail(id):
    s_backup = SystemBackup.get_by_id(id)
    ret = []
    backups = SystemBackupLog.query.filter(SystemBackupLog.system_backup==s_backup).order_by('created_at').all()
    s_ret = []
    for b in backups:
        tmp = {}
        tmp['id'] = b.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        tmp['hostname'] = b.system_backup.system.hostname
        tmp['stdout'] = b.stdout
        tmp['log_text'] = b.log_text
        tmp['stderr'] = b.stderr
        tmp['return_code'] = b.return_code
        s_ret.append(tmp)

    total = len(backups)
    try:
        hostname = b.system_backup.system.hostname
    except (IndexError, AttributeError):
        hostname = ''
    return jsonify({
        'total_count': total,
        'hostname': hostname,
        'backups': s_ret}
    )

@blueprint.route("/recentbackupdetail/", methods=["GET"])
def recentbackupdetail():
    ret = []
    limit = request.args.get('limit', 20)
    backups = SystemBackupLog.query.order_by('-created_at').limit(limit).all()
    s_ret = []
    for b in backups:
        tmp = {}
        tmp['id'] = b.id
        tmp['backup_id'] = b.system_backup.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        tmp['hostname'] = b.system_backup.system.hostname
        #tmp['stdout'] = b.stdout
        tmp['log_text'] = b.log_text
        #tmp['stderr'] = b.stderr
        tmp['return_code'] = b.return_code
        s_ret.append(tmp)

    return jsonify({
        'backups': s_ret}
    )

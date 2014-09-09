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
from moz_au_web.system.models import System, SystemUpdate, SystemUpdateLog
import json
import datetime

blueprint = Blueprint('api', __name__, static_folder="../static", url_prefix='/api')

@login_manager.user_loader
def load_user(id):
    return User.get_by_id(int(id))

@blueprint.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

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
    s.created_at = datetime.datetime.utcnow()
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


@blueprint.route("/updates/<hostname>", methods=["GET", "POST"])
def updates(hostname):
    ret = []
    limit=request.args.get('limit', 100)
    offset=request.args.get('offset', 0)
    s_system = System.query.filter_by(hostname=hostname).first()
    updates = SystemUpdate.query.filter(SystemUpdate.system==s_system).order_by('-id').limit(limit).all()
    s_ret = []
    for b in updates:
        tmp = {}
        tmp['id'] = b.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        tmp['hostname'] = hostname
        tmp['current'] = b.is_current
        tmp['status'] = b.status_code
        s_ret.append(tmp)

    total = len(s_system.updates)
    return jsonify({
        'total_count': total,
        'limit': limit,
        'offset': offset,
        'updates': s_ret}
    )
@blueprint.route("/updatedetail/<id>", methods=["GET", "POST"])
def updatedetail(id):
    s_update = SystemUpdate.get_by_id(id)
    ret = []
    updates = SystemUpdateLog.query.filter(SystemUpdateLog.system_update==s_update).order_by('id').all()
    s_ret = []
    for b in updates:
        tmp = {}
        tmp['id'] = b.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        tmp['hostname'] = b.system_update.system.hostname
        tmp['stdout'] = b.stdout
        tmp['log_text'] = b.log_text
        tmp['stderr'] = b.stderr
        tmp['return_code'] = b.return_code
        s_ret.append(tmp)

    total = len(updates)
    try:
        hostname = s_update.system.hostname
    except (IndexError, AttributeError):
        hostname = ''
    return jsonify({
        'total_count': total,
        'hostname': hostname,
        'updates': s_ret}
    )

@blueprint.route("/recentupdatedetail/", methods=["GET"])
def recentupdatedetail():
    ret = []
    limit = request.args.get('limit', 20)
    updates = SystemUpdateLog.query.order_by('-id').limit(limit).all()
    s_ret = []
    for b in updates:
        tmp = {}
        tmp['id'] = b.id
        tmp['update_id'] = b.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        try:
            tmp['hostname'] = b.system_update.system.hostname
        except AttributeError:
            tmp['hostname'] = ''
        #tmp['stdout'] = b.stdout
        tmp['log_text'] = b.log_text
        #tmp['stderr'] = b.stderr
        tmp['return_code'] = b.return_code
        s_ret.append(tmp)

    return jsonify({
        'updates': s_ret}
    )

@blueprint.route("/logcapture/", methods=["GET", "POST"])
def logcapture():
    log_obj = json.loads(request.data)
    s = SystemUpdateLog()
    s.return_code = log_obj['return_code']
    s.stdout = log_obj['stdout']
    s.stderr = log_obj['stderr']
    try:
        s.log_text = log_obj['message']
    except KeyError:
        pass
    s.created_at = datetime.datetime.utcnow()
    try:
        s.log_text = log_obj['log_text']
    except KeyError:
        pass
    system_update = SystemUpdate.query.filter_by(system_id=log_obj['system_id']).filter_by(is_current=1).first()
    s.system_update_id = system_update.id
    s.save()
    return make_response('OK', 200)

@blueprint.route("/finishupdate/<id>/", methods=["GET", "POST"])
def finishupdate(id):
    current_update = SystemUpdate.query.filter_by(system_id=id).filter_by(is_current=1).first()
    if current_update:
        current_update.is_current = False
        current_update.save()
        update_log = SystemUpdateLog()
        update_log.system_update_id = current_update.id
        update_log.log_text = "Update Finished"
        update_log.created_at = datetime.datetime.utcnow()
        update_log.return_code = 0
        update_log.save()
        log_id = current_update.id
    else:
        log_id = -1

    return make_response(
        jsonify(
            {
                'total_count': 1,
                'limit': 1,
                'offset': 0,
                'id': log_id
            }
        ), 200)

@blueprint.route("/createupdate/<id>/", methods=["POST"])
def createupdate(id):
    current_update = SystemUpdate.query.filter_by(system_id=id).order_by('-id').first()
    if current_update:
        current_update.is_current = False
        current_update.save()
    new_update = SystemUpdate(system_id=id, is_current=True, created_at=datetime.datetime.utcnow()).save()
    update_log = SystemUpdateLog()
    update_log.system_update_id = new_update.id
    update_log.log_text = "Update Started"
    update_log.system_id = id
    update_log.return_code = 0
    update_log.created_at = datetime.datetime.utcnow()
    update_log.save()
    return make_response(
        jsonify(
            {
                'total_count': 1,
                'limit': 1,
                'offset': 0,
                'id': new_update.id
            }
        ), 200)

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
    return jsonify({
        'total_count': 1,
        'limit': 1,
        'offset': 0,
        'system': s_dict}
    )

# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''
from flask import (Blueprint, request, render_template, flash, url_for,
                    redirect, session, jsonify, make_response, current_app)
from flask.ext.login import login_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError

from moz_au_web.extensions import login_manager
from moz_au_web.user.models import User
from moz_au_web.public.forms import LoginForm
from moz_au_web.user.forms import RegisterForm
from moz_au_web.utils import flash_errors
from moz_au_web.database import db
from celery_tasks import async_ping, async_start_update
from moz_au_web.system.models import System, SystemUpdate, SystemUpdateLog, ScriptAvailable, ScriptsInstalled
from moz_au_web.system.models import UpdateGroup
import json
import datetime

blueprint = Blueprint('api', __name__, static_folder="../static", url_prefix='/api')

def get_es():
    es = ES(current_app.config['ES_SERVER'])
    return es

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
        s_dict['cronfile'] = s.cronfile
        s_dict['created_at'] = s.created_at
        ret.append(s_dict)
    return jsonify({
        'total_count': total,
        'limit': limit,
        'offset': offset,
        'systems': ret}
    )

@blueprint.route("/cronfile/<id>/", methods=["GET"])
def cronfile(id):
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
    s_dict['cronfile'] = system.cronfile
    return make_response(jsonify({'system': s_dict}), 200)

@blueprint.route("/groups/", methods=["GET"])
def groups():
    limit=request.args.get('limit', 100)
    offset=request.args.get('offset', 0)

    all_groups = UpdateGroup.query.all()
    total_count = len(all_groups)
    r_list = []
    for g in all_groups:
        tmp = {}
        tmp['id'] = g.id
        tmp['group_name'] = g.group_name
        r_list.append(tmp)
    return jsonify({
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
        'groups': r_list}
    )
    return make_response(jsonify({'groups': s_dict}), 200)

@blueprint.route("/groups/create/", methods=["POST"])
def groups_create():
    json_data = request.get_json()
    try:
        u_group = UpdateGroup()
        u_group.group_name = json_data.get('group_name')
        u_group.save()
    except:
        return make_response(jsonify({'groups': s_dict}), 200)

    message = 'Group Created'
    return make_response(jsonify({'message': message}), 200)

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

    if system is None:
        return make_response(jsonify({'error': 'Cannot find system'}), 404)

    s_dict = {}
    s_dict['id'] = system.id
    s_dict['hostname'] = system.hostname
    s_dict['cronfile'] = system.cronfile
    s_dict['created_at'] = system.created_at
    s_dict['pings'] = []
    counter = 0
    ping_limit = 5
    for ping in reversed(system.pings):
        tmp = {}
        tmp['id'] = ping.id
        tmp['success'] = ping.success
        try:
            tmp['ping_time'] = ping.ping_time.strftime("%Y-%m-%d %H:%I:%S")
        except AttributeError:
            tmp['ping_time'] = ''

        try:
            tmp['pong_time'] = ping.pong_time.strftime("%Y-%m-%d %H:%I:%S")
        except AttributeError:
            tmp['pong_time'] = ''

        if counter < ping_limit:
            s_dict['pings'].append(tmp)
        else:
            continue
        counter += 1
    return make_response(jsonify({'system': s_dict}), 200)

@blueprint.route("/updatecronfile/<id>/", methods=["POST"])
def updatecronfile(id):
    s = System.get_by_id(id)
    s.cronfile = request.get_json()['cronfile']
    s.save()
    return make_response(jsonify({'status': 'OK'}), 200)

@blueprint.route("/system/<hostname>/", methods=["POST"])
def create_system(hostname):
    s = System()
    s.hostname = hostname
    s.created_at = datetime.datetime.utcnow()
    s.save()
    s_dict = {}
    s_dict['id'] = s.id
    s_dict['hostname'] = s.hostname
    s_dict['cronfile'] = s.cronfile
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
    s_dict['cronfile'] = s.cronfile
    s_dict['created_at'] = s.created_at
    return make_response(jsonify({'system': ret}), 200)

@blueprint.route("/system/<id>/", methods=["DELETE"])
def delete_system(id):
    s = System.get_by_id(id)
    s.delete()
    return make_response(jsonify({'success': 'success'}), 200)

@blueprint.route("/ping/<hostname>/", methods=["GET"])
def ping(hostname):
    s = System.query.filter_by(hostname=hostname).first()
    if not s is None:
        res = async_ping.delay(s, current_app.config)
        #res.wait()
    return make_response(jsonify({'success': 'success'}), 200)

@blueprint.route("/start_update/<hostname>/", methods=["GET"])
def start_update(hostname):
    s = System.query.filter_by(hostname=hostname).first()
    if not s is None:
        res = async_start_update.delay(s, current_app.config)
    return make_response(jsonify({'success': 'success'}), 200)


@blueprint.route("/updates/<hostname>", methods=["GET", "POST"])
def updates(hostname):
    ret = []
    limit=request.args.get('limit', 100)
    offset=request.args.get('offset', 0)
    s_system = System.query.filter_by(hostname=hostname).first()
    total_count = SystemUpdate.query.filter(SystemUpdate.system==s_system).count()
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

    return jsonify({
        'total_count': total_count,
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

@blueprint.route("/recentupdateonly/", methods=["GET"])
def recentupdateonly():
    limit = request.args.get('limit', 20)
    #s = System.query.filter_by(hostname=hostname).first()
    #if not s is None:
    #    updates = SystemUpdate.query.filter_by(system_id=s.id).order_by('-id').limit(limit).all()
    #else:
    #    return 'System Not Found'
    updates = SystemUpdate.query.order_by('-id').limit(limit).all()
    s_ret = []
    for b in updates:
        tmp = {}
        tmp['id'] = b.id
        tmp['update_id'] = b.id
        tmp['created_at'] = b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        try:
            tmp['hostname'] = b.system.hostname
        except AttributeError:
            tmp['hostname'] = ''
        s_ret.append(tmp)

    return jsonify({
        'updates': s_ret}
    )
@blueprint.route("/recentupdatedetail/", methods=["GET"])
def recentupdatedetail():
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

@blueprint.route("/scriptdetail/<id>/", methods=["GET"])
def scriptdetail(id):
    s = ScriptAvailable.get_by_id(id)
    s_obj = {}
    s_obj['id'] = s.id
    s_obj['file_name'] = s.file_name
    s_obj['description'] = s.description
    return jsonify({
        'total_count': 1,
        'limit': 0,
        'offset': 0,
        'script': s_obj}
    )

@blueprint.route("/scriptedit/<id>/", methods=["GET", "POST"])
def scriptedit(id):
    s = ScriptAvailable.get_by_id(id)
    json_data = request.get_json()
    s.file_name = json_data['file_name']
    s.description = json_data['description']
    try:
        s.save()
    except IntegrityError:
        return make_response("Script with this name already exists.", 500)
    return make_response('OK', 200)

@blueprint.route("/scriptcreate/", methods=["GET", "POST"])
def scriptcreate():
    s = ScriptAvailable()
    json_data = request.get_json()
    s.file_name = json_data['file_name']
    s.description = json_data['description']
    try:
        s.save()
    except IntegrityError:
        return make_response("Script with this name already exists.", 500)
    return make_response('OK', 200)

@blueprint.route("/createupdate/<id>/", methods=["GET", "POST"])
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

@blueprint.route("/updatehostscripts/<hostname>/", methods=["GET", "POST"])
def updatehostscripts(hostname):
    ret = []
    s_dict = []
    if request.method == "POST":
        host = System.query.filter_by(hostname=hostname).first()
        # @TODO: Figure out a better way to delete than this
        current_scripts = ScriptsInstalled.query.filter_by(system=host).all()
        for c in current_scripts:
            c.delete()
        data = request.get_json()
        order = 0
        for i in data:
            available_script = ScriptAvailable.get_by_id(i['id'])
            if not available_script is None:
                tmp = ScriptsInstalled()
                tmp.script = available_script
                tmp.script_order = order
                tmp.system = host
                tmp.save()
                order += 1
    return jsonify({
        'total_count': len(s_dict),
        'limit': 0,
        'offset': 0,
        'scripts': s_dict}
    )

@blueprint.route("/hostscripts/<hostname>/", methods=["GET"])
def hostscripts(hostname):
    ret = []
    s_dict = []
    host = System.query.filter_by(hostname=hostname).first()
    all_scripts = ScriptsInstalled.query.filter_by(system_id = host.id).order_by('script_order').all()
    for s in all_scripts:
        tmp = {}
        tmp['id'] = s.script.id
        tmp['file_name'] = s.script.file_name
        tmp['order'] = s.script_order
        s_dict.append(tmp)
    return jsonify({
        'total_count': len(s_dict),
        'limit': 0,
        'offset': 0,
        'scripts': s_dict}
    )

@blueprint.route("/scripts/", methods=["GET"])
def scripts():
    ret = []
    s_dict = []
    all_scripts = ScriptAvailable.query.all()
    for s in all_scripts:
        tmp = {}
        tmp['id'] = s.id
        tmp['file_name'] = s.file_name
        tmp['description'] = s.description
        s_dict.append(tmp)
    return jsonify({
        'total_count': len(s_dict),
        'limit': 0,
        'offset': 0,
        'scripts': s_dict}
    )
@blueprint.route("/getsystemid/<hostname>/", methods=["GET"])
def getsystemid(hostname):
    ret = []
    system = System.query.filter_by(hostname=hostname).first()
    if not system:
        system = System(hostname=hostname)
        system.cronfile = "0 0 0 * *"
        system.save()

    s_dict = {}
    s_dict['id'] = system.id
    s_dict['hostname'] = system.hostname
    s_dict['cronfile'] = system.cronfile
    s_dict['created_at'] = system.created_at
    return jsonify({
        'total_count': 1,
        'limit': 1,
        'offset': 0,
        'system': s_dict}
    )

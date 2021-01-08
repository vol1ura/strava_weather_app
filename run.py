import manage_db
import os
from pprint import pprint
import utilities

from flask import Flask, render_template, url_for, request, abort, make_response, g, flash, redirect
from flask_restful import reqparse


app = Flask(__name__)


@app.route('/')
def index():
    redirect_uri = url_for('auth', _external=True)
    url_to_get_code = utilities.make_link_to_get_code(redirect_uri)
    return render_template('index.html', url_to_get_code=url_to_get_code)


@app.route('/authorization_successful', methods=['GET'])
def auth():
    code = request.values.get('code', None)
    if not code:
        return abort(500)
    tokens = utilities.get_tokens(code)
    try:
        athlete = tokens['athlete']['firstname'] + ' ' + tokens['athlete']['lastname']
        data = (tokens['athlete']['id'], tokens['access_token'], tokens['refresh_token'], tokens['expires_at'])
    except KeyError:
        return abort(500)
    if manage_db.add_athlete(data):
        return render_template('authorized.html', athlete=athlete)
    else:
        return abort(500)


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        print('POST request:')
        parser = reqparse.RequestParser()
        parser.add_argument('owner_id', type=int, required=True)  # athlete's ID
        parser.add_argument('object_type', type=str, required=True)  # we need "activity" here
        parser.add_argument('object_id', type=int, required=True)  # activity's ID
        parser.add_argument('aspect_type', type=str, required=True)  # Always "create," "update," or "delete."
        parser.add_argument('updates', type=dict, required=True)  # For deauth, there is {"authorized": "false"}
        args = parser.parse_args()
        if args['aspect_type'] == 'create' and args['object_type'] == 'activity':
            # Make operation
            utilities.add_weather(args['owner_id'], args['object_id'], lan='ru')
        if not args['updates'].get('authorized', True):
            manage_db.delete_athlete(args['owner_id'])
        pprint(args)  # TODO remove after debugging
        return 'webhook ok', 200
    if request.method == 'GET':
        if utilities.is_subscribed():
            return 'You are already subscribed', 200
        req = request.values
        mode = req.get('hub.mode', '')
        token = req.get('hub.verify_token', '')
        print(mode, token)
        if mode == 'subscribe' and token == os.environ.get('STRAVA_WEBHOOK_TOKEN'):
            print('WEBHOOK_VERIFIED')
            challenge = req.get('hub.challenge', '')
            response = make_response({'hub.challenge': challenge}, 200)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            print('verify tokens do not match')
    return 'ouups... something wrong', 500


@app.route('/admin/')
def admin():
    if utilities.is_subscribed():
        return 'subscription is OK'
    else:
        return 'no subscription'


@app.route('/features/')
def features():
    return render_template('features.html')


@app.route('/contacts/')
def contacts():
    return render_template('contacts.html')


@app.errorhandler(404)
def http_404_handler(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def http_500_handler(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    isDEBUG_MODE = os.environ.get('DEBUG')
    app.run(debug=isDEBUG_MODE)

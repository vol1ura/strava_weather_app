import os
from multiprocessing import Process

from flask import Flask, url_for, render_template, request, session, abort, redirect, jsonify, send_from_directory
from flask_restful import reqparse

from utils import weather, manage_db, strava_helpers, git_helpers, env_check
from utils.exceptions import StravaAPIError


# check that all necessary environmental vars have been set...
env_check.check_env_vars()

app = Flask(__name__)
app.config.from_mapping(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SECRET_KEY=os.environ.get('SECRET_KEY'),
)

@app.route('/')
def index():
    redirect_uri = url_for('auth', _external=True)
    url_to_get_code = strava_helpers.make_link_to_get_code(redirect_uri)
    return render_template('index.html', url_to_get_code=url_to_get_code)


@app.route('/final/', methods=['POST'])
def final():
    if 'id' not in session:
        return abort(500)
    settings = manage_db.Settings(session['id'], request.values.get('units', 'imperial'))
    manage_db.add_settings(settings)
    return render_template('final.html', athlete=session['athlete'])


@app.route('/authorization_successful')
def auth():
    code = request.values.get('code', None)
    if not code:
        return abort(500)
    auth_data = strava_helpers.get_tokens(code)
    try:
        athlete = auth_data['athlete']['firstname'] + ' ' + auth_data['athlete']['lastname']
        tokens = manage_db.Tokens(
            auth_data['athlete']['id'], auth_data['access_token'],
            auth_data['refresh_token'], auth_data['expires_at']
        )
    except KeyError:
        return abort(500)
    manage_db.add_athlete(tokens)
    session['athlete'] = athlete
    session['id'] = tokens.id
    return render_template('authorized.html', athlete=athlete)


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        process_webhook_post()
        return 'webhook ok', 200
    else:
        return jsonify(process_webhook_get())


def process_webhook_post():
    parser = reqparse.RequestParser()
    parser.add_argument('owner_id', type=int, required=True)     # athlete's ID
    parser.add_argument('object_type', type=str, required=True)  # we need "activity" here
    parser.add_argument('object_id', type=int, required=True)    # activity's ID
    parser.add_argument('aspect_type', type=str, required=True)  # always "create," "update," or "delete."
    parser.add_argument('updates', type=dict, required=True)     # for de-auth, there is {"authorized": "false"}
    args = parser.parse_args()
    app.logger.info(args)
    if args['aspect_type'] == 'create' and args['object_type'] == 'activity':
        p = Process(target=weather.add_weather, args=(args['owner_id'], args['object_id']))
        p.daemon = True
        p.start()
    if args['updates'].get('authorized', '') == 'false':
        manage_db.delete_athlete(args['owner_id'])


def process_webhook_get():
    if strava_helpers.is_app_subscribed():
        return {'status': 'You are already subscribed'}
    req = request.values
    mode = req.get('hub.mode', '')
    token = req.get('hub.verify_token', '')
    if mode == 'subscribe' and token == os.environ.get('STRAVA_WEBHOOK_TOKEN'):
        print('WEBHOOK VERIFIED')
        challenge = req.get('hub.challenge', '')
        return {'hub.challenge': challenge}
    else:
        return {'error': 'verification tokens does not match'}


@app.route('/features/')
def features():
    return render_template('features.html')


@app.route('/contacts/')
def contacts():
    return render_template('contacts.html')


@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


@app.route('/update_server', methods=['POST'])
def update_server():
    x_hub_signature = request.headers.get('X-Hub-Signature')
    if not git_helpers.is_valid_signature(x_hub_signature, request.data):
        return 'wrong signature', 406
    git_helpers.pull()
    return 'Server successfully updated', 202


@app.errorhandler(404)
def http_404_handler(error):
    return render_template('404.html'), 404


@app.errorhandler(405)
def http_405_handler(error):
    return redirect(url_for('index')), 302


@app.errorhandler(500)
def http_500_handler(error):
    return render_template('500.html'), 500


@app.errorhandler(StravaAPIError)
def api_errors_handler(error):
    return 'error', 500


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))

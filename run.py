import os
import utilities

from flask import Flask, render_template, url_for, request, abort, make_response

app = Flask(__name__)


@app.route('/')
def index():
    redirect_uri = url_for('auth', _external=True)
    url_to_get_code = utilities.make_link_to_get_code(redirect_uri)
    return render_template('index.html', link_to_get_code=url_to_get_code)


@app.route('/authorization_successful/', methods=['GET'])
def auth():
    code = request.values.get('code', None)
    if not code:
        abort(500)
    token_response = utilities.get_tokens(code)
    try:
        athlete = token_response['athlete']['firstname'] + ' ' + token_response['athlete']['lastname']
    except KeyError:
        abort(500)
    else:
        return render_template('authorized.html', athlete=athlete)


@app.route('/webhook', methods=['GET'])
def webhook():
    req = request.values
    print(req)
    mode = req.get('hub.mode', '')
    token = req.get('hub.verify_token', '')
    print(mode, token)
    if mode and token:
        if mode == 'subscribe' and token == os.environ.get('STRAVA_WEBHOOK_TOKEN'):
            print('WEBHOOK_VERIFIED')
            challenge = req.get('hub.challenge')
            print(challenge)
            res = make_response({'hub.challenge': challenge}, 200)
            res.headers['Content-Type'] = 'application/json'
            return res
        else:
            print('verify tokens do not match')
    return 'ouups... something wrong', 500


@app.route('/admin/')
def admin():
    url = url_for('webhook', _external=True)
    print(url)
    subs = utilities.subscribe_webhooks(url)
    print(subs)
    return 'subscribe'


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
    app.run()  # debug=True

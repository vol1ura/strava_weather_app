import json

import responses

from utils import strava_helpers


@responses.activate
def test_get_tokens():
    expected_tokens = {'access_token': 'test_access_token', 'refresh_token': 'test_refresh_token', 'expires_at': 1000}
    responses.add(responses.POST, 'https://www.strava.com/oauth/token', body=json.dumps(expected_tokens))
    actual_tokens = strava_helpers.get_tokens(1)
    assert actual_tokens == expected_tokens


@responses.activate
def test_is_app_subscribed():
    """Should return True"""
    responses.add(responses.GET, 'https://www.strava.com/api/v3/push_subscriptions', json=[{'id': 1}])
    subscription_status = strava_helpers.is_app_subscribed()
    assert isinstance(subscription_status, bool)
    assert subscription_status


@responses.activate
def test_is_app_subscribed_not():
    """Should return False"""
    responses.add(responses.GET, 'https://www.strava.com/api/v3/push_subscriptions', json=[{}])
    subscription_status = strava_helpers.is_app_subscribed()
    assert isinstance(subscription_status, bool)
    assert not subscription_status


@responses.activate
def test_is_app_subscribed_wrong():
    """Should return False"""
    responses.add(responses.GET, 'https://www.strava.com/api/v3/push_subscriptions', body='')
    subscription_status = strava_helpers.is_app_subscribed()
    assert isinstance(subscription_status, bool)
    assert not subscription_status

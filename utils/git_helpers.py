import hashlib
import hmac
import os

import git


def pull():  # pragma: no cover
    repo = git.Repo(os.getenv('APP_PATH'))
    repo.remotes.origin.pull()


def is_valid_signature(x_hub_signature, data):
    # x_hub_signature and data are from the GitHub webhook payload
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(os.getenv('GITHUB_SECRET'), 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

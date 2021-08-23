from utils import git_helpers


def test_is_valid_signature(monkeypatch):
    payload_body = 'test'
    signature = 'sha256=aa75f94e241dc47464e24ff1f9ebd44b3f132fea4c85cd742e873f99a05d4aaf'
    monkeypatch.setenv('GITHUB_SECRET', '123abc')
    assert git_helpers.is_valid_signature(signature, bytes(payload_body, 'utf-8'))

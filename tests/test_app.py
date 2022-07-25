from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
import pytest


def make_headers(url: str, priv_key_str: str, pub_key: str) -> dict:
    priv_key: rsa.RSAPrivateKey = serialization.load_pem_private_key(
        priv_key_str.encode('utf8'), None
    )
    signature = b64encode(
        priv_key.sign(
            url.encode('utf8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    ).decode('utf8')
    return {
        'Authorization': pub_key,
        'X-Signature': signature,
    }


def test_list_plugins(client: TestClient):
    response = client.get('/v1/plugins?page=1&page_size=10')
    assert response.status_code == 200, response.text
    assert len(response.json()['data']) == 3


def test_list_plugin_versions(client: TestClient):
    n_versions = [4, 1, 1]
    for i, n_version in enumerate(n_versions, start=1):
        response = client.get(f'/v1/plugins/plugin_{i}/versions')
        assert response.status_code == 200, response.text
        assert len(response.json()['data']) == n_version

    response = client.get('/v1/plugins/plugin_0')
    assert response.status_code == 404, response.text
    assert response.json()['detail'] == 'Plugin plugin_0 not found.', response.text


def test_get_plugin_version_latest(client: TestClient):
    versions = ['2.0.1', '1.0.0', '1.0.0']
    for i, version in enumerate(versions, start=1):
        response = client.get(f'/v1/plugins/plugin_{i}/versions/latest')
        assert response.status_code == 200, response.text
        data = response.json()['data']
        assert data['version'] == version

    response = client.get('/v1/plugins/plugin_0/versions/latest')
    assert response.status_code == 404, response.text
    assert response.json()['detail'] == 'Plugin plugin_0 not found.', response.text


def test_get_plugin_version(client: TestClient):
    versions = [
        {
            "id": 1,
            "version": "1.0.0",
            "plugin_id": 1
        },
        {
            "id": 2,
            "version": "1.1.0",
            "plugin_id": 1
        },
        {
            "id": 3,
            "version": "2.0.0",
            "plugin_id": 1
        },
        {
            "id": 4,
            "version": "1.0.0",
            "plugin_id": 2
        },
        {
            "id": 5,
            "version": "2.0.1",
            "plugin_id": 1
        },
        {
            "id": 6,
            "version": "1.0.0",
            "plugin_id": 3
        }
    ]

    for v in versions:
        response = client.get(f'/v1/plugins/plugin_{v["plugin_id"]}/versions/{v["version"]}')
        assert response.status_code == 200
        assert response.json()['data']['id'] == v['id']

    response = client.get('/v1/plugins/plugin_0/versions/1.0.0')
    assert response.status_code == 404
    assert response.json()['detail'] == 'Plugin plugin_0 not found.'

    response = client.get('/v1/plugins/plugin_1/versions/0.0.0')
    assert response.status_code == 404
    assert response.json()['detail'] == 'Version 0.0.0 not found for plugin plugin_1.'


def test_create_plugin_ok(client: TestClient, pub_key_johndoe: str):
    payload = {
        'name': 'plugin_4'
    }
    headers = {
        'X-Maintainer-Email': 'john.doe@example.com',
        'Authorization': pub_key_johndoe
    }
    response = client.post(
        '/v1/plugins', json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    plugin = client.get('/v1/plugins/plugin_4').json()['data']
    assert plugin['name'] == 'plugin_4'
    assert plugin['id'] == 4
    assert 'john.doe@example.com' in plugin['maintainers']


def test_create_plugin_already_exists(client: TestClient, pub_key_johndoe: str):
    payload = {
        'name': 'plugin_1'
    }
    headers = {
        'X-Maintainer-Email': 'john.doe@example.com',
        'Authorization': pub_key_johndoe
    }
    response = client.post(
        '/v1/plugins', json=payload,
        headers=headers,
    )

    assert response.status_code == 406, response.text


def test_create_plugin_no_auth(client: TestClient):
    payload = {
        'name': 'plugin_4'
    }
    headers = {
        'X-Maintainer-Email': 'john.doe@example.com',
    }
    response = client.post(
        '/v1/plugins', json=payload,
        headers=headers,
    )

    assert response.status_code == 403, response.text


def test_create_plugin_create_maintainer(client: TestClient, pub_key_newguy: str):
    payload = {
        'name': 'plugin_4'
    }
    headers = {
        'X-Maintainer-Email': 'new.guy@example.com',
        'Authorization': pub_key_newguy
    }
    response = client.post(
        '/v1/plugins', json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    response = client.get('/v1/plugins/plugin_4/maintainers')

    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert 'new.guy@example.com' in [d['email'] for d in data], 'new.guy@example.com not in maintainers list.'  # noqa


@pytest.mark.skip
def test_add_new_maintainer_to_plugin(
    client: TestClient, pub_key_newguy: str, priv_key_johndoe: str, pub_key_johndoe: str
):
    payload = {
        'email': 'new.guy@example.com',
        'ssh_key': pub_key_newguy,
    }
    headers = make_headers(
        '/v1/plugins/plugin_1/maintainers',
        priv_key_johndoe,
        pub_key_johndoe,
    )
    headers['X-Maintainer-Email'] = 'new.guy@example.com'
    response = client.post(
        '/v1/plugins/plugin_1/maintainers',
        json=payload, headers=headers
    )
    assert response.status_code == 201, response.text


@pytest.mark.skip
def test_add_existing_maintainer_to_plugin(
    client: TestClient, pub_key_johndoe: str, priv_key_spameggs: str, pub_key_spameggs: str
):
    payload = {
        'email': 'john.doe@example.com',
        'ssh_key': pub_key_johndoe,
    }
    headers = make_headers(
        '/v1/plugins/plugin_2/maintainers',
        priv_key_spameggs, pub_key_spameggs,
    )
    headers['X-Maintainer-Email'] = 'john.doe@example.com'
    response = client.post(
        '/v1/plugins/plugin_2/maintainers',
        json=payload, headers=headers
    )
    assert response.status_code == 200, response.text


@pytest.mark.skip
def test_create_plugin_version(
    client: TestClient, file: dict, monkeypatch: pytest.MonkeyPatch,
    data_dir: Path, pub_key_johndoe: str, priv_key_johndoe: str
):
    monkeypatch.setenv('DIRECTORY_PATH', str(data_dir / 'store'))
    headers = make_headers(
        '/v1/plugins/plugin_1/versions/3.0.0',
        priv_key_johndoe, pub_key_johndoe
    )
    response = client.post(
        '/v1/plugins/plugin_1/versions/3.0.0',
        files=file, headers=headers
    )

    assert response.status_code == 201, response.text

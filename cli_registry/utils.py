from base64 import b64decode, b85encode
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import padding


def check_auth(
    message: bytes, authorization: str, x_signature: str,
) -> bool:
    '''Checks that the user is properly authorized and that the signature is valid'''
    key = crypto_serialization.load_ssh_public_key(authorization.encode('utf8'))
    try:
        key.verify(
            b64decode(x_signature),
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return False
    return True


def encode_file(file_path: Path) -> str:
    try:
        with open(file_path, 'rb') as fp:
            return b85encode(fp.read(), True).decode('utf8')
    except FileNotFoundError:
        return ''

from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from cli_registry.utils import check_auth, encode_file


def test_encode_file(data_dir: Path):
    encoded = encode_file(data_dir / 'plugin.tar.gz')
    expected = (
        'ABzY8SuEya00Zq*O^e$w5Z$wX#axUmu(k5y#Kn+O=%qchd)Qoh3f@?51<?nRTu6R>B{_E5'
        'Z8p%u(p|_vqLK7wp5BuZy&JxBN%a2a<$_YWtSSg&y<EhR-i`ARWxXh&tnO<6S=6)wT2}Rv'
        '-T-~UGtDtr*BXBm%Y~AU%5-cm*%_RN_5FoDqZXLQHxdY;<fD>5nQ<1n)-elCLC5=^873X{'
        '%81t4B;dHv%D9MfT(BhRjS^t^_6HodwBgcCIJei#BuTQ_`0kb~x!J%9P)R7EC~39!vxp(<'
        '@SS0g{ot3$RteF{&M$PVk91k!^EV)L1D+uVVH<c<YB#sI*UmF!YcsGMP*DhrFoxoNfHw*F'
        '@Cs(3EzAuAKtU_v^TYkSB`qUgP#bD^ADChq;#72dyMof+bKHumv&j}RC&8Y%<Rk$TZq?{('
        'hH>m*m>Y})dfovK&mt^zZooQ|$LZK3E<E)CrQeEF6lu3kKQ-x>CVfEBma!z}J;KQ)hXNVI'
        '8*YzG7p;2E1b;XklDL&0JN>f-?vRb*|02latsInOXN~ykH==TPxcDIc6m?Yk+wUNdKwz2l'
        'K64z;fBqqy1czlj_aKJpUAy&9{J>?eR&&uLiwtgyNo%LM2d<_ZKe7ITt^fOv<{H<y#;c28'
        'Pcl6X015yA'
    )
    assert encoded == expected, encoded


def test_check_auth(data_dir: Path):
    message = b'Hello, World!'
    pub_key = (data_dir / 'maintainers/john.doe.pub').read_text()
    priv_key_str = (data_dir / 'maintainers/john.doe').read_text()
    priv_key: rsa.RSAPrivateKey = serialization.load_pem_private_key(
        priv_key_str.encode('utf8'), None
    )
    signature = b64encode(
        priv_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    ).decode('utf8')

    assert check_auth(message, pub_key, signature), signature

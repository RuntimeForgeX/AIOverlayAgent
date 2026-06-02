"""
RS256 public key for offline JWT verification.
Auto-synced from license-server/keys/public.pem — run: npm run keys:sync-python
"""

LICENSE_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwXr75QleuZqNDA3vp1xo
lZaRVP3i3nIf2g1Kx1hYlQLo63SJKuh5ZGN8rgaYNxo9PfoHyPR0cdIYIWCGgJeX
f5Zhm/cQoSaFG8kYifh3MzKEMpLoMQ2AJCHxpVN0eVYk0fMV3aFCAhH2r7Fs1T5n
r2fn/wg1BYisr92aoyXilqAME5EKNC4Y6oRstixDH8jAOA7wQHJmuftLJJCKVf5+
TdSd6qj+nhyKZxMhfeb3t1taNPFKaUHWXFyK6VjjZ4A2kcBBv+1NtCvB7VoXsbG4
zsdaY7nde1Iy685A2qSe4xU1fH9U4my47sCU98NfIy6Dc/03xBkCnl72ZmuvGO/O
jwIDAQAB
-----END PUBLIC KEY-----"""


def get_license_public_key():
    pem = (LICENSE_PUBLIC_KEY_PEM or "").strip()
    if "REPLACE_WITH" in pem:
        return None
    return pem

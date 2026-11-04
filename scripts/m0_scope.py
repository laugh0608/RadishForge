"""Exact Gitea M0 scope profiles; no network or application authorization service."""
import json
from pathlib import Path
import urllib.parse

PROFILE_PATH = Path(__file__).resolve().parent.parent / 'tests/contracts/m0/gitea-auth-profile.json'


class ProfileError(ValueError):
    """A requested authorization is outside the reviewed M0 profile."""


def load_contract(path=PROFILE_PATH):
    data = json.loads(Path(path).read_text())
    if (set(data) != {'schema_version', 'provider', 'provider_version', 'client_registration',
                     'test_provider_settings', 'test_security_settings', 'profiles'}
            or data['schema_version'] != 2 or data['provider'] != 'gitea'
            or data['provider_version'] != '28.2.0'):
        raise ProfileError('Unsupported M0 authorization contract')
    registration = data['client_registration']
    if (set(registration) != {'confidential_client', 'skip_secondary_authorization', 'redirect_uris'}
            or registration['confidential_client'] is not True
            or registration['skip_secondary_authorization'] is not False
            or len(registration['redirect_uris']) != 1):
        raise ProfileError('Confidential client and explicit consent are required')
    redirect = urllib.parse.urlsplit(registration['redirect_uris'][0])
    if (redirect.scheme != 'http' or redirect.hostname != '127.0.0.1'
            or redirect.username or redirect.password or not redirect.port
            or redirect.path != '/callback' or redirect.query or redirect.fragment):
        raise ProfileError('Only the registered M0 loopback callback is accepted')
    settings = data['test_provider_settings']
    if (set(settings) != {'INVALIDATE_REFRESH_TOKENS', 'ACCESS_TOKEN_EXPIRATION_TIME',
                         'REFRESH_TOKEN_EXPIRATION_TIME', 'DEFAULT_APPLICATIONS'}
            or settings['INVALIDATE_REFRESH_TOKENS'] is not True
            or type(settings['ACCESS_TOKEN_EXPIRATION_TIME']) is not int
            or not 5 <= settings['ACCESS_TOKEN_EXPIRATION_TIME'] <= 60
            or type(settings['REFRESH_TOKEN_EXPIRATION_TIME']) is not int
            or settings['REFRESH_TOKEN_EXPIRATION_TIME'] != 1
            or settings['DEFAULT_APPLICATIONS'] != ''):
        raise ProfileError('Invalid short-lived M0 provider settings')
    security = data['test_security_settings']
    if set(security) != {'DISABLE_QUERY_AUTH_TOKEN'} or security['DISABLE_QUERY_AUTH_TOKEN'] is not True:
        raise ProfileError('Reviewed profiles require header-only resource authentication')
    if set(data['profiles']) != {'identity', 'resource_read', 'issue_write', 'release_write'}:
        raise ProfileError('Unexpected M0 authorization purpose')
    for profile in data['profiles'].values():
        scopes = profile['scopes']
        if (set(profile) != {'issuer', 'scopes'} or not isinstance(scopes, list)
                or not scopes or any(not isinstance(s, str) or not s or any(c.isspace() for c in s) for s in scopes)
                or len(set(scopes)) != len(scopes)):
            raise ProfileError('Invalid profile scope declaration')
        origin = urllib.parse.urlsplit(profile['issuer'])
        if (origin.scheme != 'https' or origin.hostname != 'localhost'
                or origin.port not in (18443, 19443) or origin.path
                or origin.query or origin.fragment or origin.username or origin.password):
            raise ProfileError('Profile issuer is outside the local validation origins')
    return data


def scope_for(profile_name, requested=None, *, origin=None):
    """Accept a complete reviewed combination, never arbitrary subsets or a union."""
    profiles = load_contract()['profiles']
    if not isinstance(profile_name, str) or profile_name not in profiles:
        raise ProfileError('Unknown authorization purpose')
    profile = profiles[profile_name]
    if origin is not None and origin != profile['issuer']:
        raise ProfileError('Issuer does not match the authorization purpose')
    canonical = profile['scopes']
    if requested is None:
        parts = canonical
    elif isinstance(requested, str):
        parts = requested.split(' ')
    elif isinstance(requested, (list, tuple)):
        parts = list(requested)
    else:
        raise ProfileError('Scope must be a space-separated string or sequence')
    if (any(not isinstance(s, str) or not s for s in parts)
            or len(set(parts)) != len(parts) or set(parts) != set(canonical)):
        raise ProfileError('Scope combination is not approved for this purpose')
    return ' '.join(canonical)

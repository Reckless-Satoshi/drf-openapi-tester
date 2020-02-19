import json
import logging

import yaml

from openapi_tester.exceptions import ImproperlyConfigured

logger = logging.getLogger('openapi_tester')


def fetch_from_dir(path: str) -> dict:
    """
    Fetches json or yaml contents from a file.

    :param path: str
    :return: dict
    :raises: ImproperlyConfigured
    """
    try:
        logger.debug('Fetching OpenAPI schema from %s', path)
        with open(path, 'r') as f:
            content = f.read()
    except Exception as e:
        logger.exception('Exception raised when fetching OpenAPI schema from %s. Error: %s.', path, e)
        raise ImproperlyConfigured(
            f'\n\nCould not read the openapi specification. Please make sure the path setting is correct.\n\nError: {e}'
        )
    if '.json' in path:
        return json.loads(content)
    elif '.yaml' in path or '.yml' in path:
        return yaml.load(content, Loader=yaml.FullLoader)
    else:
        raise ImproperlyConfigured('The specified file path does not seem to point to a JSON or YAML file.')

from django.core.exceptions import ImproperlyConfigured

from django_swagger_tester.schema_loaders import _LoaderBase
from django_swagger_tester.validation.utils import get_endpoint_paths


def test_get_endpoint_paths():
    """
    Make sure the function returns a valid list of strings.
    """
    urls = list(set(get_endpoint_paths()))
    expected = [
        '/api/v1/trucks/incorrect/',
        '/api/v1/{vehicle_type}/correct/',
        '/api/v1/{vehicle_type}/incorrect/',
        '/api/v1/vehicles/',
        '/api/v1/items/',
        '/api/v1/trucks/correct/',
    ]
    assert [url in expected for url in urls]
    assert len(expected) == len(urls)


def test_valid_methods_pass():
    """
    Make sure valid methods pass the validation.
    """
    for method in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
        assert _LoaderBase().validate_method(method=method) == method


def test_invalid_methods_raise():
    """
    Make sure invalid methods raise the appropriate exception.
    """
    for method in ['test', '', -1, 22, 0.2, [], {}, (None,), None]:
        with pytest.raises(
            ImproperlyConfigured, match='is invalid. Should be one of: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD.'
        ):
            _LoaderBase().validate_method(method=method)


def test_successful_unpack():
    """
    This should run without errors.
    """

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {'test': 'test'}

    response = MockResponse()
    response.status_code = 200

    data, status_code = unpack_response(response)
    assert data == {'test': 'test'}
    assert status_code == 200


def test_unsuccesful_unpack():
    """
    Verify that the appropriate error is raised when unpack fails.
    """

    class NonJsonMockResponse:
        status_code = 204

    response = NonJsonMockResponse()

    with pytest.raises(
        Exception,
        match='Response does not contain a JSON-formatted response and cannot be tested against a response schema.',
    ):
        unpack_response(response)


import pytest

from django_swagger_tester.validation.utils import resolve_path

paths = ['/api/v1/cars/correct/', '/api/v1/trucks/correct/', '/api/v1/cars/incorrect/', '/api/v1/trucks/incorrect/']


def test_successful_resolve() -> None:
    """
    This should run without errors.
    """
    for path in paths:
        resolve_path(path)


def test_successful_resolve_despite_missing_leading_slash():
    """
    A path should resolve despite missing a leading slash.
    """
    for path in paths:
        resolve_path(path[1:])


def test_successful_resolve_despite_missing_trailing_slash():
    """
    A trailing slash isn't always necessary, but when it is, a path missing its trailing slash should still resolve successfully.
    """
    for path in paths:
        resolve_path(path[:-1])


def test_path_suggestions():
    """
    When a resolve fails, we want to output useful output.
    """
    with pytest.raises(ValueError, match='Did you mean one of these?'):
        resolve_path('trucks/correct')


def test_no_path_suggestions():
    """
    Make sure the appropriate error is raised.
    """
    with pytest.raises(ValueError, match='Could not resolve path'):
        resolve_path('this is not a path')

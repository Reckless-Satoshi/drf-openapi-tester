import inspect
import logging
from re import compile
from types import FunctionType
from typing import Callable, List

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger('django_swagger_tester')


class MiddlewareSettings(object):
    """
    Holds middleware specific settings.
    """

    def __init__(self, middleware_settings: dict) -> None:
        """
        Initializes tester class with base settings.
        """
        # Define default values for middleware settings
        self.LOG_LEVEL = 'ERROR'
        self.REJECT_INVALID_REQUEST_BODIES = False
        self.VALIDATE_RESPONSE = True
        self.VALIDATE_REQUEST_BODY = True
        self.VALIDATION_EXEMPT_URLS: List[str] = []

        # Overwrite defaults
        for setting, value in middleware_settings.items():
            if hasattr(self, setting):
                setattr(self, setting, value)
            else:
                raise ImproperlyConfigured(
                    f'Received excess middleware setting, `{setting}`, for SWAGGER_TESTER. '
                    f'Please correct or remove this from the middleware settings.'
                )

        self.validate_and_set_logger()
        self.validate_bool(self.REJECT_INVALID_REQUEST_BODIES, 'REJECT_INVALID_REQUEST_BODIES')
        self.validate_bool(self.VALIDATE_REQUEST_BODY, 'VALIDATE_REQUEST_BODY')
        self.validate_bool(self.VALIDATE_RESPONSE, 'VALIDATE_RESPONSE')
        self.validate_exempt_urls(self.VALIDATION_EXEMPT_URLS)
        self.validate_validate_request_body()  # must be below bool validation of VALIDATE_REQUEST_BODY

    def validate_and_set_logger(self) -> None:
        """
        Makes sure the LOG_LEVEL setting is the right type, and sets LOGGER.

        Bad strings are handled in self.get_logger
        """
        if not isinstance(self.LOG_LEVEL, str):
            raise ImproperlyConfigured(f'The SWAGGER_TESTER middleware setting `LOG_LEVEL` must be a string value')
        self.LOGGER: Callable = self.get_logger(self.LOG_LEVEL.upper(), 'django_swagger_tester')

    def validate_validate_request_body(self) -> None:
        """
        Makes sure the VALIDATE_REQUEST_BODY and REJECT_INVALID_REQUEST_BODIES settings are compatible.
        """
        if not self.VALIDATE_REQUEST_BODY and self.REJECT_INVALID_REQUEST_BODIES:
            raise ImproperlyConfigured(
                'REJECT_INVALID_REQUEST_BODIES middleware setting cannot be True if VALIDATE_REQUEST_BODY is False.'
            )

    @staticmethod
    def validate_bool(value: bool, setting_name: str) -> None:
        """
        Validates a boolean setting.
        """
        if not isinstance(value, bool):
            raise ImproperlyConfigured(
                f'The SWAGGER_TESTER middleware setting `{setting_name}` must be a boolean value'
            )

    @staticmethod
    def validate_exempt_urls(values: List[str]) -> None:
        """
        Makes sure we're able to compile the input values as regular expressions.
        """
        try:
            [compile(url_pattern) for url_pattern in values]
        except Exception:
            raise ImproperlyConfigured('Failed to compile the passed VALIDATION_EXEMPT_URLS as regular expressions')

    @staticmethod
    def get_logger(level: str, logger_name: str) -> Callable:
        """
        Return logger.

        :param level: log level
        :param logger_name: logger name
        :return: logger
        """
        if level == 'DEBUG':
            return logging.getLogger(logger_name).debug
        elif level == 'INFO':
            return logging.getLogger(logger_name).info
        elif level == 'WARNING':
            return logging.getLogger(logger_name).warning
        elif level == 'ERROR':
            return logging.getLogger(logger_name).error
        elif level == 'EXCEPTION':
            return logging.getLogger(logger_name).exception
        elif level == 'CRITICAL':
            return logging.getLogger(logger_name).critical
        else:
            raise ImproperlyConfigured(
                f'`{level}` is not a valid log level. Please change the `LOG_LEVEL` setting in your `SWAGGER_TESTER` '
                f'settings to one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `EXCEPTION`, or `CRITICAL`.'
            )


class SwaggerTesterSettings(object):
    """
    Loads and validates the packages Django settings.
    """

    def __init__(self) -> None:  # sourcery skip: remove-redundant-pass
        """
        Initializes tester class with base settings.
        """
        # Get SWAGGER_TESTER settings
        swagger_tester_settings = self.get_package_settings()

        # Required package settings
        self.SCHEMA_LOADER = None

        # Defaulted package settings
        self.CASE_TESTER: Callable = lambda: None
        self.CAMEL_CASE_PARSER = False
        self.CASE_WHITELIST: List[str] = []

        # Overwrite defaults
        for setting, value in swagger_tester_settings.items():
            if hasattr(self, setting):
                setattr(self, setting, value)
            else:
                # Some loader classes will have extra settings passed to the loader class as kwargs
                # Because of this, we cannot raise errors for extra settings
                pass

        # Load middleware settings as its own class
        middleware_settings = swagger_tester_settings.get('MIDDLEWARE', {})
        self.MIDDLEWARE = MiddlewareSettings(middleware_settings if middleware_settings is not None else {})

        # Make sure schema loader was specified
        self.set_and_validate_schema_loader(swagger_tester_settings)

        # Validate other specified settings to make sure they are valid
        self.validate_case_tester_setting()
        self.validate_camel_case_parser_setting()
        self.validate_case_whitelist()

    @staticmethod
    def get_package_settings() -> dict:
        """
        Loads the SWAGGER_TESTER settings from the Django application's settings.py
        """
        from django.conf import settings as django_settings

        if not hasattr(django_settings, 'SWAGGER_TESTER'):
            raise ImproperlyConfigured(
                'Please configure SWAGGER_TESTER in your settings or remove django-swagger-tester as a dependency'
            )

        if not django_settings.SWAGGER_TESTER:
            raise ImproperlyConfigured('Your SWAGGER_TESTER settings need to be configured')

        return django_settings.SWAGGER_TESTER

    def validate_case_tester_setting(self) -> None:
        """
        Make sure we receive a callable or a None.
        """
        if self.CASE_TESTER is not None and not isinstance(self.CASE_TESTER, FunctionType):
            logger.error('CASE_TESTER setting is misspecified.')
            raise ImproperlyConfigured(
                f'The django-swagger-tester CASE_TESTER setting is misspecified. '
                f'Please pass a case tester callable from django_swagger_tester.case_testers, '
                f'make your own, or pass `None` to skip case validation.'
            )
        elif self.CASE_TESTER is None:
            # If None is passed, we want to do nothing when self.CASE_TESTER is called, so we just assign a lambda expression
            self.CASE_TESTER = lambda: None

    def validate_camel_case_parser_setting(self) -> None:
        """
        Make sure CAMEL_CASE_PARSER is a boolean, and that the required dependencies are installed if set to True.
        """
        if not isinstance(self.CAMEL_CASE_PARSER, bool):
            raise ImproperlyConfigured('`CAMEL_CASE_PARSER` needs to be True or False')
        if self.CAMEL_CASE_PARSER:
            try:
                import djangorestframework_camel_case  # noqa: F401
            except ImportError:
                raise ImproperlyConfigured(
                    'The package `djangorestframework_camel_case` is not installed, '
                    'and is required to enable camel case parsing.'
                )
        else:
            from django.conf import settings as django_settings

            if hasattr(django_settings, 'REST_FRAMEWORK') and 'djangorestframework_camel_case.parser' in str(
                django_settings.REST_FRAMEWORK
            ):
                logger.warning(
                    'Found `djangorestframework_camel_case` in REST_FRAMEWORK settings, '
                    'but CAMEL_CASE_PARSER is not set to True'
                )

    def set_and_validate_schema_loader(self, package_settings: dict) -> None:
        """
        Sets self.LOADER_CLASS and validates the setting.
        """
        from django_swagger_tester.loaders import _LoaderBase

        addon = '. Please pass a loader class from django_swagger_tester.schema_loaders.'
        if self.SCHEMA_LOADER is None:
            raise ImproperlyConfigured(
                'SCHEMA_LOADER is missing from your SWAGGER_TESTER settings, and is required' + addon
            )

        if not inspect.isclass(self.SCHEMA_LOADER):
            raise ImproperlyConfigured('SCHEMA_LOADER must be a class' + addon)
        elif not issubclass(self.SCHEMA_LOADER, _LoaderBase):
            raise ImproperlyConfigured(
                'The supplied LOADER_CLASS must inherit django_swagger_tester.schema_loaders._LoaderBase' + addon
            )

        self.LOADER_CLASS: _LoaderBase = self.SCHEMA_LOADER()
        self.LOADER_CLASS.validation(package_settings=package_settings)

    def validate_case_whitelist(self) -> None:
        """
        Validates the case whitelist as a list of strings.
        """
        if self.CASE_WHITELIST is None:
            self.CASE_WHITELIST = []
        if not isinstance(self.CASE_WHITELIST, list):
            raise ImproperlyConfigured('The CASE_WHITELIST setting needs to be a list of strings')
        elif any(not isinstance(item, str) for item in self.CASE_WHITELIST):
            raise ImproperlyConfigured('The CASE_WHITELIST setting list can only contain strings')


settings = SwaggerTesterSettings()

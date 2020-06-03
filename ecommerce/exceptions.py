from rest_framework import status
from rest_framework.exceptions import APIException


class BaseClientError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


class YAMLParserError(BaseClientError):
    default_detail = 'YAML parser error, check file formatting.'
    default_code = 'Parser error'


class URLError(BaseClientError):
    default_detail = 'Incorrect URL.'
    default_code = 'URL validation error'


class ResourceUnavailableError(BaseClientError):
    default_detail = 'Unable to fetch a resource, check if resource is available.'
    default_code = 'Resource unavailable'

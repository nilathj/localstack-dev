import json
import logging
import os
from http import HTTPStatus
from botocore.vendored import requests
from urllib.parse import unquote_plus

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.WARNING)

SEARCH_PAGE_SIZE = os.getenv('SEARCH_PAGE_SIZE', '10')
SEARCH_FROM = os.getenv('SEARCH_FROM', '0')
SEARCH_MIN_LENGTH = os.getenv('SEARCH_MIN_LENGTH', '3')
SEARCH_FIELD_DISPLAY_SIZE = os.getenv('SEARCH_FIELD_DISPLAY_SIZE', '150')
SEARCH_FIELD_DISPLAY_FRAGMENTS = os.getenv(
    'SEARCH_FIELD_DISPLAY_FRAGMENTS', '10')
HTTP_TIMEOUT = os.getenv('HTTP_TIMEOUT', '15')
ES_SCHEME = os.getenv('ES_SCHEME', 'http://')
ES_HOST = os.getenv('ES_HOST', '172.17.0.2:4571')
ES_INDEX = os.getenv('ES_INDEX', 'workspace')
ES_URL = ES_SCHEME + ES_HOST + "/" + ES_INDEX + "/_search"

LOG_PREFIX = '[Elastic Search][Suggestion]'

# Elastic search key, input request param filter key
MATCHED_FIELDS = {
    "participant.reference": "subscriberRef",
    "workspace.number": "workspaceNumber",
    "propertys.landIdentifier": "landIdentifier",
    "parties.name": "partyName",
    "propertys.address": "address",
    "propertys.lotInUnregisteredPlan": "lotInUnregisteredPlan",
    "workspace.jurisdiction": "jurisdiction"
}


def lambda_handler(event, context):
    try:
        if not event['queryStringParameters']:
            return create_response(HTTPStatus.OK.value, "UP")
        event_data = get_event_data(event)
        LOGGER.info('%s %s %s', LOG_PREFIX, 'EVENT_DATA:', event_data)
        query = build_suggest_search_query(event_data)
        results = search(query)
        return create_response(HTTPStatus.OK.value, results)
    except ValidationError as err:
        return create_response(HTTPStatus.BAD_REQUEST.value, err.data)
    except InternalError as err:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR.value, err.data)
    except requests.exceptions.HTTPError as err:
        LOGGER.error('%s %s %s', LOG_PREFIX,
                     'HttpError retrieving user profile:', err)
        return create_response(HTTPStatus.SERVICE_UNAVAILABLE.value, "Error retrieving user profile")
    except requests.exceptions.ConnectionError as err:
        LOGGER.error('%s %s %s', LOG_PREFIX, 'Error Connecting:', err)
        return create_response(HTTPStatus.SERVICE_UNAVAILABLE.value, "Error Connecting to user API")
    except requests.exceptions.Timeout as err:
        LOGGER.error('%s %s %s', LOG_PREFIX, 'Timeout Error:', err)
        return create_response(HTTPStatus.SERVICE_UNAVAILABLE.value, "Timeout Error with user API")
    except requests.exceptions.RequestException as err:
        LOGGER.error('%s %s %s', LOG_PREFIX, 'Requeset Error:', err)
        return create_response(HTTPStatus.SERVICE_UNAVAILABLE.value, "Requeset Error with user API")


def build_suggest_search_query(event_data):
    profile_data = build_profile(
        event_data['subscriber_id'], event_data['work_groups'])
    query = unquote_plus((event_data['q']).lower())
    sanitized = ''
    for character in query:
        if needs_escaping(character):
            sanitized += '\\%s' % character
        else:
            sanitized += character

    query_string = '*' + sanitized + '*'
    query = {
        "size": event_data['page_size'],
        "from": event_data['from_record'],
        "query": {
            "bool": {
                "filter": [
                    {
                        "bool": {
                            "should": [
                                {
                                    "nested": {
                                        "path": "propertys",
                                        "query": {
                                            "bool": {
                                                "should": [
                                                    {
                                                        "wildcard": {
                                                            "propertys.address.keywordstring": query_string
                                                        }
                                                    },
                                                    {
                                                        "wildcard": {
                                                            "propertys.landIdentifier.keywordstring": query_string
                                                        }
                                                    },
                                                    {
                                                        "wildcard": {
                                                            "propertys.lotInUnregisteredPlan.keywordstring": query_string
                                                        }
                                                    }
                                                ]
                                            }
                                        },
                                        "inner_hits": {
                                            "_source": "false",
                                            "highlight": {
                                                "fields": {
                                                    "propertys.address.keywordstring": {
                                                        "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                                                        "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                                                    },
                                                    "propertys.landIdentifier.keywordstring": {
                                                        "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                                                        "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                                                    },
                                                    "propertys.lotInUnregisteredPlan.keywordstring": {
                                                        "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                                                        "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                                {
                                    "nested": {
                                        "path": "parties",
                                        "query": {
                                            "bool": {
                                                "should": [
                                                    {
                                                        "wildcard": {
                                                            "parties.name.keywordstring": query_string
                                                        }
                                                    },
                                                    {
                                                        "wildcard": {
                                                            "parties.titlePartyFullName.keywordstring": query_string
                                                        }
                                                    }
                                                ]
                                            }
                                        },
                                        "inner_hits": {
                                            "_source": "false",
                                            "highlight": {
                                                "fields": {
                                                    "parties.name.keywordstring": {
                                                        "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                                                        "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                                                    },
                                                    "parties.titlePartyFullName.keywordstring": {
                                                        "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                                                        "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                                {
                                    "bool": {
                                        "should": [
                                            {
                                                "wildcard": {
                                                    "participant.reference.keywordstring": query_string
                                                }
                                            },
                                            {
                                                "wildcard": {
                                                    "workspace.number.keywordstring": query_string
                                                }
                                            },
                                            {
                                                "wildcard": {
                                                    "workspace.jurisdiction.keywordstring": query_string
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "query_string": {
                            "query": "NOT ABANDONED",
                            "fields": [
                                "workspace.status"
                            ]
                        }
                    },
                    {
                        "query_string": {
                            "query": "ACTIVE",
                            "fields": [
                                "participant.status"
                            ]
                        }
                    },
                    {
                        "bool": {
                            "should": [{"term": {"workspace.workgroups": w}} for w in profile_data['workgroups']]
                        }
                    },
                    {
                        "bool": {
                            "should": [
                                {"term": {
                                    "participant.subscriberId": profile_data['subscriber_id']}}
                            ]
                        }
                    }
                ]
            }
        },
        "_source": "false",
        "highlight": {
            "fields": {
                "participant.reference.keywordstring": {
                    "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                    "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                },
                "workspace.number.keywordstring": {
                    "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                    "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                },
                "workspace.jurisdiction.keywordstring": {
                    "fragment_size": int(SEARCH_FIELD_DISPLAY_SIZE),
                    "number_of_fragments": int(SEARCH_FIELD_DISPLAY_FRAGMENTS)
                }
            }
        }
    }
    LOGGER.info('%s %s', LOG_PREFIX, json.dumps(query, indent=2))
    return query


def needs_escaping(character):
    escape_chars = {
        '\\': True, '+': True, '-': True, '!': True,
        '(': True, ')': True, ':': True, '^': True,
        '[': True, ']': True, '\"': True, '{': True,
        '}': True, '~': True, '*': True, '?': True,
        '|': True, '&': True, '/': True
    }
    return escape_chars.get(character, False)


def search(query):
    headers = {"Content-Type": "application/json"}
    try:
        LOGGER.info('%s DOING Elastic Search: %s', LOG_PREFIX, ES_URL)
        resp = requests.get(ES_URL, headers=headers, data=json.dumps(
            query), timeout=int(HTTP_TIMEOUT))
        if resp.status_code != HTTPStatus.OK:
            LOGGER.error('%s Elastic search error: %s', LOG_PREFIX, resp)
            raise InternalError('Error connecting to Elastic Search')
        LOGGER.info('%s DONE Elastic Search: %s', LOG_PREFIX, resp.status_code)
        resp_json = json.loads(resp.text)
        LOGGER.info('ES_RESPONSE: %s', resp_json)

        # Get workspaces search results list and get the highlighted sections for each of them.
        try:
            workspaces = resp_json['hits']['hits']
        except KeyError as err:
            LOGGER.error('%s %s %s', LOG_PREFIX,
                         'ES suggest query error:', err)
            raise InternalError('Error running generated suggest search query')

        workspace_results = {"results": []}
        LOGGER.info('%s WORKSPACES: %s', LOG_PREFIX, workspaces)
        for workspace in workspaces or []:
            # Get non nested main sections.
            try:
                matched_main_sections = workspace['highlight']
                for matched_field, display_value in MATCHED_FIELDS.items():
                    if matched_field + '.keywordstring' in matched_main_sections:
                        workspace_results['results'].append(
                            {display_value: matched_main_sections[matched_field + '.keywordstring']})
            except KeyError:
                pass

            # Get nested propertys sections.
            try:
                property_sections = workspace['inner_hits']['propertys']['hits']['hits']
                for property_section in property_sections:
                    matched_propertys_sections = property_section['highlight']
                    for matched_field, display_value in MATCHED_FIELDS.items():
                        if matched_field + '.keywordstring' in matched_propertys_sections:
                            workspace_results['results'].append(
                                {display_value: matched_propertys_sections[matched_field + '.keywordstring']})
            except (KeyError, IndexError):
                pass

            # Get nested parties sections.
            try:
                parties_sections = workspace['inner_hits']['parties']['hits']['hits']
                for parties_section in parties_sections:
                    matched_partie_sections = parties_section['highlight']
                    for matched_field, display_value in MATCHED_FIELDS.items():
                        if matched_field + '.keywordstring' in matched_partie_sections:
                            workspace_results['results'].append(
                                {display_value: matched_partie_sections[matched_field + '.keywordstring']})
            except (KeyError, IndexError):
                pass
        return json.dumps(workspace_results)

    except requests.exceptions.HTTPError as errh:
        LOGGER.error('%s %s %s', LOG_PREFIX, 'ES HTTPError:', errh)
        raise


def get_event_data(event):
    try:
        query_params = event['queryStringParameters']
    except KeyError:
        raise ValidationError("Missing queryStringParameters")
    try:
        q = query_params['q']
    except (KeyError, Exception):
        raise ValidationError("Missing q query string")
    if len(q) < int(SEARCH_MIN_LENGTH):
        raise ValidationError(
            "Search query needs at least " + str(SEARCH_MIN_LENGTH) + " characters")
    try:
        page_size = query_params['size']
    except KeyError:
        page_size = int(SEARCH_PAGE_SIZE)
    try:
        from_record = query_params['from']
    except KeyError:
        from_record = int(SEARCH_FROM)
    try:
        work_groups_str = query_params['workGroups']
        work_groups = work_groups_str.split(",")
    except KeyError:
        raise ValidationError("Missing workGroups query string")
    try:
        subscriber_id = query_params['subscriberId']
    except KeyError:
        raise ValidationError("Missing subscriberId query string")

    return {
        'q': q,
        'page_size': page_size,
        'from_record': from_record,
        'work_groups': work_groups,
        'subscriber_id': subscriber_id
    }


def build_profile(subscriber_id, workgroups):
    return {
        'subscriber_id': subscriber_id,
        'workgroups': workgroups
    }


def create_response(code, body):
    return {
        'statusCode': code,
        'body': body,
        'headers': {'Content-Type': 'application/json'}
    }


class ValidationError(Exception):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return repr(self.data)


class InternalError(Exception):
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return repr(self.data)

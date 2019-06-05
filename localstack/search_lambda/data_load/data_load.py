import logging
import os
import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.WARNING)

s3 = None

ES_USE_SSL = os.getenv('ES_USE_SSL', 'False')
ES_VERIFY_CERTS = os.getenv('ES_VERIFY_CERTS', 'False')
ES_PORT = os.getenv('ES_PORT', '4571')
ES_HOST = os.getenv('ES_HOST', '172.17.0.2')
ES_INDEX = os.getenv('ES_INDEX', 'workspace')
ES_DOC_TYPE = os.getenv('ES_DOC_TYPE', 'doc')
SCHEMA_VERSION = os.getenv('SCHEMA_VERSION', '1.0')

LOG_PREFIX = '[Elastic Search][Data Load]'


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


if str2bool(ES_USE_SSL):
    # Running against aws
    s3 = boto3.client('s3')
else:
    # Running against localstack
    s3 = boto3.client('s3', endpoint_url='http://172.17.0.2:4572')

# Elastic search mapping
INDEX_MAPPING = {
    "mappings": {
        ES_DOC_TYPE: {
            "properties": {
                "created_date": {
                    "type": "date"
                },
                "schema_version": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "participant": {
                    "properties": {
                        "id": {
                            "type": "long"
                        },
                        "reference": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "role": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "status": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "subscriberId": {
                            "type": "long"
                        }
                    }
                },
                "parties": {
                    "type": "nested",
                    "properties": {
                        "id": {
                            "type": "long"
                        },
                        "name": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "titlePartyFullName": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "partySource": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        }
                    }
                },
                "propertys": {
                    "type": "nested",
                    "properties": {
                        "address": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "id": {
                            "type": "long"
                        },
                        "landIdentifier": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "lotInUnregisteredPlan": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "lvReportAddress": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        }
                    }
                },
                "workspace": {
                    "properties": {
                        "id": {
                            "type": "long"
                        },
                        "jurisdiction": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "number": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                },
                            },
                            "analyzer": "standard"
                        },
                        "status": {
                            "type": "text",
                            "fields": {
                                "keywordstring": {
                                    "type": "text",
                                    "analyzer": "keyword_analyzer"
                                },
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            },
                            "analyzer": "standard"
                        },
                        "workgroups": {
                            "type": "long"
                        }
                    }
                }
            }
        }
    },
    "settings": {
        "index": {
            "analysis": {
                "filter": {},
                "analyzer": {
                    "keyword_analyzer": {
                        "filter": [
                            "lowercase",
                            "asciifolding",
                            "trim"
                        ],
                        "char_filter": [],
                        "type": "custom",
                        "tokenizer": "keyword"
                    }
                }
            }
        }
    }
}


es_client = None
try:
    es_client = Elasticsearch(
        hosts=[{'host': ES_HOST, 'port': int(ES_PORT)}],
        use_ssl=str2bool(ES_USE_SSL),
        verify_certs=str2bool(ES_VERIFY_CERTS),
        connection_class=RequestsHttpConnection)
    if not es_client.ping():
        raise Exception('ConnectTimeout')
except Exception as E:
    LOGGER.error("{} Unable to connect to {} with Exception {}".format(LOG_PREFIX, ES_HOST, str(E)))
    exit(1)

try:
    if es_client.indices.exists(ES_INDEX) is False:
        LOGGER.warning("{} Index does not exists {}".format(LOG_PREFIX, ES_INDEX))
        es_client.indices.create(ES_INDEX, body=INDEX_MAPPING)
        LOGGER.warning("{} Index created {}".format(LOG_PREFIX, ES_INDEX))
except Exception as E:
    LOGGER.error("{} Unable to Create Index {} with Exception {}".format(LOG_PREFIX, ES_INDEX, str(E)))
    exit(1)


def lambda_handler(event, context):
    bucket_name = ''
    file_key = ''
    try:
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        LOGGER.warning('{} Reading {} from {}'.format(LOG_PREFIX, file_key, bucket_name))
    except KeyError as ex:
        LOGGER.error(
            '{} Failed parsing S3 trigger event:{} : {}'.format(LOG_PREFIX, event, str(ex)))
        exit(1)

    try:
        # get the object
        obj = s3.get_object(Bucket=bucket_name, Key=file_key)
        payload = obj['Body'].read().decode("utf-8")
        bulk_index_doc_element(payload, bucket_name, file_key)
    except Exception as ex:
        LOGGER.error(
            '{} Failed indexing Elasticsearch to ES_HOST: {} and ES_INDEX: {} with Exception {}'.format(LOG_PREFIX,
                                                                                                        ES_HOST,
                                                                                                        ES_INDEX,
                                                                                                        str(ex)))
        exit(1)


def bulk_index_doc_element(body, bucket_name, file_key):
    try:
        es_client.bulk(body=body, index=ES_INDEX, doc_type=ES_DOC_TYPE, _source=False, request_timeout=120)
        LOGGER.warning("{} Created bulk index for bucket: {} and key: {}".format(LOG_PREFIX, bucket_name, file_key))
    except Exception as ex:
        LOGGER.error(
            "{} Failed to index document for bucket: {} and key: {} with Exception {}".format(LOG_PREFIX, bucket_name,
                                                                                              file_key, str(ex)))

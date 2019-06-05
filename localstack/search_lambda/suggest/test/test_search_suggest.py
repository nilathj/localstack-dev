import unittest
import json
from jsondiff import diff
from search_lambda.suggest.search_suggest import lambda_handler
from search_lambda.suggest.search_suggest import build_suggest_search_query
from os import path

basepath = path.dirname(__file__)


class TestSearchSuggest(unittest.TestCase):
    """
    Search service lambda tests
    """

    def test_health_check_up_with_no_search_query_string(self):

        event = {'queryStringParameters': {}}
        res = lambda_handler(event, None)
        self.assertEqual(res['statusCode'], 200)
        self.assertEqual(res['body'], 'UP')

    def test_failure_response_with_missing_work_groups(self):

        event = {
            "queryStringParameters": {
                "q": "collins",
                "size": 10,
                "from": 0
            }
        }
        res = lambda_handler(event, None)
        self.assertEqual(res['statusCode'], 400)
        self.assertEqual(res['body'], 'Missing workGroups query string')

    def test_failure_response_with_missing_subscriber_id(self):

        event = {
            "queryStringParameters": {
                "q": "collins",
                "size": 10,
                "from": 0,
                "workGroups": "724,1299",
            }
        }
        res = lambda_handler(event, None)
        self.assertEqual(res['statusCode'], 400)
        self.assertEqual(res['body'], 'Missing subscriberId query string')

    def test_failure_response_with_short_query_string(self):
        event = {
            "queryStringParameters": {
                "q": "12",
                "size": 10,
                "from": 0
            }
        }
        res = lambda_handler(event, None)
        self.assertEqual(res['statusCode'], 400)
        self.assertEqual(res['body'], 'Search query needs at least 3 characters')

    def test_suggests_query(self):
        filepath = path.abspath(path.join(basepath, "data", "complete_suggestions_query.json"))
        # Given
        with open(filepath) as expected_schema_file:
            expected_schema = json.load(expected_schema_file)
            event_data = {
                "q": "12/5",
                "page_size": 10,
                "from_record": 0,
                "work_groups": ['55555', '1299'],
                "subscriber_id": "55555"
            }

            # When
            actual = build_suggest_search_query(event_data)
            # print('QUERY:', json.dumps(actual, indent=2))

            # Then
            difference = diff(actual, expected_schema)
            if not difference == {}:
                self.fail('Invalid generated search suggestions query: {0}'.format(difference))


if __name__ == '__main__':
    unittest.main()

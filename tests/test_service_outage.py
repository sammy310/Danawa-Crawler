import unittest
from unittest.mock import Mock, patch

from requests import Response

from danawa_http_static import (
    DanawaServiceUnavailable,
    DanawaStaticHttpClient,
    ParsedProductPage,
)


class ServiceOutageTests(unittest.TestCase):
    def setUp(self):
        self.client = DanawaStaticHttpClient()
        self.url = 'https://prod.danawa.com/list/?cate=112747'
        self.fields = {f'field{i}': '' for i in range(32)}
        self.session = Mock(headers={})

    def response(self, url, status):
        response = Response()
        response.url = url
        response.status_code = status
        response.headers['Content-Type'] = 'text/html'
        response._content = b'<html>notice</html>'
        self.session.post.return_value = response

    def fetch(self):
        return self.client.FetchProductPage('CPU', self.url, self.fields, 'NEW', 1)

    def test_maintenance_redirect_is_not_retried_or_parsed(self):
        for status in (200, 503):
            with self.subTest(status=status):
                self.session.reset_mock()
                self.response('https://construction.danawa.com/?cate=112747', status)
                with patch.object(self.client, 'CreateSession', return_value=self.session), \
                     patch.object(self.client, 'ParseProductPageHtml') as parse, \
                     patch('danawa_http_static.time.sleep') as sleep:
                    with self.assertRaisesRegex(DanawaServiceUnavailable, 'construction.danawa.com'):
                        self.fetch()
                self.session.post.assert_called_once()
                self.session.close.assert_called_once()
                parse.assert_not_called()
                sleep.assert_not_called()

    def test_unknown_html_still_fails_closed_and_retries(self):
        self.response('https://prod.danawa.com/list/ajax/getProductList.ajax.php', 200)
        with patch.object(self.client, 'CreateSession', return_value=self.session), \
             patch.object(self.client, 'ParseProductPageHtml', side_effect=RuntimeError('Product list container missing')), \
             patch('danawa_http_static.time.sleep'), patch('builtins.print') as log:
            with self.assertRaisesRegex(RuntimeError, 'after 4 attempts'):
                self.fetch()
        self.assertEqual(self.session.post.call_count, 4)
        self.assertEqual(self.session.close.call_count, 4)
        self.assertTrue(any('status=200' in str(call) and 'bytes=19' in str(call) for call in log.call_args_list))

    def test_normal_response_keeps_original_success_path(self):
        self.response('https://prod.danawa.com/list/ajax/getProductList.ajax.php', 200)
        expected = ParsedProductPage(products=('sentinel',))
        with patch.object(self.client, 'CreateSession', return_value=self.session), \
             patch.object(self.client, 'ParseProductPageHtml', return_value=expected) as parse, \
             patch('danawa_http_static.time.sleep') as sleep:
            self.assertEqual(self.fetch(), expected)
        parse.assert_called_once()
        self.session.post.assert_called_once()
        self.session.close.assert_called_once()
        sleep.assert_not_called()

    def test_forbidden_still_fails_closed(self):
        self.response('https://prod.danawa.com/list/ajax/getProductList.ajax.php', 403)
        with patch.object(self.client, 'CreateSession', return_value=self.session), \
             patch.object(self.client, 'ParseProductPageHtml') as parse, \
             patch('danawa_http_static.time.sleep'), patch('builtins.print'):
            with self.assertRaisesRegex(RuntimeError, '403 Client Error'):
                self.fetch()
        self.assertEqual(self.session.post.call_count, 4)
        parse.assert_not_called()

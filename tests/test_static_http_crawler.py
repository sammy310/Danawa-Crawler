# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from danawa_contracts import (
    GetStaticProductListFields,
    STATIC_PRODUCT_LIST_CONTRACTS,
)
from danawa_http_static import (
    DanawaStaticHttpClient,
    ParsedProductPage,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, source, calls):
        self.source = source
        self.calls = calls
        self.headers = dict()

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return FakeResponse(self.source)

    def close(self):
        return None


class StaticHttpCrawlerTests(unittest.TestCase):
    def test_all_17_static_contracts_validate(self):
        self.assertEqual(len(STATIC_PRODUCT_LIST_CONTRACTS), 17)

        for name, contract in STATIC_PRODUCT_LIST_CONTRACTS.items():
            fields = GetStaticProductListFields(
                name,
                contract['url'],
            )
            self.assertEqual(len(fields), 32)
            self.assertNotIn('page', fields)
            self.assertNotIn('sortMethod', fields)
            self.assertEqual(fields['listCount'], '90')

        headset = GetStaticProductListFields(
            'Headset',
            STATIC_PRODUCT_LIST_CONTRACTS['Headset']['url'],
        )
        self.assertEqual(headset['listCategoryCode'], '52451')
        self.assertEqual(headset['categoryCode'], '38749')

    def test_static_contract_rejects_url_drift(self):
        with self.assertRaises(RuntimeError):
            GetStaticProductListFields(
                'RAM',
                'https://prod.danawa.com/list/?cate=999999',
            )

    def test_build_static_fields_adds_only_dynamic_fields(self):
        client = DanawaStaticHttpClient()
        contract = STATIC_PRODUCT_LIST_CONTRACTS['RAM']
        staticFields = GetStaticProductListFields(
            'RAM',
            contract['url'],
        )

        fields = client.BuildStaticProductListFields(
            staticFields,
            'BEST',
            8,
        )

        self.assertEqual(len(fields), 34)
        self.assertEqual(fields['page'], '8')
        self.assertEqual(fields['sortMethod'], 'BEST')
        self.assertEqual(fields['listCategoryCode'], '752')
        self.assertEqual(fields['categoryCode'], '752')
        self.assertEqual(fields['priceUnit'], '1')
        self.assertEqual(fields['priceUnitSort'], 'Y')

    def test_ajax_total_product_count_is_runtime_authority(self):
        client = DanawaStaticHttpClient()

        self.assertEqual(
            client.ParseTotalProductCount(
                '<input id="totalProductCount" value="693" />'
            ),
            693,
        )
        self.assertEqual(
            client.ParseTotalProductCount(
                '<input id="totalProductCount" value="20,469" />'
            ),
            20469,
        )
        self.assertEqual(
            client.GetExpectedBestPageCount(693),
            8,
        )
        self.assertEqual(
            client.GetExpectedBestPageCount(410),
            5,
        )

    def test_parse_product_page_combines_products_and_runtime_total(self):
        client = DanawaStaticHttpClient()
        source = '<input id="totalProductCount" value="1,371" />'
        sentinelProducts = ['a', 'b']

        with patch.object(
            client,
            'ParseProductListHtml',
            return_value=sentinelProducts,
        ):
            page = client.ParseProductPageHtml(
                source,
                requireTotalProductCount=True,
            )

        self.assertEqual(page.totalProductCount, 1371)
        self.assertEqual(page.products, ('a', 'b'))

    def test_fetch_product_page_uses_cold_post_contract(self):
        client = DanawaStaticHttpClient()
        contract = STATIC_PRODUCT_LIST_CONTRACTS['Case']
        staticFields = GetStaticProductListFields(
            'Case',
            contract['url'],
        )
        calls = list()

        def create_session():
            return FakeSession('ignored', calls)

        expectedPage = ParsedProductPage(
            products=('sentinel',),
            totalProductCount=1371,
        )

        with patch.object(
            client,
            'CreateSession',
            side_effect=create_session,
        ), patch.object(
            client,
            'ParseProductPageHtml',
            return_value=expectedPage,
        ) as parsePage:
            page = client.FetchProductPage(
                'Case',
                contract['url'],
                staticFields,
                'BEST',
                1,
                requireTotalProductCount=True,
            )

        self.assertEqual(page, expectedPage)
        self.assertEqual(len(calls), 1)
        parsePage.assert_called_once_with(
            'ignored',
            requireTotalProductCount=True,
        )

        _, kwargs = calls[0]
        fields = kwargs['data']
        self.assertEqual(len(fields), 34)
        self.assertEqual(fields['page'], '1')
        self.assertEqual(fields['sortMethod'], 'BEST')
        self.assertEqual(fields['listCategoryCode'], '775')

    def test_missing_required_ajax_total_fails_closed(self):
        client = DanawaStaticHttpClient()
        contract = STATIC_PRODUCT_LIST_CONTRACTS['RAM']
        staticFields = GetStaticProductListFields(
            'RAM',
            contract['url'],
        )
        calls = list()

        def create_session():
            return FakeSession(
                '<div class="main_prodlist main_prodlist_list"></div>',
                calls,
            )

        with patch.object(
            client,
            'CreateSession',
            side_effect=create_session,
        ), patch(
            'danawa_http_static.time.sleep',
            return_value=None,
        ):
            with self.assertRaises(RuntimeError):
                client.FetchProductPage(
                    'RAM',
                    contract['url'],
                    staticFields,
                    'BEST',
                    1,
                    requireTotalProductCount=True,
                )

        self.assertEqual(len(calls), 4)


if __name__ == '__main__':
    unittest.main()

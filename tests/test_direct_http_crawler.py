# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from danawa_http import DanawaHttpClient


BOOTSTRAP_SOURCE = r'''
<html>
<body>
<select><option value="90">90</option></select>
<input type="hidden" id="totalProductCount" value="690" />
<li data-sort-method="BEST"></li>
<li data-sort-method="NEW"></li>
<script>
var oGlobalSetting = {
    nGroup: 11,
    nDepth: 2,
    nCategoryCode: 752,
    nListCategoryCode: 752,
    nListGroup: 11,
    nListDepth: 2,
    sPhysicsCate1: "861",
    sPhysicsCate2: "874",
    sPhysicsCate3: "0",
    sPhysicsCate4: "0",
    sCategoryMappingCode: "704",
    sPriceUnitSort: "Y",
    sPriceUnitSortOrder: "A",
    bMakerDisplayYN: "Y",
    sQuickDeliveryCategoryYN: "N",
    sQuickDeliveryDisplay: "",
    sSimpleDescriptionDisplayYN: "N",
    bDpgZoneCategory: "N",
    bAssemblyGalleryCategory: "N",
    nestedObject: {enabled: true}
};
var sProductListApi = 'search';
var sDnwSwitchYN = '';
var oExpansionContent = {
    "nPriceCompareListPackageType": "3",
    "nPriceCompareListPackageLimit": "5",
    "nPriceUnit": "1",
    "nPriceUnitValue": "0",
    "sPriceUnitClass": ""
};
var oCurrentCategoryCode = "a:2:{i:1;i:97;i:2;i:752;}";
var isAddDelivery = 'N';
var coupangMemberSort = '';
var coupangMemberSortLayerType = '';
var simpleDescriptionOpen = 'Y';
</script>
</body>
</html>
'''


PRODUCT_SOURCE = r'''
<div class="main_prodlist main_prodlist_list">
  <ul class="product_list">
    <li class="prod_item prod_layer" id="productItem18911780">
      <div class="prod_main_info">
        <div class="thumb_image"></div>
        <div class="prod_info">
          <p class="prod_name"><a>삼성전자 DDR5-5600</a></p>
        </div>
        <div class="prod_pricelist">
          <ul>
            <li class="rocket-shipping"><strong>ignore</strong></li>
            <li id="productInfoDetail_1">
              <p class="price_sect"><a><strong>797,900</strong></a></p>
              <div class="over_preview">
                <p class="memory_sect">
                  <span class="rank_one">1위</span>
                  <span class="text">32GB</span>
                  <a><span class="memory_price_sect">24,934원/1GB</span></a>
                </p>
              </div>
            </li>
            <li id="productInfoDetail_2">
              <p class="price_sect"><a><strong>364,630</strong></a></p>
              <div class="over_preview">
                <p class="memory_sect">
                  <span class="delivery">수량별배송비</span>
                  <span class="text">16GB</span>
                  <a><span class="memory_price_sect">22,789원/1GB</span></a>
                </p>
              </div>
            </li>
            <li id="productInfoDetail_3" style="display: none;">
              <p class="price_sect"><a><strong>182,580</strong></a></p>
              <div class="over_preview">
                <p class="memory_sect">
                  <span class="text">8GB</span>
                  <a><span class="memory_price_sect">22,823원/1GB</span></a>
                </p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </li>
    <li class="prod_item prod_layer" id="productItem12345678">
      <div class="prod_main_info">
        <div class="thumb_image"></div>
        <div class="prod_info">
          <p class="prod_name"><a>몰 상품</a></p>
        </div>
        <div class="prod_pricelist prod_top5">
          <ul>
            <li><a><div><span>11번가</span></div><div><em>123,450</em></div></a></li>
            <li class="top5_button">ignore</li>
          </ul>
        </div>
      </div>
    </li>
  </ul>
</div>
'''


EMPTY_PRODUCT_SOURCE = r'''
<div class="main_prodlist main_prodlist_list">
  <ul class="product_list"></ul>
</div>
'''


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, source, counter):
        self.source = source
        self.counter = counter
        self.headers = dict()

    def post(self, *args, **kwargs):
        self.counter.append((args, kwargs))
        return FakeResponse(self.source)

    def close(self):
        return None


class DirectHttpCrawlerTests(unittest.TestCase):
    def test_bootstrap_parser_and_request_contract(self):
        client = DanawaHttpClient()

        self.assertTrue(client.IsCompleteBootstrapShell(BOOTSTRAP_SOURCE))
        bootstrap = client.ParseBootstrap(BOOTSTRAP_SOURCE)
        fields = client.BuildProductListFields(bootstrap, 'BEST', 8)

        self.assertEqual(bootstrap['totalProductCount'], 690)
        self.assertEqual(client.GetExpectedBestPageCount(bootstrap), 8)
        self.assertEqual(fields['page'], '8')
        self.assertEqual(fields['listCategoryCode'], '752')
        self.assertEqual(fields['categoryCode'], '752')
        self.assertEqual(fields['physicsCate1'], '861')
        self.assertEqual(fields['physicsCate2'], '874')
        self.assertEqual(fields['categoryMappingCode'], '704')
        self.assertEqual(fields['priceUnit'], '1')
        self.assertEqual(fields['priceUnitSort'], 'Y')
        self.assertEqual(fields['listPackageType'], '3')
        self.assertEqual(fields['nPackageLimit'], '5')
        self.assertEqual(fields['oCurrentCategoryCode'], 'a:2:{i:1;i:97;i:2;i:752;}')
        self.assertEqual(fields['sMallMinPriceDisplayYN'], 'undefined')
        self.assertEqual(fields['simpleDescriptionDisplayYN'], 'N')
        self.assertEqual(fields['sProductListApi'], 'search')

    def test_product_parser_preserves_historical_visible_text_semantics(self):
        client = DanawaHttpClient()
        products = client.ParseProductListHtml(PRODUCT_SOURCE)

        self.assertEqual(len(products), 2)
        ram = products[0]
        self.assertEqual(ram.productId, '18911780')
        self.assertEqual(ram.productName, '삼성전자 DDR5-5600')
        self.assertFalse(ram.isMall)
        self.assertEqual(len(ram.prices), 3)
        self.assertEqual(
            ram.prices[0].productType,
            '1위\n32GB\n24,934원/1GB',
        )
        self.assertEqual(
            ram.prices[1].productType,
            '수량별배송비 16GB\n22,789원/1GB',
        )
        self.assertEqual(ram.prices[2].productType, '')
        self.assertEqual(ram.prices[2].price, '')

        def remove_rank_text(value):
            if len(value) >= 2 and value[0].isdigit() and value[1] == '위':
                return value[2:].strip()
            return value

        formatted = client.FormatProductPrice(
            ram,
            remove_rank_text,
            '_',
            '|',
        )
        self.assertEqual(
            formatted,
            '_32GB_24,934원/1GB_797,900|'
            '수량별배송비 16GB_22,789원/1GB_364,630|',
        )

        mall = products[1]
        self.assertTrue(mall.isMall)
        self.assertEqual(
            client.FormatProductPrice(mall, remove_rank_text, '_', '|'),
            '11번가_123,450',
        )

    def test_natural_end_uses_bootstrap_total_without_requesting_next_page(self):
        client = DanawaHttpClient()
        bootstrap = client.ParseBootstrap(BOOTSTRAP_SOURCE)
        calls = list()

        def create_session():
            return FakeSession('', calls)

        with patch.object(client, 'CreateSession', side_effect=create_session):
            products = client.FetchProductPage(
                'RAM',
                'https://prod.danawa.com/list/?cate=112752',
                bootstrap,
                'BEST',
                9,
                True,
            )

        self.assertEqual(products, [])
        self.assertEqual(len(calls), 0)

    def test_expected_last_page_still_fails_closed_if_empty(self):
        client = DanawaHttpClient()
        bootstrap = client.ParseBootstrap(BOOTSTRAP_SOURCE)
        calls = list()

        def create_session():
            return FakeSession(EMPTY_PRODUCT_SOURCE, calls)

        with patch.object(client, 'CreateSession', side_effect=create_session), patch(
            'danawa_http.time.sleep',
            return_value=None,
        ):
            with self.assertRaises(RuntimeError):
                client.FetchProductPage(
                    'RAM',
                    'https://prod.danawa.com/list/?cate=112752',
                    bootstrap,
                    'BEST',
                    8,
                    True,
                )

        self.assertEqual(len(calls), 4)

    def test_empty_first_page_is_failure_not_natural_end(self):
        client = DanawaHttpClient()
        bootstrap = client.ParseBootstrap(BOOTSTRAP_SOURCE)
        calls = list()

        def create_session():
            return FakeSession(EMPTY_PRODUCT_SOURCE, calls)

        with patch.object(client, 'CreateSession', side_effect=create_session), patch(
            'danawa_http.time.sleep',
            return_value=None,
        ):
            with self.assertRaises(RuntimeError):
                client.FetchProductPage(
                    'RAM',
                    'https://prod.danawa.com/list/?cate=112752',
                    bootstrap,
                    'BEST',
                    1,
                    False,
                )

        self.assertEqual(len(calls), 4)


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-

from dataclasses import dataclass
import re
import time

from bs4 import BeautifulSoup

from danawa_contracts import GetStaticProductListFields
from danawa_http import (
    DanawaHttpClient,
    PRODUCT_LIST_COUNT,
    PRODUCT_LIST_ENDPOINT,
    PRODUCT_REQUEST_ATTEMPTS,
    PRODUCT_REQUEST_RETRY_DELAY_SECONDS,
    PRODUCT_REQUEST_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class ParsedProductPage:
    products: tuple
    totalProductCount: int | None = None


class DanawaStaticHttpClient(DanawaHttpClient):
    def GetStaticProductListFields(self, crawlingName, crawlingURL):
        return GetStaticProductListFields(crawlingName, crawlingURL)

    def BuildStaticProductListFields(
        self,
        staticFields,
        sortMethod,
        pageNumber,
    ):
        fields = dict(staticFields)

        if 'page' in fields or 'sortMethod' in fields:
            raise RuntimeError(
                'Static Danawa contract must not contain dynamic fields'
            )

        fields['page'] = str(pageNumber)
        fields['sortMethod'] = sortMethod

        if len(fields) != 34:
            raise RuntimeError(
                f'Danawa product-list request field count mismatch: {len(fields)} != 34'
            )

        return fields

    def ParseTotalProductCount(self, source):
        soup = BeautifulSoup(source, 'html.parser')
        totalProductCountNode = soup.select_one('#totalProductCount')
        if totalProductCountNode is None:
            raise RuntimeError('AJAX totalProductCount missing')

        rawTotalProductCount = totalProductCountNode.get('value', '') or ''
        totalProductCountDigits = re.sub(r'[^0-9]', '', rawTotalProductCount)
        if not totalProductCountDigits:
            raise RuntimeError(
                f'Invalid AJAX totalProductCount: {rawTotalProductCount!r}'
            )

        totalProductCount = int(totalProductCountDigits)
        if totalProductCount <= 0:
            raise RuntimeError(
                f'Invalid AJAX totalProductCount: {rawTotalProductCount!r}'
            )

        return totalProductCount

    def GetExpectedBestPageCount(self, totalProductCount):
        return (
            totalProductCount + PRODUCT_LIST_COUNT - 1
        ) // PRODUCT_LIST_COUNT

    def ParseProductPageHtml(
        self,
        source,
        requireTotalProductCount=False,
    ):
        totalProductCount = None
        if requireTotalProductCount:
            totalProductCount = self.ParseTotalProductCount(source)

        products = self.ParseProductListHtml(source)

        if not products:
            raise RuntimeError('No products returned')

        return ParsedProductPage(
            products=tuple(products),
            totalProductCount=totalProductCount,
        )

    def FetchProductPage(
        self,
        crawlingName,
        crawlingURL,
        staticFields,
        sortMethod,
        pageNumber,
        requireTotalProductCount=False,
    ):
        fields = self.BuildStaticProductListFields(
            staticFields,
            sortMethod,
            pageNumber,
        )
        lastError = None

        for attempt in range(1, PRODUCT_REQUEST_ATTEMPTS + 1):
            session = self.CreateSession()
            session.headers.update(
                {
                    'Referer': crawlingURL,
                    'Origin': 'https://prod.danawa.com',
                    'X-Requested-With': 'XMLHttpRequest',
                }
            )

            try:
                response = session.post(
                    PRODUCT_LIST_ENDPOINT,
                    data=fields,
                    timeout=PRODUCT_REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()

                page = self.ParseProductPageHtml(
                    response.text,
                    requireTotalProductCount=requireTotalProductCount,
                )

                if attempt > 1:
                    print(
                        f'HTTP product page recovered : {crawlingName} '
                        f'-> {sortMethod} page {pageNumber}, '
                        f'attempt {attempt}/{PRODUCT_REQUEST_ATTEMPTS}'
                    )

                return page

            except Exception as error:
                lastError = error
                print(
                    f'HTTP product page failed : {crawlingName} '
                    f'-> {sortMethod} page {pageNumber}, '
                    f'attempt {attempt}/{PRODUCT_REQUEST_ATTEMPTS}: {error}'
                )

            finally:
                session.close()

            if attempt < PRODUCT_REQUEST_ATTEMPTS:
                time.sleep(PRODUCT_REQUEST_RETRY_DELAY_SECONDS * attempt)

        raise RuntimeError(
            f'HTTP product page failed after {PRODUCT_REQUEST_ATTEMPTS} attempts: '
            f'{crawlingName} -> {sortMethod} page {pageNumber}: {lastError}'
        ) from lastError

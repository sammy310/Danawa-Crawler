# -*- coding: utf-8 -*-

from dataclasses import dataclass
import html as html_module
import json
import re
import time

from bs4 import BeautifulSoup
import requests


PRODUCT_LIST_ENDPOINT = 'https://prod.danawa.com/list/ajax/getProductList.ajax.php'
PRODUCT_LIST_COUNT = 90
HTTP_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/126.0.0.0 Safari/537.36'
)

BOOTSTRAP_ATTEMPTS = 12
BOOTSTRAP_TIMEOUT_SECONDS = 30
BOOTSTRAP_RETRY_DELAY_SECONDS = 2

PRODUCT_REQUEST_ATTEMPTS = 4
PRODUCT_REQUEST_TIMEOUT_SECONDS = 30
PRODUCT_REQUEST_RETRY_DELAY_SECONDS = 2


@dataclass(frozen=True)
class ParsedPrice:
    productType: str = ''
    mallName: str = ''
    price: str = ''


@dataclass(frozen=True)
class ParsedProduct:
    productId: str
    productName: str
    isMall: bool
    prices: tuple[ParsedPrice, ...]


class DanawaHttpClient:
    def CreateSession(self):
        session = requests.Session()
        session.headers.update(
            {
                'User-Agent': HTTP_USER_AGENT,
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
        )
        return session

    def FindAssignmentStart(self, source, name):
        match = re.search(
            rf'\b(?:var|let|const)\s+{re.escape(name)}\s*=\s*',
            source,
        )
        if match is None:
            raise RuntimeError(f'Assignment missing: {name}')
        return match.end()

    def ExtractBalancedObject(self, source, name):
        start = self.FindAssignmentStart(source, name)
        while start < len(source) and source[start].isspace():
            start += 1

        if start >= len(source) or source[start] != '{':
            raise RuntimeError(f'Object missing: {name}')

        depth = 0
        quote = None
        escaped = False

        for index in range(start, len(source)):
            char = source[index]

            if quote is not None:
                if escaped:
                    escaped = False
                    continue
                if char == '\\':
                    escaped = True
                    continue
                if char == quote:
                    quote = None
                continue

            if char in ("'", '"', '`'):
                quote = char
                continue

            if char == '{':
                depth += 1
                continue

            if char == '}':
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]

        raise RuntimeError(f'Unbalanced object: {name}')

    def ExtractJsScalar(self, objectSource, key):
        keyRe = re.escape(key)

        stringMatch = re.search(
            rf'''(?<![\w$])
                ["']?{keyRe}["']?
                \s*:\s*
                (["'])
                (.*?)
                \1
            ''',
            objectSource,
            flags=re.VERBOSE | re.DOTALL,
        )
        if stringMatch is not None:
            return html_module.unescape(stringMatch.group(2))

        scalarMatch = re.search(
            rf'''(?<![\w$])
                ["']?{keyRe}["']?
                \s*:\s*
                (
                    -?\d+(?:\.\d+)?
                    |true
                    |false
                    |null
                    |undefined
                )
                (?=\s*[,}}])
            ''',
            objectSource,
            flags=re.VERBOSE,
        )
        if scalarMatch is not None:
            return scalarMatch.group(1)

        raise KeyError(key)

    def ExtractStringVar(self, source, name):
        match = re.search(
            rf'\b(?:var|let|const)\s+{re.escape(name)}\s*=\s*([\'\"])(.*?)\1\s*;',
            source,
            flags=re.DOTALL,
        )
        if match is None:
            raise RuntimeError(f'String var missing: {name}')
        return html_module.unescape(match.group(2))

    def ParseBootstrap(self, source):
        globalSource = self.ExtractBalancedObject(source, 'oGlobalSetting')
        expansionSource = self.ExtractBalancedObject(source, 'oExpansionContent')

        globalRequired = (
            'nListCategoryCode',
            'nCategoryCode',
            'sPhysicsCate1',
            'sPhysicsCate2',
            'sPhysicsCate3',
            'sPhysicsCate4',
            'nListGroup',
            'nListDepth',
            'sCategoryMappingCode',
            'sPriceUnitSort',
            'sPriceUnitSortOrder',
            'bMakerDisplayYN',
        )
        globalOptional = (
            'sMallMinPriceDisplayYN',
            'sQuickDeliveryCategoryYN',
            'sQuickDeliveryDisplay',
            'sSimpleDescriptionDisplayYN',
            'bDpgZoneCategory',
            'bAssemblyGalleryCategory',
        )

        globalValues = dict()
        for key in globalRequired:
            try:
                globalValues[key] = self.ExtractJsScalar(globalSource, key)
            except KeyError as error:
                raise RuntimeError(f'Required global missing: {key}') from error

        for key in globalOptional:
            try:
                globalValues[key] = self.ExtractJsScalar(globalSource, key)
            except KeyError:
                globalValues[key] = None

        try:
            expansionValues = json.loads(expansionSource)
        except json.JSONDecodeError as error:
            raise RuntimeError('oExpansionContent is not valid JSON') from error

        expansionRequired = (
            'nPriceCompareListPackageType',
            'nPriceCompareListPackageLimit',
            'nPriceUnit',
            'nPriceUnitValue',
            'sPriceUnitClass',
        )
        for key in expansionRequired:
            if key not in expansionValues:
                raise RuntimeError(f'Required expansion missing: {key}')

        soup = BeautifulSoup(source, 'html.parser')
        totalProductCountNode = soup.select_one('#totalProductCount')
        if totalProductCountNode is None:
            raise RuntimeError('totalProductCount missing')

        rawTotalProductCount = totalProductCountNode.get('value', '') or ''
        totalProductCountDigits = re.sub(r'[^0-9]', '', rawTotalProductCount)
        if not totalProductCountDigits:
            raise RuntimeError(
                f'Invalid totalProductCount: {rawTotalProductCount!r}'
            )

        totalProductCount = int(totalProductCountDigits)
        if totalProductCount <= 0:
            raise RuntimeError(
                f'Invalid totalProductCount: {rawTotalProductCount!r}'
            )

        return {
            'global': globalValues,
            'totalProductCount': totalProductCount,
            'expansion': expansionValues,
            'oCurrentCategoryCode': self.ExtractStringVar(source, 'oCurrentCategoryCode'),
            'sProductListApi': self.ExtractStringVar(source, 'sProductListApi'),
            'sDnwSwitchYN': self.ExtractStringVar(source, 'sDnwSwitchYN'),
            'isAddDelivery': self.ExtractStringVar(source, 'isAddDelivery'),
            'coupangMemberSort': self.ExtractStringVar(source, 'coupangMemberSort'),
            'coupangMemberSortLayerType': self.ExtractStringVar(
                source,
                'coupangMemberSortLayerType',
            ),
            'simpleDescriptionOpen': self.ExtractStringVar(
                source,
                'simpleDescriptionOpen',
            ),
        }

    def IsCompleteBootstrapShell(self, source):
        return bool(
            re.search(r'\boGlobalSetting\s*=', source)
            and re.search(r'\boExpansionContent\s*=', source)
            and 'data-sort-method="BEST"' in source
            and 'data-sort-method="NEW"' in source
            and re.search(r'<option[^>]+value=["\']90["\']', source)
        )

    def FetchBootstrap(self, crawlingName, crawlingURL):
        lastError = None

        for attempt in range(1, BOOTSTRAP_ATTEMPTS + 1):
            session = self.CreateSession()
            try:
                response = session.get(
                    crawlingURL,
                    timeout=BOOTSTRAP_TIMEOUT_SECONDS,
                )
                response.raise_for_status()

                if not self.IsCompleteBootstrapShell(response.text):
                    raise RuntimeError('Incomplete bootstrap shell')

                bootstrap = self.ParseBootstrap(response.text)

                if attempt > 1:
                    print(
                        f'HTTP bootstrap recovered : {crawlingName} '
                        f'-> attempt {attempt}/{BOOTSTRAP_ATTEMPTS}'
                    )

                return bootstrap

            except Exception as error:
                lastError = error
                print(
                    f'HTTP bootstrap failed : {crawlingName} '
                    f'-> attempt {attempt}/{BOOTSTRAP_ATTEMPTS}: {error}'
                )

                if attempt < BOOTSTRAP_ATTEMPTS:
                    time.sleep(
                        min(
                            BOOTSTRAP_RETRY_DELAY_SECONDS * attempt,
                            10,
                        )
                    )
            finally:
                session.close()

        raise RuntimeError(
            f'HTTP bootstrap failed after {BOOTSTRAP_ATTEMPTS} attempts: '
            f'{crawlingName}: {lastError}'
        ) from lastError

    def FormValue(self, value):
        if value is None:
            return ''
        if isinstance(value, bool):
            return 'true' if value else 'false'
        return str(value)

    def GetExpectedBestPageCount(self, bootstrap):
        totalProductCount = bootstrap['totalProductCount']
        return (totalProductCount + PRODUCT_LIST_COUNT - 1) // PRODUCT_LIST_COUNT

    def BuildProductListFields(self, bootstrap, sortMethod, pageNumber):
        globalValues = bootstrap['global']
        expansionValues = bootstrap['expansion']

        return {
            'page': str(pageNumber),
            'listCategoryCode': self.FormValue(globalValues['nListCategoryCode']),
            'categoryCode': self.FormValue(globalValues['nCategoryCode']),
            'physicsCate1': self.FormValue(globalValues['sPhysicsCate1']),
            'physicsCate2': self.FormValue(globalValues['sPhysicsCate2']),
            'physicsCate3': self.FormValue(globalValues['sPhysicsCate3']),
            'physicsCate4': self.FormValue(globalValues['sPhysicsCate4']),
            'viewMethod': 'LIST',
            'sortMethod': sortMethod,
            'listCount': str(PRODUCT_LIST_COUNT),
            'group': self.FormValue(globalValues['nListGroup']),
            'depth': self.FormValue(globalValues['nListDepth']),
            'categoryMappingCode': self.FormValue(
                globalValues['sCategoryMappingCode']
            ),
            'priceUnit': self.FormValue(expansionValues['nPriceUnit']),
            'priceUnitValue': self.FormValue(expansionValues['nPriceUnitValue']),
            'priceUnitClass': self.FormValue(expansionValues['sPriceUnitClass']),
            'priceUnitSort': self.FormValue(globalValues['sPriceUnitSort']),
            'priceUnitSortOrder': self.FormValue(
                globalValues['sPriceUnitSortOrder']
            ),
            'listPackageType': self.FormValue(
                expansionValues['nPriceCompareListPackageType']
            ),
            'nPackageLimit': self.FormValue(
                expansionValues['nPriceCompareListPackageLimit']
            ),
            'bMakerDisplayYN': self.FormValue(globalValues['bMakerDisplayYN']),
            'dnwSwitchOn': bootstrap['sDnwSwitchYN'],
            'oCurrentCategoryCode': bootstrap['oCurrentCategoryCode'],
            'sMallMinPriceDisplayYN': (
                self.FormValue(globalValues['sMallMinPriceDisplayYN'])
                if globalValues['sMallMinPriceDisplayYN'] is not None
                else 'undefined'
            ),
            'quickDeliveryCategoryYN': (
                self.FormValue(globalValues['sQuickDeliveryCategoryYN'])
                if globalValues['sQuickDeliveryCategoryYN'] is not None
                else 'N'
            ),
            'quickDeliveryDisplay': (
                self.FormValue(globalValues['sQuickDeliveryDisplay'])
                if globalValues['sQuickDeliveryDisplay'] is not None
                else ''
            ),
            'simpleDescriptionDisplayYN': (
                self.FormValue(globalValues['sSimpleDescriptionDisplayYN'])
                if globalValues['sSimpleDescriptionDisplayYN'] is not None
                else 'N'
            ),
            'simpleDescriptionOpen': bootstrap['simpleDescriptionOpen'],
            'isDpgZoneUICategory': (
                self.FormValue(globalValues['bDpgZoneCategory'])
                if globalValues['bDpgZoneCategory'] is not None
                else 'N'
            ),
            'isAssemblyGalleryCategory': (
                self.FormValue(globalValues['bAssemblyGalleryCategory'])
                if globalValues['bAssemblyGalleryCategory'] is not None
                else 'N'
            ),
            'addDelivery': bootstrap['isAddDelivery'],
            'coupangMemberSort': bootstrap['coupangMemberSort'],
            'coupangMemberSortLayerType': bootstrap['coupangMemberSortLayerType'],
            'sProductListApi': bootstrap['sProductListApi'],
        }

    def NormalizeText(self, node):
        if node is None:
            return ''
        return ' '.join(node.stripped_strings)

    def IsHidden(self, node):
        style = node.get('style', '') or ''
        normalizedStyle = re.sub(r'\s+', '', style).lower()
        return 'display:none' in normalizedStyle

    def ExtractProductTypeText(self, priceNode):
        if self.IsHidden(priceNode):
            return ''

        typeNode = priceNode.select_one('div.over_preview > p')
        if typeNode is None:
            typeNode = priceNode.select_one('div > p')
        if typeNode is None:
            raise RuntimeError(
                f'Product type node missing: {priceNode.get("id", "")}'
            )

        normalizedText = self.NormalizeText(typeNode)
        if not normalizedText:
            return ''

        rankText = ''
        rankMatch = re.match(r'^(\d+위)(?:\s+|$)', normalizedText)
        if rankMatch is not None:
            rankText = rankMatch.group(1)
            normalizedText = normalizedText[rankMatch.end():].strip()

        unitNode = typeNode.select_one('span.memory_price_sect')
        unitText = self.NormalizeText(unitNode)
        if unitText and normalizedText.endswith(unitText):
            normalizedText = normalizedText[:-len(unitText)].rstrip()

        lines = list()
        if rankText:
            lines.append(rankText)
        if normalizedText:
            lines.append(normalizedText)
        if unitText:
            lines.append(unitText)

        return '\n'.join(lines)

    def ParseProductListHtml(self, source):
        soup = BeautifulSoup(source, 'html.parser')
        productListDiv = soup.select_one('div.main_prodlist.main_prodlist_list')
        if productListDiv is None:
            raise RuntimeError('Product list container missing')

        productList = productListDiv.find('ul', class_='product_list')
        if productList is None:
            raise RuntimeError('Product list missing')

        parsedProducts = list()

        for product in productList.find_all('li', recursive=False):
            productIdValue = (product.get('id', '') or '').strip()
            productClasses = product.get('class', []) or []

            if not productIdValue:
                continue
            if 'prod_ad_item' in productClasses:
                continue
            if productIdValue.startswith('ad'):
                continue

            productIdMatch = re.fullmatch(r'productItem(\d+)', productIdValue)
            if productIdMatch is None:
                continue

            productId = productIdMatch.group(1)

            mainInfo = product.find('div', class_='prod_main_info', recursive=False)
            if mainInfo is None:
                raise RuntimeError(f'Product main info missing: {productId}')

            directDivs = mainInfo.find_all('div', recursive=False)
            if len(directDivs) < 3:
                raise RuntimeError(f'Product columns missing: {productId}')

            productNameNode = directDivs[1].select_one('p.prod_name a')
            if productNameNode is None:
                raise RuntimeError(f'Product name missing: {productId}')
            productName = self.NormalizeText(productNameNode)

            priceColumn = directDivs[2]
            isMall = 'prod_top5' in (priceColumn.get('class', []) or [])
            priceList = priceColumn.find('ul', recursive=False)
            if priceList is None:
                raise RuntimeError(f'Product price list missing: {productId}')

            parsedPrices = list()

            for priceNode in priceList.find_all('li', recursive=False):
                priceClasses = priceNode.get('class', []) or []

                # The raw AJAX response can contain this presentation-only row,
                # while the final browser DOM used by the historical crawler does not.
                if 'rocket-shipping' in priceClasses:
                    continue

                if isMall:
                    if 'top5_button' in priceClasses:
                        continue

                    if self.IsHidden(priceNode):
                        mallName = ''
                        price = ''
                    else:
                        anchor = priceNode.find('a', recursive=False)
                        if anchor is None:
                            raise RuntimeError(
                                f'Mall price anchor missing: {productId}'
                            )
                        anchorDivs = anchor.find_all('div', recursive=False)
                        if len(anchorDivs) < 2:
                            raise RuntimeError(
                                f'Mall price columns missing: {productId}'
                            )

                        mallName = self.NormalizeText(anchorDivs[0])
                        if not mallName:
                            fallbackMallName = anchorDivs[0].find('span')
                            mallName = self.NormalizeText(fallbackMallName)

                        price = self.NormalizeText(anchorDivs[1].find('em'))

                    parsedPrices.append(
                        ParsedPrice(
                            mallName=mallName,
                            price=price,
                        )
                    )
                else:
                    productType = self.ExtractProductTypeText(priceNode)
                    if self.IsHidden(priceNode):
                        price = ''
                    else:
                        priceNodeValue = priceNode.select_one('p.price_sect a strong')
                        if priceNodeValue is None:
                            raise RuntimeError(
                                f'Product price missing: {productId} '
                                f'-> {priceNode.get("id", "")}'
                            )
                        price = self.NormalizeText(priceNodeValue)

                    parsedPrices.append(
                        ParsedPrice(
                            productType=productType,
                            price=price,
                        )
                    )

            parsedProducts.append(
                ParsedProduct(
                    productId=productId,
                    productName=productName,
                    isMall=isMall,
                    prices=tuple(parsedPrices),
                )
            )

        return parsedProducts

    def FormatProductPrice(
        self,
        product,
        removeRankText,
        rowDivider,
        productDivider,
    ):
        productPriceStr = ''

        if product.isMall:
            for productPrice in product.prices:
                if productPriceStr:
                    productPriceStr += productDivider

                productPriceStr += (
                    f'{productPrice.mallName}{rowDivider}{productPrice.price}'
                )
        else:
            for productPrice in product.prices:
                if productPriceStr:
                    productPriceStr += productDivider

                productType = productPrice.productType.replace(
                    '\n',
                    rowDivider,
                )
                productType = removeRankText(productType)

                if productType:
                    productPriceStr += (
                        f'{productType}{rowDivider}{productPrice.price}'
                    )
                else:
                    productPriceStr += productPrice.price

        return productPriceStr

    def FetchProductPage(
        self,
        crawlingName,
        crawlingURL,
        bootstrap,
        sortMethod,
        pageNumber,
        allowNaturalEnd,
    ):
        if sortMethod == 'BEST' and allowNaturalEnd:
            expectedBestPageCount = self.GetExpectedBestPageCount(bootstrap)
            if pageNumber > expectedBestPageCount:
                print(
                    f'HTTP terminal page skipped : {crawlingName} '
                    f'-> BEST page {pageNumber}; '
                    f'bootstrap total pages {expectedBestPageCount}'
                )
                return list()

        fields = self.BuildProductListFields(
            bootstrap,
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

                products = self.ParseProductListHtml(response.text)
                if products:
                    if attempt > 1:
                        print(
                            f'HTTP product page recovered : {crawlingName} '
                            f'-> {sortMethod} page {pageNumber}, '
                            f'attempt {attempt}/{PRODUCT_REQUEST_ATTEMPTS}'
                        )
                    return products

                raise RuntimeError(
                    f'No products returned: {sortMethod} page {pageNumber}'
                )

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

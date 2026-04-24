from scrapy import Spider
from scrapy import Request
import json
import re
from urllib import parse

class HeadphonesSpider(Spider):
    name = "headphones_crawler"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "DOWNLOAD_DELAY": 0.01,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "COOKIES_ENABLED": True,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        },
    }

    start_urls = [

        "https://www.sony.co.uk/store/search?query=:relevance:normalSearch:true:category:gwx-audio:category:gwx-headphones"
    ]

    allowed_domains = [
        "www.sony.co.uk"
    ]

    async def start(self):
        for url in self.start_urls:
            yield Request(
                url,
                callback=self.parse,
                meta={"zyte_api_automap" : {"browserHtml" : True}}
                )

    def parse(self, response):
        # product links: any <a> whose class starts with "sn-product"
        headphone_links = response.css('a[class^="sn-product"]::attr(href)').getall()

        if headphone_links:
            yield from response.follow_all(headphone_links, callback=self.parse_page, meta={"zyte_api_automap": {"browserHtml": True}})

        # pagination links — extract href for the page after the current page
        try:
            qs = parse.urlparse(response.url).query
            params = parse.parse_qs(qs)
            current_idx = int(params.get("currentPage", [0])[0])
        except Exception:
            current_idx = 0

        next_idx = current_idx + 1
        next_page_links = []

        # prefer links that include the explicit currentPage parameter
        for href in response.css('a::attr(href)').getall():
            if not href:
                continue
            if f'currentPage={next_idx}' in href:
                next_page_links.append(response.urljoin(href))
                break

        # fallback: find pagination anchor whose visible number equals the next page display
        if not next_page_links:
            next_display = current_idx + 2
            for a in response.css('a'):
                text = a.xpath('normalize-space(string(.))').get()
                if not text:
                    continue
                try:
                    if int(text) == next_display:
                        href = a.xpath('./@href').get()
                        if href:
                            next_page_links.append(response.urljoin(href))
                        break
                except Exception:
                    continue

        if next_page_links:
            yield from response.follow_all(next_page_links, callback=self.parse, meta={"zyte_api_automap": {"browserHtml": True}})#"""

    def parse_page(self, response):
        # Name: prefer H1 name, then JSON-LD `name`, then og:title. Keep product name as-is.
        name = None
        if not name:
            name = response.css('h1::text').get()
        if not name:
            for script in response.xpath('//script[@type="application/ld+json"]/text()').getall():
                try:
                    data = json.loads(script)
                except Exception:
                    continue

                def _find_name(obj):
                    if isinstance(obj, dict):
                        if 'name' in obj and isinstance(obj.get('name'), str):
                            return obj.get('name')
                        # sometimes product is nested in main graph
                        for k, v in obj.items():
                            found = _find_name(v)
                            if found:
                                return found
                    elif isinstance(obj, list):
                        for i in obj:
                            found = _find_name(i)
                            if found:
                                return found
                    return None

                name = _find_name(data)
                if name:
                    name = name.strip()
                    break

        if not name:
            name = response.css('meta[property="og:title"]::attr(content)').get()
        if name:
            # keep product name as-is (trim whitespace only)
            name = name.strip()

        # Price:
        price = None
        # Visible text: look for currency symbol (e.g., '£84.99') inside common price elements
        visible_selectors = [
            '.price', '.product-price__price', '.price-with-tax', '.product-price span',
            '.product-price__amount', '.price-amount', '.pdp-price__amount', '.priceValue',
            '.store-price', '.product-price', '.priceBlock', '.price--amount',
        ]
        for sel in visible_selectors:
            for node in response.css(sel):
                texts = node.xpath('.//text()').getall()
                txt = ' '.join(t.strip() for t in texts if t and t.strip())
                if not txt:
                    continue
                # prefer '£' symbol matches
                m = re.search(r'£\s*(\d{1,3}(?:[.,]\d{1,3})*(?:[.,]\d+)?)', txt)
                if m:
                    price = m.group(1)
                    break
                # look for GBP code
                m = re.search(r'GBP\s*(\d{1,3}(?:[.,]\d{1,3})*(?:[.,]\d+)?)', txt, re.IGNORECASE)
                if m:
                    price = m.group(1)
                    break
            if price:
                break

        # Final normalization
        if price:
            price = str(price).strip()
            price = price.replace('\u00a3', '')
            if ',' in price and '.' not in price:
                price = price.replace(',', '.')
            price = price.replace(',', '').replace(' ', '')
            try:
                if '.' in price:
                    price = f"{float(price):.2f}"
                else:
                    price = f"{int(price):.2f}"
            except Exception:
                pass

        # MPN: prefer `sku` query parameter if present, else try meta or JSON-LD
        mpn = None
        try:
            qs = parse.urlparse(response.url).query
            params = parse.parse_qs(qs)
            sku = params.get('sku') or params.get('SKU')
            if sku:
                mpn = sku[0].upper()
            else:
                mpn = response.css('meta[name="mpn"]::attr(content)').get()
                if not mpn:
                    for script in response.xpath('//script[@type="application/ld+json"]/text()').getall():
                        try:
                            data = json.loads(script)
                        except Exception:
                            continue

                        def _find_mpn(obj):
                            if isinstance(obj, dict):
                                if 'mpn' in obj:
                                    return obj.get('mpn')
                                if 'sku' in obj:
                                    return obj.get('sku')
                                if 'offers' in obj and isinstance(obj['offers'], dict):
                                    return obj['offers'].get('sku') or obj['offers'].get('mpn')
                            elif isinstance(obj, list):
                                for i in obj:
                                    found = _find_mpn(i)
                                    if found:
                                        return found
                            return None

                        found = _find_mpn(data)
                        if found:
                            mpn = found
                            break

                if mpn:
                    mpn = str(mpn).upper()
        except Exception:
            mpn = mpn or None

        yield {
            "name": name or "",
            "price": price or "",
            "mpn": mpn or "",
            "url": response.url,
        }

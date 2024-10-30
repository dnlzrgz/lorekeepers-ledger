# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "environs>=11.0.0",
#   "markdown>=3.7",
#   "scrapy-playwright>=0.0.41",
#   "scrapy>=2.11.2",
# ]
# ///

import scrapy
from environs import Env
from itemloaders.processors import MapCompose, TakeFirst
from scrapy.crawler import CrawlerProcess
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from scrapy_playwright.page import PageMethod


def remove_white_spaces(value):
    return value.strip().replace("\n", "").replace("\r", "")


def remove_dashes(value):
    return value.replace("-", "")


class Product(scrapy.Item):
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    author = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    url = scrapy.Field()
    parent_url = scrapy.Field()
    image = scrapy.Field()
    price = scrapy.Field(
        input_processor=MapCompose(
            remove_tags,
            remove_white_spaces,
        ),
        output_processor=TakeFirst(),
    )
    isbn = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    publisher = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    publication_date = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    summary = scrapy.Field()


class CasaDelLibroSpider(scrapy.Spider):
    name = "casa_del_libro"
    start_urls = [
        "https://www.casadellibro.com/libros/comics-y-manga-infantil-y-juvenil/manga-juvenil/shonen/412004002",
        "https://www.casadellibro.com/libros/comics/manga/seinen/411006004",
        "https://www.casadellibro.com/libros/comics-y-manga-infantil-y-juvenil/manga-juvenil/shojo/412004001",
        "https://www.casadellibro.com/libros/arte/101000000",
        "https://www.casadellibro.com/libros/comics/411000000",
        "https://www.casadellibro.com/libros/literatura-en-otros-idiomas/124000000",
    ]
    meta = {
        "playwright": True,
        "playwright_include_page": True,
        "playwright_page_goto_kwargs": {
            "wait_until": "networkidle",
        },
        "playwright_page_methods": [
            PageMethod("evaluate", "window.scrollBy(0, document.body.scrollHeight)"),
        ],
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, self.parse, meta={**self.meta, "base_url": url})

    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.wait_for_selector("div.products")

        product_links = await page.query_selector_all("div.compact-product a")
        for link in product_links:
            href = await link.get_attribute("href")
            yield response.follow(
                href,
                self.parse_product,
                meta={
                    **self.meta,
                    "parent_url": response.url,
                },
            )

        last_page_button = await page.query_selector(
            "div.paginator button.btn:last-child"
        )
        if last_page_button:
            base_url = response.meta["base_url"]
            last_page_text = await last_page_button.inner_text()
            last_page_number = int(last_page_text.strip())
            for page_number in range(2, last_page_number + 1):
                next_page_url = f"{base_url}/p{page_number}"
                yield scrapy.Request(
                    next_page_url, self.parse, meta={**self.meta, "base_url": base_url}
                )

        await page.close()

    async def parse_product(self, response):
        page = response.meta["playwright_page"]

        loader = ItemLoader(Product(), response=response)
        loader.add_value("url", response.url)
        loader.add_value("parent_url", response.meta["parent_url"])

        title = await page.query_selector(".titleProducto")
        if title:
            loader.add_value("title", await title.inner_text())

        author = await page.query_selector(".autor h4")
        if author:
            loader.add_value("author", await author.inner_text())

        price = await page.query_selector(".info-price p")
        if price:
            loader.add_value("price", await price.inner_text())

        publisher = await page.query_selector(
            ".campo[data-campo='Editorial'] span.truncate-text"
        )
        if publisher:
            loader.add_value("publisher", await publisher.inner_text())

        isbn = await page.query_selector(".campo[data-campo='ISBN'] span.truncate-text")
        if isbn:
            loader.add_value("isbn", await isbn.inner_text())

        publication_date = await page.query_selector(
            ".campo[data-campo='Fecha de lanzamiento'] span.truncate-text"
        )
        if publication_date:
            loader.add_value("publication_date", await publication_date.inner_text())

        summary = await page.query_selector(".resumen-content")
        if summary:
            loader.add_value("summary", await summary.inner_text())

        image = await page.query_selector("div.portada img")
        if image:
            loader.add_value("image", await image.get_attribute("src"))

        yield loader.load_item()
        await page.close()


if __name__ == "__main__":
    env = Env()
    env.read_env()

    process = CrawlerProcess(
        settings={
            "FEEDS": {
                "products.csv": {"format": "csv"},
            },
            "USER_AGENT": env(
                "USER_AGENT",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Vivaldi/6.9.3447.54",
            ),
            "REQUEST_FINGERPRINTER_IMPLEMENTATION": env(
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                "2.7",
            ),
            "FEED_EXPORT_ENCODING": env(
                "FEED_EXPORT_ENCODING",
                "utf-8",
            ),
            "CONCURRENT_REQUESTS": env.int(
                "CONCURRENT_REQUESTS",
                8,
            ),
            "DOWNLOAD_DELAY": env.float(
                "DOWNLOAD_DELAY",
                2,
            ),
            "DNS_TIMEOUT": env.int(
                "DNS_TIMEOUT",
                60,
            ),
            "AUTOTHROTTLE_ENABLED": env.bool(
                "AUTOTHROTTLE_ENABLED",
                True,
            ),
            "AUTOTHROTTLE_START_DELAY": env.float(
                "AUTOTHROTTLE_START_DELAY",
                5,
            ),
            "AUTOTHROTTLE_MAX_DELAY": env.float(
                "AUTOTHROTTLE_MAX_DELAY",
                60,
            ),
            "AUTOTHROTTLE_TARGET_CONCURRENCY": env.float(
                "AUTOTHROTTLE_TARGET_CONCURRENCY",
                1.0,
            ),
            "CLOSESPIDER_ITEMCOUNT": env.int(
                "CLOSESPIDER_ITEMCOUNT",
                100,
            ),
            "ROBOTSTXT_OBEY": env.bool(
                "ROBOTSTXT_OBEY",
                False,
            ),
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            "TWISTED_REACTOR": env(
                "TWISTED_REACTOR",
                "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            ),
            "PLAYWRIGHT_BROWSER_TYPE": "chromium",
            "PLAYWRIGHT_LAUNCH_OPTIONS": {
                "headless": env.bool("PLAYWRIGHT_LAUNCH_OPTIONS_HEADLESS", False),
            },
        }
    )

    process.crawl(CasaDelLibroSpider)
    process.start()

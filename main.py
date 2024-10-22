import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.loader import ItemLoader
from itemloaders.processors import MapCompose, TakeFirst
from w3lib.html import remove_tags
from environs import Env


def remove_white_spaces(value):
    return value.strip().replace("\n", "")


def format_isbn(value):
    return value.replace("book_", "").replace("-", "")


def remove_currency_symbol(value):
    return float(value.replace("€", "").strip().replace(",", "."))


class Book(scrapy.Item):
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    author = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    isbn = scrapy.Field(
        input_processor=MapCompose(
            remove_tags,
            remove_white_spaces,
            format_isbn,
        ),
        output_processor=TakeFirst(),
    )
    summary = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    price = scrapy.Field(
        input_processor=MapCompose(
            remove_tags, remove_white_spaces, remove_currency_symbol
        ),
        output_processor=TakeFirst(),
    )
    book_url = scrapy.Field()
    # cover_image = scrapy.Field()
    # publisher = scrapy.Field()
    # publication_date = scrapy.Field()
    # categories = scrapy.Field()


class TodosTusLibrosSpider(scrapy.Spider):
    name = "todostuslibros"
    start_urls = ["https://www.todostuslibros.com/mas_vendidos"]

    def parse(self, response):
        for book in response.css("li.book"):
            loader = ItemLoader(Book(), selector=book)
            loader.add_css("title", "div.book-details h2.title a::text")
            loader.add_css("author", "div.book-details h3.author a::text")
            loader.add_css("isbn", "li::attr(id)")
            loader.add_css("summary", "p.synopsis::text")
            loader.add_css("book_url", "div.book-details h2.title a::attr(href)")
            loader.add_css(
                "price", "div.book-action__content--top .book-price strong::text"
            )
            yield loader.load_item()

        next_page = response.css(
            "ul.pagination li.page-item a[rel='next']::attr(href)"
        ).get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)


if __name__ == "__main__":
    env = Env()
    env.read_env()

    process = CrawlerProcess(
        settings={
            "FEEDS": {
                "books.csv": {"format": "csv"},
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
                1,
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
            "TWISTED_REACTOR": env(
                "TWISTED_REACTOR",
                "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            ),
        }
    )

    process.crawl(TodosTusLibrosSpider)
    process.start()

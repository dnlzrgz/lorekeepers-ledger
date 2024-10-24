import scrapy
from environs import Env
from itemloaders.processors import MapCompose, TakeFirst
from scrapy.crawler import CrawlerProcess
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags


def remove_white_spaces(value):
    return value.strip().replace("\n", "").replace("\r", "")


def remove_currency_symbol(value):
    return float(value.replace("€", "").strip().replace(",", "."))


def remove_dashes(value):
    return value.replace("-", "")


def format_author_name(value):
    if "/" in value:
        value = value.split("/")[0].strip()

    if "," in value:
        last, first = value.split(",", 1)
        return f"{first.strip()} {last.strip()}"

    return value


class Book(scrapy.Item):
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces),
        output_processor=TakeFirst(),
    )
    author = scrapy.Field(
        input_processor=MapCompose(
            remove_tags, remove_white_spaces, format_author_name
        ),
        output_processor=TakeFirst(),
    )
    url = scrapy.Field()
    price = scrapy.Field(
        input_processor=MapCompose(
            remove_tags, remove_white_spaces, remove_currency_symbol
        ),
        output_processor=TakeFirst(),
    )
    isbn = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_white_spaces, remove_dashes),
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


class TodosTusLibrosSpider(scrapy.Spider):
    name = "todos_tus_libros"
    start_urls = ["https://www.todostuslibros.com/mas_vendidos"]

    def parse(self, response):
        books = response.css("li.book")
        for book in books:
            book_url = book.css("h2.title a::attr(href)").get()
            if book_url:
                yield response.follow(book_url, self.parse_book)

        next_page = response.css(
            "ul.pagination li.page-item a[rel='next']::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_book(self, response):
        loader = ItemLoader(Book(), response=response)
        loader.add_css("title", "h1.title::text")
        loader.add_css("author", "a.author::text")
        loader.add_value("url", response.url)
        loader.add_css("price", "div.total-book-price strong::text")
        loader.add_css("isbn", "dt:contains('ISBN:') + dd::text")
        loader.add_css("publisher", "dt:contains('Editorial:') + dd a::text")
        loader.add_css(
            "publication_date", "dt:contains('Fecha publicación :') + dd::text"
        )

        yield loader.load_item()


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
            "TWISTED_REACTOR": env(
                "TWISTED_REACTOR",
                "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            ),
        }
    )

    process.crawl(TodosTusLibrosSpider)
    process.start()

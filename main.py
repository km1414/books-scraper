import itertools
import json
import logging
import os
import time
from asyncio import create_task, gather, run
from parser.parser_pb2 import Request
from parser.parser_pb2_grpc import ParserStub
from urllib.parse import urljoin

import grpc
import requests
import schedule
from aiohttp import ClientSession
from bs4 import BeautifulSoup

logging.basicConfig(
    format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

GRPC_HOST = os.environ["GRPC_HOST"]
GRPC_PORT = os.environ["GRPC_PORT"]
INTERVAL_MINUTES = float(os.environ.get("INTERVAL_MINUTES", 1))


class BooksScraper:
    def __init__(self):
        self.url = "https://books.toscrape.com/catalogue/page-1.html"

    def get_pages_count(self) -> int:
        """
        Get total count of pages in web-page
        """
        resp = requests.get(self.url)
        soup = BeautifulSoup(resp.text, "html.parser")
        page_info = soup.find("li", class_="current").get_text().strip()
        return int(page_info.split(" of ")[-1])

    @staticmethod
    async def get_books_links(session: ClientSession, page_url: str) -> list:
        """
        Collect all the book links from single page
        """
        async with session.get(page_url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")
            links = [urljoin(page_url, x.get("href")) for x in soup.select("h3 a")]
            return links

    @staticmethod
    async def get_book_data(session: ClientSession, book_url: str) -> dict:
        """
        Collect data of the single book
        """
        async with session.get(book_url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")
            name = soup.find("h1").get_text().strip()
            book_data = {"Name": name}

            for row in soup.find("table", class_="table table-striped").find_all("tr"):
                key = row.find("th").get_text().strip()
                value = row.find("td").get_text().strip()
                book_data[key] = value

            return book_data

    async def scrape(self) -> None:
        """
        Asynchronously run scraping job, send collected data for parsing
        """

        t0 = time.time()
        logging.info("Started scraping.")

        pages_count = self.get_pages_count()
        async with ClientSession() as session:
            page_links = [self.url.replace("1", str(n + 1)) for n in range(pages_count)]
            tasks = [create_task(self.get_books_links(session, x)) for x in page_links]
            books_links_nested = await gather(*tasks)
            books_links = list(itertools.chain(*books_links_nested))

            tasks = [create_task(self.get_book_data(session, x)) for x in books_links]
            books_data = await gather(*tasks)

            data_string = json.dumps(books_data)

            with grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}") as channel:
                stub = ParserStub(channel)
                try:
                    stub.Parse(Request(data=data_string))
                    t1 = time.time()
                    logging.info(f"Finished. Time: {round(t1 - t0, 2)}s.")
                except grpc.RpcError as e:
                    logging.error(f"Failed:  {e.code()}, {e.details()}")

    def run(self) -> None:
        """
        Start the application
        """
        logging.info(
            f"Scraper service started. Rerun interval: {INTERVAL_MINUTES} min."
        )
        schedule.every(INTERVAL_MINUTES).minutes.do(lambda: run(self.scrape()))
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    s = BooksScraper()
    s.run()

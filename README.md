# Lorekeeper's Ledger

This is a small project that utilizes `Scrapy`` in a single file,`main.py`, to scrape data for testing another project I'm developing for a client. I thought it might be interesting to share the concept of using`Scrapy`in a single file, so I decided to publish it.
Another peculiarity of this project is that it uses`uv`to run the script without relying on a`pyproject.toml` to handle the dependencies.
To run the project, you just need to clone this repository and run:

```bash
cd lorekeepers-ledger

# &

uv run main.py
```

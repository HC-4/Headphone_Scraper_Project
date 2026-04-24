import scrapy_poet
import scrapy_zyte_api

BOT_NAME = "headphone_scraper"
    
SPIDER_MODULES = ["headphone_scraper.spiders"]
NEWSPIDER_MODULE = "headphone_scraper.spiders"

ADDONS = {
    scrapy_poet.Addon: 300,
    scrapy_zyte_api.Addon: 500,
}

SCRAPY_POET_DISCOVER = ["headphone_scraper.pages"]

ZYTE_API_KEY = "" # Enter your Zyte API key here. This is required for the crawler to work. If you sign up for the free trial that gives about 10-15 full crawls.
#ZYTE_API_TRANSPARENT_MODE = False

# Playwright download handler settings
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Use the asyncio reactor required by scrapy-playwright
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Playwright launch options (headless by default)
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}

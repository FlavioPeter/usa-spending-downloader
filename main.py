import os
import glob
import asyncio


def read_lines_from_txt(file_path="keywords.txt"):
    with open(file_path, "r") as file:
        lines = file.readlines()
        # Remove any trailing newline characters from each line
        lines = (line.strip() for line in lines)
    return lines


def remove_files_in_directory(directory_path):
    # Get a list of all file paths in the directory
    files = glob.glob(os.path.join(directory_path, "*"))

    # Loop through the list and remove each file
    for file_path in files:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                pass
        except Exception as e:
            pass


async def download(page, button, to_path):
    async with page.expect_download(timeout=120 * 60 * 1000) as download_info:
        # Perform the action that initiates download
        # await page.get_by_text("Download file").click()
        await button.click()

    download = await download_info.value
    path_zip = os.path.join(to_path, download.suggested_filename)
    await download.save_as(path_zip)


from playwright.async_api import async_playwright


async def usa_spending_downloader(headless=True):
    print("Starting Downloader")
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(
        accept_downloads=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    )
    page = await context.new_page()
    url = "https://www.usaspending.gov/search/"
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("networkidle")

    await page.wait_for_selector("div.search-results", state="attached", timeout=60000)

    # Adding keywords
    await page.click("button.filter-toggle__button")

    for k in read_lines_from_txt():
        await page.wait_for_timeout(1000)
        await page.click("input#search")
        await page.fill("input#search", k)
        await page.click("button.keyword-submit")

    filters_container = await page.query_selector("div.fy-columns-container")
    year_checkboxes = await filters_container.query_selector_all(
        "label.fy-option-wrapper"
    )
    submit_button = await page.query_selector("button:has-text('Submit')")
    pwd = os.getcwd()
    download_dir = os.path.join(pwd, "downloads")
    for y in year_checkboxes:
        # setting up year dir

        year = (await y.inner_text()).replace(" ", "_")
        download_year_dir = os.path.join(download_dir, year)
        print(download_year_dir)
        os.makedirs(download_year_dir, exist_ok=True)
        remove_files_in_directory(download_year_dir)

        # download
        await y.click()
        await submit_button.click()

        # award
        await page.wait_for_selector(
            "div.usa-dt-tab__label", state="attached", timeout=60000
        )
        await page.click("button[title='Download']")
        await page.wait_for_selector(
            "div.full-download-modal", state="attached", timeout=60 * 000
        )
        download_window = await page.query_selector("div.full-download-modal")
        award = await download_window.query_selector("button:has-text('Award')")
        await award.click()
        everything = await download_window.query_selector("button[title='Everything']")
        await download(page, everything, to_path=download_year_dir)
        await page.wait_for_timeout(3000)
        await page.press("body", "Escape")

        # await page.reload()

        # transaction
        await page.wait_for_selector(
            "div.usa-dt-tab__label", state="attached", timeout=60000
        )
        await page.click("button[title='Download']")
        await page.wait_for_selector(
            "div.full-download-modal", state="attached", timeout=60 * 000
        )
        download_window = await page.query_selector("div.full-download-modal")
        transaction = await download_window.query_selector(
            "button:has-text('Transaction')"
        )
        await transaction.click()
        everything = await download_window.query_selector("button[title='Everything']")
        await download(page, everything, to_path=download_year_dir)
        await page.wait_for_timeout(3000)
        await page.press("body", "Escape")

        await y.click()

        # break

    await page.wait_for_timeout(5000)

    await browser.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(usa_spending_downloader())

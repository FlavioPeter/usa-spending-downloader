import os
import glob
from termcolor import colored
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
    async with page.expect_download(timeout=2 * 60 * 1000) as download_info:
        # Perform the action that initiates download
        # await page.get_by_text("Download file").click()
        await button.click()

    download = await download_info.value
    path_zip = os.path.join(to_path, download.suggested_filename)
    await download.save_as(path_zip)
    # Get the URL of the downloaded file
    download_url = download.url
    print(colored(f"Downloaded: {download_url}", "green"))


async def download_the(page, what, to_path):
    await page.wait_for_selector(
        "div.usa-dt-tab__label", state="attached", timeout=3 * 60 * 1000
    )
    await page.click("button[title='Download']")
    await page.wait_for_selector(
        "div.full-download-modal", state="attached", timeout=3 * 60 * 1000
    )
    download_window = await page.query_selector("div.full-download-modal")
    button = await download_window.query_selector(f"button:has-text('{what}')")
    await button.click()
    everything = await download_window.query_selector("button[title='Everything']")

    undownloaded_data = None

    try:
        await download(page, everything, to_path=to_path)
    except:
        undownloaded_data = dict()
        await page.wait_for_timeout(15 * 1000)
        undownloaded_data["url"] = await (
            await download_window.query_selector("div.link")
        ).inner_text()
        undownloaded_data["to_path"] = to_path
    finally:
        return undownloaded_data


async def download_revisit(page, not_yet_downloaded):
    url = not_yet_downloaded["url"]
    to_path = not_yet_downloaded["to_path"]
    async with page.expect_download(timeout=2 * 60 * 1000) as download_info:
        # Perform the action that initiates download
        # await page.get_by_text("Download file").click()
        await page.goto(url)

    download = await download_info.value
    path_zip = os.path.join(to_path, download.suggested_filename)
    await download.save_as(path_zip)
    print(colored(f"Downloaded: {not_yet_downloaded['url']}", "green"))


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
    # await page.wait_for_load_state("networkidle")

    await page.wait_for_selector("div.search-results", state="attached", timeout=60000)

    # Adding keywords
    await page.click("button.filter-toggle__button")

    for k in read_lines_from_txt():
        await page.wait_for_timeout(500)
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
    pending_downloads = []
    for i in range(len(year_checkboxes)):
        # setting up year dir
        y = year_checkboxes[i]
        year = (await y.inner_text()).replace(" ", "_")
        download_year_dir = os.path.join(download_dir, year)
        print(download_year_dir)
        os.makedirs(download_year_dir, exist_ok=True)
        zips = [
            f
            for f in os.listdir(download_year_dir)
            if os.path.isfile(os.path.join(download_year_dir, f))
        ]
        missing_award = True
        missing_transaction = True
        if len(zips) == 2:
            print(colored("Already downloaded both files", "green"))
            continue
        else:
            missing_award = (
                sum(["PrimeAwardSummariesAndSubawards" in f for f in zips]) == 0
            )
            if not missing_award:
                print(colored("Awards already downloaded", "green"))

            missing_transaction = (
                sum(["SubawardsAndPrimeTransactions" in f for f in zips]) == 0
            )
            if not missing_transaction:
                print(colored("Transactions already downloaded", "green"))

        # remove_files_in_directory(download_year_dir)

        # download
        await y.click()
        await submit_button.click()

        # award
        if missing_award:
            undownloaded_data = await download_the(
                page, what="Award", to_path=download_year_dir
            )

            await page.wait_for_timeout(3000)
            await page.press("body", "Escape")

            if undownloaded_data != None and undownloaded_data != {}:
                print(colored(f"Queued: {undownloaded_data['url']}", "yellow"))
                await page.reload()
                pending_downloads.append(undownloaded_data)
                await page.wait_for_selector(
                    "div.fy-columns-container", state="attached", timeout=30 * 1000
                )
                await page.wait_for_timeout(10 * 1000)
                filters_container = await page.query_selector(
                    "div.fy-columns-container"
                )
                year_checkboxes = await filters_container.query_selector_all(
                    "label.fy-option-wrapper"
                )
                y = year_checkboxes[i]
                submit_button = await page.query_selector("button:has-text('Submit')")
                undownloaded_data = None

        if missing_transaction:
            # transaction
            undownloaded_data = await download_the(
                page, what="Transaction", to_path=download_year_dir
            )

            await page.wait_for_timeout(3000)
            await page.press("body", "Escape")

            if undownloaded_data != None and undownloaded_data != {}:
                print(colored(f"Queued: {undownloaded_data['url']}", "yellow"))
                await page.reload()
                pending_downloads.append(undownloaded_data)
                await page.wait_for_selector(
                    "div.fy-columns-container", state="attached", timeout=30 * 1000
                )
                await page.wait_for_timeout(10 * 1000)
                filters_container = await page.query_selector(
                    "div.fy-columns-container"
                )
                year_checkboxes = await filters_container.query_selector_all(
                    "label.fy-option-wrapper"
                )
                y = year_checkboxes[i]
                submit_button = await page.query_selector("button:has-text('Submit')")
                undownloaded_data = None

        await y.click()

        # break

    while len(pending_downloads) > 0:
        n_pending = len(pending_downloads)
        print(f"Pending downloads: {n_pending}")
        current_pending_downloads = []
        for to_down in pending_downloads:
            print(colored(f"Revisiting: {to_down['url']}", "magenta"))
            try:
                await download_revisit(page, to_down)
            except:
                print(colored(f"Still not ready: {to_down['url']}", "red"))
                current_pending_downloads.append(to_down)

        pending_downloads = current_pending_downloads

    print(colored(f"Finished", "green"))

    await page.wait_for_timeout(5000)

    await browser.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(usa_spending_downloader())

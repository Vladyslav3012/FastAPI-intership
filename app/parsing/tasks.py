import logging
import os
from time import sleep

from bs4 import BeautifulSoup
from curl_cffi import Session
from app.celery_config import c_app
from readability import Document
import time


logger = logging.getLogger(__name__)


@c_app.task(bind=True)
def parsing_site(self, url):

    with Session() as client:
        response = client.get(url, impersonate="chrome110")
        if response.status_code != 200:
            logger.error(f"Parsing site return {response.status_code}")
            raise Exception(f"Parsing site error: {response.status_code}")

    doc = Document(response.text)
    article_title = doc.title()
    clean_html = doc.summary()

    soup = BeautifulSoup(clean_html, 'html.parser')
    clean_text = soup.get_text(separator=' ', strip=True)

    save_dir = "scrapped_files"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"parsed_{self.request.id}.txt"
    filepath = os.path.join(save_dir, filename)

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(f"--- Parsing website: {url} ---\n\n")
        file.write(f"--- Title: {article_title} ---\n")
        file.write(clean_text)
    return filepath


@c_app.task
def cleanup_old_files():
    save_dir = "scrapped_files"

    if not os.path.exists(save_dir):
        logger.info("No such file in directory")
        return "No directory"

    max_age_seconds = 24 * 3600
    current_time = time.time()

    deleted_count = 0

    for filename in os.listdir(save_dir):
        filepath = os.path.join(save_dir, filename)

        if os.path.isfile(filepath):
            file_modified_time = os.path.getmtime(filepath)
            if (current_time - file_modified_time) > max_age_seconds:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Delete file: {filename}")
                except Exception as e:
                    logger.error(f"Error delete file {filename}: {e}")

    logger.info(f"Clean up finished, success delete: {deleted_count}")
    return f"Deleted {deleted_count} files"

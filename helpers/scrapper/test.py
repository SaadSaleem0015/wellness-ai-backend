import uuid
import time
import os
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from os import environ
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage


class RefinedText(BaseModel):
    text: str

# Initialize model
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=environ.get("OPENAI_API_KEY")
).with_structured_output(RefinedText)


async def beautifulsoap_scrape(url):
    try:
        print("[1] Starting scraper...")
        print(f"[2] Target URL: {url}")

        def run_selenium():
            try:
                print("[3] Launching headless Chrome...")
                options = Options()
                options.add_argument("--headless")
                driver = webdriver.Chrome(options=options)

                print("[4] Loading page, waiting for JavaScript...")
                driver.get(url)
                time.sleep(3)

                print("[5] Extracting HTML...")
                html = driver.page_source
                driver.quit()
                print("[6] Browser closed")

                return html
            except Exception as e:
                print(f"[ERROR] Selenium error: {e}")
                raise

        html = await asyncio.to_thread(run_selenium)

        print("[7] Parsing HTML...")
        soup = BeautifulSoup(html, "html.parser")

        print("[8] Removing <header> and <footer>...")
        for tag in soup.find_all(["header", "footer"]):
            tag.decompose()

        print("[9] Extracting main text...")
        text = soup.get_text(separator="\n", strip=True)

        # Create 'scrape' folder in current directory if it doesn't exist
        scrape_dir = os.path.join(os.getcwd(), "scrape")
        os.makedirs(scrape_dir, exist_ok=True)

        print("[11] Raw scrape saved!")
        return text

    except Exception as e:
        print(f"[ERROR] BeautifulSoup scrape failed: {e}")
        return "", ""


def chunk_text(text, max_chars=6000):
    chunks = []
    while len(text) > max_chars:
        split_at = text.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)
    return chunks


async def refine_chunk(chunk: str) -> str:
    try:
        system_prompt = """
You clean and refine text scraped from a webpage.
Remove irrelevant content, navigation items, ads, duplicate text,
and anything that is not the "main content".
Return ONLY a clean, refined version of the text.
"""

        user_text = f"""
Here is a chunk of text. 
Clean it, remove irrelevant parts, and return ONLY refined useful content.

TEXT:
{chunk}
"""
        refined: RefinedText = await model.ainvoke([
            HumanMessage(content=system_prompt),
            HumanMessage(content=user_text)
        ])
        return refined.text

    except Exception as e:
        print(f"[ERROR] Refining chunk failed: {e}")
        return ""


async def refine_full_text(text: str, domain_file_path: str):
    try:
        print("[12] Splitting large text into safe chunks...")
        chunks = chunk_text(text)

        print(f"[13] Total chunks to refine: {len(chunks)}")

        refined_chunks = []
        for i, chunk in enumerate(chunks, start=1):
            print(f"[14] Refining chunk {i}/{len(chunks)}...")
            refined = await refine_chunk(chunk)
            refined_chunks.append(refined)

        final_text = "\n".join(refined_chunks)

        print(f"[15] Appending refined text to: {domain_file_path}")
        with open(domain_file_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + final_text)

        print("[16] Final refined text appended!")
        return final_text, domain_file_path

    except Exception as e:
        print(f"[ERROR] Full text refinement failed: {e}")
        return "", ""


async def scrape_and_refine(url: str):
    try:
        # Scrape webpage
        scraped_text = await beautifulsoap_scrape(url)

        if not scraped_text:
            print("[ERROR] No text scraped. Aborting refinement.")
            return {}

        # Determine domain name
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "")
        scrape_dir = os.path.join(os.getcwd(), "scrape")
        domain_file_path = os.path.join(scrape_dir, f"{domain}.txt")

        # Refine with GPT and append to domain file
        final_text, final_path = await refine_full_text(scraped_text, domain_file_path)

        return {
            "refined_text_path": final_path,
            "refined_text": final_text
        }

    except Exception as e:
        print(f"[ERROR] scrape_and_refine failed: {e}")
        return {}




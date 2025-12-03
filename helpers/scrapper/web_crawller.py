import advertools as adv
import pandas as pd
from urllib.parse import urlparse
import asyncio
import os
import logging
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from uuid import uuid4



logging.getLogger('scrapy').setLevel(logging.CRITICAL)
logging.getLogger('advertools').setLevel(logging.CRITICAL)
logging.disable(logging.CRITICAL)   


async def crawl_and_save_urls(seed_url):
    """
    Async crawl a website starting from seed_url and save all URLs to a domain_name.txt file
    """

    parsed_url = urlparse(seed_url)
    domain = parsed_url.netloc
    domain_name = domain.replace('www.', '')
    os.makedirs("crawller_result", exist_ok=True)

    jsonl_file = f'crawl_results/{domain_name}_{str(uuid4())}_crawl.jl'
    

    try:
        # Run crawler in a separate thread
        await asyncio.to_thread(
            adv.crawl,
            seed_url,
            output_file=jsonl_file,
            follow_links=True,
            allowed_domains=[domain],
        )

        # Load results
        df = await asyncio.to_thread(pd.read_json, jsonl_file, lines=True)
        all_urls = df['url'].unique().tolist()

        print(f"Total pages found: {len(all_urls)}")

       

        print("-" * 50)
        print("First 10 URLs:")
        for url in sorted(all_urls)[:10]:
            print(f"  - {url}")

        if len(all_urls) > 10:
            print(f"... and {len(all_urls) - 10} more URLs")

        return {
            'domain': domain,
            'domain_name': domain_name,
            'total_urls': len(all_urls),
            'jsonl_file': jsonl_file,
            'urls': all_urls
        }

    except Exception as e:
        print(f"Error during crawling: {e}")
        return e






class UrlFormat(BaseModel):
    urls: list[str]


model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
).with_structured_output(UrlFormat)


system_prompt = """
You are an intelligent system. 
You will receive a list of URLs from the user. 
Return ONLY 30–40 of the most relevant and important URLs that best represent the website.
Respond only with the JSON structure { "urls": [...] }.
"""



async def refine_urls(urls: list[str]):
    try:
        
        user_message_text = "Here are URLs:\n" + "\n".join(urls) + "\nReturn the best 30-40."

        refined: UrlFormat = model.invoke([
            HumanMessage(content=system_prompt),
            HumanMessage(content=user_message_text)
        ])
        
        
        urls_list = refined.urls  

        
        return urls_list 

    except Exception as error:
        print(f"error in refine_urls: {error}")
        return None

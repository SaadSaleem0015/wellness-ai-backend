
import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import re
import time
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_scraper")

class SimpleAsyncScraper:
    def __init__(self):
        """Initialize the scraper"""
        self.playwright = None
        self.browser = None
        self.context = None
        
    async def initialize(self):
        """Initialize browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                timeout=30000
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                java_script_enabled=True
            )
            logger.info("Browser initialized")
            return True
        except Exception as e:
            logger.error(f"Browser init error: {e}")
            await self.save_error("browser_init_error", str(e), "Browser initialization failed")
            return False
    
    async def close(self):
        """Close browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Close error: {e}")
    
    async def save_error(self, filename: str, error_msg: str, context: str = ""):
        """Save error to error folder"""
        try:
            error_dir = os.path.join("scraped_data", "errors")
            os.makedirs(error_dir, exist_ok=True)
            
            error_file = os.path.join(error_dir, f"{filename}.txt")
            
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"Error Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Context: {context}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Error: {error_msg}\n")
                f.write("=" * 50 + "\n")
            
            logger.info(f"Error saved to: {error_file}")
            return error_file
        except Exception as e:
            logger.error(f"Could not save error file: {e}")
            return None
    
    async def scroll_full_page(self, page):
        """Scroll to load all content"""
        try:
            logger.info("Scrolling page...")
            
            last_height = await page.evaluate('document.body.scrollHeight')
            scroll_count = 0
            
            while scroll_count < 10:
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1000)
                
                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scroll_count += 1
            
            logger.info(f"Scrolled {scroll_count} times")
            return True
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            await self.save_error("scroll_error", str(e), "Page scrolling failed")
            return False
    
    async def remove_unwanted_elements(self, page):
        """Remove headers, footers, etc."""
        try:
            removed = await page.evaluate('''() => {
                const selectors = [
                    'header', 'footer', 'nav', 'aside',
                    '.header', '.footer', '.navbar', '.sidebar',
                    '.ad', '.advertisement', '.social-share',
                    '.cookie-banner', '.popup', '.modal',
                    'script', 'style', 'iframe', 'noscript'
                ];
                
                let count = 0;
                selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        el.remove();
                        count++;
                    });
                });
                return count;
            }''')
            
            logger.info(f"Removed {removed} elements")
            return True
        except Exception as e:
            logger.error(f"Element removal error: {e}")
            return False
    
    async def extract_clean_text(self, page):
        """Extract clean text content"""
        try:
            await self.remove_unwanted_elements(page)
            
            content = await page.evaluate('''() => {
                // Try main content areas first
                const mainSelectors = ['main', 'article', '.content', '.post-content'];
                let content = '';
                
                for (const selector of mainSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.innerText.trim().length > 100) {
                        content = el.innerText;
                        break;
                    }
                }
                
                // Fallback to body
                if (!content) {
                    content = document.body.innerText;
                }
                
                return content;
            }''')
            
            # Clean the text
            cleaned = self._clean_text(content)
            return cleaned
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            await self.save_error("text_extraction_error", str(e), "Text extraction failed")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 30 and len(line.split()) > 3:
                cleaned_lines.append(line)
        
        return '\n\n'.join(cleaned_lines)
    
    def _get_safe_name(self, url: str) -> str:
        """Create safe filename from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace(':', '_').replace('.', '_')
            path = parsed.path.strip('/')
            
            if not path:
                name = f"{domain}_index"
            else:
                # Clean path
                clean_path = re.sub(r'[^a-zA-Z0-9]', '_', path)
                if len(clean_path) > 40:
                    clean_path = clean_path[:40]
                name = f"{domain}_{clean_path}"
            
            return name
        except Exception as e:
            logger.error(f"Filename error: {e}")
            return f"page_{int(time.time())}"
    
    async def save_content(self, url: str, title: str, content: str, output_dir: str):
        """Save text content to file"""
        try:
            # Create main directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Create safe filename
            safe_name = self._get_safe_name(url)
            txt_file = os.path.join(output_dir, f"{safe_name}.txt")
            
            # Write content
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Title: {title}\n")
                f.write(f"Scraped: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(content)
            
            logger.info(f"Text saved: {txt_file}")
            return txt_file
        except Exception as e:
            logger.error(f"Save content error: {e}")
            await self.save_error("save_content_error", str(e), f"URL: {url}")
            return ""
    
    async def save_screenshot(self, page, url: str, output_dir: str):
        """Save page screenshot"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            safe_name = self._get_safe_name(url)
            img_file = os.path.join(output_dir, f"{safe_name}.png")
            
            await page.screenshot(path=img_file, full_page=True)
            logger.info(f"Screenshot saved: {img_file}")
            return img_file
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            await self.save_error("screenshot_error", str(e), f"URL: {url}")
            return ""
    
    async def scrape_single_url(self, url: str, output_dir: str = "scraped_data") -> Dict[str, Any]:
        """
        Scrape single URL - saves only TXT and PNG files
        """
        result = {
            'success': False,
            'url': url,
            'txt_file': '',
            'img_file': '',
            'title': '',
            'error': '',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        page = None
        
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                result['url'] = url
            
            # Initialize browser if not already
            if not self.browser:
                init_success = await self.initialize()
                if not init_success:
                    result['error'] = "Browser initialization failed"
                    return result
            
            # Create page
            page = await self.context.new_page()
            
            # Navigate
            logger.info(f"Navigating to: {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                await self.save_error("navigation_error", str(e), f"URL: {url}")
                result['error'] = f"Navigation failed: {str(e)}"
                return result
            
            # Handle CAPTCHA (simple check)
            try:
                captcha_elements = await page.query_selector_all('iframe[src*="captcha"], div.g-recaptcha')
                if captcha_elements:
                    logger.warning("CAPTCHA detected - waiting 10 seconds")
                    await page.wait_for_timeout(10000)
            except Exception as e:
                logger.warning(f"CAPTCHA check error: {e}")
            
            # Scroll page
            await self.scroll_full_page(page)
            await page.wait_for_timeout(1000)
            
            # Get title
            result['title'] = await page.title()
            logger.info(f"Page title: {result['title']}")
            
            # Extract text
            content = await self.extract_clean_text(page)
            if not content or len(content.strip()) < 50:
                logger.warning("Very little content extracted")
            
            # Save files
            txt_file = await self.save_content(url, result['title'], content, output_dir)
            img_file = await self.save_screenshot(page, url, output_dir)
            
            if txt_file:
                result['txt_file'] = txt_file
                result['success'] = True
            
            if img_file:
                result['img_file'] = img_file
            
            logger.info(f"Scraping completed: {url}")
            
        except Exception as e:
            logger.error(f"Scraping error for {url}: {e}")
            result['error'] = str(e)
            
            # Save error details
            error_filename = f"error_{self._get_safe_name(url)}_{int(time.time())}"
            await self.save_error(error_filename, str(e), f"URL: {url}")
            
        finally:
            # Close page
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.error(f"Page close error: {e}")
        
        return result

# Main async function
async def scrape_url(url: str, output_dir: str = "scraped_data") -> Dict[str, Any]:
    """
    Simple async function to scrape URL
    Returns only TXT and PNG files
    """
    scraper = SimpleAsyncScraper()
    
    try:
        result = await scraper.scrape_single_url(url, output_dir)
        return result
    except Exception as e:
        logger.error(f"Function error: {e}")
        
        # Save error
        error_dir = os.path.join(output_dir, "errors")
        os.makedirs(error_dir, exist_ok=True)
        
        error_file = os.path.join(error_dir, f"function_error_{int(time.time())}.txt")
        try:
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error: {str(e)}\n")
        except:
            pass
        
        return {
            'success': False,
            'url': url,
            'error': str(e),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    finally:
        await scraper.close()

# Batch scraping function
async def scrape_urls(urls: list, output_dir: str = "scraped_data", max_concurrent: int = 2):
    """
    Scrape multiple URLs
    """
    results = []
    
    for i, url in enumerate(urls):
        logger.info(f"Scraping URL {i+1}/{len(urls)}: {url}")
        result = await scrape_url(url, output_dir)
        results.append(result)
        
        # Small delay between requests
        if i < len(urls) - 1:
            await asyncio.sleep(1)
    
    return {
        'total': len(urls),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'results': results
    }


# Quick function
async def quick_scrape(url: str):
    """Quick scrape function"""
    return await scrape_url(url)

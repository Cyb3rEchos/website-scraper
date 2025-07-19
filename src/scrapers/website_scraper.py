import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import hashlib
from tqdm import tqdm
import logging
import time
import mimetypes
import json
import re

class WebsiteScraper:
    def __init__(self, base_url, output_dir="website_content"):
        """
        Initialize the scraper with a base URL and output directory.
        
        Args:
            base_url (str): The website URL to scrape
            output_dir (str): Directory to save scraped content
        """
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.visited_urls = set()
        self.page_hierarchy = {}
        self.product_pages = set()
        self.category_pages = set()
        self.content_pages = set()
        self.setup_logging()
        self.setup_directories()
        
    def setup_logging(self):
        """Configure logging for the scraper."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(self.output_dir, exist_ok=True)
        
    def is_valid_url(self, url):
        """Check if URL belongs to the same domain as base_url."""
        if not url:
            return False
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        return base_domain == url_domain
        
    def clean_url(self, url):
        """Clean URL by removing query parameters and fragments."""
        parsed = urlparse(url)
        clean = parsed._replace(query="", fragment="").geturl()
        return clean.rstrip('/')
        
    def get_page_type(self, url, soup):
        """Determine the type of page (product, category, content)."""
        url_path = urlparse(url).path.lower()
        
        # Check for product pages
        if (
            'product' in url_path or
            soup.find('div', class_='product') or
            soup.find('div', class_='woocommerce-product-gallery')
        ):
            return 'product'
            
        # Check for category/shop pages
        if (
            'category' in url_path or
            'shop' in url_path or
            soup.find('ul', class_='products') or
            soup.find('div', class_='woocommerce-products-header')
        ):
            return 'category'
            
        return 'content'
        
    def get_page_path(self, url):
        """
        Convert URL to a filesystem path.
        Example: https://example.com/products/item1 -> products/item1
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            path = 'home'
        else:
            # Clean the path for filesystem
            path = unquote(path)  # Handle URL-encoded characters
            path = re.sub(r'[<>:"/\\|?*]', '-', path)
            path = path.lower()
        return path
        
    def create_page_directory(self, url):
        """Create directory structure for a page."""
        page_path = self.get_page_path(url)
        full_path = os.path.join(self.output_dir, page_path)
        os.makedirs(full_path, exist_ok=True)
        os.makedirs(os.path.join(full_path, 'images'), exist_ok=True)
        os.makedirs(os.path.join(full_path, 'text'), exist_ok=True)
        return full_path
        
    def download_image(self, img_url, page_dir):
        """
        Download and save an image in the page's directory.
        
        Args:
            img_url (str): URL of the image
            page_dir (str): Directory to save the image
        
        Returns:
            dict: Image metadata including local path and original URL
        """
        try:
            response = requests.get(img_url, stream=True)
            if response.status_code == 200:
                # Get original filename from URL
                orig_filename = os.path.basename(urlparse(img_url).path)
                name_without_ext = os.path.splitext(orig_filename)[0]
                
                # Get extension from content type
                content_type = response.headers.get('content-type', '')
                ext = mimetypes.guess_extension(content_type) or os.path.splitext(orig_filename)[1] or '.bin'
                
                # Create safe filename
                safe_filename = re.sub(r'[<>:"/\\|?*]', '-', name_without_ext) + ext
                safe_filename = safe_filename.lower()
                filepath = os.path.join(page_dir, 'images', safe_filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
                self.logger.info(f"Downloaded image: {img_url}")
                return {
                    'original_url': img_url,
                    'local_path': os.path.relpath(filepath, self.output_dir),
                    'filename': safe_filename,
                    'content_type': content_type
                }
        except Exception as e:
            self.logger.error(f"Failed to download image {img_url}: {str(e)}")
        return None
        
    def extract_metadata(self, soup, url):
        """Extract metadata from the page."""
        metadata = {
            'title': soup.title.string if soup.title else None,
            'meta_description': None,
            'meta_keywords': None,
            'h1_headings': [h1.get_text(strip=True) for h1 in soup.find_all('h1')],
            'h2_headings': [h2.get_text(strip=True) for h2 in soup.find_all('h2')],
            'h3_headings': [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
        }
        
        # Get meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            metadata['meta_description'] = meta_desc.get('content')
            
        # Get meta keywords
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords:
            metadata['meta_keywords'] = meta_keywords.get('content')
            
        # Extract product-specific metadata if it's a product page
        if self.get_page_type(url, soup) == 'product':
            price = soup.find(class_=['price', 'woocommerce-Price-amount'])
            sku = soup.find(class_='sku')
            stock = soup.find(class_='stock')
            
            metadata['product_info'] = {
                'price': price.get_text(strip=True) if price else None,
                'sku': sku.get_text(strip=True) if sku else None,
                'stock_status': stock.get_text(strip=True) if stock else None,
                'categories': [cat.get_text(strip=True) for cat in soup.find_all(class_='posted_in')],
                'tags': [tag.get_text(strip=True) for tag in soup.find_all(class_='tagged_as')]
            }
            
        return metadata
        
    def extract_structured_data(self, soup):
        """Extract structured data (JSON-LD, microdata) from the page."""
        structured_data = []
        
        # Extract JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except:
                pass
                
        return structured_data if structured_data else None
        
    def scrape_page(self, url):
        """
        Scrape a single page for content and links.
        
        Args:
            url (str): URL to scrape
            
        Returns:
            tuple: (list of discovered URLs, page data dictionary)
        """
        clean_url = self.clean_url(url)
        if clean_url in self.visited_urls or not self.is_valid_url(clean_url):
            return [], None
            
        self.visited_urls.add(clean_url)
        page_dir = self.create_page_directory(clean_url)
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch {url}: Status code {response.status_code}")
                return [], None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Determine page type
            page_type = self.get_page_type(clean_url, soup)
            
            # Extract metadata and structured data
            metadata = self.extract_metadata(soup, clean_url)
            structured_data = self.extract_structured_data(soup)
            
            # Extract and save text content
            text_content = soup.get_text(separator='\n', strip=True)
            text_file = os.path.join(page_dir, 'text', 'content.txt')
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Page Type: {page_type}\n\n")
                f.write(text_content)
            
            # Download images
            images = []
            for img in soup.find_all('img'):
                img_url = img.get('src')
                if img_url:
                    img_url = urljoin(url, img_url)
                    img_data = self.download_image(img_url, page_dir)
                    if img_data:
                        img_data['alt_text'] = img.get('alt', '')
                        images.append(img_data)
            
            # Find all links
            links = []
            link_data = []
            for link in soup.find_all('a'):
                href = link.get('href')
                if href:
                    absolute_url = urljoin(url, href)
                    if self.is_valid_url(absolute_url):
                        clean_link = self.clean_url(absolute_url)
                        links.append(clean_link)
                        link_data.append({
                            'url': clean_link,
                            'text': link.get_text(strip=True),
                            'title': link.get('title', '')
                        })
            
            # Create page data structure
            page_data = {
                'url': clean_url,
                'original_url': url,
                'path': self.get_page_path(clean_url),
                'type': page_type,
                'metadata': metadata,
                'structured_data': structured_data,
                'images': images,
                'links': link_data,
                'local_text_file': os.path.relpath(text_file, self.output_dir)
            }
            
            # Save page data as JSON
            page_info_file = os.path.join(page_dir, 'page_info.json')
            with open(page_info_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, indent=2)
            
            # Update hierarchy and page sets
            self.page_hierarchy[clean_url] = {
                'path': self.get_page_path(clean_url),
                'title': metadata['title'],
                'type': page_type,
                'children': []
            }
            
            # Add to appropriate page set
            if page_type == 'product':
                self.product_pages.add(clean_url)
            elif page_type == 'category':
                self.category_pages.add(clean_url)
            else:
                self.content_pages.add(clean_url)
            
            return links, page_data
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return [], None
            
    def save_site_hierarchy(self):
        """Save the complete site hierarchy to JSON files."""
        # Save main hierarchy
        hierarchy_file = os.path.join(self.output_dir, 'site_hierarchy.json')
        with open(hierarchy_file, 'w', encoding='utf-8') as f:
            json.dump(self.page_hierarchy, f, indent=2)
            
        # Save page type listings
        pages_file = os.path.join(self.output_dir, 'page_listings.json')
        page_listings = {
            'products': list(self.product_pages),
            'categories': list(self.category_pages),
            'content': list(self.content_pages)
        }
        with open(pages_file, 'w', encoding='utf-8') as f:
            json.dump(page_listings, f, indent=2)
            
    def scrape_website(self, max_pages=None):
        """
        Scrape the entire website starting from base_url.
        
        Args:
            max_pages (int, optional): Maximum number of pages to scrape
        """
        to_visit = [self.base_url]
        pages_scraped = 0
        
        with tqdm(total=max_pages or float('inf'), desc="Scraping pages") as pbar:
            while to_visit and (max_pages is None or pages_scraped < max_pages):
                current_url = to_visit.pop(0)
                new_links, page_data = self.scrape_page(current_url)
                
                if page_data:
                    # Update parent-child relationships in hierarchy
                    current_clean = self.clean_url(current_url)
                    for link in page_data['links']:
                        link_clean = self.clean_url(link['url'])
                        if link_clean in self.page_hierarchy:
                            self.page_hierarchy[current_clean]['children'].append(link_clean)
                
                # Add new links to visit
                for link in new_links:
                    if self.clean_url(link) not in self.visited_urls:
                        to_visit.append(link)
                
                pages_scraped += 1
                pbar.update(1)
                
                # Respect rate limiting
                time.sleep(1)
        
        # Save final site hierarchy and page listings
        self.save_site_hierarchy()
        self.logger.info(f"Scraping completed. Processed {pages_scraped} pages.")
        self.logger.info(f"Found {len(self.product_pages)} products, {len(self.category_pages)} categories, and {len(self.content_pages)} content pages.") 
from src.scrapers.website_scraper import WebsiteScraper
import argparse
import os
import sys

def validate_url(url):
    """Basic URL validation."""
    if not url.startswith(('http://', 'https://')):
        return False
    return True

def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description='Website Content Scraper - Downloads all content from a website in a structured format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python example.py https://example.com
  python example.py https://example.com --max-pages 10
  python example.py https://example.com --output-dir my_website_content
        """
    )
    
    parser.add_argument('url', 
                       help='The website URL to scrape (must start with http:// or https://)')
    parser.add_argument('--max-pages', 
                       type=int, 
                       help='Maximum number of pages to scrape (optional)')
    parser.add_argument('--output-dir', 
                       default='website_content', 
                       help='Directory to save scraped content (default: website_content)')
    
    args = parser.parse_args()
    
    # Validate URL
    if not validate_url(args.url):
        print("Error: Invalid URL. Please provide a URL starting with http:// or https://")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"\nStarting website scraper...")
    print(f"Target URL: {args.url}")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")
    if args.max_pages:
        print(f"Maximum pages to scrape: {args.max_pages}")
    print("\nPress Ctrl+C to stop the scraper at any time.\n")
    
    try:
        # Initialize and run the scraper
        scraper = WebsiteScraper(base_url=args.url, output_dir=args.output_dir)
        scraper.scrape_website(max_pages=args.max_pages)
        
        print("\nScraping completed! Content structure:")
        print(f"\nOutput directory: {os.path.abspath(args.output_dir)}")
        print("\nDirectory structure contains:")
        print("- site_hierarchy.json - Overall site structure")
        print("- page_listings.json - Categorized list of all pages")
        print("- Each page has its own directory containing:")
        print("  - page_info.json - Page metadata, links, and image information")
        print("  - images/ - Downloaded images with meaningful names")
        print("  - text/ - Text content in content.txt")
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user. Partial content has been saved.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
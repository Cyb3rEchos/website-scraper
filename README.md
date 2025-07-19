# Website Content Scraper

A comprehensive website scraping tool that captures all content and maintains the site's structure. This tool downloads and organizes:
- All text content
- All images
- Site hierarchy
- Page metadata
- Links and relationships

## Features

- Scrapes entire websites while maintaining structure
- Downloads and organizes all images
- Captures page metadata and content
- Creates a complete site hierarchy
- Respects rate limiting
- Provides detailed logging
- Shows real-time progress
- Handles errors gracefully
- Creates meaningful file names

## Installation

1. Clone this repository:
```bash
git clone https://github.com/cyb3rechos/website-scraper.git
cd website-scraper
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
python example.py https://example.com
```

With options:
```bash
# Limit the number of pages to scrape
python example.py https://example.com --max-pages 100

# Specify a custom output directory
python example.py https://example.com --output-dir my_website_content
```

The scraped content will be saved in the following structure:
```
website_content/              # Main output directory
├── site_hierarchy.json      # Overall site structure
├── page_listings.json       # Categorized list of all pages
└── [page-paths]/           # Directories for each page
    ├── page_info.json      # Page metadata and content info
    ├── images/             # Page-specific images
    │   └── [image-files]
    └── text/
        └── content.txt     # Page text content
```

## Output Structure

1. **site_hierarchy.json**:
   - Complete site structure
   - Parent-child relationships
   - Navigation paths

2. **page_listings.json**:
   - Categorized page lists
   - Product pages
   - Category pages
   - Content pages

3. **Page Directories**:
   - Named after page URLs
   - Contains all page-specific content
   - Maintains original structure

4. **page_info.json** (per page):
   - Page metadata
   - Image information
   - Link relationships
   - Content structure

## Configuration

The scraper automatically:
- Creates necessary directories
- Saves detailed logs to `scraper.log`
- Respects website rate limiting (1 second delay between requests)
- Only scrapes pages from the same domain as the base URL

## Error Handling

The scraper includes comprehensive error handling:
- Failed downloads are logged but don't stop the process
- Invalid URLs are skipped
- Network errors are caught and logged
- Malformed content is handled gracefully
- Keyboard interrupt (Ctrl+C) saves partial progress

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License 
import json
from playwright.sync_api import sync_playwright


def extract_entertainment_news(page):
    
    entertainment_news = []
    
    page.goto("https://ekantipur.com/", timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    
    # Navigate to the entertainment section
    page.goto("https://ekantipur.com/entertainment", timeout=60000)
    
    # Wait for the news articles to load
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("article", timeout=30000)
    
    # Get all article elements
    articles = page.query_selector_all("article")
    
    # Extract data from top 5 articles
    count = 0
    for article in articles:
        if count >= 5:
            break
        
        try:
            # Extract title from the article heading
            title_el = article.query_selector("h2, h3, h4")
            if not title_el:
                continue
            title = title_el.text_content().strip() if title_el else None
            
            if not title:
                continue
            
            # Extract image URL
            img_el = article.query_selector("img")
            image_url = None
            if img_el:
                # Try different image attributes (src, data-src for lazy loading)
                image_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")
            
            # Extract category from category label/tag
            category_el = article.query_selector(".caption, .category, [class*='category'], [class*='label'], span.d-block")
            category = category_el.text_content().strip() if category_el else "मनोरञ्जन"
            
            # Extract author if available
            author_el = article.query_selector(".author, [class*='author'], .byline, [class*='writer']")
            author = author_el.text_content().strip() if author_el else None
            
            entertainment_news.append({
                "title": title,
                "image_url": image_url,
                "category": category,
                "author": author
            })
            count += 1
            
        except Exception as e:
            # Continue to next article if there's an error extracting data
            continue
    
    return entertainment_news


def extract_cartoon_of_the_day(page):
    
    cartoon_data = {
        "title": None,
        "image_url": None,
        "author": None
    }
    
    try:
        # Navigate to the homepage to find cartoon section
        page.goto("https://ekantipur.com", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        
        # Scroll down to load more content
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(2000)
        
        # Look for the cartoon section on the homepage
        # The cartoon section typically has "कार्टुन" heading and shows cartoons like "गजब छ बा"
        cartoon_section = page.query_selector("a[href*='/cartoon']")
        
        if cartoon_section:
            # Get the parent section that contains cartoon info
            # Look for the cartoon image and title near the cartoon link
            parent = page.evaluate("""() => {
                const cartoonLink = document.querySelector("a[href*='/cartoon']");
                if (cartoonLink) {
                    // Find the nearest image
                    let parent = cartoonLink.closest('section') || cartoonLink.closest('div');
                    if (parent) {
                        const img = parent.querySelector('img');
                        const text = parent.textContent;
                        return {
                            imgSrc: img ? (img.src || img.getAttribute('data-src')) : null,
                            text: text
                        };
                    }
                }
                return null;
            }""")
        
        # Try to find cartoon by looking for specific patterns on the page
        # Look for image with "gajab" or cartoon-related content
        cartoon_img = page.query_selector("img[src*='gajab'], img[alt*='गजब'], img[alt*='व्यंग्य']")
        if not cartoon_img:
            # Try alternate selector
            all_images = page.query_selector_all("img")
            for img in all_images:
                src = img.get_attribute("src") or ""
                if "gajab" in src.lower() or "cartoon" in src.lower() or "vyangya" in src.lower():
                    cartoon_img = img
                    break
        
        if cartoon_img:
            cartoon_data["image_url"] = cartoon_img.get_attribute("src") or cartoon_img.get_attribute("data-src")
            
            # Try to get alt text as title
            alt_text = cartoon_img.get_attribute("alt")
            if alt_text:
                cartoon_data["title"] = alt_text
        
        # Extract title and author from the page content
        # Look for text patterns like "गजब छ बा! - अविन"
        page_content = page.evaluate("""() => {
            // Look for cartoon section text
            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                const text = el.textContent;
                if (text && (text.includes('गजब छ बा') || text.includes('व्यंग्य'))) {
                    // Check if this is a small element with just the caption
                    if (el.textContent.length < 100) {
                        return el.textContent.trim();
                    }
                }
            }
            return null;
        }""")
        
        if page_content:
            # Parse the caption - format is typically "Title - Author"
            # Clean up any prefix like "कार्टुन"
            page_content = page_content.replace("कार्टुन", "").strip()
            if " - " in page_content:
                parts = page_content.split(" - ")
                if len(parts) >= 2:
                    cartoon_data["title"] = parts[0].strip()
                    cartoon_data["author"] = parts[-1].strip()
            else:
                cartoon_data["title"] = page_content.strip()
        
        # If we still don't have complete data, try navigating to cartoon page
        page.goto("https://ekantipur.com/cartoon", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        
        if not cartoon_data["image_url"] or not cartoon_data["title"]:
            
            # Get first article
            article = page.query_selector("article")
            if article:
                # Get the article link and navigate
                link = article.query_selector("a")
                if link:
                    href = link.get_attribute("href")
                    if href:
                        if not href.startswith("http"):
                            href = "https://ekantipur.com" + href
                        page.goto(href, timeout=60000)
                        page.wait_for_load_state("domcontentloaded")
                        
                        # Extract from detail page
                        title_el = page.query_selector("h1")
                        if title_el and not cartoon_data["title"]:
                            title_text = title_el.text_content().strip()
                            # Clean up title - format might be "Title - Date"
                            if " - " in title_text:
                                parts = title_text.split(" - ")
                                cartoon_data["title"] = parts[0].strip()
                            else:
                                cartoon_data["title"] = title_text
                        
                        img_el = page.query_selector("figure img, article img")
                        if img_el and not cartoon_data["image_url"]:
                            cartoon_data["image_url"] = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                        
                        # Get author from the detail page
                        author_el = page.query_selector(".author-name a, .author a, [class*='author'] a")
                        if author_el and not cartoon_data["author"]:
                            cartoon_data["author"] = author_el.text_content().strip()
                
    except Exception as e:
        # Return partial data if extraction fails
        print(f"Error extracting cartoon: {e}")
    
    return cartoon_data


def main():
    """
    Main function that orchestrates the scraping process.
    Extracts entertainment news and cartoon of the day, then saves to output.json.
    """
    with sync_playwright() as p:
        # Launch browser (headless mode for production)
        print("Opening browser...")
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        # Set a reasonable timeout for page loads
        page.set_default_timeout(30000)
        
        # Extract entertainment news
        print("Extracting entertainment news...")
        entertainment_news = extract_entertainment_news(page)
        print(f"Extracted {len(entertainment_news)} entertainment articles")
        
        # Extract cartoon of the day
        print("Extracting cartoon of the day...")
        cartoon_of_the_day = extract_cartoon_of_the_day(page)
        print("Cartoon extraction complete")
        
        # Close browser
        browser.close()
        
        # Prepare output data
        output_data = {
            "entertainment_news": entertainment_news,
            "cartoon_of_the_day": cartoon_of_the_day
        }
        
        # Save to output.json with proper Nepali text encoding
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print("Data saved to output.json")


if __name__ == "__main__":
    main()

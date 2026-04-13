import json
from urllib.parse import urljoin, urlparse
from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

BASE_URL = "https://ekantipur.com"

SELECTORS = {
    # ── Entertainment Section ────────────────────────────────────────────────
    "entertainment": {
        # Container element for a single news article card
        "article_card": (
            "div.category, article, .article-item, .post-item, .news-item, li.post"
        ),

        # Headline element inside a card (tried in order)
        "title": "h2 a, h3 a, h4 a, .title a, h2, h3, h4, .title",

        # Thumbnail / post image inside a card
        "image": ".category-image img, img",

        # Category / section label inside a card
        "category": (
            ".badge, .label, .section-tag, .tag, "
            ".category-name a, .category-name p a"
        ),

        # Author byline inside a card
        "author": (
            ".author-name a, .author-name, .author, .byline, "
            "[class*='author'], [class*='byline'], [class*='writer']"
        ),
    },

    # ── Cartoon Section ──────────────────────────────────────────────────────
    "cartoon": {
        # First article card on the cartoon listing page
        "article_card": (
            ".cartoon-wrapper, article, .article-item, .post-item, li.post, .category"
        ),

        # Title / description on cartoon listing page directly
        "title": ".cartoon-description p",

        # Image on cartoon listing page directly
        "image": ".cartoon-image img",

        # ── Selectors used on the cartoon *detail* page (if it exists) ───────
        # Main headline on detail page
        "detail_title": "h1.article-title, h1, .article-header h1",

        # Primary image on detail page (figure first, then fallback)
        "detail_image": (
            "figure img, .article-img img, .post-thumbnail img, "
            ".featured-image img, article img, .content img"
        ),

        # Author on detail page
        "detail_author": (
            ".author-name a, .author a, [class*='author'] a, "
            ".byline a, .writer a, [class*='author'], .byline"
        ),
    },
}

DISCOVERY_RULES = {
    "entertainment": {
        "label": "मनोरञ्जन",
        "text_keywords": ("मनोरञ्जन", "मनोरंजन", "entertainment"),
        "href_keywords": ("entertainment", "manoranjan"),
    },
    "cartoon": {
        "label": "व्यंग्यचित्र / कार्टुन",
        "text_keywords": ("व्यंग्यचित्र", "कार्टुन", "कार्टून", "cartoon"),
        "href_keywords": ("cartoon", "vyangya"),
    },
}

def make_absolute(url: str | None) -> str | None:
    """Convert a relative URL to absolute using BASE_URL.  Returns None if empty."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(BASE_URL, url)


def safe_text(element) -> str | None:
    """Return stripped text_content of an element, or None if element is falsy."""
    if element is None:
        return None
    try:
        text = element.text_content()
        return text.strip() if text else None
    except Exception:
        return None


def resolve_image_src(img_element) -> str | None:
    """
    Extract image URL from an <img> element, checking multiple attributes.
    Lazy-loaded images use data-src / data-lazy-src instead of src.
    """
    if img_element is None:
        return None
    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
        try:
            val = img_element.get_attribute(attr)
            if val and not val.startswith("data:"):   # skip base64 placeholders
                return make_absolute(val)
        except Exception:
            continue
    return None


def scroll_page_to_load_images(page: Page) -> None:
    """
    Scroll incrementally to trigger lazy-loaded images.
    ekantipur.com uses IntersectionObserver-based lazy loading.
    """
    page.evaluate("""
        () => {
            return new Promise(resolve => {
                let scrollCount = 0;
                let stableRounds = 0;
                let lastHeight = document.body.scrollHeight;

                const maxScrolls = 30;
                const step = 500;
                const timer = setInterval(() => {
                    window.scrollBy(0, step);
                    scrollCount += 1;

                    const currentHeight = document.body.scrollHeight;
                    if (currentHeight === lastHeight) {
                        stableRounds += 1;
                    } else {
                        stableRounds = 0;
                        lastHeight = currentHeight;
                    }

                    if (scrollCount >= maxScrolls || stableRounds >= 4) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 120);
            });
        }
    """)
    # Brief pause to let network requests settle after scrolling
    page.wait_for_timeout(800)
    # Scroll back to top so first articles are visible
    page.evaluate("window.scrollTo(0, 0)")


def dismiss_overlay_ad(page: Page) -> None:
    """
    Attempt to dismiss a full-page roadblock / overlay ad.
    Tries a close button first; falls back to JavaScript removal.
    Swallows all errors — ad may simply not be present.
    """
    try:
        close_btn = page.locator(
            "#roadblock-ad .close, #roadblock-ad [class*='close'], "
            "[class*='roadblock'] .close, [class*='overlay'] .close, "
            "button[class*='close'], button[aria-label='Close']"
        ).first
        close_btn.click(timeout=3000)
        page.wait_for_timeout(600)
        print("  [ad] Dismissed overlay ad via close button.")
        return
    except Exception:
        pass

    try:
        page.evaluate("""
            () => {
                const selectors = [
                    '#roadblock-ad',
                    '[class*="roadblock"]',
                    '[id*="roadblock"]',
                    '[class*="overlay-ad"]',
                    '[id*="overlay-ad"]',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                // Remove scroll lock that ads sometimes add to <body>
                document.body.style.overflow = '';
                document.documentElement.style.overflow = '';
            }
        """)
        print("  [ad] Removed overlay ad via JavaScript.")
    except Exception:
        pass  # No ad present or removal failed — continue normally


def is_ekantipur_internal(url: str | None) -> bool:
    """Return True for ekantipur.com absolute URLs."""
    if not url:
        return False
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc.endswith("ekantipur.com")
    except Exception:
        return False


def score_discovered_link(
    candidate: dict,
    text_keywords: tuple[str, ...],
    href_keywords: tuple[str, ...],
) -> int:
    """Score one anchor candidate; higher score means better section link match."""
    score = 0
    text = (candidate.get("text") or "").lower()
    href = (candidate.get("href") or "").lower()

    if any(k.lower() in text for k in text_keywords):
        score += 10
    if any(k.lower() in href for k in href_keywords):
        score += 8
    if candidate.get("in_nav"):
        score += 5

    path = urlparse(candidate.get("href") or "").path.strip("/")
    parts = [p for p in path.split("/") if p]

    # Prefer top-level section paths over deep detail links
    if len(parts) == 1:
        score += 10
    elif len(parts) == 2:
        score += 3
    elif len(parts) >= 4:
        score -= 4

    # Penalize article/detail links that include date fragments
    if any(any(ch.isdigit() for ch in part) for part in parts):
        score -= 6

    return score


def discover_section_link(page: Page, section_key: str) -> str | None:
    """Discover a section URL from live DOM anchors via keyword + structure scoring."""
    rules = DISCOVERY_RULES[section_key]
    label = rules["label"]

    print(f"  [nav] Discovering link for '{label}' from page anchors...")

    anchors = page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: (a.getAttribute('href') || '').trim(),
                text: (a.innerText || a.textContent || '').replace(/\\s+/g, ' ').trim(),
                in_nav: Boolean(a.closest('nav, header, [role="navigation"], .menu, .navbar'))
            }));
        }
    """)

    best_by_url: dict[str, dict] = {}
    for item in anchors:
        raw_href = (item.get("href") or "").strip()
        if not raw_href or raw_href.startswith("#") or raw_href.startswith("javascript:"):
            continue

        abs_href = make_absolute(raw_href)
        if not is_ekantipur_internal(abs_href):
            continue

        candidate = {
            "href": abs_href,
            "text": item.get("text") or "",
            "in_nav": bool(item.get("in_nav")),
        }
        candidate["score"] = score_discovered_link(
            candidate,
            text_keywords=rules["text_keywords"],
            href_keywords=rules["href_keywords"],
        )

        current = best_by_url.get(abs_href)
        if current is None or candidate["score"] > current["score"]:
            best_by_url[abs_href] = candidate

    if not best_by_url:
        print(f"  [nav] No anchors discovered for '{label}'.")
        return None

    ranked = sorted(best_by_url.values(), key=lambda c: c["score"], reverse=True)
    best = ranked[0]

    if best["score"] < 8:
        print(
            f"  [nav] Could not confidently detect '{label}' link "
            f"(best score={best['score']})."
        )
        return None

    print(f"  [nav] Discovered link for '{label}' -> {best['href']}")
    return best["href"]


def navigate_to_section(page: Page, section_key: str) -> bool:
    """
    Discover section link from live DOM and navigate to that extracted URL.
    Returns True only when discovery and navigation both succeed.
    """
    rules = DISCOVERY_RULES[section_key]
    label = rules["label"]

    target_url = discover_section_link(page, section_key)
    if not target_url:
        return False

    print(f"  [nav] Navigating to extracted URL for '{label}'...")

    try:
        page.goto(target_url, timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        print(f"  [nav] Arrived at discovered link for '{label}'. URL: {page.url}")
        return True
    except Exception as e:
        print(f"  [nav] Failed navigating to discovered link for '{label}': {e}")
        return False


# ---------------------------------------------------------------------------
# ENTERTAINMENT NEWS EXTRACTOR
# ---------------------------------------------------------------------------

def extract_entertainment_news(page: Page) -> list[dict]:
    """
    Navigate to the entertainment section and extract the top-5 article cards.

    For each article:
        title     – headline text
        image_url – absolute thumbnail URL (lazy-src aware)
        category  – section/category label text
        author    – byline text or None if absent
    """
    print("\n=== ENTERTAINMENT NEWS EXTRACTION ===")

    # ── Step 1: Load homepage first so nav links are rendered ────────────────
    print("[1/4] Loading homepage...")
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("domcontentloaded", timeout=30000)
    dismiss_overlay_ad(page)

    # ── Step 2: Navigate to entertainment section ────────────────────────────
    print("[2/4] Navigating to Entertainment section...")
    ok = navigate_to_section(page, section_key="entertainment")
    if not ok:
        print("[!] Could not reach entertainment section. Returning empty list.")
        return []

    dismiss_overlay_ad(page)

    # ── Step 3: Wait for article cards then scroll to trigger lazy-load ──────
    print("[3/4] Waiting for article cards to appear...")
    try:
        page.wait_for_selector(SELECTORS["entertainment"]["article_card"], timeout=25000)
    except PlaywrightTimeoutError:
        print("[!] Article card selector timed out. Proceeding with whatever is loaded.")

    print("[3/4] Scrolling page to trigger lazy-loaded images...")
    scroll_page_to_load_images(page)

    # ── Step 4: Collect and parse top-5 cards ────────────────────────────────
    print("[4/4] Locating article cards...")
    cards = page.query_selector_all(SELECTORS["entertainment"]["article_card"])
    print(f"Found {len(cards)} article card(s) on page. Targeting top 5.")

    entertainment_news: list[dict] = []

    for idx, card in enumerate(cards):
        if len(entertainment_news) >= 5:
            break

        print(f"\n  Extracting article {len(entertainment_news) + 1} (DOM index {idx})...")

        # ── Title ────────────────────────────────────────────────────────────
        title: str | None = None
        try:
            title_el = card.query_selector(SELECTORS["entertainment"]["title"])
            title = safe_text(title_el)
            if not title:
                # No title means this card is probably an ad or non-article widget; skip it
                print("    [skip] No title found — likely a non-article card.")
                continue
            title_preview = f"{title[:60]}…" if len(title) > 60 else title
            print(f"    title    : {title_preview}")
        except Exception as e:
            print(f"    [warn] Title extraction error: {e}. Skipping card.")
            continue

        # ── Image URL ────────────────────────────────────────────────────────
        image_url: str | None = None
        try:
            img_el = card.query_selector(SELECTORS["entertainment"]["image"])
            image_url = resolve_image_src(img_el)
            print(f"    image_url: {image_url or '(not found)'}")
        except Exception as e:
            print(f"    [warn] Image extraction error: {e}")

        # ── Category ─────────────────────────────────────────────────────────
        category: str | None = None
        try:
            cat_el = card.query_selector(SELECTORS["entertainment"]["category"])
            category = safe_text(cat_el) or "मनोरञ्जन"
            print(f"    category : {category or '(not found)'}")
        except Exception as e:
            print(f"    [warn] Category extraction error: {e}")
            category = "मनोरञ्जन"

        # ── Author ───────────────────────────────────────────────────────────
        # Explicitly set to None if not found — outputs as JSON null
        author: str | None = None
        try:
            author_el = card.query_selector(SELECTORS["entertainment"]["author"])
            author = safe_text(author_el) or None
            print(f"    author   : {author or 'null (not found)'}")
        except Exception as e:
            print(f"    [warn] Author extraction error: {e} — defaulting to null")
            author = None

        entertainment_news.append(
            {
                "title": title,
                "image_url": image_url,
                "category": category,
                "author": author,
            }
        )

    print(f"\n✓ Entertainment extraction complete. {len(entertainment_news)} article(s) extracted.")
    return entertainment_news


# ---------------------------------------------------------------------------
# CARTOON OF THE DAY EXTRACTOR
# ---------------------------------------------------------------------------

def extract_cartoon_of_the_day(page: Page) -> dict:
    """
    Navigate to the cartoon section, pick the most recent cartoon entry,
    and extract:
        title     – cartoon headline/caption
        image_url – absolute URL of the cartoon image
        author    – cartoonist name or None if absent
    """
    print("\n=== CARTOON OF THE DAY EXTRACTION ===")

    cartoon_data: dict = {
        "title": None,
        "image_url": None,
        "author": None,
    }

    # ── Step 1: Navigate to cartoon listing page ─────────────────────────────
    print("[1/3] Navigating to Cartoon section...")
    # Start from homepage so discovery runs against global navigation anchors.
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("domcontentloaded", timeout=30000)
    dismiss_overlay_ad(page)

    ok = navigate_to_section(page, section_key="cartoon")
    if not ok:
        print("[!] Could not reach cartoon section. Returning empty cartoon data.")
        return cartoon_data

    dismiss_overlay_ad(page)

    # ── Step 2: Wait for at least one article card ───────────────────────────
    print("[2/3] Waiting for cartoon article cards...")
    try:
        page.wait_for_selector(SELECTORS["cartoon"]["article_card"], timeout=15000)
    except PlaywrightTimeoutError:
        print("[!] Cartoon card selector timed out — trying to continue anyway.")

    scroll_page_to_load_images(page)

    # ── Step 3: Extract from the first cartoon card ──────────────────────────
    print("[3/3] Locating first cartoon card and extracting data...")
    try:
        first_card = page.query_selector(SELECTORS["cartoon"]["article_card"])
        if not first_card:
            print("[!] No cartoon card found on listing page.")
            return cartoon_data

        # ── Title & Author ───────────────────────────────────────────────────
        print("  Extracting title and author...")
        try:
            title_el = first_card.query_selector(SELECTORS["cartoon"]["title"])
            raw_title = safe_text(title_el)
            if raw_title:
                # It usually looks like "गजब छ बा! - अविन"
                parts = raw_title.split(" - ")
                if len(parts) > 1:
                    cartoon_data["title"] = parts[0].strip()
                    cartoon_data["author"] = parts[-1].strip()
                else:
                    cartoon_data["title"] = raw_title.strip()
            print(f"    title    : {cartoon_data['title'] or '(not found)'}")
            print(f"    author   : {cartoon_data['author'] or '(not found)'}")
        except Exception as e:
            print(f"    [warn] Title/Author extraction error: {e}")

        # ── Image URL ────────────────────────────────────────────────────────
        print("  Extracting image...")
        try:
            img_el = first_card.query_selector(SELECTORS["cartoon"]["image"])
            cartoon_data["image_url"] = resolve_image_src(img_el)
            print(f"    image_url: {cartoon_data['image_url'] or '(not found)'}")
        except Exception as e:
            print(f"    [warn] Image extraction error: {e}")

    except Exception as e:
        print(f"  [error] Cartoon listing page extraction failed: {e}")

    print(f"\n✓ Cartoon extraction complete.")
    return cartoon_data


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Orchestrates the full scraping run:
      1. Launch a Chromium browser
      2. Extract entertainment news (top 5)
      3. Extract cartoon of the day
      4. Merge results and write output.json
    """
    print("=" * 60)
    print("  ekantipur.com Scraper — Starting")
    print("=" * 60)

    with sync_playwright() as pw:
        # ── Browser setup ────────────────────────────────────────────────────
        # headless=True for production; set to False for visual debugging
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
        )
        page = context.new_page()

        # ── Entertainment news ───────────────────────────────────────────────
        entertainment_news = extract_entertainment_news(page)
        print(f"\nSummary: extracted {len(entertainment_news)} entertainment article(s).")

        # ── Cartoon of the day ───────────────────────────────────────────────
        cartoon_of_the_day = extract_cartoon_of_the_day(page)
        has_cartoon = any(v is not None for v in cartoon_of_the_day.values())
        print(f"Summary: cartoon data {'found' if has_cartoon else 'not found'}.")

        # ── Teardown ─────────────────────────────────────────────────────────
        context.close()
        browser.close()
        print("\nBrowser closed.")

    # ── Write output.json ────────────────────────────────────────────────────
    output = {
        "entertainment_news": entertainment_news,
        "cartoon_of_the_day": cartoon_of_the_day,
    }

    output_path = "output.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        # ensure_ascii=False is mandatory so Devanagari characters render
        # correctly instead of being escaped as \uXXXX sequences
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print(f"\n✓ Data saved to '{output_path}'.")
    print("=" * 60)
    print("  Scraping complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()

# Playwright Python Automation

## Ekantipur News Scraper

### Purpose

This project scrapes selected content from [ekantipur.com](https://ekantipur.com) using Playwright (Python sync API).

The script collects:

- Up to 5 entertainment news items from the entertainment section
- One cartoon entry from the cartoon section

Results are saved as JSON in `output.json`.

### What the Program Collects

#### Entertainment News

For each collected article card, the script writes:

- **title**: article headline text
- **image_url**: resolved absolute image URL when available
- **category**: category label text (defaults to `मनोरञ्जन` when missing)
- **author**: byline text, or `null` when not found

#### Cartoon of the Day

For the first detected cartoon card, the script writes:

- **title**: cartoon caption/title when available
- **image_url**: resolved absolute image URL when available
- **author**: author/cartoonist when available, otherwise `null`

### How It Works (Based on `scraper.py`)

1. Launches Chromium with `headless=False`, custom user agent, and a fixed viewport.
2. Opens the homepage and attempts to dismiss overlay ads.
3. Discovers the entertainment section link from page anchors using keyword and URL scoring.
4. Navigates to the discovered entertainment URL, waits for cards, scrolls for lazy-loaded images, and extracts up to 5 valid cards.
5. Repeats homepage navigation and link discovery for the cartoon section.
6. Extracts data from the first matching cartoon card on the listing page.
7. Writes `output.json` with UTF-8 encoding and `ensure_ascii=False` (preserves Nepali text).

### Output Format

`output.json` has this structure:

```json
{
  "entertainment_news": [
    {
      "title": "string",
      "image_url": "string or null",
      "category": "string",
      "author": "string or null"
    }
  ],
  "cartoon_of_the_day": {
    "title": "string or null",
    "image_url": "string or null",
    "author": "string or null"
  }
}
```

### Tech Stack

- Python `>=3.12`
- Playwright for Python (sync API)

### Dependencies

From `pyproject.toml`:

- `playwright>=1.57.0`

Locked versions in `uv.lock`:

- `playwright==1.57.0`
- `greenlet==3.3.1`
- `pyee==13.0.0`
- `typing-extensions==4.15.0`

### Installation

#### Prerequisites

- Python `3.12` or newer
- `uv` package manager

From the repository root:

```bash
cd ekantipur-scraper
uv sync
```

### Usage

From the `ekantipur-scraper` directory:

```bash
uv run python scraper.py
```

The script has no CLI arguments defined in the codebase.

### Configuration

No command-line flags, environment variables, or external configuration files are clearly defined in the current codebase.

### Where Results Are Saved

The script writes to `output.json` in the current working directory. If you run the command from `ekantipur-scraper`, the file path is `ekantipur-scraper/output.json`.

### Project Structure

- `README.md`: repository documentation
- `ekantipur-scraper/`: scraper project directory
- `ekantipur-scraper/scraper.py`: main scraping script
- `ekantipur-scraper/output.json`: sample output file
- `ekantipur-scraper/pyproject.toml`: project metadata and direct dependency
- `ekantipur-scraper/uv.lock`: locked dependency versions

### Notes and Limitations

- Section navigation depends on runtime link discovery (keyword and URL scoring on page anchors).
- Cartoon extraction currently uses the first matching cartoon card on the listing page.
- Selectors for a cartoon detail page exist in code but are not used in the current extraction flow.
- The browser currently runs in headed mode (`headless=False`).
- A dedicated browser-installation step is not clearly defined in the codebase.
- Retry strategy, scheduling, and rate-limiting behavior are not clearly defined in the codebase.

### Contribution

A contribution workflow (branching strategy, linting/testing requirements, and pull request rules) is not clearly defined in the codebase.

### License

A license is not clearly defined in the codebase (no license file was found in the repository root).

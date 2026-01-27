# Data-QA-Intern-Practical-Test
## Ekantipur News Scraper

### Purpose

This project automatically collects news and cartoon information from ekantipur.com, a popular Nepali news website. The program opens a web browser, visits the website, and gathers specific pieces of information without any manual work needed.

The collected information includes:

- The top 5 entertainment news articles
- The daily cartoon (known as "Cartoon of the Day")

### What the Program Collects

#### Entertainment News

For each of the top 5 entertainment news articles, the program collects:

- **Title**: The headline of the news article
- **Image URL**: The web address of the article's picture
- **Category**: The section label (such as "मनोरञ्जन" which means Entertainment in Nepali)
- **Author**: The name of the person who wrote the article (if available)

#### Cartoon of the Day

For the daily cartoon, the program collects:

- **Title**: The name or caption of the cartoon
- **Image URL**: The web address of the cartoon image
- **Author**: The name of the cartoonist

### How It Works (Step by Step)

#### Step 1: Opening the Browser

The program starts by opening a web browser (Chromium). You will see this browser window appear on your screen, allowing you to watch the entire process happen.

#### Step 2: Collecting Entertainment News

1. The browser first goes to the main ekantipur.com website
2. It then navigates to the Entertainment section of the website
3. The program waits for the page to fully load
4. It looks through the news articles on the page
5. For each of the first 5 articles it finds, it reads and saves the title, picture address, category, and author name

#### Step 3: Collecting the Cartoon of the Day

1. The browser returns to the main ekantipur.com homepage
2. The program scrolls down the page to make sure all content is visible
3. It searches for the cartoon section by looking for specific words and image patterns
4. It reads the cartoon's title, picture address, and the cartoonist's name
5. If the cartoon information is not complete, the program visits the dedicated cartoon page to find any missing details

#### Step 4: Saving the Results

1. The browser closes
2. All collected information is organized into a structured format
3. The data is saved to a file called "output.json"
4. The file is saved with proper encoding to correctly display Nepali text

### How to Run the Program

#### Requirements

- Python version 3.12 or newer
- The uv package manager
- Playwright browser automation tool

#### Running the Script

Open a terminal or command prompt in the project folder and type:

```
uv run python scraper.py
```

The browser will open and you will see the program navigating through the website. Messages will appear in the terminal showing the progress.

### Where Results Are Saved

All collected data is saved in a file named **output.json** located in the same folder as the program. This file contains all the entertainment news articles and cartoon information in a structured format that can be easily read by other programs or opened in a text editor.

The file uses a format called JSON, which organizes the data with clear labels for each piece of information. Nepali text is preserved correctly in this file.

### Project Files

- **scraper.py**: The main program that does all the work
- **output.json**: The file where results are saved after running the program
- **pyproject.toml**: A configuration file that lists what software the program needs to run
- **prompts.txt**: A record of instructions used during the project development

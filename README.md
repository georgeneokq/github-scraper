# Github repositories scraper

Scrapes statistics from all repositories in an organization.

Currently scrapes for the following:
- Number of commits
- Time of last commit to main branch (should work even if it is named something else, e.g. "master")
- Full list of commit messages
- Contributors (scraped from commits)

NOTE: Only tested on organizations

## Requirements

Chrome installed on device (uses chrome webdriver to scrape)

## Usage
Fill `.env` file with relevant information.

`WEBSITE_URL`: A repository listing (e.g. https://github.com/orgs/google/repositories)

`USER_EMAIL`: Your github account email

`USER_PASSWORD`: Your github account password

`START_PAGE`: Page to start scraping from

`END_PAGE`: Page to stop scraping at

Login is currently a mandatory part of the process, the code can be altered to skip login.

Also prompts for OTP; if OTP isn't set up for your account, you could just press the enter key on
in the terminal to skip the process.
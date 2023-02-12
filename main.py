from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from os import getenv
from time import sleep
from sys import exit
from pathlib import Path
import time
import json

load_dotenv()

WEBSITE_URL = getenv('WEBSITE_URL')
USER_EMAIL = getenv('USER_EMAIL')
USER_PASSWORD = getenv('USER_PASSWORD')
START_PAGE = int(getenv('START_PAGE'))
END_PAGE = int(getenv('END_PAGE'))
LOGIN_PAGE_URL = 'https://github.com/login'

no_more_content_selector = '.blankslate-heading'

def no_more_content(browser: webdriver.Chrome):
  el = browser.find_element(By.CSS_SELECTOR, no_more_content_selector)
  return el is None

def main():
  save_dir = 'tmp'
  Path(save_dir).mkdir(parents=True, exist_ok=True)
  file_name = f'{int(time.time())}.json'

  chrome_options = Options()
  chrome_options.headless = True
  chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
  service = Service(executable_path=ChromeDriverManager().install())
  driver = webdriver.Chrome(service=service, options=chrome_options)
  driver.maximize_window()
  driver.get(LOGIN_PAGE_URL)

  print('Hold on while we load the OTP page...')

  email_input_element = driver.find_element(By.CSS_SELECTOR, '#login_field')
  password_input_element = driver.find_element(By.CSS_SELECTOR, '#password')
  login_button = driver.find_element(By.CSS_SELECTOR, 'input[type=submit]')

  email_input_element.send_keys(USER_EMAIL)
  password_input_element.send_keys(USER_PASSWORD)
  login_button.click()

  # Loading OTP page...

  try:
    otp_input_element = driver.find_element(By.CSS_SELECTOR, '#app_totp')
    otp = input('Enter OTP: ')
    otp_input_element.send_keys(otp)
    submit_otp_button = driver.find_element(By.CSS_SELECTOR, 'button[type=submit]')
    submit_otp_button.click()
  except:
    pass

  # Prepare dict of items to serialize
  statistics = {}

  print(f'Scraping from page {START_PAGE} to {END_PAGE}')

  for i in range(START_PAGE - 1, END_PAGE):
    # browse to page to scrape
    current_page_num = i + 1

    # form the URL and browse to it
    current_page_url = f'{WEBSITE_URL}?type=all&page={current_page_num}'
    driver.get(current_page_url)

    # Get list of repositories on the current page
    repository_list_items = driver.find_elements(By.CSS_SELECTOR, '.org-repos li')

    for i in range(len(repository_list_items)):
      repository_list_items = driver.find_elements(By.CSS_SELECTOR, '.org-repos li')
      repository_list_item = repository_list_items[i]
      link_to_repository = repository_list_item.find_element(By.CSS_SELECTOR, 'a')
      link = link_to_repository.get_attribute('href')

      driver.get(link)

      # read the url, get repo name
      repo_name = driver.current_url.split('/')[-1]
      print(f'Getting statistics for {repo_name}')

      statistics_item = {}

      # Get number of commits. Seems like it takes some time to load, might need to retry
      retries = 0
      while retries < 3:
        try:
          num_commits_element = driver.find_element(By.CSS_SELECTOR, '.d-none.d-sm-inline strong')
          statistics_item['num_commits'] = int(num_commits_element.text)
          break
        except:
          retries += 1
          sleep(1)

      if statistics_item.get('num_commits'):
        print(f'Number of commits: {statistics_item["num_commits"]}')
      
      # Get time of last commit to main branch.
      try:
        time_element = driver.find_element(By.CSS_SELECTOR, 'relative-time')
        statistics_item['last_commit_to_main'] = time_element.get_attribute('title')
        print(f'Last commit to main: {statistics_item["last_commit_to_main"]}')
      except:
        pass

      # Go into the commits page. Some people actually still keep the main branch as 'master'...
      commits_page_possible_link_elements = driver.find_elements(By.CSS_SELECTOR, '[data-pjax="#repo-content-pjax-container"]')
      commits_page_link_elements = list(filter(
        lambda link: link.get_attribute('href') and '/commits/' in link.get_attribute('href'),
        commits_page_possible_link_elements))
      
      if len(commits_page_link_elements) <= 0:
        statistics[repo_name] = {}
        driver.get(current_page_url)
        continue

      driver.get(f'{commits_page_link_elements[0].get_attribute("href")}')

      # Combine all commits into one string. Also keep track of contributors
      contributors = set()
      commit_names = []

      def scrape_commit_names_and_contributors(commit_names_list: list, contributors_set: set):
        # Commit names
        commit_name_elements = driver.find_elements(By.CSS_SELECTOR, '.flex-auto.min-width-0.js-details-container.Details p.mb-1')
        commit_names = [commit_name_element.text for commit_name_element in commit_name_elements]
        commit_names_list += commit_names

        # Contributors
        link_elements = driver.find_elements(By.CSS_SELECTOR, '.commit-author.user-mention')
        current_page_contributors = [link_element.text for link_element in link_elements]
        current_page_contributors_set = set(current_page_contributors)
        contributors_set.update(current_page_contributors_set)

      def get_older_commits_link(driver) -> WebElement:
        # Repeat the process as long as the "Older" button is clickable
        buttons = driver.find_elements(By.CSS_SELECTOR, '.btn.btn-outline.BtnGroup-item')
        older_button = list(filter(lambda button: button.text == 'Older', buttons))[0]
        return older_button

      scrape_commit_names_and_contributors(commit_names, contributors)

      try:
        while (older_commits_link := get_older_commits_link(driver)).get_attribute('href'):
          driver.get(older_commits_link.get_attribute('href'))
          scrape_commit_names_and_contributors(commit_names, contributors)
      except:
        pass

      statistics_item['commit_names'] = commit_names
      print('Commit names:')
      print('\n'.join(commit_names))

      statistics_item['contributors'] = list(contributors)
      print('Contributors:')
      print('\n'.join(contributors))

      statistics[repo_name] = statistics_item

      # Save progressively, in case the program gets interrupted
      with open(f'{save_dir}/{file_name}', 'w+') as f:
        json.dump(statistics, f, indent=2)

      driver.get(current_page_url)

  # Create tmp directory to save data
  with open(f'{save_dir}/{file_name}', 'w+') as f:
    json.dump(statistics, f, indent=2)


### Currently unused utility functions
def switch_to_tab(tab_num: int, driver: webdriver.Chrome):
  """
  tab_num is zero-indexed.
  If the tab number provided is out of range, it will switch to the latest tab.
  """
  _tab_num = tab_num
  num_tabs = len(driver.window_handles)

  if tab_num > num_tabs - 1:
    print(f'Error switching to tab {tab_num}, switching to latest tab')
    _tab_num = num_tabs - 1

  driver.switch_to.window(driver.window_handles[_tab_num])

def close_current_tab(driver):
  driver.close()

def close_all_tabs_except_first(driver: webdriver.Chrome):
  num_tabs = len(driver.window_handles)

  # If more than 1 tab found, close the rest
  if num_tabs > 1:
    for i in range(num_tabs - 1, 0, -1):
      switch_to_tab(i, driver)
      close_current_tab(driver)
    
    # Switch focus back to first tab
    switch_to_tab(0, driver)

def wait_for_exit():
  input('Press ENTER key to continue.')
  exit()

if __name__ == '__main__':
  main()
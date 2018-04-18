import argparse
import datetime
import json
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Create a class 'CustomsearchAi', to hold all the functionality
class CustomsearchAi:
    """Handle backup/restore to/from file of customsearch.ai search instances."""

    ACTION_BACKUP = 'backup'
    ACTION_RESTORE = 'restore'
    CUSTOMSEARCH_AI_URL = 'http://customsearch.ai'

    def __init__(self, username, password):
        options = Options()
        # options.add_argument('-headless')

        # Drivers 'geckodriver'/'chromedriver' available in $PATH (/usr/local/bin).
        self.driver = webdriver.Firefox(firefox_options=options)
        self.username = username
        self.password = password
        self.search_instances = []
        self.instance_configuration_file = ''

    def administer_instances(self, action=ACTION_BACKUP, file=''):
        """Maintain search instances, either by backing up, or restoring them."""
        self.login()

        if action == self.ACTION_RESTORE:
            self.instance_configuration_file = file
            self.restore()
        else:
            self.backup()

        self.logout()
        # Close the browser.
        self.driver.quit()

    def login(self):
        """Log in to the customsearch.ai site with provided credentials."""
        print('Logging in user "{0}" at {1}'.format(self.username, self.CUSTOMSEARCH_AI_URL))
        self.driver.get(self.CUSTOMSEARCH_AI_URL)

        signin_elements = self.driver.find_elements_by_link_text('Sign in')
        signin_elements[0].click()

        username_element = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.XPATH, "//form[@name = 'f1']//input[@name = 'loginfmt']"))
        )
        username_element.send_keys(self.username + Keys.RETURN)

        # Once the displayName banner is shown, we're on the next (part of the) form.
        banner = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id = 'displayName']"))
        )

        password_element = self.driver.find_element_by_xpath("//form[@name = 'f1']//input[@name = 'passwd']")
        password_element.send_keys(self.password + Keys.RETURN)

    def logout(self):
        """Log out of the customsearch.ai site."""
        signout_element = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.XPATH, "//button[text() = 'Sign out']"))
        )
        signout_element.click()

    def backup(self):
        """Backup search instance(s) configuration to file."""
        self.create_instance_list(self.search_instances)

        # Iterate the list of instances (we can go to each instance URL directly).
        for search_instance in self.search_instances:
            print('Backing up search instance "{0}"'.format(search_instance['name']))

            # Navigate direct to instance details page.
            self.driver.get(search_instance['url'])
            # We're left on the 'Active' tab screen by default, so don't need to select it, to begin.
            self.create_active_list(search_instance)

            # Navigate to and get the 'Blocked' data.
            blocked_element = self.driver.find_element_by_link_text('Blocked')
            blocked_element.click()
            self.create_blocked_list(search_instance)

            # Navigate to and get the 'Pinned' data.
            pinned_element = self.driver.find_element_by_link_text('Pinned')
            pinned_element.click()
            self.create_pinned_list(search_instance)

        self.write_instance_configuration_file()

    def create_instance_list(self, search_instances=[], page_number=0):
        """Create a list of all the search instances, from HTML."""
        row_elements = []

        try:
            # Wait until the HTML table of data is available.
            row_elements = WebDriverWait(self.driver, 3).until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[td/a/@class = 'instance-name']"))
            )
        except TimeoutException:
            print('Timed out waiting for list of search instances')

        # Pull the data from the HTML table.
        for index, row in enumerate(row_elements):
            link_element = row.find_element_by_xpath(".//a[@class = 'instance-name']")
            created_element = row.find_element_by_xpath(".//td[2]")

            data = {
                'page_number': page_number,
                'page_index': index,
                'name': link_element.text,
                'created': created_element.text,
                'url': link_element.get_attribute('href'),
                'active': [],
                'blocked': [],
                'pinned': [],
            }

            search_instances.append(data)

        # Navigate through any pagination, to get all data.
        if self.pagination_available() and self.pagination_next():
            self.create_active_list(search_instances, page_number + 1)

    def create_active_list(self, search_instance, page_number=0):
        """Create a list of all the 'Active' instance configuration."""
        row_elements = self.configuration_table_elements('Active')

        for index, row in enumerate(row_elements):
            website_element = row.find_element_by_xpath(".//td[1]/a")
            created_element = row.find_element_by_xpath(".//td[2]/div")
            subpages_element = row.find_element_by_xpath(".//td[3]")
            rank_adjust_element = row.find_element_by_xpath(".//td[4]/div[@class = 'ranking-column']/span[last()]")

            data = {
                'page_number': page_number,
                'page_index': index,
                'website': website_element.text,
                'created': created_element.text,
                'subpages': True if subpages_element.text == 'Yes' else False,
                'rank': {
                    'super_boosted': True if 'Super Boosted' == rank_adjust_element.text else False,
                    'boosted': True if 'Boosted' == rank_adjust_element.text else False,
                    'demoted': True if 'Demoted' == rank_adjust_element.text else False,
                },
            }

            search_instance['active'].append(data)

        if self.pagination_available() and self.pagination_next():
            self.create_active_list(search_instance, page_number + 1)

    def configuration_table_elements(self, tab_title='Active'):
        """Return search instance configuration table data."""
        row_elements = []

        try:
            row_elements = WebDriverWait(self.driver, 3).until(
                # The (FF only?) driver seems not to like the more specific XPath:
                # //tr[@class = 'site-row' and ancestor::div[@role = 'tabpanel']
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@class = 'site-row']"))
            )
        except TimeoutException:
            print('Timed out waiting for "{0}" content'.format(tab_title))

        return row_elements

    def pagination_available(self):
        """Determine if there are pagination links being shown."""
        try:
            pagination_element = self.driver.find_element_by_xpath("//ul[contains(@class, 'pagination ')]")

            return True

        except NoSuchElementException:
            return False

    def pagination_next(self):
        """Find, and click, any non-disabled pagination 'Next' link."""
        try:
            next_page_element = self.driver.find_element_by_xpath("//a[@aria-label = 'Next page' and not(contains(@class, ' disable'))]")
            next_page_element.click()

            return True

        except NoSuchElementException:
            return False

    def create_blocked_list(self, search_instance, page_number=0):
        """Create a list of all the 'Blocked' instance configuration."""
        row_elements = self.configuration_table_elements('Blocked')

        for index, row in enumerate(row_elements):
            website_element = row.find_element_by_xpath(".//td[1]/a")
            date_element = row.find_element_by_xpath(".//td[2]/div")
            subpages_element = row.find_element_by_xpath(".//td[3]")

            data = {
                'page_number': page_number,
                'page_index': index,
                'website': website_element.text,
                'date': date_element.text,
                'subpages': True if subpages_element.text == 'Yes' else False,
            }

            search_instance['blocked'].append(data)

        if self.pagination_available() and self.pagination_next():
            self.create_blocked_list(search_instance, page_number + 1)

    def create_pinned_list(self, search_instance, page_number=0):
        """Create a list of all the 'Pinned' instance configuration."""
        row_elements = self.configuration_table_elements('Pinned')

        for index, row in enumerate(row_elements):
            website_element = row.find_element_by_xpath(".//td[1]/a")
            query_element = row.find_element_by_xpath(".//td[2]")

            data = {
                'page_number': page_number,
                'page_index': index,
                'website': website_element.text,
                'query': query_element.text,
            }

            search_instance['pinned'].append(data)

        if self.pagination_available() and self.pagination_next():
            self.create_pinned_list(search_instance, page_number + 1)

    def write_instance_configuration_file(self):
        """Write instance configuration to file."""

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = 'customsearch.ai.{0}.json'.format(timestamp)
        print('Writing data to "{0}"'.format(filename))

        with open(filename, 'w') as destination:
            json.dump(self.search_instances, destination, ensure_ascii=False)

    def read_instance_configuration_file(self):
        """Read instance configuration from file."""

        filename = self.instance_configuration_file

        try:
            with open(filename) as origin:
                self.search_instances = json.load(origin)

        except FileNotFoundError:
            print('File "{0}" not found'.format(filename))

    def restore(self):
        """Restore search instance(s) from file to customsearch.ai."""

        self.read_instance_configuration_file()

        for search_instance in self.search_instances:
            print('Restoring search instance "{0}"'.format(search_instance['name']))

            self.create_instance(search_instance)
            self.restore_active_list(search_instance['active'])
            self.restore_blocked_list(search_instance['blocked'])
            self.restore_pinned_list(search_instance['pinned'])

            # Click 'My Instances' link (to return to instance 'index', ready to restore next set of instance data).
            self.wait_modal_disappear()

            my_instances_element = self.driver.find_element_by_link_text('My Instances')
            my_instances_element.click()

        print('Restore done!')

    def create_instance(self, search_instance):
        """Create a new Custom Search instance, based on import data."""

        # TODO: Handle duplicate named instance(s). Will cause immediate failure.
        try:
            button_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[text() = 'New Instance']"))
            )

            button_element.click()

        except TimeoutException:
            print('Timed out waiting for "New Instance" button to become available')
            self.driver.quit()

        # Enter name of instance being restored. Prefix name with '(I)', to show it's from a restore.
        # TODO: Value is limited to a maximum of 50 chars. Ensure value length is <= this.
        input_element = self.driver.find_element_by_xpath("//input[@id = 'newInstanceNameInput']")
        input_element.send_keys('(I) {0}'.format(search_instance['name']) + Keys.RETURN)

        # Wait for modal to fade out, before continuing.
        self.wait_modal_disappear()

    def wait_modal_disappear(self):
        """Delay progress until modal window fades."""

        try:
            modal = WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located((By.XPATH, "//bs-modal-container"))
            )

        except TimeoutException:
            print('Timed out waiting for "bs-modal-container" to disappear')
            self.driver.quit()

    def wait_website_list(self):
        """Delay progress until website list shown."""

        try:
            list = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@class = 'site-row']"))
            )

        except TimeoutException:
            print('Timed out waiting for "Active" table to become available (after adding website)')
            self.driver.quit()

    def restore_active_list(self, active_items):
        """Restore the 'Active' list from backup data."""

        for index, item in enumerate(active_items):
            self.add_website(item)
            self.amend_website_ranking(item)

    def add_website(self, item):
        """Add a website to the 'Active' list."""

        # Enter the URL.
        try:
            website_element = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//input[@formcontrolname = 'website']"))
            )

            website_element.send_keys(item['website'])

        except TimeoutException:
            print('Timed out waiting for "Active" tab form to become available')
            self.driver.quit()

        # The subpages control defaults to 'true', so only needs changing if current item is subpages 'false'.
        if not item['subpages']:
            # Different UI/behaviour for first, then any subsequent entries, for this value.
            if item['page_number'] == 0 and item['page_index'] == 0:
                # Uncheck a checkbox.
                subpages_element = self.driver.find_element_by_xpath(
                    "//input[@type = 'checkbox' and following-sibling::span[contains(text(), 'Include Subpages')]]")
                subpages_element.click()

            else:
                # Select option from drop down.
                subpages_element = self.driver.find_element_by_xpath("//button[@id = 'siteOrUrlSelectionDropdown']")
                subpages_element.click()

                subpages_no_element = self.driver.find_element_by_xpath("//button[text() = 'No']")
                subpages_no_element.click()

        # Add the website.
        add_element = self.driver.find_element_by_xpath("//button[@title = 'Add Website']")
        add_element.click()

        # Wait for the website list to be shown before continuing.
        self.wait_website_list()

    def amend_website_ranking(self, item):
        """Amend website ranking, if needed."""

        # Use the 'page_index' as basis to find the correct row up/down elements.
        xpath_index = item['page_index'] + 1

        if item['rank']['demoted']:
            down_element = self.driver.find_element_by_xpath("//tr[@class = 'site-row'][{0}]//button[@name = 'Decrease']".format(xpath_index))
            down_element.click()

        elif item['rank']['boosted'] or item['rank']['super_boosted']:
            up_element = self.driver.find_element_by_xpath("//tr[@class = 'site-row'][{0}]//button[@name = 'Increase']".format(xpath_index))
            up_element.click()

            if item['rank']['super_boosted']:
                up_element.click()

    def restore_blocked_list(self, blocked_items):
        """Restore the 'Blocked' list from backup data."""

        # TODO: Refactor to a 'select a named tab' function. Same is done in backup functionality too.
        blocked_element = self.driver.find_element_by_link_text('Blocked')
        blocked_element.click()

        for index, item in enumerate(blocked_items):
            self.add_website(item)

    def restore_pinned_list(self, pinned_items):
        """Restore the 'Pinned' list from backup data."""

        for index, item in enumerate(pinned_items):
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backup/restore of customsearch.ai instance configuration(s)')
    parser.add_argument('username', help='customsearch.ai account username')
    parser.add_argument('password', help='Password for specified username')
    parser.add_argument('--restore_file', help='Restore instance config from specified file')
    # parser.add_argument('--headless-mode', help='Use Firefox in headless mode')
    args = parser.parse_args()

    action = CustomsearchAi.ACTION_BACKUP
    file = ''

    if args.restore_file:
        action = CustomsearchAi.ACTION_RESTORE
        file = args.restore_file

    customsearch = CustomsearchAi(args.username, args.password)
    customsearch.administer_instances(action, file)

from bs4 import BeautifulSoup
from credentials import Credentials
import util
import time
from selenium.webdriver.common.by import By
import constant as c
import db
from sqlalchemy.orm import sessionmaker
from actions import Actions

class Collector():
    def __init__(self, credentials=None):
        
        # initilaize credentials
        self.credentials = credentials
        if not credentials:
            self.credentials = Credentials()

        # initialize db Session
        Session = sessionmaker(db.db)
        self.session = Session()

    def __login(self, driver, credentials):
        actions = Actions(driver, credentials)
        actions.do_login()

    def collect(self, driver, **options):

        # check collector options
        skip = None
        if 'skip_my_network' in options:
            skip = options.get('skip_my_network')            

        # perform login
        self.__login(driver, self.credentials)

        # scrap MyNetwork Page
        if not skip:
            my_connection = MyConnectionsCollector(driver)
            connections = my_connection.scrap()
        else:
            print('Getting list connections from db...')
            connections = self.session.query(db.Connections)\
                                    .filter(db.Connections.connected_with_user_id == self.credentials.get_uid())\
                                    .all()
        
        # proceed to ProfileCollector        
        # Execute parallelly.
        for c in connections:
            print(c.profile_link)
            pc = ProfileCollector(driver, c.profile_link)
            pc.dump_html()
            pc.scrap()
            break


class MyConnectionsCollector(Collector):
    def __init__(self, driver, credentials=None, scroll_wait=5, max_tries=3):
        super().__init__(credentials)

        # chromedriver
        self._driver = driver

        # collector properties
        self.wait = scroll_wait
        self.max_tries = max_tries

    def __open_page(self, url):
        return self._driver.get(url)

    def __scroll_to_bottom(self, max_tries=3):
        # get current browser height
        last_height = self.__get_browser_height()

        # maximum trial to find load_more button
        tries = 0
        
        print('Scrolling...')
        while True:
            # scroll down
            util.scroll(self._driver)
            time.sleep(2)
            
            # get new height
            new_height = self.__get_browser_height()

            # if scroll reached the end
            if new_height == last_height:
                
                # add trial count
                tries += 1

                print(f'Reached the end of page. Trying to looking for `Load more` button ({tries})')
                
                try:
                    # look for load_more button
                    load_more = util.browser_wait(
                        self._driver,
                        'scaffold-finite-scroll__load-button',
                        locator=By.CLASS_NAME
                    )
                    # click load more button
                    load_more.click()

                    # reset tries
                    tries = 0
                except:
                    if tries >= max_tries:
                        print('Load more button not found!')
                        break
            
            # update last height            
            last_height = new_height

    def __get_browser_height(self):
        return self._driver.execute_script('return document.body.scrollHeight')

    def scrap(self):
        print('Start scraping...')
        self.__open_page(c.MY_NETWORK_URL)
        self.__scroll_to_bottom(self.max_tries)

        # get raw output
        raw = BeautifulSoup(self._driver.page_source.encode('utf-8'), 'lxml')
        raw.prettify()                
        
        # parse raw output
        parse_result, total_expected = self._parse(raw)

        # insert connections parse result
        counter = 0
        duplicate = 0
        for p in parse_result:
            # prevent duplicate value
            people = self.session.query(db.Connections)\
                                    .filter(db.Connections.profile_link == p.profile_link)\
                                    .first()
            if people:
                duplicate += 1
                continue

            self.session.add(p)
            counter += 1
        
        try:
            self.session.commit()
        except Exception as e:
            print(e)

        # data verification again        
        print(f'Found duplicated {duplicate} data(s)')
        print(f'Successfully insert {counter}/{total_expected} record(s) to DB. Missing {total_expected - (counter+duplicate)} data(s).')

        # TODO: insert collector log to DB

        return parse_result

    def _parse(self, raw_html):            
        # get all container items
        containers = raw_html.findAll(
            'li',
            {'class': 'mn-connection-card artdeco-list'}
        )
        # count total expected connections
        expected_connections = len(containers)

        print(f'Got {expected_connections} connections.')

        # create empty array to store result
        profiles = []

        # get all connection
        for c in containers:
            # data model
            name = c.find('span', {'class': 'mn-connection-card__name'}).text.strip()
            occupation = c.find('span', {'class': 'mn-connection-card__occupation'}).text.strip()
            profile_link = 'https://linkedin.com{}'.format((c.find('a', {'class': 'mn-connection-card__link'})['href']))
            connected_at = c.find('time').text.strip().split('\n')[-1].strip().split()
            connected_at = f'{connected_at[0]}{connected_at[1][0].upper()}'            

            profiles.append(
                db.Connections(
                    name=name,
                    occupation=occupation,
                    connected_at=connected_at,
                    connected_with_user_id=self.credentials.get_uid(),
                    profile_link=profile_link,
                    circle_level=1  # default to 1 cz we're scraped from My Network page
                )
            )

        # data verification
        print(f'Successfully scraped {len(profiles)}/{expected_connections} connections. Missing {expected_connections-len(profiles)} data(s).')

        return profiles, expected_connections
    



class ProfileCollector(Collector):
    def __init__(self, driver, profile_link, credentials=None, max_tries=3):
        super().__init__(credentials)
        
        # chromedriver
        self._driver = driver

        # collector properties
        self.max_tries = max_tries
        self.profile_link = profile_link

    def __open_page(self, url):
        return self._driver.get(url)

    def __find_link_url(self):
        try:
            # search connections link
            link = util.browser_wait(
                self._driver,
                'li.text-body-small:nth-child(2)',
                locator=By.CSS_SELECTOR,
                timeout=30
            )
            link.click()
        except:
            print('Connections link not found in profile.')

    def __set_connection_filter(self):
        try:
            # trigger filter dropdown
            filter_btn = util.browser_wait(
                self._driver, 
                'div.search-reusables__filter-trigger-and-dropdown:nth-child(1)', 
                By.CSS_SELECTOR, 
                timeout=30
            )
            filter_btn.click()

            # disable 1st circle connection
            first_circle = util.browser_wait(
                self._driver, 
                'li.search-reusables__collection-values-item:nth-child(1) > label', 
                By.CSS_SELECTOR, 
                timeout=30
            )
            first_circle.click()

            # enable 3rd circle connection
            third_circle = util.browser_wait(
                self._driver, 
                'li.search-reusables__collection-values-item:nth-child(3) > label', 
                By.CSS_SELECTOR, 
                timeout=30
            )
            third_circle.click()

            # submit option
            submit = util.browser_wait(self._driver, '/html/body/div[7]/div[3]/div[2]/section/div/nav/div/ul/li[3]/div/div/div/div[1]/div/form/fieldset/div[2]/button[2]')
            submit.click()
        except:
            print('There is a problem when we trying to filter connection to 2nd and 3rd circle.')

    def __next_page(self, max_tries=3):
        for i in range(max_tries):
            try:
                # click next button
                next_btn = util.is_element_clickable(
                    self._driver, 
                    'button.artdeco-pagination__button--next',
                    locator=By.CSS_SELECTOR,
                    timeout=50
                )
                # button still clickable
                next_btn.click()

                return 'NEXT_PAGE'

            except:
                print(f'Cannot click the button. Trying again... ({i+1})')
    
        # if i+1 == max_tries:
        print('Seems we\'re reached the end of pagination. Start inserting to db now...')
        return 'END_PAGE'

    def __get_browser_height(self):
        return self._driver.execute_script('return document.body.scrollHeight')

    def __scroll_to_bottom(self):
        # get current browser height
        last_height = self.__get_browser_height()

        while True:
            # scroll down
            util.scroll(self._driver)
            time.sleep(2)

            # get new height
            new_height = self.__get_browser_height()

            # if scroll reached the end
            if new_height == last_height:
                break

            # update last height
            last_height = new_height

    def _parse(self, raw_html):
        # get all container items
        containers = raw_html.findAll(
            'div', {'class': 'entity-result__item'}
        )
        # count total expected connections
        expected_connections = len(containers)

        # create empty array to store result
        profiles = []

        # get all connection
        for c in containers:
            heading = c.find('span', {'class': 'entity-result__title-text t-16'})    
            # data model
            name = heading.find('span', {'dir': 'ltr'}).span.text
            circle_level = heading.find('span', {'class': 'image-text-lockup__text entity-result__badge-text'}).span.text.split()[-1][0]
            profile_link = heading.a['href']
            occupation = c.find('div', {'class': 'entity-result__primary-subtitle t-14 t-black t-normal'}).text.strip()

            profiles.append(
                db.Connections(
                    name=name,
                    occupation=occupation,
                    connected_with_user_id=self.credentials.get_uid(),
                    profile_link=profile_link,
                    circle_level=circle_level
                )
            )

        # data verification
        print(f'Got {len(profiles)}/{expected_connections} connections in this page. Missing {expected_connections-len(profiles)} data(s).')

        return profiles

    def scrap(self):
        # go to profile
        self.__open_page(self.profile_link)

        self.__find_link_url()
        self.__set_connection_filter()

        # get expected result
        try:
            expect_total = util.browser_wait(
                self._driver, 
                '/html/body/div[7]/div[3]/div[2]/div/div[1]/main/div/div/h2'
            )
            expect_total = int(expect_total.text.split()[0])
        except:
            print('[WARNING] Failed to get expected total result.')

        # connections puller
        parse_result = []

        while True:

            # get raw output
            raw = BeautifulSoup(self._driver.page_source.encode('utf-8'), 'lxml')
            raw.prettify()

            # scrap connections in current page
            profiles = self._parse(raw)
            # add scraped connections to puller array
            parse_result.extend(profiles)

            # scroll to bottom
            self.__scroll_to_bottom()
            # try to click next button
            state = self.__next_page(self.max_tries)

            if state == 'END_PAGE':
                break

            # wait several seconds
            time.sleep(5)

        # data verification
        if expect_total:
            print(f'Successfully scraped {len(parse_result)}/{expect_total} connection(s). Missing {expect_total - len(parse_result)} data(s).')
        else:
            print(f'Successfully scraped {len(parse_result)} connection(s).')
    
        # insert data
        counter = 0
        duplicate = 0
        for p in parse_result:
            # prevent duplicate value
            people = self.session.query(db.Connections)\
                                .filter(db.Connections.profile_link == p.profile_link)\
                                .first()

            if people:
                duplicate += 1
                continue

            self.session.add(p)
            counter += 1
        
        try:
            self.session.commit()
        except Exception as e:
            print(e)

        # data verification again
        print(f'Found duplicated {duplicate} data(s)')
        if expect_total:
            print(f'Successfully insert {counter}/{expect_total}')
        else:
            print(f'Successfully insert {counter}')

    def dump_html(self):
        # scroll to bottom
        self.__scroll_to_bottom()

        # get html tags
        page = BeautifulSoup(self._driver.page_source.encode('utf-8'), 'html.parser')
        page.prettify()

        # write html to file
        print('Dump profile page...')
        with open(f'raw/{self.profile_link.split("/")[-2]}.html', 'w', encoding='utf-8') as w:
            w.write(str(page))
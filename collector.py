from bs4 import BeautifulSoup
from credentials import Credentials
import util
import time
from selenium.webdriver.common.by import By
import constant as c
import db
from sqlalchemy.orm import sessionmaker
from actions import Actions
import threading
from objectpool import ObjectPool
from driver import Driver
from datetime import date, datetime

class Collector():
    def __init__(self, credentials=None, max_pool=10, max_thread=10):
        
        # initilaize credentials
        self.credentials = credentials
        if not credentials:
            self.credentials = Credentials()

        # initialize db Session
        Session = sessionmaker(db.db)
        self.session = Session()        
        self.db_pool = None
        
        # parallel execution properties
        self.lock_db = threading.Lock()
        self.threads = []
        self.pool = None
        self.max_pool = max_pool
        self.max_thread = max_thread
        self._thread_index = 0

        # collector metadata
        self.collectortask = self.__get_task_id()

    def __get_task_id(self):
        taskid = date.today().strftime('%Y%m%d')

        # check if task exist
        t = self.session.query(db.Tasks).filter(db.Tasks.timestamp == taskid).first()

        if t:
            return t.task_id

        # insert if no task timestamp found
        task = db.Tasks(timestamp=taskid)
        self.session.add(task)
        self.session.commit()

        return task.task_id

    def __login(self, driver, credentials):
        actions = Actions(driver, credentials)
        actions.do_login()    

    def run_thread(self, profile, pool, db_pool, thread_name):
        print(f'{thread_name} starting...')
        # borrow object
        driver = pool.borrow_resource()
        session = db_pool.borrow_resource()
        
        # do the job
        pc = ProfileCollector(driver, profile.profile_link)
        pc.dump_html(session)
        # insert to db with locking operation
        # with self.lock_db:
        pc.scrap(session)

        # return object
        pool.return_resource(driver)
        db_pool.return_resource(session)
        print(f'{thread_name} done.')

        self.__thread_callback()

    def __thread_callback(self):
        # continue execute threads
        if self._thread_index < len(self.threads):
            self.threads[self._thread_index].start()
            self._thread_index += 1

        # once all threads has been executed.
        # TODO: write collectorstatus


    def collect(self, driver, **options):

        ###########################
        # check collector options #
        ###########################
        skip = None
        if 'skip_my_network' in options:
            skip = options.get('skip_my_network')   
        
        if 'max_pool' in options:
            self.max_pool = options.get('max_pool')
        
        if 'max_thread' in options:
            self.max_thread = options.get('max_thread')



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
        
        # create driver pool
        drivers = []
        for _ in range(self.max_pool):
            # init driver
            driver = Driver().get_driver()
            # perform login
            action = Actions(driver, self.credentials)
            action.do_login()
            # add to pool
            drivers.append(driver)

        # object pool
        self.pool = ObjectPool()
        self.pool.set_resource(drivers)
        
        # create db pool
        dbs = []
        for _ in range(self.max_pool):
            Session = sessionmaker(db.db)
            session = Session()
            dbs.append(session)

        # object pool
        self.db_pool = ObjectPool()
        self.db_pool.set_resource(dbs)


        # create thread                
        for i, item in enumerate(connections[:self.max_thread]):
            # init thread
            thread_name = f'Thread-{i}'
            t = threading.Thread(target=self.run_thread, args=(item, self.pool, self.db_pool, thread_name))
            t.name = thread_name
            self.threads.append(t)

        # execute threads w/ max = max_thread        
        for _ in range(self.max_thread):            
            # run thread
            self.threads[self._thread_index].start()
            self._thread_index += 1            


        # # proceed to ProfileCollector             
        # # Execute parallelly.
        # for c in connections:
        #     print(c.profile_link)
        #     pc = ProfileCollector(driver, c.profile_link)
        #     pc.dump_html()
        #     pc.scrap()
        #     break


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

    def __scroll_to_bottom(self, max_tries=3):
        # get current browser height
        last_height = self.__get_browser_height()

        tries = 0

        while True:
            # scroll down
            util.scroll(self._driver)
            time.sleep(2)

            # get new height
            new_height = self.__get_browser_height()

            # if scroll reached the end
            if new_height == last_height:

                tries += 1

                if tries == max_tries:
                    break
            
            else:
                tries = 0

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

    def scrap(self, session):     
        # go to profile
        self.__open_page(self.profile_link)    
        # make sure page is loaded
        # while True:
        #     if util.wait_loaded(self._driver):
        #         break          

        self.__find_link_url()
        self.__set_connection_filter()

        # get expected result
        expect_total = None
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
            people = session.query(db.Connections)\
                                .filter(db.Connections.profile_link == p.profile_link)\
                                .first()

            if people:
                duplicate += 1
                continue

            session.add(p)
            counter += 1
        
        try:
            session.commit()
        except Exception as e:
            print(e)

        # data verification again
        print(f'Found duplicated {duplicate} data(s)')
        if expect_total:
            print(f'Successfully insert {counter}/{expect_total}')
        else:
            print(f'Successfully insert {counter}')

    def dump_html(self, session):      

        # go to profile
        self.__open_page(self.profile_link)    
        # make sure page is loaded
        while True:
            if util.wait_loaded(self._driver):
                break           

        # scroll to bottom
        self.__scroll_to_bottom()

        # get html tags
        page = BeautifulSoup(self._driver.page_source.encode('utf-8'), 'html.parser')
        page.prettify()

        # write html to file
        print('Dump profile page...')
        filename = f'{self.profile_link.split("/")[-2]}.html'
        filepath = 'raw'

        # check if page already scraped
        taskfile = session.query(db.CollectorTaskFiles)\
                            .filter(db.CollectorTaskFiles.filename == filename)\
                            .first()

        if taskfile:
            # found duplicate
            return

        # write a new record        
        with open(f'{filepath}/{filename}', 'w', encoding='utf-8') as w:
            w.write(str(page))        

        # writing to db
        collectortaskfiles = db.CollectorTaskFiles(
            collectortask_id = self.collectortask,
            filename=filename,
            filepath=filepath
        )
        session.add(collectortaskfiles)
        try:            
            session.commit()        
        except Exception as e:
            print(e)
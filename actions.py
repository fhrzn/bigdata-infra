from getpass import getpass
import util
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import constant as c

class Actions():

    def __init__(self, driver, credentials=None):
        # user auth credentials
        self.credentials = credentials
        # chromedriver
        self.driver = driver        
        
    def __is_logged_in(self, ):
        pass

    def do_login(self):
        # check cookie        
        if self.credentials.li_at:
            return self.__login_w_cookie()

        # check credentials
        # if not self.email or not self.pwd:
        #     print('Please insert your credentials.')
        #     self.__prompt_credentials()

        # go to login page
        self.driver.get(c.LOGIN_URL)
        # fill credentials
        while True:
            if util.wait_loaded(self.driver):
                try:
                    email_field = util.browser_wait(self.driver, '#username', locator=By.CSS_SELECTOR)
                    pwd_field = util.browser_wait(self.driver, '#password', locator=By.CSS_SELECTOR)
                    # insert email password
                    email_field.send_keys(self.credentials.email)
                    pwd_field.send_keys(self.credentials.password)
                    # submit
                    print('Attempting to login...')                
                    pwd_field.send_keys(Keys.RETURN)
                    break
                except:
                    print('Cannot find email or passowrd field!')
                    break

        # set li_at cookies
        while True:
            if util.wait_loaded(self.driver):
                try:
                    self.credentials.li_at = self.driver.get_cookie('li_at')['value']                
                except:
                    pass
                break

    def __login_w_cookie(self):
        self.driver.get(c.LOGIN_URL)
        self.driver.add_cookie({
            'name': 'li_at',
            'value': self.credentials.li_at
        })

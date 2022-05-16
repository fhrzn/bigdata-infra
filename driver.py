from selenium import webdriver

class Driver():
    
    def __init__(self, *params):
        # TODO: add params validation

        options = webdriver.ChromeOptions()

        # iterate through params
        for p in params:            
            options.add_argument(p)

        # add experimental option
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # create selenium instance
        self.driver = webdriver.Chrome(options=options)

    def get_driver(self):
        return self.driver    
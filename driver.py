from selenium import webdriver

class Driver():

    # default params
    __params = [
        '--incognito',
        '--disable-gpu',
        '--disable-extensions',
        # '--headless'
    ]
    
    def __init__(self, *params):
        # TODO: add params validation
        if params:
            self.__params = params

        self.options = webdriver.ChromeOptions()        

        # iterate through params
        for p in self.__params:            
            self.options.add_argument(p)

        # add experimental option
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # create selenium instance
        self.driver = webdriver.Chrome(options=self.options)

    @classmethod
    def set_default_params(cls, params):
        cls.__params = params

    def get_driver(self):
        return self.driver  

    def get_params(self):
        return self.__params

    def destroy(self):
        return self.driver.quit()

if __name__ == '__main__':
    params = [
        '--incognito',
        '--disable-gpu',
        '--disable-extensions',
    ]
    d = Driver(*params)
    print(d)

    d2 = Driver()
    print(d2)
    print(d2.get_params())
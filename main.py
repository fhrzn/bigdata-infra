from driver import Driver
from collector import Collector

if __name__ == '__main__':
    
    # create an instance
    params = [
        '--incognito',
        '--disable-gpu',
        '--disable-extensions',
        '--headless'
    ]
    driver = Driver(*params).get_driver()

    # scrap and collect data
    collector = Collector(max_pool=1, max_thread=1)
    collector.collect(driver, skip_my_network=True)

    # driver.quit()
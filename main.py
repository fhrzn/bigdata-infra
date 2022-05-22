from driver import Driver
from collector import Collector
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-mp', '--maxpool', type=int)
    parser.add_argument('-mt', '--maxthread', type=int)
    parser.add_argument('--skip-network', action='store_true')    
    parser.add_argument('--headless', action='store_true')

    args = parser.parse_args()
    
    # create an instance
    params = [
        '--incognito',
        '--disable-gpu',
        '--disable-extensions',        
    ]
    
    if args.headless:
        params.append('--headless')

    driver = Driver(*params).get_driver()

    # scrap and collect data
    collector = Collector(max_pool=args.maxpool, max_thread=args.maxthread)
    collector.collect(driver, skip_my_network=args.skip_network)

    driver.quit()
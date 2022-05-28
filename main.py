from driver import Driver
from collector import Collector
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-mp', '--maxpool', type=int)
    parser.add_argument('-mt', '--maxthread', type=int)
    parser.add_argument('--skip-network', action='store_true')    
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('-b', '--batch', type=int)
    parser.add_argument('--network-only', action='store_true')
    parser.add_argument('--parse-only', action='store_true')
    parser.add_argument('-id', '--id', type=int)

    args = parser.parse_args()

    if args.network_only:
        mode = ['network']
    elif args.parse_only:
        mode = ['parse']
    else:
        mode = ['parse', 'network']
    
    print(f'[LOG] Got mode {mode}')
    
    # create an instance
    params = [
        '--incognito',
        '--disable-gpu',
        '--disable-extensions',        
    ]
    
    if args.headless:
        params.append('--headless')

    # set default driver parameters
    Driver.set_default_params(params)    
    driver = Driver(*params).get_driver()

    # scrap and collect data
    collector = Collector(max_pool=args.maxpool, max_thread=args.maxthread, batch=args.batch, mode=mode, id=args.id)
    collector.collect(driver, skip_my_network=args.skip_network)

    driver.quit()
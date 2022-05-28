from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

def browser_wait(driver, element, locator=By.XPATH, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((locator, element))                
    )

def browser_wait_multi(driver, element, locator=By.XPATH, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((locator, element))
    )

def is_element_clickable(driver, element, locator=By.XPATH, timeout=30):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((locator, element))
    )

def _scroll(driver, start=0, end='document.body.scrollHeight'):    
    driver.execute_script(f'window.scrollTo({start}, {end});')    

def wait_loaded(driver):
    state = driver.execute_script('return document.readyState;')
    return state == 'complete'

def get_browser_height(driver):
    return driver.execute_script('return document.body.scrollHeight')

def scroll_to_bottom(driver, start=0, end='document.body.sccrollHeight', load_more_btn=None, locator=None, max_tries=3):
    # get current browser height
    last_height = get_browser_height(driver)
    # trial counter
    tries = 0

    while True:
        # scroll down
        _scroll(driver, start=start, end=end)
        time.sleep(2)
        # get new height
        new_height = get_browser_height(driver)

        # scroll reached the end
        if new_height == last_height:
            # add trial count
            tries += 1

            if load_more_btn:
                try:
                    # looking for load more button
                    load_more = browser_wait(
                        driver,
                        load_more_btn,
                        locator=locator
                    )
                    # click load more
                    load_more.click()
                    # reset tries
                    tries = 0
                except:
                    if tries >= max_tries:
                        break
            else:
                if tries == max_tries:
                    break
        else:
            tries = 0

        # update last height
        last_height = new_height

def find_elem_and_click(driver, elem, locator=By.CSS_SELECTOR, timeout=30):
    try:
        elem = browser_wait(
            driver,
            elem,
            locator,
            timeout
        )
        elem.click()
    except Exception as e:
        print(e)
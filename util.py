from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def browser_wait(driver, element, locator=By.XPATH, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((locator, element))
    )

def is_element_clickable(driver, element, locator=By.XPATH, timeout=30):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((locator, element))
    )

def scroll(driver, start=0, end='document.body.scrollHeight'):
    driver.execute_script(f'window.scrollTo({start}, {end});')    

def wait_loaded(driver):
    state = driver.execute_script('return document.readyState;')
    return state == 'complete'

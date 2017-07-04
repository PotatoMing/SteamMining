from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

geck_path = 'D:\Program Files\geckodriver-v0.17.0-win64\geckodriver'

def loginViaFirefox(url,log_username,log_password):
    driver = webdriver.Firefox(executable_path=geck_path)
    driver.get(url)
    time.sleep(5)
    username = driver.find_element_by_name("username")
    password = driver.find_element_by_name("password")
    username.send_keys(log_username)
    password.send_keys(log_password)
    login_attempt = driver.find_element_by_xpath("//*[@type='submit']")
    login_attempt.click()
    time.sleep(5)
    return driver

def connectViaFirefox(url,driver):
    driver.get(url)
    time.sleep(7)
    return driver.page_source


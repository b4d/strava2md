from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
import os
import time

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1280,1280")

path='file://'+os.path.abspath(os.path.curdir)+'/tmp/index.html'
driver = webdriver.Chrome(options=chrome_options)
driver.get(path)
time.sleep(2)

driver.save_screenshot(os.path.abspath(os.path.curdir)+"/tmp/shot.png")
for e in ['map_div','height_profile']:
  el = driver.find_element(By.ID, e)
  location=el.location
  size=el.size
  x = location['x']
  y = location['y']
  w = size['width']
  h = size['height']
  width = x + w
  height = y + h
  im = Image.open(os.path.abspath(os.path.curdir)+"/tmp/shot.png")
  im = im.crop((int(x), int(y), int(width), int(height)))
  im.save(os.path.abspath(os.path.curdir)+"/tmp/screenshot_"+e+".png")

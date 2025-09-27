from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions
from PIL import Image
import os
import time


def pageshot(driver, fin, fout):
  path='file://'+fin
  driver.get(path)
  time.sleep(2)
  driver.save_screenshot(fout)

def cropshop(driver, fin, fout, element):
  try:
    el = driver.find_element(By.ID, element)
    location=el.location
    size=el.size
    x = location['x']
    y = location['y']
    w = size['width']
    h = size['height']
    width = x + w
    height = y + h
    im = Image.open(fin)
    im = im.crop((int(x), int(y), int(width), int(height)))
    im.save(fout)
  except selenium.common.exceptions.NoSuchElementException:
    print("Such element could not be found.") 

def main():
  chrome_options = Options()
  chrome_options.add_argument("--headless=new")
  chrome_options.add_argument("--window-size=1280,1280")
  d = webdriver.Chrome(options=chrome_options)

  pageshot(driver=d,
          fin=os.path.abspath(os.path.curdir)+'/Rides/2024-09-10-12375824200.html',
          fout=os.path.abspath(os.path.curdir)+"/tmp/shot.png")

  cropshop(driver=d,
          fin=os.path.abspath(os.path.curdir)+"/tmp/shot.png",
          fout=os.path.abspath(os.path.curdir)+"/tmp/screenshot_map.png",
          element='map_div')
  
if __name__ == "__main__":
  main()
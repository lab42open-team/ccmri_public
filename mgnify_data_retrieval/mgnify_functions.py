#!/usr/bin/python3.5

########################################################################################
# script name: mgnify_functions.py
# developed by: Haris Zafeiropoulos
# modified by: Alexios Loukas, Evangelos Pafilis
# framework: CCMRI
########################################################################################
# GOAL
# On this script you can find all the functions that are used in all the scripts that have been implemented to get data from the MGnify database.
# This script has 3 main parts; one for each of the scripts made for MGnify.
# Some functions are used in more than one scripts.
########################################################################################



import time, datetime, random
import json, re, os, sys, traceback, glob
import asyncio, concurrent.futures
import requests, wget, urllib
from requests.exceptions import Timeout
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
import http.client
from bs4 import BeautifulSoup
import re

DEEP_LOG = True

#checks if a directory exists and creates it if it doesn't exist
def check_create_dir(dir):
    isExist = os.path.exists(dir)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(dir)


def remove_dir(dir):
    filelist = glob.glob(os.path.join(dir, "*"))
    for f in filelist:
        os.remove(f)


# just get the content of a page
def get_page(url_to_get, sec):
    page = requests.get(url = url_to_get, timeout = sec)
    return page

# read a json file
def load_json_file(file):
    return file.json()
          
        
        
#ccmri - method to get json from url and return json content to a variable
def get_json_url_with_exception_handling(url_that_contains_json, timeout_in_sec, sleep_min, sleep_max, limiter):
    if DEEP_LOG:
        print("check: get_json_url_with_exception_handling: ", "url: ", url_that_contains_json, "limiter: ", limiter)

    if limiter==0:
        print("Permanently failed to get json from url: ", url_that_contains_json, "\n")
        return
    try:
        variable_to_load_json=""
        sleepy = random.uniform(sleep_min, sleep_max)
        time.sleep(sleepy)
        #print ("Slept for: ", sleepy, " seconds")
        url_page = get_page(url_that_contains_json, timeout_in_sec)
        if url_page.status_code == 200:
            variable_to_load_json = load_json_file(url_page)
            return variable_to_load_json
        else:
            print("An HTTP error occured : ", url_page.status_code, " - while downloading URL: ",url_that_contains_json, "\n")
            get_json_url_with_exception_handling(url_that_contains_json, timeout_in_sec, sleep_min, sleep_max, limiter-1)
    except Exception as error:
            print("An exception error occured : ", error, " - while downloading URL: ",url_that_contains_json, "\n")
            get_json_url_with_exception_handling(url_that_contains_json, timeout_in_sec, sleep_min, sleep_max, limiter-1)



# get urls from failed_urls list
def retry(failed_urls, directory_to_save, suffix, sleep_min, sleep_max):
    print("i am inside the retry function!")
    sec = random.uniform(sleep_min,sleep_max)
    if len(failed_urls) == 0:
        print("All urls are downloaded properly!")
        pass
    else:
        url = failed_urls[0]
        print("url under process: " + url)
        page = requests.get(url, allow_redirects = True, timeout = 130)
        time.sleep(sec)
        try:
            try_page = page.json()
        except:
            print("i had an exception...")
            pass
        if str(page.status_code) == '200':
            print("i have a new file downloaded!")
            number_of_page = url.split("=")[1]
            filename = directory_to_save + str(number_of_page) + suffix
            open(filename, 'wb').write(page.content)
            failed_urls.remove(url)



def download_pages(url, path_to_save, prefix, timeout_time, sleep_min, sleep_max):
    if DEEP_LOG:
        print("check: download_pages: ", "url: ", url, " path_to_save: ", path_to_save, " prefix:", prefix)

    # try to get a response for your url
    try:
        sleepy = random.uniform(sleep_min, sleep_max)
        time.sleep(sleepy)
        #print("A new url is about to start downloading: " + str(datetime.datetime.now()))
        samples_page = requests.get(url, allow_redirects = True, timeout = timeout_time)
        print(url + "\t" + "status: " + str(samples_page.status_code))
        # if everything is fine, then save the page.
        if str(samples_page.status_code) == '200':
            try_page = samples_page.json()
            suffix = url.split("=")[1]
            filename = path_to_save + suffix + prefix
            open(filename, 'wb').write(samples_page.content)
            print("the corresponding page was saved! \n")
            message = "ok"
            return message
        # if an error was returned then keep the url for the retry step.
        else:
            print("this url: " + url + "returned an error:" + str(samples_page.status_code) + " and has been kept in a temp file.")
    # if timeout is over, then also keep the url for the retry step.
    except Timeout:
        print(url + " got a TIMEOUT! \n")
    # in case that a request exceeds the configured number of maximum redirections
    except requests.exceptions.TooManyRedirects:
        print("url: " + url + " ..this is a bad url! no clue how this may have happened.. that is a crucial error for this script. ")
    # check for a HTTP client disconnection
    except http.client.HTTPException:
        print("a Connection Error occured while trying to get the " + url + " it was the http.client excpetion that was hit!")
    # if a connection error occurs
    except requests.exceptions.ConnectionError:
        print("a Connection Error occured while trying to get the " + url)
    # in case that any other exception takes place
    except requests.exceptions.RequestException:
        print("a kind of error that i do not understand took place.. please try again later with this url: " + url)



#created for ccmri - downloading available file downloads from mgnify
def download_file_via_wget_url(url, path_to_save, sleep_min, sleep_max, limiter):
    if DEEP_LOG:
        print("check: download_file_via_wget_url: ", "url: ", url, "limiter: ", limiter)

    if limiter==0:
        print("Permanently failed to download from URL: ", url, "\n")
        return
    try:
        sleepy = random.uniform(sleep_min, sleep_max)
        time.sleep(sleepy)
        filename = wget.detect_filename(url)
        print("The filename is : ", filename, "\n")
        wget.download(url, out=path_to_save)
        isExist = os.path.exists(path_to_save+"/"+filename)
        if isExist:
            print("The file was downloaded:", filename, "\n")
        else:
            print("The file was NOT downloaded:", filename, "and the function will return(which is wrong)" "\n")
        return 
    except Exception as error:
        print("An error occured : ", error, " - while downloading URL: ",url, "\n")
        print("The file was NOT downloaded:", filename, "\n")
        download_file_via_wget_url(url, path_to_save, sleep_min, sleep_max, limiter-1)
        
        
        
#cleans text from newlines,spaces and HTML code
def clean_text(input_text):
    # Remove HTML code
    cleaned_text = BeautifulSoup(input_text, "html.parser").get_text()

    # Replace tabs, newlines, and carriage returns with spaces
    cleaned_text = re.sub(r'[\t\n\r]', ' ', cleaned_text)

    # Replace consecutive spaces with a single space
    cleaned_text = re.sub(r' +', ' ', cleaned_text)

    # Remove trailing whitespaces
    cleaned_text = cleaned_text.rstrip()

    return cleaned_text
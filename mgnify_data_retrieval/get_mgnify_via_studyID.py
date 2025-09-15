#!/usr/bin/python3.5

########################################################################################
# script name: get_mgnify_via_studyID.py
# developed by: Haris Zafeiropoulos
# modified by: Alexios Loukas, Evangelos Pafilis
# framework: CCMRI - WP1
########################################################################################
# GOAL
# this script aims to get all the data needed for CCMRI WP1 via the MGnify API using the
# study id entries from mgnify
########################################################################################
## usage: ./get_mgnify_via_studyID.py --wd='/_full_path_in_your_server_to_/' --threads=5 
# --dev_mode=True --studyid_pmid_file=studyid_pmid.tsv --min=1.5 --max=3.5
## note: the working directory should include the trailing slash (/)
########################################################################################


# import libraries needed
import os, glob
import requests, time, datetime
import json, re, os, sys, traceback, asyncio
import concurrent.futures
import shutil, wget
import re
from requests.exceptions import Timeout
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
from mgnify_functions import get_page, load_json_file, retry, download_pages, check_create_dir, download_file_via_wget_url, get_json_url_with_exception_handling, remove_dir, clean_text
import logging



##global variables to control script execution upon development (initialize parameters to default)
WORKING_DIR = "/_full_path_in_your_server_to_/"
NUM_OF_THREADS = 5
DEVELOPMENT_MODE_ENABLED = True
STUDY_PMID_FILE = "studyid_pmid.tsv"
SLEEP_MIN = 1.5
SLEEP_MAX = 3.5

DEEP_LOG_ENABLED = True
RECURSIONS_LIMIT = 2
NUMBER_OF_STUDY_PAGES_LIMIT = 1    #must be >1 and no more than mgnify's recorded studies
MGNIFY_REST_API_URL_BASE = 'https://www.ebi.ac.uk/metagenomics/api/v1/'


#print("Initially: " + WORKING_DIR+ ", " + str(NUM_OF_THREADS) + ", " + str(DEVELOPMENT_MODE_ENABLED) + ", " + STUDY_PMID_FILE,"\n")

#e.g. If we want to filter info mined from json files
#ANALYSIS_GROUP_TYPES_TO_INCLUDE = {
#  "Taxonomic analysis": False,	
#   "Functional analysis": False,	
#   "Taxonomic analysis LSU rRNA": True,
#   "Taxonomic analysis SSU rRNA": True,
#   "Statistics": False
#}


#extraction of the argument values imported from sys.argv
arguments_dict = {}
for arg in sys.argv[1:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep], arg[sep + 1:]
        arguments_dict[key] = value

#update parameters based on the values passed by the command line (if any)
if "--wd" in arguments_dict:
    WORKING_DIR = arguments_dict["--wd"]
if "--threads" in arguments_dict:
    NUM_OF_THREADS = arguments_dict["--threads"]
if "--dev_mode" in arguments_dict:
    DEVELOPMENT_MODE_ENABLED = eval(arguments_dict["--dev_mode"])
if "--studyid_pmid_file" in arguments_dict:
    STUDY_PMID_FILE = arguments_dict["--studyid_pmid_file"]
if "--sleep_min" in arguments_dict:
    SLEEP_MIN = arguments_dict["--sleep_min"]
if "--sleep_max" in arguments_dict:
    SLEEP_MAX = arguments_dict["--sleep_min"]

#print("Finally: " + WORKING_DIR+ ", " + str(NUM_OF_THREADS) + ", " + str(DEVELOPMENT_MODE_ENABLED) + ", " + STUDY_PMID_FILE,"\n")


#keeping time for the script duration
start = datetime.datetime.now()
date =  datetime.date.today()
old_stdout = sys.stdout

#convert the date format for the mgnify versioning system
date_with_underscores = str(date).replace("-", "_")
#print("The date with underscores: ",date_with_underscores, "\n")



#if the script is running with dev_mode=False, then versioning will be created for the working directory
#It is now disabled and propably manually implemented later
#if DEVELOPMENT_MODE_ENABLED==False:
#    mgnify_wd = WORKING_DIR+str(date_with_underscores)+"/"
#else:
#    mgnify_wd = WORKING_DIR
mgnify_wd = WORKING_DIR

# keep in variables all the paths needed for this script
check_create_dir(mgnify_wd)
log_file_path = "/_full_path_in_your_server_to_/logs/"
check_create_dir(log_file_path)
log_file_name = log_file_path + "mgnify_via_studyID_"+ str(date) + ".log"
log_file = open(log_file_name,"w")
sys.stdout = log_file   #redirecting stardard out to the log file
study_list_page_json_dir = mgnify_wd + "studies_list_page_json_files/"
check_create_dir(study_list_page_json_dir)
harv_studies = mgnify_wd + "harvested_mgnify_studies/"
check_create_dir(harv_studies)
#opening the file to store studyids - pmids
studyid_pmid_file_full_path = mgnify_wd+STUDY_PMID_FILE 
studyid_pmid_file_handler = open(studyid_pmid_file_full_path, "a")

#This code is for the tracking of URL calls for the efficient use of the mgnify server
#now we will Create and configure logger (import required - is found above)
logging.basicConfig(filename=log_file_path+"url_calls.log", 
					format='%(asctime)s %(message)s', 
					filemode='w') 
#Let us Create an object 
logger=logging.getLogger() 
#Now we are going to Set the threshold of logger to DEBUG 
logger.setLevel(logging.DEBUG)


##########################################################################################################################
## STEP 1
## Find all mgnify study API links, save them in a list and download their json files
##########################################################################################################################

# this is the URL for the first page for all mgnify studies.
url_studies_pages=MGNIFY_REST_API_URL_BASE+"studies?page=1"

#we need to get the json variable from the above URL in order to count the study pages
json_data = get_json_url_with_exception_handling(url_studies_pages, 30, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT)


# get the total number of study pages from the json variable
number_of_pages = json_data['meta']['pagination']['pages']
print("\nNumber of study data pages to be retrieved: " + str(number_of_pages) + "\n")

# get all the study URLs in a list - We manipulate the nr in the "while counter < page_limiter" to test the script
counter = 0
page_limiter = number_of_pages   #will iterate though all the study pages
if DEVELOPMENT_MODE_ENABLED==True:
    page_limiter = NUMBER_OF_STUDY_PAGES_LIMIT
study_urls = []
while counter < page_limiter :
    counter += 1
    page_url= MGNIFY_REST_API_URL_BASE+"studies?page=" + str(counter)
    study_urls.append(page_url)
    

# Use an executor, built thanks to the concurrent.futures package, using the number of threads you want to, in order to perform your download!
print("The study list executor is about to start. \n" + str(datetime.datetime.now()))
with concurrent.futures.ThreadPoolExecutor(max_workers = int(NUM_OF_THREADS)) as executor:
    print("The executor for downloading studies list pages just started! \n")
    # Start the load operations and mark each future with its URL. HERE is where the concurrent.futures part is taking place!
    future_to_url = {executor.submit(download_pages, url, study_list_page_json_dir, "_study_list_page.json", 15, SLEEP_MIN, SLEEP_MAX): url for url in study_urls}


# The urls that failed, they have been kept in a temp file. Read that file and keep each url as a list element.
temp_file = study_list_page_json_dir + "temp_file_with_failed_urls.tsv"
f = open(temp_file, "w")
#for i in range(1, "number of study pages" + 1):
for i in range(1, page_limiter + 1):     # The page_limiter has to be the number of study pages we whish to download
    item = str(i) + "_study_list_page.json"
    file = study_list_page_json_dir + item
    try:
        f = open(file)
    except IOError:
        print("File " + file + " was not accessible in the first attempt! \n")
        with open(temp_file, "a") as temp:
            missing_url= MGNIFY_REST_API_URL_BASE+"studies?page=" + str(i) + "\n"
            temp.write(missing_url)
            temp.close()
    finally:
        f.close()

# make a list with all the missing urls
failed_study_urls = [line[:-1] for line in open(temp_file, "r").readlines()]
print("The number of the missing urls is equal to " + str(len(failed_study_urls)) + "\n")


# for as long as there are still missing urls..
while len(failed_study_urls) > 0 :
    print("We still have " + str(len(failed_study_urls)) + " urls to get! \n")
    # .... perform the "retry" function. 
    retry(failed_study_urls, study_list_page_json_dir, "_study_list_page.json", float(SLEEP_MIN), float(SLEEP_MAX))

# erase everything from the temp_file without removing it - in order to use it in the next run of the robot.
#open(temp_file, 'w').close()
# HZ: After discussed the robots architecture, it is better to remove this temp file after getting all the studies needed. 

os.remove(temp_file)



#########################################################################################################
## STEP 2
## Get the study IDs from the downloaded json files and create folders with study IDs as folder names 
#########################################################################################################

# from the json files returned in the previous block of code, keep all MGnify study IDs (i.e MGYS89342)
study_ids_from_json = []

# read one by one all the files that were downloaded from the previous step
counter_for_study_files = 0
for filename in os.listdir(study_list_page_json_dir):
    # get the path for each specific file
    file = study_list_page_json_dir + filename
    counter_for_study_files += 1
    # open it as a json file
    with open(file, 'r', encoding='utf-8') as f:
        study_list_json = json.load(f)
    #the next comment lines are experimentation on how to access the json data in python
    #with open(file) as f:
    #    study_list_json = json.load(f)
    #print("we now are in the file:", filename, "\n")
    #print(study_list_json['data'][0], "\n\n")
    #print(len(study_list_json['data']))
    # for each entry in the 'data' part of the study json file:
    for study in range(len(study_list_json['data'])):
        studyID = study_list_json['data'][study]['id']
        # if this ID appears for the first time, then add it on the list of studies reached
        # and create a folder named with the ID of the study
        if studyID not in study_ids_from_json:
            study_ids_from_json.append(studyID)
            study_id_dir = harv_studies + studyID
            check_create_dir(study_id_dir)
        else:
            print("Found a duplicate study! (", studyID ,")\n")
    

print("Number of study page files:\t",counter_for_study_files,"\n")
print("The number of the study ids found is: " + str(len(study_ids_from_json)) + "\n")

#now that we got the studyID information we wanted, we are deleting the directory with the study list pages json files
try:
   shutil.rmtree(study_list_page_json_dir)
   print("directory is removed successfully\n")
except OSError as x:
   print("Error occured: %s : %s" % (study_list_page_json_dir, x.strerror))


timepoint_1 = datetime.datetime.now()
first_step_durance = timepoint_1 - start
print("The first and second step took: ", first_step_durance, "\n")





##########################################################################################################################
## STEP 3
## Get all the text info and links we are going to need from every study and download all the downloads per study
##########################################################################################################################

study_counter = 0
asc_study_counter = 0

# for each study ID of those recorded we will gather the desired information
for study in study_ids_from_json:
    try:
        #adding a separator for reading comfort
        print("=================================================================================================================\n")
        
        
        #checking if the file COMPLETED exists and if the study is already harvested
        isExist = os.path.exists(harv_studies+study+"/COMPLETED")
        if isExist:
            print("File 'COMPLETED' found in study with ID: ",study,". Will continue to the next study\n")
            continue
        else:
            print("File 'COMPLETED' NOT found in study with ID: ",study,"\n")
            print("Directory reset: ", harv_studies+study ,"\n")
            remove_dir(harv_studies+study) 
            


        #create a file to write all the info we want to extract
        f = open(harv_studies+study+"/mined_info_"+study+".txt", "w", encoding='utf-8')  
        
    
        #we are keeping track of how many studies have been harvested so far
        study_counter += 1
        print("We are in study nr",study_counter," with study ID: ",study, "\n")

        # read the page of every study from the id's obtained in json format
        url=MGNIFY_REST_API_URL_BASE+"studies/" + study
        # check if the page was open 
        

        #we need to define an empty variable that will contain the json to import as argument in the next method
        study_json = get_json_url_with_exception_handling(url, 30, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT)
        
        

        # extract the desired information from the obtained json variable
        # create a file and write all the desired data
        #printing basic attributes to file
        attribute = ''
        attribute = study_json['data']['id']
        f.write("study_id\t"+attribute+"\n")
        attribute = study_json['data']['attributes']['study-name']
        cleaned_study_name = clean_text(attribute)
        f.write("study_name\t"+cleaned_study_name+"\n")
        attribute = study_json['data']['attributes']['study-abstract']
        cleaned_study_abstract = clean_text(attribute)
        #cleaned_abstract = re.sub(r'\s+', ' ', attribute)
        #cleaned_abstract = attribute.replace('\n', ' ')
        #cleaned_abstract_rstriped = cleaned_abstract.rstrip()
        f.write("study_abstract\t"+cleaned_study_abstract+"\n")
        attribute = study_json['data']['attributes']['data-origination']
        f.write("study_origination\t"+attribute+"\n")
        attribute = study_json['data']['attributes']['bioproject']
        if attribute:
            f.write("study_bioproject_id\t"+attribute+"\n")
        else: 
            f.write("study_bioproject_id\tunavailable\n")
        attribute = study_json['data']['attributes']['secondary-accession']
        f.write("study_secondary_acession\t"+attribute+"\n")
        attribute = study_json['data']['attributes']['last-update']
        f.write("study_last_update\t"+attribute+"\n")
        #printing associated studies (if any) to file
        for asc_study in range(len(study_json['data']['relationships']['studies']['data'])):
            f.write("associated_study_"+str(asc_study)+"\t"+study_json['data']['relationships']['studies']['data'][asc_study]['id']+"\n")
            asc_study_counter += 1
        #printing associated biomes to file
        for biome in range(len(study_json['data']['relationships']['biomes']['data'])):
            f.write("biome_info_"+str(biome)+"\t"+study_json['data']['relationships']['biomes']['data'][biome]['id']+"\n")
        
        
        f.write("=========================================================================================\n")

        #now we need to access other attributes like "publications" which are in a new json.
        #we get the link for "publications" like this:
        url_publications = study_json['data']['relationships']['publications']['links']['related']
        if url_publications:
            pub_json = get_json_url_with_exception_handling(url_publications, 30, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT)

            #print("type:",type(pub_json['data']),"\n")
            #print("Printing json keys :",pub_json.keys(),"\n")
            for publication in range(len(pub_json['data'])):
                #print("i is: ", publication, "\n")
                pub_attribute = pub_json['data'][publication]['attributes']['pubmed-id']
                studyid_pmid_file_handler.write(study+"\t"+str(pub_attribute)+"\n")

                #print("The type is: ", type(pub_attribute), "\n")
                f.write("publication_nr_"+str(publication)+"_pubmed_id\t"+str(pub_attribute)+"\n")
                pub_attribute = pub_json['data'][publication]['attributes']['pub-title']
                f.write("publication_nr_"+str(publication)+"_title\t"+str(pub_attribute)+"\n")
                pub_attribute = pub_json['data'][publication]['attributes']['published-year']
                f.write("publication_nr_"+str(publication)+"_publication_year\t"+str(pub_attribute)+"\n")

            f.write("=========================================================================================\n")
        else:
            f.write("Publications unavailable from the server\n")
            f.write("=========================================================================================\n")


        """
        #we get the link for "samples" like this:
        #url_samples = study_json['data']['relationships']['samples']['links']['related']
        url_samples = MGNIFY_REST_API_URL_BASE+'studies/'+study+'/samples?page=1'
        
        
        #geting the page info for samples
        json_data_samples = get_json_url_with_exception_handling(url_samples, 30, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT)

        # get the total number of pages 
        number_of_pages = json_data_samples['meta']['pagination']['pages']
        print("Number of sample pages to be retrieved from "+study+": " + str(number_of_pages) + "\n")


        #going through all sample pages
        sample_nr = 0
        for i in range (int(number_of_pages)):
            
            
            page_nr = i+1
            
            if page_nr == 1 : 
                sam_json = json_data_samples.copy()
            else:
                url_samples = MGNIFY_REST_API_URL_BASE+'studies/'+study+'/samples?page='+str(page_nr)
                sam_json = get_json_url_with_exception_handling(url_samples, 30, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT)
            #for every sample page we get the json and extract info
            for sample in range(len(sam_json['data'])):
                sam_attribute = sam_json['data'][sample]['attributes']['accession']
                f.write("sample_nr_"+str(sample_nr)+"_sample_id\t"+str(sam_attribute)+"\n")
                sam_attribute = sam_json['data'][sample]['attributes']['sample-desc']
                if sam_attribute:
                    cleaned_sample_desc = clean_text(sam_attribute)
                    f.write("sample_nr_"+str(sample_nr)+"_sample_description\t"+str(cleaned_sample_desc)+"\n")
                else:
                    cleaned_sample_desc = "unavailable"
                    f.write("sample_nr_"+str(sample_nr)+"_sample_description\t"+cleaned_sample_desc+"\n")
                
                sample_nr += 1         
             
        
            #print("The page nr is:",page_nr,"\n")
        
        print("Total number of sample pages retrieved:",page_nr,"\n")
        print("Total number of samples:",sample_nr,"\n")
        f.write("\n")
        """
        #after the data extraction is completed we close the file for this study inside the loop
        f.close()
        
        
        #after we have harvested the desired text & info, we download files available for each study (ex. functional annotations)
        
        
        
        #will skip this step to save time
        
        #we get the link for "downloads" like this:
        
        
        
        """
        url_downloads = study_json['data']['relationships']['downloads']['links']['related']
        
        
        dwn_json = get_json_url_with_exception_handling(url_downloads, 30, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT) 
             
        #before downloading we clear the download path from previous .tsv files, so as not to get altered filenames
        # like GO-slim_abundances_v5.0 (1).tsv
        dir_name = harv_studies+study
        test = os.listdir(dir_name)
        for item in test:
            if item.endswith(".tsv"):
                os.remove(os.path.join(dir_name, item))
                

        #now we go though every download link in the study
        for download in range(len(dwn_json['data'])):
            #print("i is: ", publication, "\n")
            dwn_url = dwn_json['data'][download]['links']['self']
            #print("The group type is: ", dwn_json['data'][download]['attributes']['group-type'], "\n")
            #group_type = dwn_json['data'][download]['attributes']['group-type']
            #if ANALYSIS_GROUP_TYPES_TO_INCLUDE.get(group_type):
                #get the info if we want it
            #and now we can download the files
            download_file_via_wget_url(dwn_url, harv_studies+study, float(SLEEP_MIN), float(SLEEP_MAX), RECURSIONS_LIMIT)\
        
        """
        
        #now creating the 'COMPLETED' file
        completion_file = open(harv_studies+study+"/COMPLETED", "w", encoding='utf-8')
        completion_file.close()
        print("File 'COMPLETED' created\n")
    except Exception as error:
        print("The study loop encountered an error: ", error ,"in study:",study,". Will empty the study folder and continue to the next study\n")
        continue
## the for study in study_ids_from_json ended here         
        
    
studyid_pmid_file_handler.close        
print("=================================================================================================================\n")     

#for every incomplete study we empty its directory, so it can be downloaded again, clean
#for inc in incomplete_study_ids:
#    print("\n\nThe incomplete studies are: ", inc,"\n\n")
#    print("Directory to be removed: ", harv_studies+inc ,"\n")
#    remove_dir(harv_studies+inc) 


print("The total nr of studies with associated study found is:", asc_study_counter, "\n")
print("The total nr of harvested/checked studies are:", study_counter, "\n")





timepoint_2 = datetime.datetime.now()
third_step_durance = timepoint_2 - timepoint_1
print("The third step took: ", third_step_durance, "\n")


total_durance = timepoint_2 - start
print("Total runtime: ", total_durance)

log_file.close()
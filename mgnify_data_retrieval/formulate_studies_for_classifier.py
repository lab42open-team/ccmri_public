#! /usr/bin/python3.5

########################################################################################
# script name: formulate_studies_for_classifier.py
# modified by: Alexios Loukas
# framework: CCMRI - WP1
########################################################################################
# GOAL
# Formulate studies for classifier - this will be a python script that attaches pubmed abstracts to the files that
# contain mined info from mgnify, and primes them for another part of the pipeline.
# Steps:
# 1. reads the file studyid_pmid_sorted.tsv.
#
# 2. since it is sorted we need to decide on a number cut-off for the publications.
#
# 3. then the pubmed ids that are above threshold are blocklisted
#
# 4. then we will scan all the harvested files from mgnify :  ex. mined_info_MGYS00000633.txt
# and remove the blacklisted pubmed info from every file.
#
# 5. last step is adding pubmed abstracts to mgnify studies with attached publications.
# the abstracts are added in a single line.
########################################################################################
## usage: ./formulate_studies_for_classifier.py
########################################################################################

import sys
sys.path.append('/_full_path_in_your_server_to_/')
import os
import datetime
import re
from mgnify_functions import clean_text

#trying to get rid of a zombie process that this script creates
import signal
signal.signal(signal.SIGCHLD, signal.SIG_IGN)



# The working directory will be the most recent of the mgnify versions
WORKING_DIR = "/_full_path_in_your_server_to_"
THRESHOLD = 15
DEEP_LOG = True

# this method accepts the full pubmed as a tsv file and a dictionary of selected pubmed ids whose text is to be retrieved
# and returns a dictionary with the selected pubmed ids along with their abstract text
def get_pubmed_abstracts_for_pubmed_ids(selected_pubmedid_dictionary, pubmed_tsv_file_path):
    pubmed_dict = {}
    counter = 0
    with open(pubmed_tsv_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if len(line.split("\t")) >= 6: #process pubmed entries with abstract text, skip otherwise
                pmid_abstract_text = line.split("\t")[5]
                pmid_column_token = line.split("\t")[0]
                current_pmid = pmid_column_token.split("|")[0]

                if current_pmid in selected_pubmedid_dictionary:

                    #print("Found current_pmid ", current_pmid," and its text is: ", pmid_abstract_text.encode('utf-8'), "\n")
                    pubmed_dict[current_pmid] = pmid_abstract_text.encode('utf-8')
                    
            if DEEP_LOG:
                if counter % 100000 == 0:
                    print("Reached: " + str(counter) + " abstracts and current pmid is: " + current_pmid)
                counter = counter+1
    file.close()
    #print("containing ", len(pubmed_dict), " key-value pairs")
    return pubmed_dict





def sort_lines_by_publication_order(new_lines, blocked_ids):
    """
    Sorts the lines for the same publication_nr in the desired order:
    _pubmed_id, _pubmed_title, _pubmed_abstract, _pubmed_ebi_link, _publication_year.
    Removes all lines for any publication containing a blocked ID.
    Keeps the existing separator lines in their original positions and
    sorts publication numbers in ascending order.

    Args:
        new_lines (list): List of lines to process.
        blocked_ids (list): List of blocked IDs to filter out.

    Returns:
        list: Sorted list of lines with publication_nr fields in the correct order,
              while keeping the separator lines in their original positions and
              excluding publications with blocked IDs.
    """
    # Define the desired order of keys
    order = ["_pubmed_id", "_title", "_pubmed_abstract", "_EBI_link", "_publication_year"]

    # Create dictionaries to group lines by type
    grouped_lines = {}
    separator_lines = []  # To store separator lines
    non_publication_lines = []  # To store non-publication-specific lines

    # Step 1: Categorize lines into groups
    for line in new_lines:
        if line.strip():  # Ignore empty lines
            if "=========================================================================================" in line:
                separator_lines.append(line)  # Separator lines
            else:
                # Extract the publication_nr prefix
                prefix_match = re.match(r"publication_nr_(\d+)_", line)
                if prefix_match:
                    pub_nr = int(prefix_match.group(1))  # Ensure pub_nr is treated as an integer
                    if pub_nr not in grouped_lines:
                        grouped_lines[pub_nr] = []
                    grouped_lines[pub_nr].append(line)
                else:
                    non_publication_lines.append(line)  # General metadata or non-publication lines

    # Step 2: Filter out publications with blocked IDs
    filtered_grouped_lines = {}
    for pub_nr, lines in grouped_lines.items():
        contains_blocked_id = any(
            "_pubmed_id\t{}".format(blocked_id) in line for blocked_id in blocked_ids for line in lines
        )
        if not contains_blocked_id:
            filtered_grouped_lines[pub_nr] = lines

    # Step 3: Sort each publication group by the desired field order
    sorted_publications = []
    for pub_nr in sorted(filtered_grouped_lines):  # Ensure publication groups are processed in ascending order
        sorted_group = []
        for key in order:
            sorted_group.extend([line for line in filtered_grouped_lines[pub_nr] if key in line])
        # Include any unmatched lines for the publication
        sorted_group.extend([line for line in filtered_grouped_lines[pub_nr] if not any(key in line for key in order)])
        sorted_publications.extend(sorted_group)

    # Step 4: Reassemble all lines while preserving the original positions of separator lines
    final_lines = []
    publication_index = 0
    separator_index = 0

    for line in new_lines:
        if "=========================================================================================" in line:
            # Add separator lines at their original positions
            final_lines.append(separator_lines[separator_index])
            separator_index += 1
        elif line not in non_publication_lines:
            # Add publication lines in their sorted order
            if publication_index < len(sorted_publications):
                final_lines.append(sorted_publications[publication_index])
                publication_index += 1
        else:
            # Add non-publication-specific lines
            final_lines.append(line)

    # Step 5: Renumber all publications (id, title, abstract, etc.) starting from 0
    publication_count = 0
    publication_lines = []  # To store lines that belong to the same publication group
    in_publication_group = False  # Flag to track when we're inside a publication group

    for i, line in enumerate(final_lines):
        # Check if the line is the start of a new publication group (identified by "publication_nr_X_pubmed_id")
        if re.match(r"publication_nr_\d+_pubmed_id", line):
            if publication_lines:  # If there is a previous publication group, renumber it
                # Renumber the previous group
                for pub_line in publication_lines:
                    new_line = re.sub(r"publication_nr_\d+_", "publication_nr_{}_".format(publication_count), pub_line)
                    final_lines[pub_line[1]] = new_line  # Update the line in final_lines
                publication_count += 1  # Increment the publication count

            # Start tracking the new publication group
            publication_lines = [(line, i)]  # Store the line and its index
            in_publication_group = True
        elif in_publication_group:
            # Add lines to the current publication group
            publication_lines.append((line, i))
            
            if "_publication_year" in line:
                # Once we reach the last line for this publication (i.e., the line with _publication_year)
                # Renumber the current group
                for pub_line in publication_lines:
                    new_line = re.sub(r"publication_nr_\d+_", "publication_nr_{}_".format(publication_count), pub_line[0])
                    final_lines[pub_line[1]] = new_line  # Update the line in final_lines
                publication_count += 1  # Increment the publication count
                publication_lines = []  # Clear the lines for the current publication
                in_publication_group = False  # Mark the end of the current group

    return final_lines



def check_non_abstracted_file(file_path, blocklist):
    """
    This method checks if a file (identified by file_path) contains any lines
    with a _pubmed_id from the blocklist and processes the lines accordingly.

    Args:
        file_path (str): Path to the file to be processed.
        blocklist (list): List of blocked PubMed IDs to check against.

    Returns:
        list: List of lines from the file (can be further processed in another method).
    """

    # Read the file and store all lines in a list
    try:
        with open(file_path, 'r') as file:
            file_lines = file.readlines()

    except IOError:
        print("Error: File does not exist or can't be opened.")
        return []


    #now check if the file is non-abstracted
    abstracted = 0
    abstract_line = "_pubmed_abstract\t"
    for file_line in file_lines:
        if abstract_line in file_line:
            print("This one has abstract: ", file_path)
            abstracted = 1
    # Now call another method to process the file_lines, such as:
    # process_lines(file_lines, blocklist)  # (Define this method based on your needs)
    if not abstracted:
        new_lines = sort_lines_by_publication_order(file_lines, blocklist)
        return new_lines
    else:
        return 1



def overwrite_file_with_filtered_lines(file_path, filtered_lines):
    """
    Overwrites a file with the filtered lines.
    
    Args:
        file_path (str): Path to the file to be overwritten.
        filtered_lines (list): List of lines to write into the file.
    """
    try:
        with open(file_path, 'w') as file:
            file.writelines(filtered_lines)
        print("File '{}' has been successfully overwritten.".format(file_path))
    except IOError:
        print("Error: Unable to open or write to the file '{}'.".format(file_path))
        
        



start = datetime.datetime.now()
date =  datetime.date.today()
old_stdout = sys.stdout
log_file_formulate_name = "/_full_path_in_your_server_to_/logs/" + "formulate_studies_"+ str(date) + ".log"
log_file_formulate = open(log_file_formulate_name,"w")
sys.stdout = log_file_formulate   #redirecting stardard out to the log file


# Starting to read from the file of sorted pmids and their observed frequencies
file = '/_full_path_in_your_server_to_/studyid_pmid_sorted.tsv'
with open(file, 'r', encoding='utf-8') as info:
    blocklist = []
    # Reading all the file lines in order to collect all the frequencies and adding frequencies above threshold filenames in a blocklist
    for line in info:
        columns = line.strip().split('\t')
        if int(columns[0]) > THRESHOLD:
            print("The info that is above threshold is:", line)
            pmid = columns[1].split('/')[-1]
            # print("The pmid is:", pmid)
            blocklist.append(pmid)

print("So this is the blocklist: ", blocklist, "\n")

# Reading all the txt files from working directory and save their filenames in a list
txt_filenames = []
substring = 'mined_info' #checking if the txt files are indeed coming from our mining activity
counter = 0



# Walk through all files and sub-directories
for root, dirs, files in os.walk(WORKING_DIR):
    # Check if any abstracted file exists in this folder
    has_abstracted = any("_abstracted.txt" in f for f in files)

    # If any abstracted file is present, skip the entire folder
    if has_abstracted:
        continue

    for file in files:
        if file.endswith('.txt') and "mined_info" in file:
            file_path = os.path.join(root, file)
            txt_filenames.append(file_path)
            counter += 1





desired_pmids_dict = {}

for mined in txt_filenames:
    # Read the file and store its lines in a list
    with open(mined, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        line_number = 0
        for line in lines:
            line_number += 1
            if "_pubmed_id" in line:
                #extract the pubmed id to check the blocklist
                pub_info = line.strip().split('\t')
                pubmed_id = pub_info[1]
                #will check the blocklist
                if pubmed_id not in blocklist:
                    pubmed_id_for_dict = "PMID:"+pubmed_id
                    key, value = pubmed_id_for_dict, '1'
                    desired_pmids_dict[key]=value
                    #print("The dictionary now is : ", desired_pmids_dict, "\n")  
                   
                    
                
#print("These are the pmids that we need their abstracts:\n")
#print(desired_pmids_dict,"\n")



# to retrieve pubmed please see: - https://pubmed.ncbi.nlm.nih.gov/download/
# we are using a modified .tsv file that contains pubmed IDs, titles and abstracts
pubmed_output_file = '/_full_path_in_your_server_to_/pubmed2025.tsv'

timepoint_1 = datetime.datetime.now()
first_step_durance = timepoint_1 - start
print("Now will search for PMIDs in the output.tsv. The duration so far is: ", first_step_durance, "\n")


if desired_pmids_dict:
    #search_keys_in_file(desired_pmids_dict.keys(), pubmed_output_file)
    pubmed_id_to_text_dictionary = get_pubmed_abstracts_for_pubmed_ids(desired_pmids_dict, pubmed_output_file)
else:
    pubmed_id_to_text_dictionary = {}
    print("No PMIDs found. Skipping abstract extraction to save time and CPU.")





#print("The dictionary is:\n")
#print(pubmed_id_to_text_dictionary)

timepoint_2 = datetime.datetime.now()
second_step_durance = timepoint_2 - timepoint_1
print("The dictionary was created, the proccess took: ", second_step_durance, "\n")



    
#first_key = next(iter(pubmed_id_to_text_dictionary.keys()))
#print("First Key:", first_key, "\n")
#print("Value for the First Key:", pubmed_id_to_text_dictionary[first_key],"\n")
# Access the value associated with the key 'PMID:28703874'
#value_tuple = pubmed_dict[first_key][0]
# Split the second element of the tuple by '\t'
#split_values = value_tuple[1].split('\t')
#print(split_values[5])
#memory_usage = sys.getsizeof(pubmed_id_to_text_dictionary)
#print("Memory usage of the pubmed_id_to_text_dictionary:", memory_usage, "bytes\n")
    

files_containing_blocked_pmids=[]

for mined in txt_filenames:
    # Read the file and store its lines in a list
    with open(mined, 'r', encoding='utf-8') as file1:
        lines = file1.readlines()
        line_number = 0
        file_abstracted = 0
        pubmed_id_blocked = 0
        nr_of_papers_found = 0
        new_lines = []
        for line in lines:
            line_number += 1
            new_lines.append(line)
            if "_pubmed_id" in line:
                nr_of_papers_found += 1
                #extract the pubmed id to check the blocklist
                pub_info = line.strip().split('\t')
                pubmed_id = pub_info[1]
                #will check the blocklist
                if pubmed_id not in blocklist:
                    pubmed_id_for_dict = "PMID:"+pubmed_id
                    #print("The formated key is : ", pubmed_id_for_dict, "\n")
                    if pubmed_id_for_dict in pubmed_id_to_text_dictionary:
                        print("Key found in dict! : ", pubmed_id_for_dict, " for file:",mined,"\n")
                        file_abstracted = 1
                        dict_value = pubmed_id_to_text_dictionary[pubmed_id_for_dict]
                        cleaned_abstract = dict_value.decode('utf-8')
                        extra_cleaned_abstract = clean_text(cleaned_abstract)
                        #print("The value is:",dict_value)
                        #cleaned_abstract = cleaned_abstract.rstrip()
                        # Prepare the new lines for abstract and link
                        abstract_line = "publication_nr_" + str(nr_of_papers_found - 1) + "_pubmed_abstract\t" + extra_cleaned_abstract + "\n"
                        ebi_link_line = "publication_nr_" + str(nr_of_papers_found - 1) + "_EBI_link\thttps://www.ebi.ac.uk/metagenomics/publications/" + pubmed_id + "\n"
                        
                        new_lines.append(abstract_line)  # Add the abstract line
                        new_lines.append(ebi_link_line) # Add the EBI link line
                                
                    else:
                        print("Key NOT found in dict! : ", pubmed_id_for_dict, " for file:",mined,"\n")
                else:
                    pubmed_id_blocked = 1
                    print("This pubmed id is blocked: ", pubmed_id, " (from: ",mined,")\n")
                    files_containing_blocked_pmids.append(mined)

                    
        if file_abstracted:
            #sort the lines properly
            new_lines_sorted = sort_lines_by_publication_order(new_lines, blocklist)
            new_file = mined.replace(".txt", "")+"_abstracted.txt" 
            with open(new_file, 'w', encoding='utf-8') as file2:
                file2.writelines(new_lines_sorted)
            #this file close was added in 8.03.24, may help with memory issues
            file2.close()
    file1.close()
    


    
print("Studies counter: ",counter, "\n")
print("end of loop\n")


#now dealing with blocked publication info in non-abstracted files (just containing pubmed id, title and year)
# Convert to set (removes duplicates)
files_containing_blocked_pmids_set = set(files_containing_blocked_pmids)
print("Let's check the studies with blocked pubmed ids: ", files_containing_blocked_pmids)
#now will develop a function to remove the proper lines from the files
for non_abstracted_file in files_containing_blocked_pmids:
    new_non_abstracted_lines = check_non_abstracted_file(non_abstracted_file, blocklist)
    if (new_non_abstracted_lines!=1):
        # Overwrite the file with the new filtered lines
        overwrite_file_with_filtered_lines(non_abstracted_file, new_non_abstracted_lines)
    else:
        print("Abstracted file: ", non_abstracted_file)
        print("No changes made\n")


#added 8.03.24 also may help with memory issues
if 'pubmed_id_to_text_dictionary' in locals():
    del pubmed_id_to_text_dictionary
if 'desired_pmids_dict' in locals():
    del desired_pmids_dict
if 'lines' in locals():
    del lines
if 'new_lines' in locals():
    del new_lines

total_durance = timepoint_2 - start
print("Total runtime: ", total_durance)
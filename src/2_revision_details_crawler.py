# this script downloads the JSON files containing the details of every revision of the project specified in the settings
# the revision JSON files are saved in the 'revisions_details' dir

from urllib.request import *
import configparser
import os
import socket
import glob
import re
import json

# function to compare the review's JSON files when sorting
def compare_review_json(review_json_file_name):
    splitted_review_json_file_name = review_json_file_name.split("/")

    return int(splitted_review_json_file_name[len(splitted_review_json_file_name) - 1].split(".")[0])

######################### script starts here #################################

# regex object to extract the review number from the review JSON file
rg_id = re.compile("/(\d+)\.json")

socket.setdefaulttimeout(50)
config = configparser.ConfigParser()
# config.read("Couchbase_settings.ini")
config.read("Eclipse_settings.ini")

COMMUNITY = config['DETAILS']['community']
PROJECT = config['DETAILS']['project']
PROJECT_REVIEW_JSON = config['DETAILS']['project_review_json']
REVISION_JSON_URL=config['DETAILS']['revision_json_url']

# create the revisions_details directory if it does not exist
if os.path.isdir("revisions_details") == False:
    os.mkdir("revisions_details")

# create a revisions details directory for the project if it does not exist
if os.path.isdir("revisions_details/" + PROJECT) == False:
    os.mkdir("revisions_details/" + PROJECT)

# get the reviews's details JSON files for the community sorted in ascending order
review_jsons = sorted(glob.glob("reviews_details/"+ COMMUNITY + "/*.json"), key=compare_review_json)

# we iterate over all JSON files, filtering the ones regarding the project of interest and downloading the necessary revisions details
for review_json in review_jsons:
    review_number = rg_id.findall(review_json)[0]

    json_file = json.load(open(review_json))

    # check whether the review JSON is regarding the project
    # if yes, download the details for all revisions in the review
    if PROJECT_REVIEW_JSON == json_file["project"]:
        for key, value in json_file["revisions"].items():
            revision_number = str(value["_number"])
            revision_file_name = "revisions_details/" + PROJECT + "/%s_rev%s.json" % (review_number, revision_number)

            # if revision file already exists, skip to next
            if os.path.isfile(revision_file_name):
                continue

            revision_url = REVISION_JSON_URL % (review_number, key)

            # when downloading the revision JSON, stop if the user press ctrl + c. Skip to next revision given any other error
            try:
                print("Downloading details of revision " + revision_number + " from review " + review_number + " of " + PROJECT)
                resp = urlopen(revision_url)
            except KeyboardInterrupt:
                    raise
            except:
                continue

            content = resp.read().decode("utf-8", errors="ignore")

            # JSONs returned by the Gerrit API usually have a non-standard starting line that needs to be filtered
            if content.startswith(")]}'"):
                content = "\n".join(content.split("\n")[1:])

            revision_file = open(revision_file_name, "w")
            revision_file.write(content)
            revision_file.close()

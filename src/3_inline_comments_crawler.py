# this script downloads the JSON files containing the inline comments of every revision of the project specified in the settings
# the inline comments JSON files are saved in the 'inline_comments_details' dir

from urllib.request import *
import configparser
import os
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

config = configparser.ConfigParser()
# config.read("Couchbase_settings.ini")
config.read("Eclipse_settings.ini")

COMMUNITY = config['DETAILS']['community']
PROJECT = config['DETAILS']['project']
PROJECT_REVIEW_JSON = config['DETAILS']['project_review_json']
INLINE_COMMENT_URL=config['DETAILS']['inline_comment_url']

# create the inline_comments_details directory if it does not exist
if os.path.isdir("inline_comments_details") == False:
    os.mkdir("inline_comments_details")

# create an inline comments details directory for the project if it does not exist
if os.path.isdir("inline_comments_details/" + PROJECT) == False:
    os.mkdir("inline_comments_details/" + PROJECT)

# get the reviews's details JSON files for the community sorted in ascending order
review_jsons = sorted(glob.glob("reviews_details/"+ COMMUNITY + "/*.json"), key=compare_review_json)

# we iterate over all review's JSON files, filtering the ones regarding the project of interest
for review_json in review_jsons:
    review_number = rg_id.findall(review_json)[0]

    review_json = json.load(open(review_json))

    # check whether the review JSON is regarding the project
    # if yes, download the inline comments for each revision in the review
    if PROJECT_REVIEW_JSON == review_json["project"]:

        # iterate over all revisions, sorted by the revision number
        for key, value in sorted(review_json["revisions"].items(), key = lambda revision_item : int(revision_item[1]["_number"])):
            revision_number = str(value["_number"])

            inline_comment_file_name = "inline_comments_details/" + PROJECT + "/%s_rev%s_inline_comments.json" % (review_number, revision_number)

            # if inline comment file already exists, skip to next
            if os.path.isfile(inline_comment_file_name):
                continue

            inline_comment_url = INLINE_COMMENT_URL % (review_number, revision_number)

            # when downloading the inline comments JSON, stop if the user press ctrl + c. Skip to next inline comment given any other error
            try:
                print("Downloading inline comments of revision " + revision_number + " from review " + review_number + " of " + PROJECT)
                resp = urlopen(inline_comment_url)
            except KeyboardInterrupt:
                    raise
            except:
                continue

            content = resp.read().decode("utf-8", errors="ignore")

            # JSONs returned by the Gerrit API usually have a non-standard starting line that needs to be filtered
            if content.startswith(")]}'"):
                content = "\n".join(content.split("\n")[1:])

            inline_comment_file = open(inline_comment_file_name, "w")
            inline_comment_file.write(content)
            inline_comment_file.close()

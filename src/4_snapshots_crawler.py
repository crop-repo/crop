# this script downloads the before and after snapshots of every revision of the project specified in the settings
# the snapshots are saved in the 'snapshots' dir

import configparser
import glob
import re
import json
import os
import subprocess

# function to compare the review's JSON files when sorting
def compare_review_json(review_json_file_name):
    splitted_review_json_file_name = review_json_file_name.split("/")

    return int(splitted_review_json_file_name[len(splitted_review_json_file_name) - 1].split(".")[0])

# function to check whether both before and after snapshots of a certain revision have already been downloaded
def are_before_and_after_snapshots_downloaded(review_id, revision_number):
    if os.path.isfile("snapshots/" + PROJECT + "/before_" + review_id + "_rev" + revision_number + ".tar.gz") == False:
        return False
    elif os.path.isfile("snapshots/" + PROJECT + "/after_" + review_id + "_rev" + revision_number + ".tar.gz") == False:
        return False
    else:
        return True

# function to download a certain snapshot of a certain revision
# the 'when' parameter denotes whether the snapshot is before or after the revision
def download_snapshot(review_id, revision_number, commit_id, when):
    print("Downloading " + when + "_" + review_id + "_" + "rev" + revision_number + ".tar.gz")

    # depending on the community, the snapshot_url is different
    # see the settings file for more details
    if COMMUNITY == "Couchbase":
        snapshot_url = SNAPSHOT_URL % (PROJECT, commit_id)
    elif COMMUNITY == "Eclipse":
        SNAPSHOT_PROJECT_1 = config['DETAILS']['snapshot_project_1']
        SNAPSHOT_PROJECT_2 = config['DETAILS']['snapshot_project_2']

        snapshot_url = SNAPSHOT_URL % (SNAPSHOT_PROJECT_1, SNAPSHOT_PROJECT_2, commit_id)

    # the downloaded snapshot assumes a certain file name for different communities 
    # see the settings file for more details
    if COMMUNITY == "Couchbase":
        snapshot_file_name = SNAPSHOT_FILE_NAME % (PROJECT, commit_id)
    elif COMMUNITY == "Eclipse":
        snapshot_file_name = SNAPSHOT_FILE_NAME % (commit_id)

    # snapshots are stored following this naming pattern:
    # <review_id>_rev<revision_number>.tar.gz
    new_snapshot_file_name = "snapshots/" + PROJECT + "/" + when + "_" + review_id + "_rev" + revision_number + ".tar.gz"

    # download the snapshot and move it to the correct directory
    subprocess.Popen(["wget", "-q", snapshot_url], stdout=subprocess.PIPE).communicate()
    subprocess.Popen(["mv", snapshot_file_name, new_snapshot_file_name], stdout=subprocess.PIPE).communicate()

    # throws an error when the snapshot cannot be downloaded
    if os.path.isfile(new_snapshot_file_name) == False:
        raise ValueError("Unable to download " + new_snapshot_file_name)

    if is_snapshot_empty(new_snapshot_file_name) == True:
        raise ValueError("Empty snapshot " + new_snapshot_file_name)

def is_snapshot_empty(new_snapshot_file_name):
    snapshot_size = os.stat(new_snapshot_file_name).st_size

    if snapshot_size == 0:
        return True
    else:
        return False

######################### script starts here #################################

# regex object to extract the review number from the review JSON file
rg_id = re.compile("/(\d+)\.json")

config = configparser.ConfigParser()
# config.read("Couchbase_settings.ini")
config.read("Eclipse_settings.ini")

COMMUNITY = config['DETAILS']['community']
PROJECT = config['DETAILS']['project']
PROJECT_REVIEW_JSON = config['DETAILS']['project_review_json']
SNAPSHOT_URL = config['DETAILS']['snapshot_url']
SNAPSHOT_FILE_NAME = config['DETAILS']['snapshot_file_name']

# create the snapshots directory if it does not exist
if os.path.isdir("snapshots") == False:
    os.mkdir("snapshots")

# create a directory for the project's snapshots if it does not exist
if os.path.isdir("snapshots/" + PROJECT) == False:
    os.mkdir("snapshots/" + PROJECT)

# get the reviews's details JSON files for the community sorted in ascending order
review_jsons = sorted(glob.glob("reviews_details/"+ COMMUNITY + "/*.json"), key=compare_review_json)

# we iterate over all JSON files, filtering the ones regarding the project of interest and downloading the snapshots for all revisions
for review_json in review_jsons:
    review_number = rg_id.findall(review_json)[0]

    # if int(review_number) < 40000:
    review_json = json.load(open(review_json))

    # check whether the review JSON is regarding the project
    # if yes, download the snapshots for before and after each revision
    if PROJECT_REVIEW_JSON == review_json["project"]:

        # iterate over all revisions, sorted by the revision number
        for key, value in sorted(review_json["revisions"].items(), key = lambda revision_item : int(revision_item[1]["_number"])):
            revision_number = str(value["_number"])

            # check if snapshots have already been downloaded. If yes, skip to next revision
            if are_before_and_after_snapshots_downloaded(review_number, revision_number) == False:
                revision_json_file_name = "revisions_details/" + PROJECT + "/" + review_number + "_rev" + revision_number + ".json"

                # check if the revision file exists
                if os.path.isfile(revision_json_file_name) == True:
                    revision_json = json.load(open(revision_json_file_name))

                    # check if the revision has a parent 
                    # Sometimes Gerrit does not record the parent of a certain revision. In these cases, the revision is ignored
                    if len(revision_json["parents"]) > 0:
                        before_revision_commit_id = revision_json["parents"][0]["commit"]
                        after_revision_commit_id = revision_json["commit"]

                        # the function download_snapshot may throw an exception when an error occurs in the download
                        # in these cases print the error message and move to the next snapshot
                        try:
                            download_snapshot(review_number, revision_number, before_revision_commit_id, "before")
                            download_snapshot(review_number, revision_number, after_revision_commit_id, "after")
                        except ValueError as e:
                            print(e)
                            continue 

# this script creates a git repository for the project specified in the seetings
# it automatically extracts and commit each snapshot in sequential order to this new git repository
# the new git repository is located in the 'git_repos' dir

# in addition, the script creates a CSV file to store important data about each revision in a easily accessible way
# in the CSV, each line represents a single revision, and the following information is saved in each column:

# id: an unique id to identify the revision within an specific community
# review_number: the unique review number in which the revision is part of
# revision_number: the number of the revision in the specific review
# author: the author of the revision
# status: the status of the revision
# change_id: the change id of this revision
# url: the URL in which one can access the web view of the revision
# original_before_commit_id: the commit id listed by gerrit as the version of the system before the revision took place
# original_after_commit_id: the commit id listed by gerrit as the version of the system after the revision took place
# before_commit_id: the commit id that represents the version of the system before the revision took place in the new git repository that was created by this script
# after_commit_id: the commit id that represents the version of the system after the revision took place in the new git repository that was created by this script

import configparser
import glob
import re
import json
import os
import subprocess
import linecache

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

# function to read the csv file and convert it into a dictionary
def read_csv(csv_file_name):
    csv = {}
    headers = linecache.getline(csv_file_name, 1).split("\n")[0].split(",")

    for header in headers:
        csv[header] = []

    csv_file = open(csv_file_name, "r")
    csv_lines = csv_file.readlines()

    for index, line in enumerate(csv_lines):
        if index != 0:
            line = line.split("\n")[0]
            splitted_line = line.split(",")

            for value_index, value in enumerate(splitted_line):
                if value == "":
                    value = None

                csv[headers[value_index]].append(value)

    csv_file.close()

    return csv

# function to identify whether a certain before commit has already been added to the git repository
def get_before_commit_already_in_repo(original_before_commit_id, csv):
    for index, original_after_commit_id in enumerate(csv["original_after_commit_id"]):
        if original_after_commit_id == original_before_commit_id:
            return csv["after_commit_id"][index]

    return "None"

def populate_repo_with_revision_snapshot(revision_id, when):
    # extract the snapshot source code to the git repository
    extract_snapshot_to_repo(revision_id, when)

    # adds and/or deletes items given the changes in the git repository with the new snapshot
    prepare_repo_for_commit()

    commit_repo(revision_id, when)

    # identifies the latest commit id to be stored in the CSV
    commit_id = get_commit_id_from_last_commit()

    clean_repo()

    return commit_id

# function to extract the source code of the snapshot to the git repository
def extract_snapshot_to_repo(revision_id, when):
    # copies the snapshot file to the repository
    subprocess.Popen(["cp", "snapshots/" + PROJECT + "/" + when + "_" + revision_id + ".tar.gz", "git_repos/" + PROJECT + "/"], stdout=subprocess.PIPE).communicate()

    # extracts the tar file and checks for errors in the extraction
    tar_feedback = str(subprocess.Popen(["tar", "-xf", "git_repos/" + PROJECT + "/" + when + "_" + revision_id + ".tar.gz", "-C", "git_repos/" + PROJECT + "/"], stderr=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[1])

    if "unexpected:" in tar_feedback or "Unexpected:" in tar_feedback or "error:" in tar_feedback or "Error:" in tar_feedback:
        raise ValueError("Error in extracting tar: " + when + "_" + revision_id)

    # in the Couchbase community, the snapshot is extracted into an extra directory with the name <project>-<commit_id>
    # in this case, move all the content of this additional directory directly in the root of the repository
    if COMMUNITY == "Couchbase":
        snapshot_folder = glob.glob("git_repos/" + PROJECT + "/" + PROJECT + "*")[0]
        files_and_dirs = os.listdir(snapshot_folder)

        for item in files_and_dirs:
            if item != ".git":
                subprocess.Popen(["mv", snapshot_folder + "/" + item, "git_repos/" + PROJECT], stdout=subprocess.PIPE).wait()

        # removes the additional directory
        subprocess.Popen(["rm", "-rf", snapshot_folder], stdout=subprocess.PIPE).communicate()

    # removes the snapshot file
    subprocess.Popen(["rm", "git_repos/" + PROJECT + "/" + when + "_" + revision_id + ".tar.gz"], stdout=subprocess.PIPE).wait()

# function to add and/or remove items given the state of the git repository
def prepare_repo_for_commit():
    # the status message is used to identify the items that need to be added and/or removed
    git_status = str(subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "status"], stdout=subprocess.PIPE).communicate()[0])
    git_status = clean_status_message(git_status)

    changed_items = get_changed_items(git_status)
    untracked_items = get_untracked_items(git_status)

    # add/delete necessary items
    git_add_items(changed_items[0])
    git_add_items(untracked_items)
    git_delete_items(changed_items[1])

# function to format the status message in a line by line basis
def clean_status_message(git_status):
    cleaned_status = []
    git_status = git_status.split("\\n")

    for line in git_status:
        cleaned_status.append(line.replace("\\t", ""))

    return cleaned_status

# function to identify the items that were changed and deleted according to the status message
def get_changed_items(git_status):
    changed_line_flag = False
    changed_flag = False

    modified_items = []
    deleted_items = []

    for line in git_status:
        if changed_flag == False:
            if "Changes not staged" in line:
                changed_line_flag = True

            if changed_line_flag == True and line == "":
                changed_flag = True
        elif changed_flag == True:
            if line == "":
                break
            else:
                splitted_line = line.split(" ")
                if "modified" in splitted_line[0]:
                    modified_items.append(get_item_path(splitted_line))
                elif "deleted" in splitted_line[0]:
                    deleted_items.append(get_item_path(splitted_line))
                else:
                    raise ValueError("Unknow file state")

    return [modified_items, deleted_items]

# function to return the path of a file to be added or removed to the git repository
def get_item_path(splitted_line):
    splitted_line = splitted_line[1:len(splitted_line)]
    item_path = ""

    for item in splitted_line:
        if item != "":
            item_path = item_path + item + " "

    return item_path[0:len(item_path) - 1]

# function to identify the untracked items according to the status message
def get_untracked_items(git_status):
    untracked_line_flag = False
    untracked_flag = False
    untracked_items = []

    for line in git_status:
        if untracked_flag == False:
            if "Untracked files" in line:
                untracked_line_flag = True

            if untracked_line_flag == True and line == "":
                untracked_flag = True
        elif untracked_flag == True:
            if line == "":
                break
            else:
                untracked_items.append(line)

    return untracked_items

# function to add a list of items to the git repository
def git_add_items(items):
    for item in items:
        # add item and check for errors in the operation
        git_add_feedback = str(subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "add", item], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate())

        if "fatal:" in git_add_feedback[1]:
            raise ValueError("Error in adding item: " + item)

# function to delete a list of items to the git repository
def git_delete_items(items):
    for item in items:
        # delete item and check for errors in the operation
        git_delete_feedback = str(subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "rm", item], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate())

        if "fatal:" in git_delete_feedback[1]:
            raise ValueError("Error in deleting item: " + item)

# function to commit the current state of the git repository
def commit_repo(revision_id, when):
    subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "commit", "-m", "First commited as " + when + "_" + revision_id], stdout=subprocess.PIPE).communicate()

# function to identify the latest commit id in the git repository
def get_commit_id_from_last_commit():
    git_log = str(subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "log"], stdout=subprocess.PIPE).communicate()[0])
    git_log = git_log.split("\\n")

    return git_log[0].split(" ")[1]

# function to clean the git repository
def clean_repo():
    diR = "git_repos/" + PROJECT
    files_and_dirs = os.listdir(diR)

    for item in files_and_dirs:
        if item != ".git":
            subprocess.Popen(["rm", "-rf", diR + "/" + item], stdout=subprocess.PIPE).wait()

def is_patch_valid(revision_id, before_commit_id, after_commit_id):
    result = True

    write_repo_patch(revision_id, before_commit_id, after_commit_id)
    write_gerrit_patch(revision_id)

    repo_patch_name = revision_id + "_repo.diff"
    gerrit_patch_name = revision_id + "_gerrit.diff"

    repo_patch_lines = get_patch_lines(repo_patch_name)
    gerrit_patch_lines = get_patch_lines(gerrit_patch_name)

    line_types = ["plus", "minus"]
    for line_type in line_types:
        if len(repo_patch_lines[line_type]) == len(gerrit_patch_lines[line_type]):
            if do_lines_match(repo_patch_lines[line_type], gerrit_patch_lines[line_type]) == False:
                result = False
                break
        else:
            result = False
            break

    # subprocess.Popen(["rm", repo_patch_name], stdout=subprocess.PIPE).communicate()[0]
    # subprocess.Popen(["rm", gerrit_patch_name], stdout=subprocess.PIPE).communicate()[0]
    
    return result

def write_repo_patch(revision_id, before_commit_id, after_commit_id):
    subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "diff", before_commit_id, after_commit_id], stdout=open(revision_id + "_tmp.diff","w")).communicate()
    tmp_patch = open(revision_id + "_tmp.diff", "r")
    repo_patch = open(revision_id + "_repo.diff", "w")

    for line in tmp_patch:
        if " @@ " in line:
            repo_patch.write(line[0:line.index(" @@ ") + 3] + "\n")
        else:
            repo_patch.write(line)

    repo_patch.close()

    subprocess.Popen(["rm", revision_id + "_tmp.diff"], stdout=subprocess.PIPE).communicate()[0]

def write_gerrit_patch(revision_id):
    downloaded_gerrit_patch = open("patches_details/" + PROJECT + "/" + revision_id + "_patch.diff", "r")
    gerrit_patch = open(revision_id + "_gerrit.diff", "w")
    write_line_flag = False

    for line in downloaded_gerrit_patch:
        if "diff --git " in line:
            write_line_flag = True

        if write_line_flag == True:
            if " @@ " in line:
                gerrit_patch.write(line[0:line.index(" @@ ") + 3] + "\n")
            else:
                gerrit_patch.write(line)

    gerrit_patch.close()

def get_patch_lines(patch_file_name):
    patch_file = open(patch_file_name, "r")
    patch_lines = {}
    plus = []
    minus = []
    normal = []

    for line in patch_file:
        # line = line.replace("\t"," ").replace("\n","")

        # if len(line) > 1:
            # if line[0] == "+" and line[1] == " ":
                # plus.append(line)
            # elif line[0] == "-" and line[1] == " ":
                # minus.append(line)
            # else:
                # normal.append(line)

        if line[0] == "+" and not "+++ " in line:
            plus.append(line)
        elif line[0] == "-" and not "--- " in line:
            minus.append(line)
        else:
            normal.append(line)

    patch_lines["plus"] = plus
    patch_lines["minus"] = minus
    patch_lines["normal"] = normal

    return patch_lines

def do_lines_match(repo_patch_lines, gerrit_patch_lines):
    print(repo_patch_lines[38])
    print(repo_patch_lines[39])
    print(repo_patch_lines[40])
    print(repo_patch_lines[41])
    print(repo_patch_lines[42])

    for line in repo_patch_lines:
        if not line in gerrit_patch_lines:
            # print(repo_patch_lines.index(line))
            # print(line)
            return False

    return True

def reset_repo():
    print("Reseting " + PROJECT + " repository")

    git_status = str(subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "status"], stdout=subprocess.PIPE).communicate()[0])
    git_status = clean_status_message(git_status)

    deleted_items = get_changed_items(git_status)[1]

    for item in deleted_items:
        # checkout item
        subprocess.Popen(["git", "-C", "git_repos/" + PROJECT + "/", "checkout", item], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

######################### script starts here #################################

# regex object to extract the review number from the review JSON file
rg_id = re.compile("/(\d+)\.json")

config = configparser.ConfigParser()
config.read("Couchbase_settings.ini")
# config.read("Eclipse_settings.ini")

COMMUNITY = config['DETAILS']['community']
PROJECT = config['DETAILS']['project']
PROJECT_REVIEW_JSON = config['DETAILS']['project_review_json']
REVISION_URL = config['DETAILS']['revision_url']

# create the git_repos directory if it does not exist
if os.path.isdir("git_repos") == False:
    os.mkdir("git_repos")

# create a git repo for the project if it does not exist
if os.path.isdir("git_repos/" + PROJECT) == False:
    subprocess.Popen(["git", "init", "git_repos/" + PROJECT], stdout=subprocess.PIPE).communicate()

# open the CSV file to store the revisions' data. Creates a new one if it does not exist
if os.path.isfile("metadata/" + PROJECT + ".csv") == False:
    csv_file = open("metadata/" + PROJECT + ".csv", "w")
    csv_file.write("id,review_number,revision_number,author,status,change_id,url,original_before_commit_id,original_after_commit_id,before_commit_id,after_commit_id\n")
    csv_file.close()

csv_file = open("metadata/" + PROJECT + ".csv", "a")

# read the existing CSV to avoid populating the repo with revisions that have already been added
csv = read_csv(csv_file.name)
revisions_already_in_repo = csv["id"]

# get the reviews's details JSON files for the community sorted in ascending order
review_jsons = sorted(glob.glob("reviews_details/"+ COMMUNITY + "/*.json"), key=compare_review_json)

# we iterate over all review's JSON files, filtering the ones regarding the project of interest
for review_json in review_jsons:
    review_number = rg_id.findall(review_json)[0]

    review_json = json.load(open(review_json))

    # check whether the review JSON is regarding the project
    # if yes, populate the git repository with the snapshots for before and after each revision
    if PROJECT_REVIEW_JSON == review_json["project"]:

        # iterate over all revisions, sorted by the revision number
        for key, value in sorted(review_json["revisions"].items(), key = lambda revision_item : int(revision_item[1]["_number"])):
            revision_number = str(value["_number"])

            # check whether both before and after snapshots were downloaded for the revision
            if are_before_and_after_snapshots_downloaded(review_number, revision_number) == True:
                revision_id = review_number + "_rev" + revision_number

                # only populate the repository if the revision has not been added before
                if not revision_id in revisions_already_in_repo:
                    print("Populating " + revision_id)

                    revision_json = json.load(open("revisions_details/" + PROJECT + "/" + revision_id + ".json"))

                    # collect additional data for the CSV
                    # sometimes the author name has a comma. In these cases the comma is removed
                    author = revision_json["author"]["name"].replace(",","")
                    status = review_json["status"]
                    change_id = review_json["change_id"]
                    revision_url = REVISION_URL % (review_number, revision_number)
                    original_before_commit_id = revision_json["parents"][0]["commit"]
                    original_after_commit_id = revision_json["commit"]

                    # sometimes, revisions might share the same before commit
                    # in these cases, it does not adds the same before commit to the repository, but rather uses the one that have already been added
                    before_commit_id = get_before_commit_already_in_repo(original_before_commit_id, csv)

                    if before_commit_id == "None":
                        before_commit_id = populate_repo_with_revision_snapshot(revision_id, "before")

                    after_commit_id = populate_repo_with_revision_snapshot(revision_id, "after")

                    csv_file.write(revision_id + "," + review_number + "," + revision_number + "," + author + "," + status + "," + change_id + "," + revision_url + "," + original_before_commit_id + "," + original_after_commit_id + "," + before_commit_id + "," + after_commit_id + "\n")

reset_repo()

csv_file.close()

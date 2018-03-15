# by using the data in the several JSON files about each review and revision,
# this script extracts the discussion of each revision and writes it in a separate text file for easy access
# each revision generates a discussion file which contains the description of that revision and the discussion/comments by the developers regarding the revision
# the discussion files are saved in the 'discussion' dir

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

# function to remove the miliseconds from the date
def clean_date(date):
    return date.split(".")[0]

######################### script starts here #################################

# regex object to extract the review number from the review JSON file
rg_id = re.compile("/(\d+)\.json")

config = configparser.ConfigParser()
config.read("Couchbase_settings.ini")
# config.read("Eclipse_settings.ini")

COMMUNITY = config['DETAILS']['community']
PROJECT = config['DETAILS']['project']
PROJECT_REVIEW_JSON = config['DETAILS']['project_review_json']

# create the discussion directory if it does not exist
if os.path.isdir("discussion") == False:
    os.mkdir("discussion")

# create a discussion directory for the project if it does not exist
if os.path.isdir("discussion/" + PROJECT) == False:
    os.mkdir("discussion/" + PROJECT)

# get the reviews's details JSON files for the community sorted in ascending order
review_jsons = sorted(glob.glob("reviews_details/"+ COMMUNITY + "/*.json"), key=compare_review_json)

# we iterate over all review's JSON files, filtering the ones regarding the project of interest
for review_json in review_jsons:
    review_number = rg_id.findall(review_json)[0]

    review_json = json.load(open(review_json))

    # check whether the review JSON is regarding the project
    # if yes, write the discussion for each revision
    if PROJECT_REVIEW_JSON == review_json["project"]:

        # create a directory for the discussion of the review if it does not exist
        if os.path.isdir("discussion/" + PROJECT + "/" + review_number) == False:
            os.mkdir("discussion/" + PROJECT + "/" + review_number)

        # in some cases, a certain comment does not have a revision number attached to it
        # in these cases, the comment is added to the last revision of the review
        last_revision_number = len(review_json["revisions"])

        # iterate over all revisions, sorted by the revision number
        for key, value in sorted(review_json["revisions"].items(), key = lambda revision_item : int(revision_item[1]["_number"])):
            revision_number = str(value["_number"])
            revision_id = review_number + "_rev" + revision_number
            discussion_file_name = "discussion/" + PROJECT + "/" + review_number + "/" + revision_id + "_discussion.txt"

            # write the discussion file for the revision if it does not exist
            if os.path.isfile(discussion_file_name) == False:
                revision_json_file_name = "revisions_details/" + PROJECT + "/" + revision_id + ".json"

                # check if the revision JSON file exists
                if os.path.isfile(revision_json_file_name) == True:
                    print("Writing discussion file for " + PROJECT + " " + revision_id)

                    revision_json = json.load(open(revision_json_file_name))

                    # writes the description of the revision, and later the comments regarding the revision
                    discussion_file = open(discussion_file_name, "w")
                    discussion_file.write("DESCRIPTION\n\n")
                    discussion_file.write(revision_json["message"] + "\n\n")
                    discussion_file.write("COMMENTS\n\n")

                    inline_comments_json_file_name = "inline_comments_details/" + PROJECT + "/" + revision_id + "_inline_comments.json"

                    # check if the inline comments JSON exists
                    if os.path.isfile(inline_comments_json_file_name) == True:
                        # loads the JSON containing the inline comments of the revision
                        inline_comments_json = json.load(open(inline_comments_json_file_name))

                        # in some cases, it's not possible to match an inline comment with a specific comment given the timestamps
                        # in these cases, the inline comments are considered a MISMATCH, and they are added at the end of the discussion file
                        # this list stores the inline comments added to later check the ones that were not matched to any comment
                        inline_comments_added = []

                        for message in review_json["messages"]:
                            # in some cases, the message does not have an author
                            # in these cases, the message is simply written without author information
                            if "author" in message.keys():

                                # sometimes, the comments are not attached to a revision
                                # in these cases, the comment is added to the last revision's discussion
                                if "_revision_number" in message.keys():
                                    # writes in the discussion file only the comments attached to the especific revision
                                    if int(message["_revision_number"]) == int(revision_number):
                                        if "name" in message["author"].keys():
                                            author_name = message["author"]["name"]
                                        else:
                                            author_name = "Anonymous Coward"

                                        discussion_file.write("author: " + author_name + "\n")
                                        discussion_file.write("date: " + message["date"] + "\n\n")
                                        discussion_file.write(message["message"] + "\n\n")

                                        # check if there are inline comments for this revision
                                        # inline comments are linked to comments based on the timestamp
                                        if len(inline_comments_json) > 0:
                                            # remove the miliseconds from the date to allow for better precision
                                            message_date = clean_date(message["date"])

                                            for inline_comment_key, inline_comments in inline_comments_json.items():
                                                for i in range(len(inline_comments)):
                                                    inline_comment = inline_comments[i]

                                                    # remove the miliseconds from the date to allow for better precision
                                                    inline_comment_date = clean_date(inline_comment["updated"])

                                                    # check if the time stamp of the inline comment matches the specific comment
                                                    # if yes, the inline comment is added to the comment
                                                    if message_date == inline_comment_date:
                                                        inline_comments_added.append(inline_comment["id"])

                                                        # some inline comments are intended to the whole file, and do not have the line number
                                                        if ("line" in inline_comment.keys()) == True:
                                                            discussion_file.write("Line:" + str(inline_comment["line"]) + ", " + inline_comment_key + " -> " + inline_comment["message"] + "\n\n")
                                                        else:
                                                            discussion_file.write("File Comment: " + inline_comment_key + " -> " + inline_comment["message"] + "\n\n")

                                        discussion_file.write("-------------------------------------\n")
                                else:
                                    # writes comments without revision number to the last revision
                                    if int(last_revision_number) == int(revision_number):
                                        if "name" in message["author"].keys():
                                            author_name = message["author"]["name"]
                                        else:
                                            author_name = "Anonymous Coward"

                                        discussion_file.write("author: " + author_name + "\n")
                                        discussion_file.write("date: " + message["date"] + "\n\n")
                                        discussion_file.write(message["message"] + "\n\n")
                                        discussion_file.write("-------------------------------------\n")
                            else:
                                # for comments without author, the author is Gerrit Code Review
                                discussion_file.write("author: Gerrit Code Review\n")
                                discussion_file.write("date: " + message["date"] + "\n\n")
                                discussion_file.write(message["message"] + "\n\n")
                                discussion_file.write("-------------------------------------\n")


                        # check if all inline comments for the revision were matched to comments
                        # if not, the ones not matched are added to the end of the discussion file
                        for inline_comment_key, inline_comments in inline_comments_json.items():
                            for i in range(len(inline_comments)):
                                inline_comment = inline_comments[i]
                                
                                if not inline_comment["id"] in inline_comments_added:
                                    if "name" in inline_comment["author"].keys():
                                        author_name = inline_comment["author"]["name"]
                                    else:
                                        author_name = "Anonymous Coward"

                                    discussion_file.write("author: " + author_name + "\n")
                                    discussion_file.write("date: " + inline_comment["updated"] + "\n\n")
                                    discussion_file.write("MISMATCHED INLINE COMMENT\n")

                                    # some inline comments are intended to the whole file, and do not have the line number
                                    if ("line" in inline_comment.keys()) == True:
                                        discussion_file.write("Line:" + str(inline_comment["line"]) + ", " + inline_comment_key + " -> " + inline_comment["message"] + "\n\n")
                                    else:
                                        discussion_file.write("File Comment: " + inline_comment_key + " -> " + inline_comment["message"] + "\n\n")

                                    discussion_file.write("-------------------------------------\n")

                        discussion_file.close()

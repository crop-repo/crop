# this script downloads the JSON files containing the details of every review in a certain community
# the reviews JSON files are saved in the 'reviews_details' dir

import configparser
import os
import socket
from urllib.request import *

socket.setdefaulttimeout(50)
config = configparser.ConfigParser()
config.read("Eclipse_settings.ini")

COMMUNITY = config['DETAILS']['community']
REVIEW_URL = config['DETAILS']['review_json_url']
START_INDEX = int(config['DETAILS']['start_index'])
END_INDEX = int(config['DETAILS']['end_index']) + 1

# create the reviews_details directory if it does not exist
if os.path.isdir("reviews_details") == False:
    os.mkdir("reviews_details")

# create the directory to store the reviews details for the community if it does not exist
if os.path.isdir("reviews_details/" + COMMUNITY) == False:
    os.mkdir("reviews_details/" + COMMUNITY)

for i in range(START_INDEX, END_INDEX):
    file_name = "reviews_details/" + COMMUNITY + "/%s.json" % i

    # if JSON file is already downloaded, skip to next review
    if os.path.isfile(file_name):
        continue

    review_url = REVIEW_URL % i

    # if any error in downloading the JSON, skip to next review
    try:
        print("Downloading JSON for review " + str(i) + " from " + COMMUNITY)
        resp = urlopen(review_url)
    except:
        continue

    json = open(file_name, "w")
    content = resp.read().decode("utf-8", errors="ignore")

    # JSONs returned by the Gerrit API usually have a non-standard starting line that needs to be filtered
    if content.startswith(")]}'"):
        content = "\n".join(content.split("\n")[1:])

    json.write(content)
    json.close()

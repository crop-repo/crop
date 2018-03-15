# Code Review Open Platform

----
This repository contain the scripts necessary to replicate the CROP dataset as described in the paper entitled "CROP: Linking Code Reviews to Source Code Changes" published on the 2018th edition of the Working Workshop on Mining Software Repositories ([MSR'18](https://conf.researchr.org/home/msr-2018))

----
## Usage

The scripts are written in python3 and need to be executed sequentially in the order they are numbered. All scripts are commented, so for more details of usage please check the code for each file.

The `settings.ini` files are used to configure the scripts for which project the script will be executed. These are the scripts:

1. Reviews' Details Crawler:

> This script downloads the JSON files containing the details of every review in a certain community (Eclipse or Couchbase). The reviews JSON files are saved in the `reviews_details` dir.

2. Revisions' Details Crawler:

> This script downloads the JSON files containing the details of every revision for the project specified in the settings. The revision JSON files are saved in the `revisions_details` dir.

3. Inline Comments Crawler:

> This script downloads the JSON files containing the inline comments of every revision for the project specified in the settings. The inline comments JSON files are saved in the `inline_comments_details` dir.

4. Snapshots Crawler:

> This script downloads the before and after snapshots of every revision for the project specified in the settings. The snapshots are saved in the `snapshots` dir.

5. Discussion Writer:

> By using the data in the several JSON files about each review and revision, this script extracts the discussion of each revision and writes it in a separate text file for easy access. Each revision generates a discussion file which contains the description of that revision and the discussion/comments by the developers regarding the revision. The discussion files are saved in the `discussion` dir.

6. Git Repo Populator:

> This script creates a git repository for the project specified in the settings. It automatically extracts and commit each snapshot in sequential order to the new git repository. The new git repository is located in the `git_repos` dir.<br><br>
In addition, the script creates a CSV file to store important data about each revision in a easily accessible way. In the CSV, each line represents a single revision, and the following information is saved in each column:<br><br>
**id**: an unique id to identify the revision within an specific community<br>
**review_number**: the unique review number in which the revision is part of

> **revision_number**: the number of the revision in the specific review

> **author**: the author of the revision

> **status**: the status of the revision

> **change_id**: the change id of this revision

> **url**: the URL in which one can access the web view of the revision

> **original\_before\_commit_id**: the commit id listed by gerrit as the version of the system before the revision took place

> **original\_after\_commit_id**: the commit id listed by gerrit as the version of the system after the revision took place

> **before\_commit\_id**: the commit id that represents the version of the system before the revision took place in the new git repository that was created by this script

> **after\_commit\_id**: the commit id that represents the version of the system after the revision took place in the new git repository that was created by this script

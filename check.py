#!/usr/bin/env python

import logging
import os
import pygit2
import sys

AUDIT_OK = 0
AUDIT_FAILED = 1
ERROR = 2

issues = {}

def record_issue(issue, more_data):
    if issue in issues:
        if more_data not in issues[issue]:
            issues[issue].append(more_data)
    else:
        issues[issue] = [more_data]

def check_can_merge_to_this_branch(email):
    pass

def track_back_to_parents(this_commit, excluded_author, all_baselines, depth = 1):
    logging.debug("Checking feature branch %s by %s"%(this_commit.id, this_commit.author.email))
    if depth > 20:
        logging.info("Max depth exceeded while looking for the parents of %r"%this_commit)
        sys.exit(ERROR)
    logging.debug("Looking for parents of %r"%this_commit.message)
    if this_commit.id in all_baselines:
        logging.debug("Tracked back to base, nothing futher to do")
        return None
    if this_commit.author.email == excluded_author:
        logging.info("This feature branch contains commit %s, authored by %s, who performed the merge. (%s)"%(this_commit.id, this_commit.author.email, excluded_author))
        record_issue("Feature branch merged by one of its contributors", this_commit.id)
        return None
    for p in this_commit.parents:
        return track_back_to_parents(p, excluded_author, all_baselines, depth + 1)

def print_commit(commit):
    return "%s %s"%(commit.id, commit.message)

def find_baselines(commit):
    """ Finds all the previous revisions of the branch this commit is now the head of."""
    baselines = []
    while True:
        if len(commit.parents) > 1:
            baselines.append(commit.id)
            commit = commit.parents[0]
        elif len(commit.parents) == 0:
            logging.debug("Reached the end of the branch")
            return baselines
        else:
            record_issue("Non-merge commit on trunk", commit.id)
            baselines.append(commit.id)
            commit = commit.parents[0]

def main():
    if len(sys.argv) < 2:
        print("Usage: check.py <git directory>")
        sys.exit(ERROR)
    gitdir = sys.argv[1]
    if not os.path.isdir(gitdir):
        logging.error("%s is not a directory"%gitdir)
        sys.exit(ERROR)
    try:
        repo = pygit2.Repository(gitdir)
        head = repo.head

        # Is it a merge commit? Can we get the parents?
        commit = head.peel(pygit2.Commit)

        all_baselines = find_baselines(commit)

        while True:
            merge_author = commit.author.email
            parents = commit.parents

            if len(parents)==0:
                # We've reached the end of the repository
                break

            if len(parents)<2:
                record_issue("Non-merge commit on trunk", commit.id)
                commit = parents[0]
                continue

            check_can_merge_to_this_branch(merge_author)

            # ASSUME (!) the first parent was the previous position of the branch...
            feature_branches = parents[1:]
            logging.debug("Base of this merge is %s"%(parents[0].id))
            for p in feature_branches:
                ident = track_back_to_parents(p, merge_author, all_baselines)
            commit = parents[0]
    except None as e:
        print(e)
        sys.exit(ERROR)
    print("Analysis complete.")
    if len(issues.items()) == 0:
        print "No issues found in repository."
        sys.exit(AUDIT_OK)
    else:
        print("Issues found in git repository: ")
        for (k,v) in issues.items():
            if len(v) <= 5:
                print("  %s (%d counts)"%(k,len(v)))
                for note in v:
                    print("    %s"%note)
            else:
                print("  %s (%d counts, not listed)"%(k,len(v)))
        sys.exit(AUDIT_FAILED)


if __name__=="__main__": main()

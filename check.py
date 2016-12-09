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


def track_back_to_parents(this_commit, excluded_author,
                          all_baselines, depth=1):
    logging.debug("Checking feature branch %s by %s" % (
        this_commit.id,
        this_commit.author.email))
    if depth > 20:
        logging.info("Max depth exceeded while looking for the parents of %r" %
                     this_commit)
        sys.exit(ERROR)
    logging.debug("Looking for parents of %r" % this_commit.message)
    if this_commit.id in all_baselines:
        logging.debug("Tracked back to base; nothing futher to do")
        return None
    if this_commit.author.email == excluded_author:
        logging.info("This feature branch contains commit %s, authored by " +
                     " %s, who performed the merge." %
                     (this_commit.id, this_commit.author.email))
        record_issue("Feature branch merged by one of its contributors",
                     this_commit.id)
        return None
    for p in this_commit.parents:
        return track_back_to_parents(p, excluded_author, all_baselines,
                                     depth + 1)


def print_commit(commit):
    return "%s %s" % (commit.id, commit.message)


def find_baselines(commit):
    """ Finds all the previous revisions of the branch this
    commit is now the head of. """
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


def check_merges_by_branch_authors(repo):
    head = repo.head

    # Is it a merge commit? Can we get the parents?
    commit = head.peel(pygit2.Commit)

    all_baselines = find_baselines(commit)

    while True:
        merge_author = commit.author.email
        parents = commit.parents

        if len(parents) == 0:
            # We've reached the end of the repository
            break

        if len(parents) < 2:
            record_issue("Non-merge commit on trunk", commit.id)
            commit = parents[0]
            continue

        check_can_merge_to_this_branch(merge_author)

        # ASSUME (!) the first parent was the previous
        # position of the branch...
        feature_branches = parents[1:]
        logging.debug("Base of this merge is %s" % (parents[0].id))
        for p in feature_branches:
            ident = track_back_to_parents(p, merge_author, all_baselines)
        commit = parents[0]


def check_merge_permissions(repo):
    """ Checks the ROLES file exists and then uses it to validate all commits to
    a particular branch (only "master" at the moment) """

    # TODO: this isn't correct yet. You need to get the ROLES file *for
    # the previous revision* and use that to validate the current merge.

    commit = repo.head.peel(pygit2.Commit)
    try:
        permissions_file_id = commit.tree['ROLES'].id
    except KeyError:
        record_issue("Repository has no ROLES file", None)
        return
    permissions_file = repo[permissions_file_id]
    perms = permissions_file.data.split("\n")
    mergers = {}
    checked_branch = "master"
    for l in perms:
        if l == "":
            continue
        fields = l.strip().split(":")
        branch = fields[0]
        users = fields[1].split(",")
        mergers[branch] = users
        logging.info("Users %s are allowed to merge to %s" % (users, branch))

    all_baselines = find_baselines(commit)
    for b in all_baselines:
        commit = repo.get(b)
        if commit.author.email not in mergers[checked_branch]:
            record_issue("Unauthorised user committed to branch",
                         "%s committed to %s at %s" %
                         (commit.author.email, checked_branch, b))
        else:
            logging.info("Commit by %s to %s" %
                         (checked_branch, commit.author.email))


def main():
    if len(sys.argv) < 2:
        print("Usage: check.py <git directory>")
        sys.exit(ERROR)
    gitdir = sys.argv[1]
    if not os.path.isdir(gitdir):
        logging.error("%s is not a directory" % gitdir)
        sys.exit(ERROR)

    try:
        repo = pygit2.Repository(gitdir)
    except Exception as e:
        logging.error("Failed to open git repository %s: %r" % (gitdir, e))
        sys.exit(ERROR)

    check_merges_by_branch_authors(repo)
    check_merge_permissions(repo)

    print("Analysis complete.")
    if len(issues.items()) == 0:
        print "No issues found in repository."
        sys.exit(AUDIT_OK)
    else:
        print("Issues found in git repository: ")
        for (k, v) in issues.items():
            if len(v) <= 5:
                print("  %s (%d count%s)" % (k, len(v),
                                             's' if len(v) != 1 else ''))
                for note in v:
                    if note is not None:
                        print("    %s" % note)
            else:
                print("  %s (%d counts, not listed)" % (k, len(v)))
        sys.exit(AUDIT_FAILED)


if __name__ == "__main__":
    main()

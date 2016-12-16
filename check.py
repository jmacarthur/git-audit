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
        logging.info(("This feature branch contains commit %s, authored by " +
                      " %s, who performed the merge.") %
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


def get_mergers_for_commit(repo, commit_id):
    """ This reads the ROLES file at the time of a given commit and returns a
        list of the people allowed to merge each branch. The return value is a
        dictionary whose keys are branch names and values are lists of email
        addresses. """
    commit = repo[commit_id]
    try:
        permissions_file_id = commit.tree['ROLES'].id
    except KeyError:
        record_issue("Repository has no ROLES file", None)
        return {}
    permissions_file = repo[permissions_file_id]
    perms = permissions_file.data.split("\n")
    mergers = {}
    for l in perms:
        if l == "":
            continue
        fields = l.strip().split(":")
        branch = fields[0]
        users = fields[1].split(",")
        if users is not None:
            mergers[branch] = users
        logging.info("Users %s are allowed to merge to %s" % (users, branch))
    return mergers


def check_merge_permissions(repo):
    """ Checks the ROLES file for each baseline - at the time of the previous
        baseline - allows that merge. """

    head_commit = repo.head.peel(pygit2.Commit)
    all_baselines = find_baselines(head_commit)
    checked_branch = "master"

    # This requires that baselines are in order (most recent to oldest)
    for baseline_no in range(0, len(all_baselines)-1):
        b = all_baselines[baseline_no]
        rules_baseline = all_baselines[baseline_no+1]
        mergers = get_mergers_for_commit(repo, rules_baseline)
        if checked_branch not in mergers:
            # If there are no rules for a branch, that's considered
            # OK, so there's nothing to check at this point (although
            # this might warrant a low-level warning)
            continue
        commit = repo.get(b)
        mergers_for_branch = mergers[checked_branch]
        if commit.author.email not in mergers_for_branch:
            record_issue("Unauthorised user committed to branch",
                         "%s committed to %s at %s" %
                         (commit.author.email, checked_branch, b))
        else:
            logging.info("Commit by %s to %s" %
                         (checked_branch, commit.author.email))


def plural(n):
    return 's' if len(n) != 1 else ''


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
        print ("No issues found in repository.")
        sys.exit(AUDIT_OK)
    else:
        print ("Issues found in git repository: ")
        for (k, v) in issues.items():
            if len(v) <= 5:
                print("  %s (%d count%s)" % (k, len(v), plural(v)))
                for note in v:
                    if note is not None:
                        print("    %s" % note)
            else:
                print("  %s (%d counts, not listed)" % (k, len(v)))
        sys.exit(AUDIT_FAILED)


if __name__ == "__main__":
    main()

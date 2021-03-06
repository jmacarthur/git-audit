# git-audit

Experimental scripts to check good development practices in git repositories.

Many development teams work with some disciplines, for example:

* Only allowing a subset of the developers to merge branches to the production branch
* Not allowing a person to merge a feature branch if they have contributed patches to that branch.

Many source code management systems, such as GitHub, GitLab and Bitbucket, can implement such rules. However, when a project moves from one host to another, the metadata about who can contribute doesn't move with the repository. You will probably need to set up the same users and roles on the new host. Even if you stay on one host, you must trust that host to do the checks. If you have to give evidence to a third party that you have carried out good development practice, you may have to simply say that you trusted your host to perform the necessary checks at that point in time.

This repository will provide '''git-audit''' which will check existing repositories are compliant with good development practices. The first stage is to check existing git repositories for the separation of committer and devleoper. This can be done with the metadata already in most git repositories. It can provide basic evidence that such practices have been followed, and if the repo uses GPG signing, it can provide much stronger confidence. This is an after-the-fact check; it will not prevent people from breaking good practice in the first place, but it will report when they have been broken in the past. In the future, we may add pre-commit hooks to warn users before they break rules.

# Usage

At the moment, there is no installer, so just run the 'check' script directly:

    ./check.py <git dir>

You can run this on its own git repository with `./check .`. This will report many problems! This tool does not consider its own repository trustworthy, but it gives us some information we could use to try and improve it.

You can also try cloning https://gitlab.com/trustable/git-audit-example.git and running check.py against that. That repository contains some GPG-signed commits. Unfortunately, at the time of writing, the pygit2 library which we use can't verify GPG-signed commits.

# Example output

    Analysis complete.
    Issues found in git repository:
      Feature branch merged by one of its contributors (1 count)
        e717c8c7de6974a810d69a29b50cfdf68edbb28f
      Repository has no ROLES file (1 count)
      Non-merge commit on trunk (247 counts, not listed)

# Future improvements:

* Checking for more development practices
* User and role information in an existing database, such as LDAP. We know several people will use these roles already, and many source code management tools (e.g. Bitbucket) can use these sources to control access.
* Advisory pre-commit hooks which implement the same rules, to reduce mistakes made development

# Similar existing systems:

* Gerrit allows you to store Prolog rules in the repository which affect how gerrit handles submissions. These can be used to restrict changes to specific branches to specific users, but it isn't clear whether they can take into account features branches with multiple authors. All the examples seem to be based on the single submitter of a patch, rather than the authors of commits.
* Patch tracking in git is another aspect of trustable software. The authors of gitorious have suggested this at https://www.gitano.org.uk/ideas/git-pull-request/ and have some good requirements set out. Git-candidate is one attempt to store patch tracking information in git: http://git.661346.n2.nabble.com/PATCH-0-2-git-candidate-git-based-patch-tracking-and-review-td7642808.html

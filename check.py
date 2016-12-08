#!/usr/bin/env python

import os
import pygit2
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: check.py <git directory>")
        sys.exit(1)
    gitdir = sys.argv[1]
    if not os.path.isdir(gitdir):
        print("%s is not a directory"%gitdir)
        sys.exit(1)
    try:
        repo = pygit2.Repository(gitdir)
        print(repo.head.hex)
    except Exception as e:
        pass
    
        
if __name__=="__main__": main()

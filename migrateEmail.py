#!/bin/python3

# generic include function
import os
import sys

import xmatters

# Part 1: verify there's a file to be imported - need exactly 1 argument, and a valid, non zero file.
if len(sys.argv) <= 3:
    print ("Usage: ", sys.argv[0], "<fromdomain> <todomain> [special]")
    quit()

# Get the accounts to migrate
users =  xmatters.userList( sys.argv[1])

for user in users:
    newEmail = users[user].split('@')[0]
    if sys.argv[3] ==  'nounderscore':
        newEmail = newEmail.replace('_', '')
    newEmail = newEmail + '@' + sys.argv[2]

    #print ( user + ": " +users[user] + " -> " + newEmail )
    xmatters.updateEmail ( user, newEmail )

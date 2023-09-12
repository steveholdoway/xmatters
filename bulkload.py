#!/bin/python3

# generic include function
import os
import sys

import xmatters
import csv_reader

# Part 1: verify there's a file to be imported - need exactly 1 argument, and a valid, non zero file.
if len(sys.argv) != 2:
    print ("Usage: ", sys.argv[0], "<input>.csv")
    quit()

infile = sys.argv[1].strip()
if not os.path.isfile(infile):
    print (sys.argv[0], infile, "does not exist")
    quit()

additions = csv_reader.grab ( infile )

#Loop through creating ( in order ) Sites, Groups, People
# Well, I may later, let's just get it working...

# Variable for the created objects
created = {
    "Sites" : [],
    "Groups" : [],
    "People" : {},
    "Supervisors" : {},
}

# check to see what my ID is. It's easy if we've created a group...
MyID = ''

# 1. Sites
checkSites =  xmatters.currentSites()
site_fields = [a['value'] for a in additions if a['key'] == 'SiteFields']
if len(site_fields) > 0:
    nameOffset = xmatters.getOffset ( "name", site_fields )

    sites = [a['value'] for a in additions if a['key'] == 'Site']
    for site in sites:

        if site[nameOffset] in checkSites:
            print ( "Add site: '" + site[nameOffset] + "' already exists" )
        else:
            data =  xmatters.createData ( site_fields[0], site )
            site_id = xmatters.writeAPI ( '/sites',  xmatters.createData ( site_fields[0], site ) )
            if site_id is None:
                print ( "Add site: '" + site[nameOffset] + "' was not created")
            else:
                print ( "Add site: '" + site[nameOffset] + "' created" )
                #print ( "Add site: '" + site[nameOffset] + "' created with ID " + site_id )
                created["Sites"].append ( { site[nameOffset], site_id } )
                checkSites[site[nameOffset]] = site_id
#               Create a default group with the same name as the site - so we can put everyone in it regardless
                #xmatters.addGroup ( site[nameOffset], site_id )
# ^ been disabled for now
#   CheckSites now also contains the new sites along with their GUID in case we need them later

# 2. Groups
#for checkSite in checkSites:
    #print ( checkSite )
checkGroups =  xmatters.currentGroups()
group_fields = [a['value'] for a in additions if a['key'] == 'GroupFields']
if len(group_fields) > 0:
    groupOffset = xmatters.getOffset ( "targetName", group_fields )
    siteOffset = xmatters.getOffset ( "siteName", group_fields )

    groups = [a['value'] for a in additions if a['key'] == 'Group']
#   Check group doesn't exist already
    for group in groups:
#       Check site exists
        if group[siteOffset] not in checkSites:
            print ( "Add group: Can't add Group '" + group[groupOffset] + "' as the site '" + group[siteOffset] + "' does not exist" )
        else:
            if group[groupOffset] in checkGroups:
                print ( "Add group: '" + group[groupOffset] + "' already exists" )
            else:
                siteID = checkSites[group[siteOffset]]
                groupID = xmatters.addGroup ( group[groupOffset], siteID );
                print ( "Add group: '" + group[groupOffset] + "' added to site '" + group[siteOffset] + "'" )
                #print ( "Add group: '" + group[groupOffset] + "' added to site '" + group[siteOffset] + "' with ID " + groupID )
                checkGroups[group[groupOffset]] = groupID
                created["Groups"].append ( groupID )
                if MyID == '':
                    MyID = xmatters.getMyIDByGroup ( groupID )

# 3. People
# It seems that the standard here is to use email address as identifier.
people_fields = [a['value'] for a in additions if a['key'] == 'PeopleFields']
if len(people_fields) > 0:
    checkGroups =  xmatters.currentGroups()

    siteOffset = xmatters.getOffset ( "site", people_fields )
    groupOffset = xmatters.getOffset ( "group", people_fields )
    firstOffset = xmatters.getOffset ( "firstName", people_fields )
    lastOffset = xmatters.getOffset ( "lastName", people_fields )
    personOffset = xmatters.getOffset ( "targetName", people_fields )
    supervisorOffset = xmatters.getOffset ( "supervisor", people_fields )
    currentPeople =  xmatters.readAPI ( '/people', 'targetName' )
    #for currentPerson in currentPeople:
        #print ( currentPerson )
    #exit()

    checkPeople = {}
    for x in currentPeople:
        checkPeople[x['key']] = [x['value']['firstName'], x['value']['lastName'], x['value']['site']['name'], x['value']['site']['id']]

    #for checkPerson in checkPeople:
        #print ( checkPerson, checkPeople[checkPerson] )

    people = [a['value'] for a in additions if a['key'] == 'People']
    for person in people:
        if person[personOffset] in checkPeople:
            print ( "Add person: '" + person[firstOffset] + " " + person[lastOffset] + "' already exists" )
        if person[siteOffset] in checkSites:
            siteID = checkSites[person[siteOffset]]
            groupID = checkGroups[person[groupOffset]]
            personID = xmatters.addPerson ( siteID, groupID, dict(zip ( people_fields[0], person )) )
            print ( "Added person: '" + person[firstOffset] + " " + person[lastOffset] + "' to group " + person[groupOffset] )
            if not groupID in created["People"]:
                created["People"][groupID] = [personID]
            else:
                created["People"][groupID].append ( personID )
            if MyID == '':
                MyID = xmatters.getMyIDByPerson ( personID )
            if person[supervisorOffset].lower() == "yes":
                xmatters.addGroupSupervisor(personID)
                print ( "  Added supervisor role to '" + person[firstOffset] + " " + person[lastOffset] + "'" )
                if not groupID in created["Supervisors"]:
                    created["Supervisors"][groupID] = [personID]
                else:
                    created["Supervisors"][groupID].append ( personID )
        else:
            print ( "Add person: '" + person[firstOffset] + " " + person[lastOffset] + "' does not exist" )


# For any users that have been created:
# - If no supervisors in the group, remove the API Id
# - ditto if they are a supervisor
# - if there are supervisors for the group, then add them, and remove the API Id.
print ( "Setting up supervisors if necessary" )
if len(created['People']) > 0:
    for group in created['People']:
        if group in created['Supervisors']:
            #print ( 'we have a match' )
            for person in created['People'][group]:
                if person in created['Supervisors'][group]:
                    #print ( person, " is a super" )
                    xmatters.removeSupersFromPerson ( person, MyID )
                else:
                    #print ( person, " needs supers adding")
                    xmatters.addSupersToPerson ( person, created['Supervisors'][group], MyID )
                    #print ( person, created['Supervisors'][group], MyID )
        #else:
            #print ( group, "has no supervisors" )


# Same for the groups
if len(created['Groups']) > 0:
    for group in created['Groups']:
        if group in created['Supervisors']:
            #print ( 'we have a group match' )
            #print ( group, created['Supervisors'][group], MyID )
            xmatters.addSupersToGroup ( group, created['Supervisors'][group], MyID )
#           Just remembered, they won't let you have a group without a super...
        #else:
            #xmatters.removeSupersFromGroup ( group, MyID )

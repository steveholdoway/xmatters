############################
#settings
############################

group = 'Daily + Off Hours'             #set to group that needs to be modified

############
#imports
############

import time
import requests
from requests.auth import HTTPBasicAuth
import json

# finds the offset of a string value in a list, ignoring case
def getOffset ( field, values ):

    lower = []
    for a in values[0]:
        lower.append ( a.lower() )

    return lower.index( field.lower() )

def createData ( keys, vals ):
    # Ensure lcase
    # except of course it's case sensitive, and the site endpoint only used lcase... grr
    #keys = [row.lower() for row in keys]
    datadict = list(zip(keys, vals))
    data = {}
    for key, val in zip(keys, vals):
        data[key] = val
    #print ( data )
    return json.dumps(data)

def prepareAPI ( URL ):
    settings = json.load(open('auth.json')) #if auth.json doesn't exist, copy auth.json.sample
    base_URL = 'https://'+settings['instance']+'/api/xm/1' 
    auth = HTTPBasicAuth(settings['username'], settings['password'])
    headers = {'Content-Type': 'application/json'}

    endpoint_URL = URL
    url = base_URL + endpoint_URL 

    return url, headers, auth

def readAPI ( URL, Key ):

    url, headers, auth = prepareAPI ( URL )
#   Kludge for now.
    url = url + '?offset=0&limit=1000'
    datadict = []
    response = requests.get(url, auth=auth)

    if (response.status_code == 200):
    
        for row in response.json()['data']:
            datadict.append ({'key' : row[Key], 'value': row})

    return datadict

def writeAPI ( URL, data ):
    url, headers, auth = prepareAPI ( URL )
    response = requests.post(url, headers=headers, data=data, auth=auth)

    #print ( response.json() )
    if (response.status_code == 201 or response.status_code == 200):
        return response.json().get('id')
    else:
        print ("Write failed: " + str(response.status_code) + ":" + str(response.json()) )
        #print ("Write failed: " + str(response.status_code) )


def addGroup ( targetName, site_id ):

    defKeys = [
        'targetName',
        'recipientType',
        'status',
        'allowDuplicates',
        'useDefaultDevices',
        'observedByAll',
        'description',
        'site',
    ]

    defVals = [
        'GROUP',
        'ACTIVE',
        True,
        True,
        True,
    ]

    defVals.insert (0, targetName)
    defVals.append (targetName)
    defVals.append (site_id)
    group_id = writeAPI ( '/groups',  createData ( defKeys, defVals ) )
    # Can't create with a blank supervisor unfortunately. will need to work something out...
    print ( targetName, "created with ID ", group_id )
    return ( group_id )

def addPerson ( siteID, groupID, person ):
    
    defaults = {
        'firstName' : '',
        'lastName' : '',
        'licenseType' : 'FULL_USER',
        'roles' : ['Standard User'],
        'site' : "",
        'status' : "ACTIVE",
        'targetName': '',
        #'supervisors': [],
    }

    #print ( siteID, groupID, person,  defaults )
    for val in person:
        if val in defaults:
            defaults[val] = person[val]
#   cludge roles array
    if isinstance ( defaults['roles'], str):
        defaults['roles'] =  ['Standard User']
    defaults['site'] = siteID
    #print ( defaults )
    #print ( defaults['targetName'] )
#   check if the targetname exists. If it does, we just need to configure an existing person, not create.
    url, headers, auth = prepareAPI ( '/people/' + defaults['targetName'] )
    response = requests.get(url, auth=auth)

    if (response.status_code == 200):
        personID = response.json()['id']
    else:
        personID = writeAPI ( '/people',  json.dumps(defaults) )
    #print ( "User ", defaults['targetName'], "created with ID ", personID )
#   Add the extra fields as devices.
    addDeviceToPerson ( personID, person )
#   Add the persone to a group
    addPersonToGroup ( groupID, personID )
#   Process if a non-SSO login
    setNonSSO ( personID, person )
    return ( personID )

# Required
#   deviceType - EMAIL, VOICE, TEXT_PHONE, TEXT_PAGER, FAX(!), VOICE_IVR, GENERIC
#   name - Work Phone, Home Phone, Mobile Phone, Home Email, Work Email, SMS Phone, Pager, Fax
#   owner - GUID
#   privileged = T = all users can see, F = redacted
#   If there's more than one device, add in a default 5 minute delay.
def addDeviceToPerson ( personID, person ):
    emails = {'Work Email', 'Home Email' }
    phones = {'SMS Phone', 'Work Phone', 'Mobile Phone'}

    emaillist = { key:person[key] for key in person if key in emails and person[key].strip() != '' }
    phonelist = { key:person[key] for key in person if key in phones and person[key].strip() != '' }

    #print ( "ADTP email: ", emaillist )
 
    addDelay = False
    if len(emaillist) > 0:
        addEmailsToPerson ( personID, emaillist )
    if len(phonelist) > 0:
        addPhonesToPerson ( personID, phonelist )
    #print ( "ADTP: ", personID, person )

def modifyPerson ( personID, field ):

    if field == "SSO":
        data = {
            "id": personID,
            "password": "ChangeM3",
            "forcePasswordReset": True,
            #"externallyOwned": True,
            }
        personID = writeAPI ( '/people',  json.dumps(data) )
        addRole ( personID, "SSO Bypass" )

def setNonSSO ( personID, person ):

    SSO = { key:person[key] for key in person if key.lower() == "sso" and person[key].strip() != '' }

    if len(SSO) > 0 and SSO['sso'] == "no":
        modifyPerson ( personID, "SSO" )

def addEmailsToPerson ( personID, person ):

    data = {
        "deviceType": "EMAIL",
        "owner": personID,
        "delay": 5,
        "privileged": False,
        }

    for key, val in person.items():
        data["name"] = key
        data["description"] = val
        data["emailAddress"] = val
        group_id = writeAPI ( '/devices',  json.dumps(data) )
        #print ( "added email ", val )

def addPhonesToPerson ( personID, person ):

    data = {
        "owner": personID,
        "privileged": False,
        "delay": 5,
        }

    for key, val in person.items():
        data["deviceType"] = "VOICE"
        data["name"] = key
        data["description"] = val
        data["phoneNumber"] = val.replace ( " ", "" )
        group_id = writeAPI ( '/devices',  json.dumps(data) )
        data["deviceType"] = "TEXT_PHONE"
        group_id = writeAPI ( '/devices',  json.dumps(data) )
        #print ( "added phone ", val )

def addPersonToGroup ( groupID, personID ):
    data = {
        'id' : personID,
        'recipientType' : 'PERSON' 
    }
    #print ( groupID[0] )
    group_id = writeAPI ( '/groups/' + groupID + '/members',  json.dumps ( data ) )

def addGroupSupervisor ( personID ):
#   We reall need a bit of error handling here (:
#   Support user required to view reports. Maybe everywhere?
    #return addRole ( personID, "Group Supervisor" )
    #addRole ( personID, "Group Supervisor" )
    addRole ( personID, "Support User" )

def addRole ( personID, Role ):
    # get current config, including roles
    url, headers, auth = prepareAPI ( "/people/" + personID + "?embed=roles" )
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        person = response.json()
        roles = person['roles']
        #print ( roles )
        url, headers, auth = prepareAPI ( "/roles?name=" + Role )
        response = requests.get(url, auth=auth)
        if response.status_code == 200:
            newRoles = response.json()
            for newRole in newRoles['data']:
                roles['data'].append(newRole)
            #print ( roles )
            update = {}
            update['id'] = personID
            update['roles'] = []
            for role in roles["data"]:
                update['roles'].append (role["name"])
#           dedup if necessary
            update["roles"] = list(dict.fromkeys(update["roles"]))
            #print ( update )
            result = writeAPI ( "/people", json.dumps ( update ) )

def currentSites ():
    sites =  readAPI ( '/sites', 'name' )
    currentSites = {}
    for site in sites:
        currentSites[site['key']] = site['value']['id']
    return currentSites

def currentGroups ():
    groups =  readAPI ( '/groups', 'targetName' )
    currentGroups = {}
    for group in groups:
        currentGroups[group['key']] = group['value']['id']
    return currentGroups

def userList (domain):
    #url, headers, auth = prepareAPI ( '/people/?search=' + domain + '&operand=AND&fields=EMAIL_ADDRESS' )
    url, headers, auth = prepareAPI ( '/people/?search=@' + domain + '&operand=AND&fields=WEB_LOGIN')
    response = requests.get(url, auth=auth)

    logins = {}
    #print ( response.json() )
    if (response.status_code == 200):
        if response.json()['count'] > 0:
            for account in response.json()['data']:
                logins [account['id']] = account['webLogin'] 
    return logins

def getMyIDByGroup ( GroupID ):
    return getMyID( 'groups', GroupID )

def getMyIDByPerson ( PersonID ):
    return getMyID( 'people', PersonID )

def getMyID ( Source, ID ):
    #print ( Source, ID )
    url, headers, auth = prepareAPI ( '/' + Source + '/' + ID  + '?embed=supervisors')
    response = requests.get(url, auth=auth)

    if (response.status_code == 200):
        if response.json()['supervisors']['count'] == 1:
            return ( response.json()['supervisors']['data'][0]['id'] )

def addSupersToGroup ( personID, groupIDs, apiID ):
    return updateSupers ( personID, groupIDs, apiID, "groups" )

def removeSupersFromGroup ( personID, apiID ):
    return updateSupers ( personID, list(), apiID, 'groups' )

def addSupersToPerson ( personID, groupIDs, apiID ):
    return updateSupers ( personID, groupIDs, apiID, "people" )

def removeSupersFromPerson ( personID, apiID ):
    return updateSupers ( personID, list(), apiID, 'people' )

def updateSupers ( personID, groupIDs, apiID, Object ):
    # get current config, including supervisors
    url, headers, auth = prepareAPI ( "/" + Object + "/" + personID + "?embed=supervisors" )
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        person = response.json()
        supers = person['supervisors']

        new = groupIDs
        for currentSupers in supers['data']:
            if currentSupers['id'] != apiID:
                new.append(currentSupers['id'])
        
        update = {}
        update['id'] = personID
        update['supervisors'] = new
#       dedup if necessary
        update["supervisors"] = list(dict.fromkeys(update["supervisors"]))
        #print ( update )
        result = writeAPI ( "/" + Object, json.dumps ( update ) )

def updateEmail ( account, address ):
    # needs to be updated at the targetName and webLogin fields.
    data = {
        "id": account,
        "webLogin": address,
        "targetName": address,
    }

    print ( account, address )
    print ( data )
    writeAPI ( "/people", json.dumps(data) )

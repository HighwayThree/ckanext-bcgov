'''
Imports user information (User name, user organization)
'''

import cx_Oracle

import pprint
import json
import os
import urllib2
import urllib
import getpass

from ckanext.edc_schema.commands.base import (get_organization_id, get_import_params)
user_filename = './data/odsi_users.json' 

def get_connection():
    print '\nPlease enter connection parameters (If connection uses a service name, leave SID empty).'
    print '-----------------------------------------------------------------------------------------'
    
    service_name = None
    
    host = raw_input("Server name : ")
    port = raw_input("Port : ")
    SID = raw_input("SID : ")
    if not SID :
        service_name = raw_input("Service name : ")
    user_name = raw_input("User name : ")
    password = getpass.getpass("Password: ")

    if service_name :
        connection_str = user_name + '/' + password + '@' + host + '/' + service_name
        
        #connection_str = "proxy_metastar/h0tsh0t@slkux1.env.gov.bc.ca/idwprod1.bcgov"
        con = cx_Oracle.connect(connection_str)
    else :
        dsn_tns = cx_Oracle.makedsn(host, port, SID)    
        con = cx_Oracle.connect(user_name, password, dsn_tns)
                
    return con

def execute_user_query(con):
    '''
    Runs the query to fetch all users from odsi database
    '''
    
    user_query = "SELECT s.userid " + \
                 ",org.CREATOR_ORGANIZATION " + \
                 ",sub.sub_organization " + \
                 ",to_char(p.effective_date,'YYYY-MM-DD') " +\
                 ",to_char(p.expiry_date,'YYYY-MM-DD') " + \
                 "FROM app_dw.DW_RESOURCES r, " + \
                 "app_dw.DW_SUBJECTS s, " + \
                 "app_dw.DW_POLICIES p, " + \
                 "app_dw.DW_ACTIONS a, " + \
                 "APP_DATABC.DBC_CREATOR_ORGANIZATIONS org, " + \
                 "app_databc.DBC_SUB_ORGANIZATIONS sub " + \
                 "WHERE a.action = 'ODSI_Author' " + \
                 "AND s.subject_id = p.subject_id " + \
                 "AND r.resource_id = p.resource_id " + \
                 "AND p.action_id = a.action_id " + \
                 "AND r.resource_value = TO_CHAR(sub.sub_organization_id) " + \
                 "AND sub.CREATOR_ORGANIZATION_ID = org.CREATOR_ORGANIZATION_ID"
                 
    
    cur = con.cursor()
    cur.execute(user_query)
    user_data = cur.fetchall()
    
    return user_data


def load_users():
    
    con  = get_connection()
    
    data = execute_user_query(con)
    
    user_dict = {}
    
    
    for user_item in data :
        '''
        For each user get all the sub organizations and 
        add them to user data dictionary
        '''
        user_name = user_item[0]
        
        #Remove IDIR prefix from the user name
        if user_name :
            index = user_name.find("\\")
            user_name = user_name[index+1:]
            
        
        
        if not user_name :
            continue
        
        #Get the user sub_organization name
        user_org = user_item[2]
        
        '''
        If the user is in dictionary add this organization
        to the list of his/her organizations. Otherwise,
        add a new key to dictionary with the user name.
        '''
        if user_name in user_dict :
            user_orgs = user_dict[user_name]
        else :
            user_orgs = []
        
        user_orgs.append(user_org)
        user_dict[user_name] = user_orgs


    return user_dict
    

def user_exists(username, site_url, api_key):
    
    data_string = json.dumps({'id' : username})
    
    user = None
    try:
        request = urllib2.Request(site_url + '/api/3/action/user_show')
        request.add_header('Authorization', api_key)
        response = urllib2.urlopen(request, data_string)
        assert response.code == 200

        response_dict = json.loads(response.read())
        assert response_dict['success'] is True
        user = response_dict['result']
    except Exception:
        pass
    
    return user
    
def create_user(user_dict, site_url, api_key):
    
    data_string = json.dumps(user_dict)
    
    user = None
    try :
        request = urllib2.Request(site_url + '/api/3/action/user_create')
        request.add_header('Authorization', api_key)
        response = urllib2.urlopen(request, data_string)
        assert response.code == 200

        response_dict = json.loads(response.read())
        assert response_dict['success'] is True
        user = response_dict['result']
    except Exception:
        pass
    
    return user    

def add_user_to_org(user, org_id, site_url, api_key):
    
    member_dict = {
                   'id' : org_id,
                   'username' : user['id'],
                   'role': 'editor'}
    pprint.pprint( member_dict )
    data_string = json.dumps(member_dict)
    
    user = None
    try :
        request = urllib2.Request(site_url + '/api/3/action/organization_member_create')
        request.add_header('Authorization', api_key)
        response = urllib2.urlopen(request, data_string)
        assert response.code == 200

        response_dict = json.loads(response.read())
        assert response_dict['success'] is True
    except Exception:
        pass
            
    
def import_users(site_url, api_key):
    
    '''
    For each user in user dictionary :
    Add the user to the site if he/she doesn't exist.
    '''
    user_data = load_users()
        
    for name, user_orgs in user_data.iteritems():        
        user_name = name.lower()
        #Check if the user exists
        user = user_exists(user_name, site_url, api_key)
         
        user_dict = {
                     'name' : user_name,
                     'email' : 'databc@gov.bc.ca',
                     'password' : 'r3db1rd'
                     }
        if not user :
            user = create_user(user_dict, site_url, api_key)
         
        #Add user to organization(s) 
        if user :
            for org_title in user_orgs :
                org_id = get_organization_id(org_title, site_url, api_key)
                if org_id :
                    add_user_to_org(user, org_id, site_url, api_key)


import_params = get_import_params()
site_url =  import_params['site_url']
api_key = import_params['api_key'] 

import_users(site_url, api_key)                   
#!/usr/bin/python
# -*- coding: UTF-8 -*-
################################################################################
#                                  SDKLIB                                      #
#              https://yourdynoname.herokuapp.com:443/apiai                    #
# This file contains functions for interfacing other API's and internal tasks  #
################################################################################

#This will manage http requests
import requests
#This is a python file on the same file path created to clarify code
import spark
#This will give access to the OS environmental variables
import os

# Spark's header with Token defined in environmental variables
spark_header = {
        'Authorization': 'Bearer ' + os.environ.get('SPARK_ACCESS_TOKEN', None),
        'Content-Type': 'application/json'
        }

#------------------Interface with Smartsheet's API------------------------------

# Searchs an specified text everywhere in your account sheets.
def search_employee (smartsheet, query, parameter=0):
    search_res = smartsheet.Search.search(query)
    #print ("Se ha pedido buscar: " +query)
    # Result is a smartsheet.models.SearchResult object. This particular
    # implementation is going to take into account only the first matched search.
    # The parameters needed to get the values of the cell on the right are
    # sheetId and rowId. columnId is also needed, but only known in JSON
    # received with get_row
    sheetId= search_res.results[0].parent_object_id
    rowId  = search_res.results[0].object_id

    #[Debug] Data for get_row (parameters to be able to ask for the correct cell)
    #print('SheetId: '+str(sheetId) + ' and RowId: '+str(rowId))

    # With the parameters needed to get the entire row, we request it
    row = smartsheet.Sheets.get_row(sheetId, rowId,
                           include='discussions,attachments,columns,columnType')

    # --The following is a botched job--
    # JSON is formatted in such a way that the cell where I know where the data
    # I want is in here:
    whois= row.cells[1].value
    speech = "La respuesta a \"" + query + "\" es: " + str(whois) + "."
    return speech

#---------------End of Interface with Smartsheet's API--------------------------

def get_user(req, sbuffer, user):
    # This will retrieve personID, personEmail and displayName
    #print("API.ai ID: \t" + str(req.get("sessionId")))
    #print(" Spark ID: \t" + str(sbuffer['sessionId']))
    #if str(req.get("id"))[15:] in str(sbuffer['sessionId']):
    user['personId']   = sbuffer['personId']
    user['personEmail']= sbuffer['personEmail']
    user['displayName']= sbuffer['displayName']
    found= True
    #                       \n   personId: \t" + user['personId']
    print("Message sent by: \n   personEmail: \t" + user['personEmail']
                          +"\n   displayName: \t" + user['displayName'])
    if not found: print ("Error, different sessionId")
    return found

def is_cisco (user):
    # If users email contains @cisco.com, then is must be a Cisco Employee
    #print ("User email [is_cisco]" +  user['personEmail'])
    if "@cisco.com" in user['personEmail']: return True
    else: return False

def is_partner (smartsheet, user):
    # If user appears on Smartsheet, then is must be a Cisco Spain Partner
    # this information is on sheetid= 6064162607523716
    sheetId = 6064162607523716
    #Better to use sheetId = os.environ.get('PARTNERS_SHEET', None)
    search_res = smartsheet.Search.search_sheet(sheetId, user['personEmail'])
    try:
        if search_res.results[0].text in user['PersonEmail']: return True
        else: return False
    except:
        # Exception if the before object is empty
        return False

def search (smartsheet, user, client=None):
    # The AM of the specified customer is searched or user's AM. The sheets are
    # in an array in order to search in all them with a loop
    sheet = 0;
    # Total number of sheets
    #Better to use
    #sheetId_0 = os.environ.get('AM_SHEET_0', None)
    #sheetId_1 = os.environ.get('AM_SHEET_1', None)

    total_sheets = 2
    sheetId_0 = 7064249500493700
    sheetId_1 = 4478747907778436
    sheetId   = [sheetId_0, sheetId_1]
    # if there is a client string, then you are asking for an AM different to
    # user's one. This info can only be disclosed internally, so Alice should
    # check first if this user is a Cisco employee. If asking for own AM, Alice
    # will check to what partner user belongs to.
    if client is None:
        #print ("no client specified")
        # In this case, check if user is Cisco Employee. If true, no AM for him
        if is_cisco (user):
            #print ("Yeah. User is Cisco Employee")
            # Cisco employee that asks for its am, is not possible
            string_res = "Pero " + spark.mention(user['displayName'],
                                                 user['personEmail']) + ", usted es empleado de Cisco. No tiene AM."
    else:
        #print("client specified")
        # AM for the user that is asked, if he/she is a Cisco Employee
        if is_cisco (user):
            # At a first place, the customer is marked as not listed. Then, if
            # it is found, this string is changed
            string_res = "Disculpe, no tenemos información indexada de " + client + ". Por favor, contacte con _José Méndez_ o busque manualmente en **Smartsheet** [[Comercial Virtual Sales](https://app.smartsheet.com/b/publish?EQBCT=9d609817f70b4b199a849da34f5ca213)|[Comercial Non Virtual Sales](https://app.smartsheet.com/b/publish?EQBCT=4403c331493c4e62941333f7069b7d7a)] para más información"
            while sheet <= (total_sheets-1):
                #print ("Yeah. User is Cisco Employee")
                search_res = smartsheet.Search.search_sheet(sheetId[sheet], client)
                # As in search_employee, Result is a smartsheet.models.SearchResult
                # object.
                try:
                    rowId  = search_res.results[0].object_id
                    # With the parameters needed to get the entire row, we request it
                    row = smartsheet.Sheets.get_row(sheetId[sheet], rowId,
                                include='discussions,attachments,columns,columnType')
                    # --The following is a botched job--
                    # JSON is formatted in such a way that the cell where I know
                    # where the data I want is in here:
                    client = row.cells[1].value
                    am = row.cells[0].value
                except:
                    # Exception if the before object is empty. This means it is
                    # not contained on this sheet
                    sheet += 1
                else:
                    string_res = "El AM para el cliente **" + client + "** es: _" + str(am) + "_ . ¿Es correcta la respuesta?"
                    break;
        else:
            # In this case, user is not a partner, nor a Cisco Employee. Cannot
            # see internals
            string_res = "Disculpe " + user['displayName'] + ", usted no tiene permisos para visualizar datos internos."
    print (string_res)
    return string_res

def buffer_it(JSON, sbuffer):
    # Webhook is triggered if a message is sent to the bot. The JSON and the
    # message unciphered are then saved
    # First step is to discard bot's own messages
    if JSON['data']['personEmail'] != os.environ.get('BOT_EMAIL',
                                                                '@sparkbot.io'):
        roomId    = JSON['data']["roomId"]
        messageId = JSON['data']['id']
        # [Debug]
        #print("Message ID: \t" + messageId)
        # Message is ciphered. Unciphered message must be GET from Spark
        message = requests.get(url='https://api.ciscospark.com/v1/messages/'
                                               +messageId, headers=spark_header)
        JSON = message.json()
        # Dictionary Containing info would be like this:
        # -------------------
        # !      roomId     |  Saving just in case
        # |message decrypted|  Used to compare with the message from api.ai
        # |    personId     |  Speaker unique ID
        # |   personEmail   |  Speaker unique email
        # |   displayName   |  Speaker´s displayed name
        # -------------------
        messagedecrypt  = JSON.get("text")
        personId        = JSON.get("personId")
        personEmail     = JSON.get("personEmail")
        # The Display Name of the person must be GET from Spark too
        displayName     = spark.get_displayName(personId)
        # roomId as identification, but not very well specified in Docs
        # [Debug]
        #print ("Message Decrypted: "  + messagedecrypt
        #              + "\nroomId: \t"+ roomId
        #            + "\npersonId: \t"+ personId
        #          +"\npersonEmail: \t"+ personEmail
        #          +"\ndisplayName: \t"+ displayName
        # Save all in buffer
        sbuffer['roomId']     = roomId
        sbuffer['message']    = messagedecrypt
        sbuffer['personId']   = personId
        sbuffer['personEmail']= personEmail
        sbuffer['displayName']= displayName
        # [Debug]
        #print ("Buffer ACK")
        return True
    else:
        # Message from bot must be ignored
        print ("message from bot: ignoring")
        return False
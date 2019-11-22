# DocuSign API Walkthrough 04 (PYTHON) - Add Signature Request to Document and Send
import sys, httplib2, json;
import os
from openerp.exceptions import ValidationError

root_path = os.path.dirname(os.path.abspath(__file__))


def login_docusign(username, password, integratorKey):
    baseUrl = ''
    accountId = ''
    authenticateStr = get_auth_str(username, password, integratorKey)
    url = 'https://demo.docusign.net/restapi/v2/login_information'
    headers = {'X-DocuSign-Authentication': authenticateStr, 'Accept': 'application/json'}
    http = httplib2.Http()
    response, content = http.request(url, 'GET', headers=headers)
    status = response.get('status')
    if status != '200':
        return status, baseUrl, accountId
    data = json.loads(content)
    loginInfo = data.get('loginAccounts')
    D = loginInfo[0]
    baseUrl = D['baseUrl']
    accountId = D['accountId']
    return status, baseUrl, accountId


def send_docusign_file(username, password, integratorKey, filename, fileContents, receiver_email):

    status, baseUrl, accountId = login_docusign(username, password, integratorKey)
    authenticateStr = get_auth_str(username, password, integratorKey)

    envelopeDef = "{\"emailBlurb\":\"Click above for sign the document\"," + \
                  "\"emailSubject\":\"Signature request to document\"," + \
                  "\"documents\":[{" + \
                  "\"documentId\":\"1\"," + \
                  "\"documentBase64\":\"" + fileContents.decode("utf-8") + "\"," + \
                  "\"name\":\"" + filename + "\"}]," + \
                  "\"recipients\":{" + \
                  "\"signers\":[{" + \
                  "\"email\":\"" + receiver_email + "\"," + \
                  "\"name\":\"Name\"," + \
                  "\"recipientId\":\"1\"," + \
                  "\"tabs\":{" + \
                  "\"signHereTabs\":[{" + \
                  "\"xPosition\":\"400\"," + \
                  "\"yPosition\":\"600\"," + \
                  "\"documentId\":\"1\"," + \
                  "\"pageNumber\":\"1\"" + "}]}}]}," + \
                  "\"status\":\"sent\"}"

    requestBody = "\r\n\r\n--BOUNDARY\r\n" + \
                  "Content-Type: application/json\r\n" + \
                  "Content-Disposition: form-data\r\n" + \
                  "\r\n" + \
                  envelopeDef + "\r\n\r\n--BOUNDARY\r\n" + \
                  "Content-Type: application/pdf\r\n" + \
                  "Content-Disposition: file; filename=\"" + filename + "\"; documentId=1\r\n" + \
                  "\r\n" + \
                  "--BOUNDARY--\r\n\r\n"

    # append "/envelopes" to the baseUrl and use in the request
    url = baseUrl + "/envelopes"
    headers = {'X-DocuSign-Authentication': authenticateStr,
               'Content-Type': 'multipart/form-data; boundary=BOUNDARY', 'Accept': 'application/json'}
    http = httplib2.Http()
    response, content = http.request(url, 'POST', headers=headers, body=requestBody)
    status = response.get('status')

    if status != '201':
        raise ValidationError(("Error calling webservice, status is: %s\nError description - %s" %
                               (status, content)))
    data = json.loads(content)
    envelope_id = data.get('envelopeId')
    return envelope_id


def get_status(username, password, integratorKey, envelopeId):

    status, baseUrl, accountId = login_docusign(username, password, integratorKey)
    authenticateStr = get_auth_str(username, password, integratorKey)

    # Get Envelope Recipient Status
    # append "/envelopes/" + envelopeId + "/recipients" to baseUrl and use in the request
    url = baseUrl + "/envelopes/" + envelopeId + "/recipients"
    headers = {'X-DocuSign-Authentication': authenticateStr, 'Accept': 'application/json'}
    http = httplib2.Http()
    response, content = http.request(url, 'GET', headers=headers)
    status = response.get('status')
    if status != '200':
        raise ValidationError(("Error calling webservice, status is: %s" % status))

    data = json.loads(content)
    signers = data.get('signers')
    S = signers[0]
    status = S['status']
    return status


def download_documents(username, password, integratorKey, baseUrl, envelopeId):
    doc_status = get_status(username, password, integratorKey, envelopeId)
    complete_path = ''
    restatus = ''
    uriList = []

    if doc_status != 'completed':
        return doc_status, complete_path

    envelopeUri = "/envelopes/" + envelopeId
    authenticateStr = get_auth_str(username, password, integratorKey)

    # STEP 2 - Get Envelope Document(s) Info and Download Documents
    # append envelopeUri to baseURL and use in the request
    url = baseUrl + envelopeUri + "/documents"
    headers = {'X-DocuSign-Authentication': authenticateStr, 'Accept': 'application/json'}
    http = httplib2.Http()
    response, content = http.request(url, 'GET', headers=headers)
    status = response.get('status')
    if status != '200':
        raise ValidationError(("Error calling webservice, status is: %s" % status))
    data = json.loads(content)
    envelopeDoc = data.get('envelopeDocuments')
    envelopeDoc = envelopeDoc[0]

    uriList.append(envelopeDoc.get("uri"))
    # download each document
    url = baseUrl + uriList[len(uriList) - 1]
    headers = {'X-DocuSign-Authentication': authenticateStr}
    http = httplib2.Http()
    response, content = http.request(url, 'GET', headers=headers)
    status = response.get('status')

    if status != '200':
        raise ValidationError(("Error calling webservice, status is: %s" % status))

    directory_path = os.path.join(root_path, "files")
    if not os.path.isdir(directory_path):
        try:
            os.mkdir(directory_path)
        except:
            raise ValidationError("Please provide access rights to module")

    attach_file_name = envelopeDoc.get("name")
    file_path = os.path.join("files", attach_file_name)
    complete_path = os.path.join(root_path, file_path)
    with open(complete_path, "wb") as text_file:
        text_file.write(content)
        text_file.close()

    restatus = status
    if restatus == '200':
        return doc_status, complete_path
    else:
        raise ValidationError('Connection Failed! Please check Docusign credentials.')


def get_auth_str(username, password, integratorKey):
    return "<DocuSignCredentials>" \
            "<Username>" + username + "</Username>" \
            "<Password>" + password + "</Password>" \
            "<IntegratorKey>" + integratorKey + "</IntegratorKey>" \
            "</DocuSignCredentials>"

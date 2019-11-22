import requests, json, urllib, datetime, os
import base64
from odoo.exceptions import UserError, ValidationError

root_path = os.path.dirname(os.path.abspath(__file__))


def get_refresh_token(api_access_point,redirect_url, client_id, client_secret, refresh_token):
    base_url = api_access_point + '/oauth/refresh?'
    try:
        headers = {

                'Content-Type' : 'application/x-www-form-urlencoded'
         }
        url ='https://api.na2.echosign.com/oauth/refresh?grant_type=refresh_token&refresh_token='+ refresh_token +'&redirect_uri='+ redirect_url + '&client_id='+client_id+'&client_secret='+client_secret
        response = requests.post(url
            , headers=headers)
        response = json.loads(response.content.decode('utf-8'))
        access_token = response['access_token']
        return access_token
    except Exception as err:
        raise ValidationError(err)


def read_file(file_path):
    with open(file_path, 'rb') as f:
        content = base64.b64encode(f.read())
    return content


def upload_document(api_access_point, file_path, access_token):
    base_url = api_access_point + '/api/rest/v5' + '/transientDocuments'
    headers = {
        'Access-Token': access_token,
    }
    data = {
        'Mime-Type': 'application/pdf',
    }

    files = {'File': open(file_path, 'rb')}
    response = requests.post(base_url, headers=headers, data=data, files=files)
    return response.json().get('transientDocumentId')


def send_agreement(api_access_point, access_token, transientDocumentId, recipient_email, file_name):
    base_url = api_access_point + '/api/rest/v5' + '/agreements'
    headers = {
        'Access-Token': access_token,
        'Content-Type': 'application/json',
    }
    agreement_data ={

        "fileInfos": [{
            "transientDocumentId": transientDocumentId
        }],
        "name":file_name,
        "participantSetsInfo": [{
            "memberInfos": [{
                "email": recipient_email
            }],
            "order": 1,
            "role": "SIGNER"
        }],
        "signatureType": "ESIGN",
        "state": "IN_PROCESS"
    }
    json_dumps = json.dumps(agreement_data)
    data = json.loads(json_dumps)
    response = requests.post(base_url, headers=headers, data=json_dumps)
    response_json = response.json()
    agreement_id = response_json.get('agreementId')
    if agreement_id:
        return True, agreement_id
    return False, response_json.get('message')


def valid_token_time(expires_in):
    expires_ins = datetime.datetime.fromtimestamp(int(expires_in) / 1e3)
    expires_in = expires_ins + datetime.timedelta(seconds=3600)
    nowDateTime = datetime.datetime.now()
    if nowDateTime > expires_in:
        return  False
    return True


def get_file_path(file):
    file_name = file.name
    file_data = file.sudo().read(['datas'])
    directory_path = os.path.join(root_path, "files")
    if not os.path.isdir(directory_path):
        os.mkdir(directory_path)
    path = os.path.join("files", file_name)
    complete_path = os.path.join(root_path, path)
    with open(complete_path, "w") as text_file:
        text_file.write(str(base64.decodestring(file_data[0]['datas'])))
    return complete_path


def get_agreement_detail(api_access_point, access_token,agreement_id):
    base_url = api_access_point + '/api/rest/v5' + '/agreements' + '/' + agreement_id
    try:
        headers = {
            'Access-Token': access_token,
            'Content-Type': 'application/json',
        }
        response = requests.get(base_url, headers=headers)

        if str(response.json().get('code')) == 'INVALID_ACCESS_TOKEN':
            raise UserError((response.json().get('message')))

        status = response.json().get('status')
        name = response.json().get('name')
        return [status, name]
    except Exception as err:
        return False


def download_agreement(api_access_point, access_token,agreement_id):
    base_url = api_access_point + '/api/rest/v5' + '/agreements' + '/' + agreement_id + '/combinedDocument'
    headers = {
        'Access-Token': access_token,
    }
    response = requests.get(base_url, headers=headers)
    if str(response.status_code) == '200':
        return response.content
    return False


def verify_token(access_token, redirect_url, expire_in, api_access_point, client_id, client_secret, refresh_token):
    is_valid = valid_token_time(expire_in)
    if not is_valid:
        new_access_token = get_refresh_token(api_access_point,redirect_url, client_id, client_secret, refresh_token)
        if new_access_token:
            return new_access_token
        else:
            return False
    return access_token

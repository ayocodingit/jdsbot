import os
import re
import json
import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent /  '.env'
load_dotenv(dotenv_path=env_path)

ROOT_API_URL = os.getenv('ROOT_API_URL')
PING_API_URL = ROOT_API_URL+'/healthcheck/'
LOGBOOK_API_URL = ROOT_API_URL+'/logbook/'
LOGIN_API_URL = ROOT_API_URL+'/auth/login/'
USER_API_URL = ROOT_API_URL+'/user/'
HOLIDAY_LIST_API_URL = ROOT_API_URL+'/holiday-date/'
PROJECT_LIST_API_URL = ROOT_API_URL+'/project/?limit=300&pageSize=300'

TIMESTAMP_TRAIL_FORMAT = 'T00:00:00.000Z'
VERBOSITY_LEVEL=int(os.getenv('VERBOSITY_LEVEL', '0'))
PROJECT_LIST = None

def request_base(method, *args, **argv):
    """ wrapper for all network request """
    try:
        req = requests.request(method, *args, **argv)
    except requests.exceptions.ConnectionError as e:
        raise Exception('Terjadi masalah sambungan ke server DigiTeam. Mohon coba beberapa saat lagi')

    return req

def request_get(*args, **argv):
    return request_base('GET', *args, **argv)

def request_post(*args, **argv):
    return request_base('POST', *args, **argv)

def get_token(username, password):
    """ dapetin token dari username & password """
    req = request_post(url=LOGIN_API_URL, data={
        'username': username,
        'password': password,
    })
    res = req.json()

    if req.status_code < 300:
        if VERBOSITY_LEVEL > 0:
            print('get token response:', req.text)
        return res['auth_token']
    else:
        msg = res['detail'] if 'detail' in res else req.text
        raise Exception(msg)

def load_project_list(auth_token):
    """ dapetin list nama project & id nya """
    global PROJECT_LIST

    headers = {
        'Authorization': 'Bearer ' + auth_token,
    }
    req = request_get(url=PROJECT_LIST_API_URL, headers=headers)

    if req.status_code < 300:
        raw_response = req.json()
        PROJECT_LIST =  {
            row['projectName'].strip().lower() : {
                'id': row['_id'].strip() ,
                'originalName': row['projectName'].strip(),
            }
            for row in raw_response['results']
        }
    else:
        raise Exception('Error response: ' + req.text)

def get_attendance(auth_token, date=None):
    """ get list of attendace from /attendance endpoint """
    if date is None:
        date = str(datetime.date.today())

    headers = {
        'Authorization': 'Bearer ' + auth_token,
    }

    api_url = ROOT_API_URL+'/attendance/?limit=200&pageSize=200&date={}'.format(date)
    req = request_get(
        url=api_url,
        headers=headers
    )

    if req.status_code >= 300:
        raise Exception('Error response: ' + req.text)

    raw_response = req.json()
    return raw_response['results']

def get_users(auth_token, is_active=True, with_struktural=False, search=None):
    """ get list of all users which match parameters """
    headers = {
        'Authorization': 'Bearer ' + auth_token,
    }

    req = request_get(
        url=USER_API_URL,
        params={
            'page_size' : 300,
            'page': 1,
            'is_active' : 'true' if is_active else None,
            'search' : search,
        },
        headers=headers
    )

    if req.status_code >= 300:
        raise Exception('Error response: ' + req.text)

    raw_response = req.json()
    results = raw_response['results'] \
        if with_struktural else \
        [ i for i in raw_response['results'] if i['divisi'] != 'ASN' ]

    return results

def check_date_is_holiday(auth_token, date=None):
    """ check the given date is a holiday

    Params
    ------
    auth_token: string
    date: datetime.date object|None
        date to check. default to today
    """
    if date is None:
        date = datetime.date.today()

    headers = {
        'Authorization': 'Bearer ' + auth_token,
    }

    req = request_get(
        url=HOLIDAY_LIST_API_URL,
        params={
            'limit' : 300,
            'page': 1,
            'year' : date.year,
        },
        headers=headers
    )

    if req.status_code >= 300:
        raise Exception('Error response: ' + req.text)

    raw_response = req.json()

    if raw_response['results'] is None:
        return False

    return date in [
        datetime.datetime.strptime(i['holiday_date'], '%Y-%m-%dT%H:%M:%SZ').date()
        for i in
        raw_response['results']
    ]

def validate_report(raw_data):
    """ Validate report data
    Returns
    -------
    list of Exception for all caught error. empty string for no error
    """
    global PROJECT_LIST

    data = json.loads(json.dumps(raw_data))
    errors = []

    # dateTask validation
    if 'dateTask' not in data or len(data['dateTask'].strip()) < 1:
        errors.append(ValueError('dateTask field cannot be empty'))
    elif not re.match("^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\dZ$",data['dateTask']):
        errors.append(ValueError('dateTask format mismatch'))

    # project name validation
    if 'projectName' not in data or len(data['projectName'].strip()) < 1:
        errors.append(ValueError('projectName field cannot be empty'))
    else:
        original_project_name = data['projectName']
        data['projectName'] = data['projectName'].lower()
        if PROJECT_LIST is None:
            load_project_list(auth_token)

        if data['projectName'] not in PROJECT_LIST:
            errors.append(ValueError("projectName '{}' not found".format(original_project_name)))

    return errors

def post_report(auth_token, data, files):
    """ post laporan """
    global PROJECT_LIST

    data['projectName'] = data['projectName'].lower()
    data['projectId'] = PROJECT_LIST[data['projectName']]['id']
    data['projectName'] = PROJECT_LIST[data['projectName']]['originalName'] # replace projectName with original name

    # 'difficultyTask' column is no longer used by groupware API
    if 'difficultyTask' in data:
        del data['difficultyTask']
    if 'isMainTask' in data:
        del data['isMainTask']

    headers = {
        'Authorization': 'Bearer ' + auth_token,
    }

    if VERBOSITY_LEVEL > 0:
        print('sending input to groupware with data:', data)

    req = request_post(url=LOGBOOK_API_URL, headers=headers, files=files, data=data)
    if VERBOSITY_LEVEL >= 10:
        print('request body:', req.request.body)

    if req.status_code < 300:
        raw_response = req.json()
        if VERBOSITY_LEVEL >= 10:
            print('response', raw_response)
        return raw_response
    else:
        raise Exception('Error response: ' + req.text)

def is_groupware_api_reachable():
    """ check groupware api is connected

    Return
    ------
    ok: bool
    error_message: string|None
    """

    try:
        req = request_get(url=PING_API_URL)

        if req.status_code < 300:
            return (True, None)
        else:
            return (False, req.text)
    except Exception as e:
        return False, str(e)

if __name__ == '__main__':
    TEST_USER = os.getenv('TEST_USER', 'testuser')
    auth_token = get_token(TEST_USER, TEST_USER)
    print('auth_token :', auth_token)

    from datetime import datetime

    data = {
        'dateTask' : datetime.now().strftime('%Y-%m-%d'), #2020-08-23T00:00:00.000Z
        # 'projectId' : '', # UID project, dapat dr endpoint /project/?limit=100&pageSize=100
        'projectName' : 'Sapawarga', # project nam (from db)
        'nameTask': 'Contoh',
        'difficultyTask': 3, # integer 1-5
        'organizerTask' : 'PLD',
        'isMainTask' : 'true', #bool
        'isDocumentLink' : 'true', #bool
        'workPlace' : 'WFH',
        'documentTask': 'null', # url
    }

    files={
        'evidenceTask' : ('test.png', open('test.png', 'rb'), 'image/png'), # upload evidence
    }

    print(post_report(auth_token, data, files))




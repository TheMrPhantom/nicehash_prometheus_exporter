import prometheus_client
import config
import requests
import random
import string
import datetime
import hmac
import hashlib
import json
import urllib
import time


def getNonce():
    ''' Returns a 36 character long nonce with letters and digits '''

    possible_chars = string.ascii_letters+string.digits
    nonce = ''.join(random.choice(possible_chars) for i in range(36))
    return nonce


def sign_request(api_key, api_secret, orga_id, url, parameter, http_method, time, nonce):
    '''
    Returns the signed request infos needed for the nicehash auth header

    @param api_key The API Key provided by nicehash
    @param api_secret The API Secret provided by nicehash
    @param orga_id The Orga ID provided by nicehash
    @param url The api url starting after https://api2.nicehash.com (starts with '/')
    @param parameter The query parameters for the api call
    @param http_method Which method to use (GET, POST, DELETE, PUT)
    @param time UTC Time used in the request
    @param nonce Nonce used in the rquest

    @return sha256 hash of the parameters using the api_secret
    '''

    sign_input = str(api_key)+"\x00"
    sign_input += str(time)+"\x00"
    sign_input += str(nonce)+"\x00"

    sign_input += "\x00"

    sign_input += str(orga_id)+"\x00"

    sign_input += "\x00"

    sign_input += str(http_method)+"\x00"
    sign_input += str(url)+"\x00"
    sign_input += str(parameter)

    signature = hmac.new(
        bytes(api_secret, 'utf-8'),
        msg=bytes(sign_input, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    return signature


def nicehash_timestamp():
    ''' Gets the timestamp in the correct format for the nicehash api'''

    return str(datetime.datetime.utcnow().timestamp()).replace(".", "")[:-3]


def get_Infos_From_NiceHash(http_method, endpoint, query_params):
    '''
    Calls a enpoint from nicehash

    @param http_method Which method to use (GET, POST, DELETE, PUT)
    @param endpoint All after v2/
    @param query_params URL query parameter as dict

    @return The response of nicehas (empty dict if request fails)
    '''
    try:
        timestamp = nicehash_timestamp()
        nonce = getNonce()
        request_id = getNonce()
        orga_id = config.organization_id
        key = config.key
        s_key = config.key_secret

        signature = sign_request(
            key, s_key, orga_id, config.api_url_prefix+endpoint, urllib.parse.urlencode(query_params), http_method, timestamp, nonce)

        auth_header = key+":"+signature
        url = config.api_url+config.api_url_prefix+endpoint
        header = {}
        header['X-Time'] = timestamp
        header['X-Nonce'] = nonce
        header['X-Organization-Id'] = orga_id
        header['X-Auth'] = key+":"+signature
        header['X-Request-Id'] = request_id
        r = requests.request(http_method,
                             url,
                             headers=header,
                             params=query_params)
        return json.loads(r.text)
    except:
        print("Fail")
        return {}


def get_rig_count():
    ''' Return the total number of rigs '''
    data = {}
    request = get_Infos_From_NiceHash(
        'GET', '/mining/groups/list', {"extendedResponse": "True"})

    if 'error_id' in request:
        print(request)
        return float(0)

    data['rigs'] = request['groups']['']['rigs']
    return float(len(data['rigs']))


def check():
    ''' Updates all data in prometheus '''

    group_request = get_Infos_From_NiceHash(
        'GET', '/mining/groups/list', {"extendedResponse": "True"})
    if 'error_id' in group_request:
        print(group_request)
        return

    rigs = group_request['groups']['']['rigs']
    second_rig_id = group_request['groups']['']['rigs'][1]["rigId"]

    stats_request = get_Infos_From_NiceHash(
        'GET', '/mining/rig/stats/unpaid', {'rigId': second_rig_id})
    mining_request = get_Infos_From_NiceHash(
        'GET', '/mining/rig2/'+second_rig_id, {})

    if 'error_id' in stats_request or len(stats_request['data']) == 0 or 'error_id' in mining_request:
        print("Error")
        return

    for rig in rigs:
        name = "rig_status_"+rig['name']
        if name not in prometheus_data:
            prometheus_data[name] = prometheus_client.Enum(name, 'Status of rig: '+rig['name'],
                                                           states=['BENCHMARKING', 'MINING', 'STOPPED', 'OFFLINE', 'ERROR', 'PENDING', 'DISABLED', 'TRANSFERRED', 'UNKNOWN'])
        prometheus_data[name].state(rig['status'])

    prometheus_data['currently_unpaid'].set(stats_request['data'][0][2])

    prometheus_data['rig_temperature'].set(
        mining_request['devices'][1]['temperature'])
    prometheus_data['rig_load'].set(mining_request['devices'][1]['load'])
    prometheus_data['rig_power_usage'].set(
        mining_request['devices'][1]['powerUsage'])
    prometheus_data['profitability'].set(mining_request['profitability'])
    prometheus_data['local_profitability'].set(
        mining_request['localProfitability'])


prometheus_data = {}
prometheus_data['rig_count'] = prometheus_client.Gauge(
    'rig_count', 'The number of current rigs')
prometheus_data['rig_count'].set_function(get_rig_count)

prometheus_data['currently_unpaid'] = prometheus_client.Gauge(
    'currently_unpaid', 'The ammount of Bitcoin currently not payed')

prometheus_data['profitability'] = prometheus_client.Gauge(
    'money_profitability_actual', 'The actual profitability of the main rig')
prometheus_data['local_profitability'] = prometheus_client.Gauge(
    'money_profitability_local', 'The theoretical profitability of the main rig')
prometheus_data['rig_temperature'] = prometheus_client.Gauge(
    'rig_temperature', 'Temperature of the gpu')
prometheus_data['rig_load'] = prometheus_client.Gauge(
    'rig_load', 'Load of the gpu')
prometheus_data['rig_power_usage'] = prometheus_client.Gauge(
    'rig_power_usage', 'Power usage of the gpu')

prometheus_client.start_http_server(config.port)

while True:
    try:
        check()
    except:
        print("Fail")
    time.sleep(2)
    print(datetime.datetime.now())
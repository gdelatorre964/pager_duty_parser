#!/usr/bin/env python
#
# Copyright (c) 2016, PagerDuty, Inc. <info@pagerduty.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of PagerDuty Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL PAGERDUTY INC BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Sample script to output incident details to a CSV in the format:
# incident_id,created_at,type,user_or_agent_id,user_or_agent_summary,notification_type,channel_type,summary
# CLI Usage: ./get_incident_details_csv api_key [since] [until]
#   api_key: PagerDuty API access token
#   since: Start date of incidents you want to pull in YYYY-MM-DD format
#   until: End date of incidents you want to pull in YYYY-MM-DD format

import requests
import sys
import csv
import json
import datetime
from datetime import date

from urllib3.connectionpool import xrange


def get_incident_count(since, until, headers):
    # Retrieve the count of incidents in a given time-period, as an 'int'.
    # Dates should be in the format 'YYYY-MM-DD'.
    payload = {
        'since': since,
        'until': until
    }
    get_incident_count_url = 'https://api.pagerduty.com/incidents/count'
    r = requests.get(get_incident_count_url, params=payload, headers=headers)
    return int(r.json()['total'])

def get_incident_ids(since, until, headers, ea_hun=None):
    # Based on an incident-count used to create an 'offset',
    # retrieve incident-IDs, in batches-of-100, and return as a list.
    # Dates should be in the format 'YYYY-MM-DD'.
    id_list = []
    count = get_incident_count(since, until, headers)
    get_incident_ids_url = 'https://api.pagerduty.com/incidents'
    payload = {'since': since, 'until': until}
    for ea_hun in xrange(0,count) or int(ea_hun)==count:
        if int(ea_hun)%100==1:
            payload['offset'] = ea_hun
            r = requests.get(get_incident_ids_url, params=payload, headers=headers, stream=True)
            id_list = id_list + [ea_inc['id'] for ea_inc in r.json()['incidents']]
    return id_list

def get_details_by_incident(api_key, filename='pagerduty_export', since='', until=date.today()):
    # Based on a list of incident-IDs, retrieve incident details.
    # Process json-payload and output to CSV file.
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token=' + api_key
    }
    id_list = get_incident_ids(since, until, headers)
    fin_file = open('{filename}.csv'.format(filename=filename), 'w')
    fieldnames = ['incident_id','created_at','type','user_or_agent_id','user_or_agent_summary','notification_type','channel_type','summary']
    writer = csv.DictWriter(fin_file, fieldnames=fieldnames)
    writer.writeheader()
    for ea_id in id_list:
        r = requests.get('https://api.pagerduty.com/incidents/{0}/log_entries'.format(ea_id), headers=headers, stream=True)
        for ea_entry in reversed(r.json()['log_entries']):
            if ea_entry['type'] != 'notify_log_entry_reference' and ea_entry['type'] != 'notify_log_entry':
                if ea_entry['channel']['type'] == 'nagios' or ea_entry['channel']['type'] == 'web_trigger' or ea_entry['channel']['type'] == 'email' or ea_entry['channel']['type'] == 'api':
                    row = {
                        'incident_id': ea_id,
                        'created_at': ea_entry['created_at'],
                        'type': ea_entry['type'],
                        'user_or_agent_id': 'N/A',
                        'user_or_agent_summary': 'N/A',
                        'notification_type': 'N/A',
                        'channel_type': ea_entry['channel']['type'],
                        'summary': ea_entry['summary']
                    }
                elif ea_entry['type'] == 'assign_log_entry' or ea_entry['type'] == 'assign_log_entry_reference' or ea_entry['type'] == 'acknowledge_log_entry' or ea_entry['type'] == 'acknowledge_log_entry_reference' or ea_entry['type'] == 'resolve_log_entry' or ea_entry['type'] == 'resolve_log_entry_reference' or ea_entry['type'] == 'snooze_log_entry' or ea_entry['type'] == 'snooze_log_entry_reference' or ea_entry['type'] == 'annotate_log_entry' or ea_entry['type'] == 'annotate_log_entry_reference':
                    row = {
                        'incident_id': ea_id,
                        'created_at': ea_entry['created_at'],
                        'type': ea_entry['type'],
                        'user_or_agent_id': ea_entry['agent']['id'],
                        'user_or_agent_summary': ea_entry['agent']['summary'],
                        'notification_type': 'N/A',
                        'channel_type': ea_entry['channel']['type'],
                        'summary': ea_entry['summary']
                    }
            else:
                row = {
                    'incident_id': ea_id,
                    'created_at': ea_entry['created_at'],
                    'type': ea_entry['type'],
                    'user_or_agent_id': ea_entry['user']['id'],
                    'user_or_agent_summary': ea_entry['user']['summary'],
                    'notification_type': ea_entry['channel']['notification']['type'].replace('\n',''),
                    'channel_type': ea_entry['channel']['type'],
                    'summary': ea_entry['summary']
                }
            writer.writerow(row)
    print ("Successfully created {filename}.csv!".format(filename=filename))
    fin_file.close()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print ('Error: You did not enter any parameters.\nUsage: ./get_incident_details_csv api_key [filename] [since] [until]\n\tapi_key: PagerDuty API access token\n\tfilename: Name of the CSV file. Defaults to pagerduty_export.\n\tsince: Start date of incidents you want to pull in YYYY-MM-DD format\n\tuntil: End date of incidents you want to pull in YYYY-MM-DD format')
    elif len(sys.argv) == 2:
        get_details_by_incident(sys.argv[1])
    elif len(sys.argv) == 3:
        get_details_by_incident(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        get_details_by_incident(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        get_details_by_incident(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
#!/usr/bin/env python
#
# Copyright (c) 2016, PagerDuty, Inc. <info@pagerduty.com>
# Sample script to output incident details to a CSV in the format:
# incident_id,created_at,type,user_or_agent_id,user_or_agent_summary,notification_type,channel_type,summary
# CLI Usage: ./get_incident_details_csv api_key [since] [until]
#   api_key: PagerDuty API access token
#   since: Start date of incidents you want to pull in YYYY-MM-DD format
#   until: End date of incidents you want to pull in YYYY-MM-DD format

import csv
import re
import sys
from datetime import date
from datetime import datetime

import requests


def clean_notes(note):
    # will receive the entire note separated by commas, remove spaces and assign properly
    note = note.split(':')
    try:
        note = note[1].split(',')
        issue = (note[0]).strip(); solution = (note[1]).strip(); tag = ((note[2]).strip()).upper()

    except:
        note = note[0].split(',')
        issue = (note[0]).strip(); solution = (note[1]).strip(); tag = ((note[2]).strip()).upper()
    return issue,solution,tag


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


def get_incident_ids(since, until, headers):
    # Based on an incident-count used to create an 'offset',
    # retrieve incident-IDs, in batches-of-100, and return as a list.
    # Dates should be in the format 'YYYY-MM-DD'.
    id_list = []
    count = get_incident_count(since, until, headers)
    print('Number of incidents since ', since, ' to ', until, 'is', count)
    get_incident_ids_url = 'https://api.pagerduty.com/incidents?'
    payload = {'since': since, 'until': until}
    r = requests.get(get_incident_ids_url, params=payload, headers=headers, stream=True)
    id_list = id_list + [ea_inc['id'] for ea_inc in r.json()['incidents']]
    return id_list


def get_details_by_incident(api_key, since='', until=date.today(), filename='pagerduty_export'):
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token=' + api_key
    }
    id_list = get_incident_ids(since, until, headers)
    print(id_list)
    fin_file = open('{filename}.csv'.format(filename=filename), 'w', newline='')
    fieldnames = ['source', 'create_time', 'tech', 'issue', 'solution', 'tag', 'duration']
    writer = csv.DictWriter(fin_file, fieldnames=fieldnames)
    writer.writeheader()
    regex = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    regex1 = r"(^210|830|512|)(\d+)$"
    FMT = '%Y-%m-%dT%H:%M:%S'
    for ea_id in id_list:
        r = requests.get('https://api.pagerduty.com/incidents/{0}/alerts'.format(ea_id), headers=headers, stream=True)
        for ea_entry in reversed(r.json()['alerts']):
            source = ea_entry['body']['details']['Call back']
            if len(source) > 3:
                try:
                    matches = re.match(regex1, source)
                    source = store_number_dict[matches.group(2)]
                except:
                    print("NOT A STORE NUMBER")
            created_time = re.match(regex, ea_entry['created_at'])
            try:
                resolve_time = re.match(regex, ea_entry['resolved_at'])
                tdelta = (datetime.strptime(resolve_time.group(1), FMT)) - (
                    datetime.strptime(created_time.group(1), FMT))
            except:
                tdelta = "Open Ticket"

            s = requests.get('https://api.pagerduty.com/incidents/{0}/notes'.format(ea_id), headers=headers,
                             stream=True)
            for eb_entry in reversed(s.json()['notes']):
                tech = eb_entry['user']['summary']
                issue, solution,tag = clean_notes(eb_entry['content'])
                print(issue, solution,tag)
            row = {
                'source': source,
                'create_time': created_time.group(1),
                'tech': tech,
                'issue': issue,
                'solution': solution,
                'tag': tag,
                'duration': tdelta
            }
            writer.writerow(row)
        # print('{0},{1},{2},{3},{4}'.format(source, ea_entry['created_at'], tech, note, tdelta))
    fin_file.close()


if __name__ == '__main__':
    with open('store_numbers.csv', mode='r') as infile:
        reader = csv.reader(infile)
        store_number_dict = {rows[1]: rows[0] for rows in reader}
    with open('tags.csv', mode='r') as infile:
        reader = csv.reader(infile)
        tag_dict = {rows[1]: rows[0] for rows in reader}
    print(tag_dict)
    with open('tags.csv', mode='r') as infile:
        reader = csv.reader
    if len(sys.argv) == 1:
        print(
            'Error: You did not enter any parameters.\nUsage: ./get_incident_details_csv api_key [filename] [since] ['
            'until]\n\tapi_key: PagerDuty API access token\n\tfilename: Name of the CSV file. Defaults to '
            'pagerduty_export.\n\tsince: Start date of incidents you want to pull in YYYY-MM-DD format\n\tuntil: End '
            'date of incidents you want to pull in YYYY-MM-DD format')
    else:
        get_details_by_incident(sys.argv[1], sys.argv[2], sys.argv[3])

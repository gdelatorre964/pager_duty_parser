#!/usr/bin/env python
# Author: Gabriela De La Torre
# @2019

import csv
import re
import sys

from datetime import date, datetime, timedelta
import pandas as pd
from collections import Counter
import requests
from urllib3.connectionpool import xrange

tag_list = []
store_list = []

def daterange(d1, d2):
    for n in range(int((d2 - d1).days) + 1):

        yield d1 + timedelta(n)


def clean_notes(note):
    note = note.split(':')
    try:
        note = note[1].split(',')
        issue = (note[0]).strip();
        solution = (note[1]).strip();
        tag = ((note[2]).strip()).upper()

    except:
        try:
            note = note[0].split(',')
            issue = (note[0]).strip();
            solution = (note[1]).strip();
            tag = ((note[2]).strip()).upper()
        except:
            issue = note[0];
            solution = '';
            tag = ''
    return issue, solution, tag


def clean_source(call_back_num):
    cleaned_source = call_back_num.strip('*')
    regex1 = r"(^210|830|512|)(\d+)$"
    if len(call_back_num) > 3:
        try:
            matches = re.match(regex1, call_back_num)
            cleaned_source = store_number_dict[matches.group(2)]
        except:
            cleaned_source = call_back_num + '-!STORE #'
    return cleaned_source


def get_incident_count(since, until, headers):
    payload = {
        'since': since,
        'until': until
    }
    get_incident_count_url = 'https://api.pagerduty.com/incidents/count'
    r = requests.get(get_incident_count_url, params=payload, headers=headers)
    return int(r.json()['total'])


def get_incident_ids(since, until, headers, ea_hun=None):
    id_list = []
    count = get_incident_count(since, until, headers)
    print('Number of incidents since ', since, ' to ', until, 'is', count)
    get_incident_ids_url = 'https://api.pagerduty.com/incidents'
    payload = {'since': since, 'until': until}
    for ea_hun in xrange(0, count) or int(ea_hun) == count:
        if int(ea_hun) % 100 == 1:
            payload['offset'] = ea_hun
            r = requests.get(get_incident_ids_url, params=payload, headers=headers, stream=True)
            id_list = id_list + [ea_inc['id'] for ea_inc in r.json()['incidents']]
    return id_list


def get_details_by_incident(api_key, since='', until=date.today(), filename='pagerduty_export'):
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token=' + api_key
    }
    id_list = get_incident_ids(since, until, headers)

    fin_file = open('{filename}.csv'.format(filename=filename), 'a+', newline='')
    fieldnames = ['source', 'create_time', 'tech', 'issue', 'solution', 'tag', 'duration']
    writer = csv.DictWriter(fin_file, fieldnames=fieldnames)
    writer.writeheader()
    regex = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"

    FMT = '%Y-%m-%dT%H:%M:%S'
    for ea_id in id_list:
        r = requests.get('https://api.pagerduty.com/incidents/{0}/alerts'.format(ea_id), headers=headers, stream=True)
        for ea_entry in reversed(r.json()['alerts']):
            source = clean_source(ea_entry['body']['details']['Call back'])
            store_list.append(source)
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
                issue, solution, tag = clean_notes(eb_entry['content'])
                tag_list.append(tag)

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

    Counter(tag_list)
    Counter(store_list)
    fin_file.close()


if __name__ == '__main__':
    with open('store_numbers.csv', mode='r') as infile:
        reader = csv.reader(infile)
        store_number_dict = {rows[1]: rows[0] for rows in reader}
    with open('tags.csv', mode='r') as infile:
        reader = csv.reader(infile)
        tag_dict = {rows[1]: rows[0] for rows in reader}
    week_ = 7
    while week_:
        week_ -= 1
        from_, to_ = input('Insert dates:\n').split()
        mydates = pd.date_range(from_, to_).tolist()
        print(mydates)
        if week_ == 6:
            filename = from_
        if len(sys.argv) == 1:
            print(
                'Error: You did not enter the correct number of parameters.\n')
        else:
            get_details_by_incident(sys.argv[1], from_, to_)

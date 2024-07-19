###################################################################################
#
# This uses the Google Calendar API
#
# You need to create and download credentials.json and then log into
# the Google account that is being used to create token.json
# using these directions: https://developers.google.com/calendar/api/quickstart/python
# 


import argparse
import sys
import pytz
import re

parser = argparse.ArgumentParser(description="Read events from Google Calendar API and post on Slack")

# Add the optional positional argument
parser.add_argument("command", nargs='?', default=None, help="The optional command. Valid choices: daily_events (default), weekly_transfers")

# Parse the arguments
args = parser.parse_args()

# Access the input path argument
command = args.command

if not command:
  command="daily_events"
  

################################################################################################
# Part 1: Grab events using the Google Calendar API

from datetime import datetime, timezone, timedelta, date
import calendar
now = datetime.now(timezone.utc).astimezone()

# Default time delta is one min less than 16 hours to not catch events beginning
# at midnight if we post at 8 AM. Could be made more intelligent.
delta = timedelta(days=12, hours=15, minutes=59)
if command=="weekly_transfers":
	delta = timedelta(days=14)

end = now + delta

#print(now.isoformat())
#print(end.isoformat())

from dateutil import parser
import os.path
import math

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


"""Shows basic usage of the Google Calendar API.
"""
creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(creds.to_json())

try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            maxResults=200,
            singleEvents=True,
            orderBy="startTime",
            timeMax=end.isoformat()
        )
        .execute()
    )
    events = events_result.get("items", [])

    for event in events:
        if 'start' in event:
            if 'dateTime' in event['start']:
                event['start_timestamp'] = parser.parse(event['start']['dateTime']).timestamp()
            elif 'date' in event['start']:
                event['start_timestamp'] = parser.parse(event['start']['date']).timestamp()
                event['all_day'] = 1
        if 'end' in event:
            if 'dateTime' in event['end']:
                event['end_timestamp'] = parser.parse(event['end']['dateTime']).timestamp()
            elif 'date' in event['end']:
                event['end_timestamp'] = parser.parse(event['end']['date']).timestamp()
                event['all_day'] = 1

except HttpError as error:
    print(f"An error occurred: {error}")

#print(events)

if (command=="weekly_transfers"):
    events = [d for d in events if ('LTEE' in d['summary'].upper()) and ('TRANSFER' in d['summary'].upper())]

###################################################################################
# Part 2: Use the Slack API to send a message
#
# SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET need to be set in the slack_credentials.json file
# You must invite the App to that channel

import os
# Use the package we installed

from slack_bolt import App
from slack_sdk.errors import SlackApiError

import json

with open('slack.json') as slack_credentials_file:
  slack_credentials = json.load(slack_credentials_file)

# Initialize your app with your bot token and signing secret
app = App(
    token=slack_credentials["SLACK_BOT_TOKEN"],
    signing_secret=slack_credentials["SLACK_SIGNING_SECRET"]
)

channel_name = slack_credentials["CHANNEL"]
conversation_id = None
try:
    # Call the conversations.list method using the WebClient
    for result in app.client.conversations_list():
        if conversation_id is not None:
            break
        for channel in result["channels"]:
            if channel["name"] == channel_name:
                conversation_id = channel["id"]
                #Print result
                #print(f"Found conversation ID: {conversation_id}")
                break

except SlackApiError as e:
    print(f"Error: {e}")


################################################################################################
# Construct the post here from the Google API Event

summary_emojis = [
    { 'regexp' : r"LTEE\W+transfers", 'emoji' : ":ltee-flask:"},
    { 'regexp' : r"taco\W+train", 'emoji' : ":bullettrain_side:"},
    { 'regexp' : r"biotacos", 'emoji' : ":taco:"}
]

def prefix_emoji(message):
    for se in summary_emojis:
        if re.search (se['regexp'], message, flags=re.IGNORECASE):
            return se['emoji'] + "  "
    return ""

message = ""
if command=="daily_events":

    message +=  ":calendar: *Barrick Lab Events for " + calendar.day_name[now.weekday()] + " <!date^" + str(math.floor(now.timestamp())) + "^{date}|" + str(now) + "(US Central Time)>*\n\n"

    for event in events:
        #print(event)
        #print("\n")

        time_part = ""
        if not 'all_day' in event:
            if 'start_timestamp' in event:
                time_part +=  "<!date^" + str(math.floor(event['start_timestamp'])) + "^{time}|" + str(date.fromtimestamp(event['start_timestamp'])) + ">"
            if 'end_timestamp' in event:
                time_part +=  "–<!date^" + str(math.floor(event['end_timestamp'])) + "^{time}|" + str(date.fromtimestamp(event['end_timestamp'])) + ">"
            time_part += "  "

        emoji_part = ""
        summary_part = ""
        if 'summary' in event:
            emoji_part += prefix_emoji(event["summary"])
            summary_part +=  "*" + event["summary"] + "*" + "  "

        location_part = ""
        if 'location' in event:
            location_part += "(" + event['location'] + ")"
        #if 'description' in event:
        #    message += event['description'] + "\n"

        message += emoji_part + time_part + summary_part + location_part + "\n\n"

elif command=="weekly_transfers":

    end_of_week = now + timedelta(days=6)
    message +=  ":ltee-flask: *Upcoming LTEE Transfers for the week of " 
    message +=  "<!date^" + str(math.floor(now.timestamp())) + "^{date}|" + str(now.date()) + "> to "
    message +=  "<!date^" + str(math.floor(end_of_week.timestamp())) + "^{date}|" + str(end_of_week.date()) + ">*"
    message += "\n"

    ## Check whether each day at this time overlaps the events
    for i in range(0,7):
        transfer_delta = timedelta(days=i)
        transfer_date = now + transfer_delta
        print(transfer_date)

        local_tz = 'US/Central'

        #Find the overlapping event
        for event in events:
            event_start = datetime.fromtimestamp(event['start_timestamp']).astimezone(pytz.timezone(local_tz))
            event_end = datetime.fromtimestamp(event['end_timestamp']).astimezone(pytz.timezone(local_tz))
            
            who = event['summary']
            who = re.sub(r"LTEE\W*transfers*\W*-*\W*", "", who, flags=re.IGNORECASE)
            if transfer_date >= event_start and transfer_date <= event_end:
                message += "       " + calendar.day_name[transfer_date.weekday()] + ": " + who + "\n"

    message += ":ltee-flask: *Evolve, LTEE, evolve!*\n"

if message != "":
    app.client.api_call(
        api_method='chat.postMessage',
        json={'channel':conversation_id, 'text':message}
    )
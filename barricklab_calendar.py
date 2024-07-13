###################################################################################
#
# This uses the Google Calendar API
#
# You need to create and download credentials.json and then log into
# the Google account that is being used to create token.json
# using these directions: https://developers.google.com/calendar/api/quickstart/python
# 

from datetime import datetime, timezone, timedelta
import calendar
now = datetime.now(timezone.utc).astimezone()
onedaydelta = timedelta(days=1)

#print(now.isoformat())
onedayhence = now + onedaydelta
#print(onedayhence.isoformat())

import datetime
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
            timeMax=onedayhence.isoformat()
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



###################################################################################
# This uses the Slack API to send a message
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


message = ""
message +=  ":calendar: *Barrick Lab Events for " + calendar.day_name[now.weekday()] + " <!date^" + str(math.floor(now.timestamp())) + "^{date}|" + str(now) + "(US Central Time)>*\n\n"

for event in events:
    #print(event)
    #print("\n")


    if not 'all_day' in event:
        if 'start_timestamp' in event:
            message +=  "<!date^" + str(math.floor(event['start_timestamp'])) + "^{time}|" + str(datetime.date.fromtimestamp(event['start_timestamp'])) + ">"
        if 'end_timestamp' in event:
            message +=  "–<!date^" + str(math.floor(event['end_timestamp'])) + "^{time}|" + str(datetime.date.fromtimestamp(event['end_timestamp'])) + ">"
        message += "  "

    if 'summary' in event:
        message += "*" + event["summary"] + "*\n"
    if 'location' in event:
        message += "Location: " + event['location'] + "\n"
    #if 'description' in event:
    #    message += event['description'] + "\n"

    message += "\n"

app.client.api_call(
    api_method='chat.postMessage',
    json={'channel':conversation_id, 'text':message}
)
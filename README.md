# Barrick Lab Google Calendar -> Slack Daily Events

## Setup

You have to set up a number of things to communicate for this to work!

## Slack

Create an App in your workspace.

It needs to have these permissions:
```
channels:read
chat:write
```

You will need to set up a file called `slack.json` with the credentials so that your script can post on Slack.

```
{
	"SLACK_BOT_TOKEN":"XXXXXXXXXXXXXXX", 
	"SLACK_SIGNING_SECRET":"XXXXXXXXXXXXXXX",
	"CHANNEL":"general"
}
```

## Google Calendar

Set up a Google App using [https://developers.google.com/calendar/api/quickstart/python](these directions). Use the Calendar owner's Google account for Google Cloud. Add this email as the test user. Enable the Google Calendar API. You need to give permission to read events. You will need to download `credentials.json` from here.

## Local Setup

```bash
conda create -n slackapp python
conda activate slackapp
pip -r requirements.txt
```

Now check that it works on your local machine. You must do this to authorize for Google.
```bash
python barricklab_calendar.py
```
After run this once, you should have a local `token.json` file. Youc an copy this to another machine (the server) and it will work.

## Server Setup

You need a machine with an internet connection that is on all the time to call this at specified time.

On that machine, set up the Conda environment.

Then, add something like this to your crontab to have it run each day at 8 AM.

```
sudo crontab -e
```

```bash
PATH=/home/jbarrick/.conda/envs/slackapp/bin
0 8 * * * (cd /home/jbarrick/barricklab_calendar; python barricklab_calendar.py >> /home/jbarrick/barricklab_calendar/logs.log 2>&1)
```

Of course, fix the paths to the Conda environment bin directory and the source code.

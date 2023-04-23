import requests
import feedparser
import time
import json
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Variable loader
def getvar(variable_name, default=''):
    var = os.getenv(variable_name)
    filevar = os.getenv(variable_name + '_FILE')
    filevarcontent = ''
    if filevar:
        filevarpath = Path(filevar)
        if filevarpath.exists():
            with open(filevarpath, 'r') as f:
                filevarcontent = f.readline().strip()

    if var and filevarcontent:
        logging.warning('An environment variable and a Docker Secret have been set for ' + variable_name + '. The Docker Secret will be ignored.')
    
    if var:
        val = var
    elif filevarcontent:
        val = filevarcontent
    else:
        val = default

    return val

# Load log level from env variable and capitalize
LOG_LEVEL = getvar('LOG_LEVEL', 'WARNING')
upper_level = LOG_LEVEL.upper()
#Check if log level is valid
if not any(s in upper_level for s in ('ERROR', 'WARNING', 'INFO', 'DEBUG')):
    upper_level = 'WARNING'
    logging.basicConfig(level=upper_level, format='%(asctime)s - %(levelname)s: %(message)s', encoding='utf-8')
    logging.warning('Invalid LOG_LEVEL: "' + LOG_LEVEL + '". Allowed values: ERROR, WARNING, INFO or DEBUG')
    logging.warning('Setting LOG_LEVEL to WARNING')
#Set log level and format
logging.basicConfig(level=upper_level, format='%(asctime)s - %(levelname)s: %(message)s', encoding='utf-8')
logging.info('Log level is set to ' + upper_level)


# String to Boolean
def str2bool(str):
    return str.lower() in ("yes", "true", "t", "1")

# Notification service
NOTIFICATION_SERVICE = getvar('NOTIFICATION_SERVICE', 'ntfy')

# Feed URL
FEED_URL = getvar('FEED_URL', 'https://rpilocator.com/feed/')

# ntfy settings
NTFY_BASE_URL = getvar('NTFY_BASE_URL', 'https://ntfy.sh')
NTFY_TOPIC = getvar('NTFY_TOPIC')
NTFY_PRIORITY = getvar('NTFY_PRIORITY', 'default')
NTFY_EMOJI = getvar('NTFY_EMOJI', 'white_check_mark')

# Gotify settings
GOTIFY_BASE_URL = getvar('GOTIFY_BASE_URL')
GOTIFY_TOKEN = getvar('GOTIFY_TOKEN')
GOTIFY_PRIORITY = int(getvar('GOTIFY_PRIORITY', 5))

# After creating your pushbullet account, create an 
# Access Token and enter it here
PUSHBULLET_TOKEN = getvar('PUSHBULLET_TOKEN')

# After creating your Pushover account, register your application
# User Key
PUSHOVER_KEY = getvar('PUSHOVER_KEY')
# Application Key
PUSHOVER_API_KEY = getvar('PUSHOVER_API_KEY')
# Priority
PUSHOVER_PRIORITY = int(getvar('PUSHOVER_PRIORITY', 0))
# Sound
PUSHOVER_SOUND = getvar('PUSHOVER_SOUND')

# Initial notifications
INITIAL_NOTIFICATION = str2bool(getvar('INITIAL_NOTIFICATION', 'False'))
ONLINE_NOTIFICATION = str2bool(getvar('ONLINE_NOTIFICATION', 'True'))

# Customize the message title
MESSAGE_TITLE = getvar('MESSAGE_TITLE', 'Pilocator Stock Alert')

# User Agent
USER_AGENT = getvar('USER_AGENT', 'pilocator feed alert')

#List all variables in debug mode
logging.debug('------------------------------------')
logging.debug('Env variables:')
logging.debug('LOG_LEVEL: ' + LOG_LEVEL)
logging.debug('NOTIFICATION_SERVICE: ' + NOTIFICATION_SERVICE)
logging.debug('FEED_URL: ' + FEED_URL)
logging.debug('NTFY_BASE_URL: ' + NTFY_BASE_URL)
logging.debug('NTFY_TOPIC: ' + NTFY_TOPIC)
logging.debug('NTFY_PRIORITY: ' + NTFY_PRIORITY)
logging.debug('NTFY_EMOJI: ' + NTFY_EMOJI)
logging.debug('GOTIFY_BASE_URL: ' + GOTIFY_BASE_URL)
logging.debug('GOTIFY_TOKEN: ' + GOTIFY_TOKEN)
logging.debug('GOTIFY_PRIORITY: ' + str(GOTIFY_PRIORITY))
logging.debug('PUSHBULLET_TOKEN: ' + PUSHBULLET_TOKEN)
logging.debug('PUSHOVER_KEY: ' + PUSHOVER_KEY)
logging.debug('PUSHOVER_API_KEY: ' + PUSHOVER_API_KEY)
logging.debug('PUSHOVER_PRIORITY: ' + str(PUSHOVER_PRIORITY))
logging.debug('PUSHOVER_SOUND: ' + PUSHOVER_SOUND)
logging.debug('INITIAL_NOTIFICATION: ' + str(INITIAL_NOTIFICATION))
logging.debug('ONLINE_NOTIFICATION: ' + str(ONLINE_NOTIFICATION))
logging.debug('MESSAGE_TITLE: ' + MESSAGE_TITLE)
logging.debug('USER_AGENT: ' + USER_AGENT)
logging.debug('------------------------------------')



# Create the message body
def formatMessage(entry):

    match NOTIFICATION_SERVICE:
        case 'ntfy':
            message = entry.title + '\n\n' + 'Link: ' + entry.link
        
        case 'gotify':
            message = {
                'title': MESSAGE_TITLE,
                'message': entry.title + ': ' + entry.link,
                'priority': GOTIFY_PRIORITY,
                'extras': {
                    'client::notification': {
                        'click': {
                            'url': entry.link
                        }
                    }
                }
            }

            message = json.dumps(message)
        
        case 'pushbullet':
            message = {'type': 'link', 'title': MESSAGE_TITLE, 'body': entry.title, 'url': entry.link}

            message = json.dumps(message)

        case 'pushover':
            logging.debug('Creating Pushover message body')
            messageData = 'token='+PUSHOVER_API_KEY+'&user='+PUSHOVER_KEY+'&title='+MESSAGE_TITLE+'&priority='+str(PUSHOVER_PRIORITY)+'&sound='+PUSHOVER_SOUND
            message = messageData+'&message='+entry.title+'&url='+entry.link
            logging.debug('Message: ' + message)

    return message


# Send the push/message to all devices connected to ntfy
def sendMessage(message):

    match NOTIFICATION_SERVICE:
        case 'ntfy':
            headers = {
                    'Title': MESSAGE_TITLE,
                    'Priority': NTFY_PRIORITY,
                    'Tags': NTFY_EMOJI
            }
            
            try:
                logging.info('Sending ntfy message')
                req = requests.post(url=NTFY_BASE_URL + '/' + NTFY_TOPIC, data=message, headers=headers, timeout=20)
            except requests.exceptions.Timeout:
                logging.warning('Request Timeout')
                pass
            except requests.exceptions.TooManyRedirects:
                logging.warning('Too many requests')
                pass
            except requests.exceptions.RequestException as e:
                logging.warning(e)
                pass
        
        case 'gotify':
            headers = {'Content-Type': 'application/json'}
    
            try:
                logging.info('Sending Gotify message')
                req = requests.post(url=GOTIFY_BASE_URL + '/message?token=' + GOTIFY_TOKEN, data=message, headers=headers, timeout=20)
            except requests.exceptions.Timeout:
                logging.warning('Request Timeout')
                pass
            except requests.exceptions.TooManyRedirects:
                logging.warning('Too many requests')
                pass
            except requests.exceptions.RequestException as e:
                logging.warning(e)
                pass
        
        case 'pushbullet':
            headers = {'Access-Token': PUSHBULLET_TOKEN, 'Content-Type': 'application/json'}
    
            try:
                logging.info('Sending Pushbullet message')
                req = requests.post(url='https://api.pushbullet.com/v2/pushes', data=message, headers=headers, timeout=20)
            except requests.exceptions.Timeout:
                logging.warning('Request Timeout')
                pass
            except requests.exceptions.TooManyRedirects:
                logging.warning('Too many requests')
                pass
            except requests.exceptions.RequestException as e:
                logging.warning(e)
                pass

        case 'pushover':
            try:
                logging.info('Sending Pushover message')
                req = requests.post(url='https://api.pushover.net/1/messages.json', data=message, timeout=20)
            except requests.exceptions.Timeout:
                logging.warning('Request Timeout')
                pass
            except requests.exceptions.TooManyRedirects:
                logging.warning('Too many requests')
                pass
            except requests.exceptions.RequestException as e:
                logging.warning(e)
                pass





# Set control to blank list
logging.debug('Empty control list variable')
control = []

# Fetch the feed
logging.info('Fetching the feed')
logging.debug('Feed URL: ' + FEED_URL)
f = feedparser.parse(FEED_URL, agent=USER_AGENT)

class Message(object):
    pass

# Send online message
if ONLINE_NOTIFICATION == True:
    logging.info('ONLINE_NOTIFICATION is True, sending welcome message')
    firstmessage = Message()
    firstmessage.title = 'Hello, I am online'
    firstmessage.link = 'https://github.com/camerahacks/rpilocator-rss-feed'
    message = formatMessage(firstmessage)
    sendMessage(message)

# If there are entries in the feed, add entry guid to the control variable
if f.entries:
    logging.info('Feed contains existing entries')
    for entries in f.entries:
        if INITIAL_NOTIFICATION == True:
            logging.info('INITIAL_NOTIFICATION is True, sending a message for each existing entry')
            message = formatMessage(entries)
            sendMessage(message)
        else:
            logging.info('Waiting for new entries')
        logging.debug('Adding entry GUID ' + entries.id + ' to control list variable')
        control.append(entries.id)
        logging.debug('Current GUIDs in control variable: ' + str(control))
else:
    logging.warning('Feed contains no entries!')

#Only wait 30 seconds after initial run.
logging.debug('Waiting 30 seconds after initial run')
time.sleep(30)

logging.debug('Starting main loop')
while True:
    # Fetch the feed again, and again, and again...
    logging.debug('Fetching the feed again')
    f = feedparser.parse(FEED_URL, agent=USER_AGENT)

    # Compare feed entries to control list.
    # If there are new entries, send a message/push
    # and add the new entry to control variable
    for entries in f.entries:
        if entries.id not in control:
            logging.info('Found new entry')
            message = formatMessage(entries)
            
            sendMessage(message)

            # Add entry guid to the control variable
            logging.debug('Adding entry GUID ' + entries.id + ' to control list variable')
            control.append(entries.id)
            logging.debug('Current GUIDs in control list variable: ' + str(control))
    else:
        logging.debug('No new entries found')
    
    logging.debug('Waiting 59 seconds and repeat loop')
    time.sleep(59)
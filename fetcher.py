import signal
import sys
import time

import logging
import ConfigParser

from dateutil import tz
from datetime import datetime
from datetime import timedelta

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.api.logservice import logservice
import getpass
import simplejson as json
import base64

RECOVERY_LOG = '/tmp/recovery.log'
PERIOD_LENGTH = timedelta(minutes=2)
PERIOD_END_NOW = timedelta(minutes=1)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


def termination_handler(signal, frame):
    logger.info('Shutting down')
    sys.exit(0)

def get_time_period():
    end = datetime.utcnow() - PERIOD_END_NOW 
    #seconds=0
    end = datetime(end.year, end.month, end.day, end.hour, end.minute, 0)
    end = end.replace(tzinfo=tz.tzutc())
    # GAE logservice API expects UTC - although req_log.combined will show PDT timestamps
    start = end - PERIOD_LENGTH
    return {'start':start, 'end':end}

def fetch_logs(time_period, recovery_log, username, password, app_name, version_ids, offset=None):
    f = lambda : (username, password)

    remote_api_stub.ConfigureRemoteApi(None, '/remote_api', f, app_name)
    version_ids = version_ids
   
    end = int(time_period['end'].strftime("%s"))
    start = int(time_period['start'].strftime("%s"))

    logger.info("Fetching logs for %s %s" % (time_period['start'],time_period['end']))

    for req_log in logservice.fetch(end_time=end, 
            start_time=start, 
            minimum_log_level=logservice.LOG_LEVEL_INFO, 
            version_ids=version_ids, 
            include_app_logs=True, include_incomplete=True, 
            offset=offset):
        logger.info(req_log.combined)
        # end fetch
    
    return ""

if __name__ == '__main__':
    signal.signal(signal.SIGINT, termination_handler)
    signal.signal(signal.SIGTERM, termination_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('fetcher.conf')
    
    username = config.get('GAE','username')
    password = config.get('GAE','password')
    app_name = config.get('GAE','app_name')
    version_ids = ['1']
    offset = None
    fetch_logs(get_time_period(), RECOVERY_LOG, username, password, app_name, version_ids, offset)



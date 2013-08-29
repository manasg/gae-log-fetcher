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
GAE_TZ = 'America/Los_Angeles'

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

last_offset = None
last_time_period = None

def _get_level(level):
    # TODO - better? 
    if logservice.LOG_LEVEL_DEBUG == level:
        return "DEBUG"
    if logservice.LOG_LEVEL_INFO == level:
        return "INFO"
    if logservice.LOG_LEVEL_WARNING == level:
        return "WARNING"
    if logservice.LOG_LEVEL_ERROR == level:
        return "ERROR"
    if logservice.LOG_LEVEL_CRITICAL == level:
        return "CRITICAL"
    
    return "UNKNOWN"

def _prepare_json(req_log):
    """Prepare JSON in logstash json_event format"""
    data = {}
    data['response'] = req_log.status
    data['latency_ms'] = req_log.latency
    
    # UTC Timestamp - this helps if events are not coming in chronological order
    t = datetime.fromtimestamp(req_log.end_time)
    t = t.replace(tzinfo=tz.tzutc())
    data['@timestamp'] = t.isoformat()
    
    # processing APP Logs
    msg = req_log.combined
    if len(req_log.app_logs) > 0:
        app_log_msgs = []
        for app_log in req_log.app_logs:
            t = datetime.fromtimestamp(app_log.time)
            t = t.replace(tzinfo=tz.tzutc())
            t = t.astimezone(tz.gettz(GAE_TZ))
            l = _get_level(app_log.level)
            app_log_msgs.append("\t%s %s %s" 
                %(t.isoformat(), l, app_log.message) )
        #
        msg += "\n".join(app_log_msgs)

    data['@message'] = msg
    
    return json.dumps(data)


def termination_handler(signal, frame):
    _offset = base64.urlsafe_b64encode(str(last_offset))

    logger.info("Shutting down. Was processing : %s %s " 
            %(last_time_period, _offset))
    sys.exit(0)

def get_time_period():
    end = datetime.utcnow() - PERIOD_END_NOW 
    #seconds=0
    end = datetime(end.year, end.month, end.day, end.hour, end.minute, 0)
    end = end.replace(tzinfo=tz.tzutc())
    # GAE logservice API expects UTC - although req_log.combined will show PDT timestamps
    start = end - PERIOD_LENGTH

    gae_tz = tz.gettz(GAE_TZ)
    return {'start':start, 'end':end, 
        'start_gae_tz':start.astimezone(gae_tz), 'end_gae_tz':end.astimezone(gae_tz)}

def fetch_logs(time_period, recovery_log, username, password, app_name, version_ids, offset=None, dest="/tmp/gae_log.log"):
    f = lambda : (username, password)

    remote_api_stub.ConfigureRemoteApi(None, '/remote_api', f, app_name)
    version_ids = version_ids
   
    end = int(time_period['end'].strftime("%s"))
    start = int(time_period['start'].strftime("%s"))

    logger.info("Fetching logs from %s to %s (GAE TZ)" 
            % (time_period['start_gae_tz'],time_period['end_gae_tz']))

    # TODO - move to classes instead of globals
    global last_time_period 
    last_time_period = time_period
   
    i = 0
    f = open(dest,'w')
    try:
        for req_log in logservice.fetch(end_time=end, 
                start_time=start, 
                minimum_log_level=logservice.LOG_LEVEL_INFO, 
                version_ids=version_ids, 
                include_app_logs=True, include_incomplete=True, 
                offset=offset):
            
            logger.debug("Retrieved - %s" % req_log.combined)
            
            i = i + 1
            if i % 100 == 0:
                logger.info("Fetched %d logs so far" % i)

            f.write(_prepare_json(req_log))
            f.write('\n')

            # keeping track in case - if need to resume
            global last_offset 
            last_offset = req_log.offset
            # end fetch
    except:
        pass
    
    logger.info("Retrieved %d logs" % i)

    f.close()
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



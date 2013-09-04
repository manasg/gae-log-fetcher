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

import argparse

RECOVERY_LOG = '/tmp/recovery.log'
PERIOD_LENGTH = timedelta(minutes=2)
PERIOD_END_NOW = timedelta(minutes=1)
GAE_TZ = tz.gettz('US/Pacific')

logger = logging.getLogger()

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
    
    # Timestamp - this helps if events are not coming in chronological order
    t = datetime.fromtimestamp(req_log.end_time)
    t = t.replace(tzinfo=GAE_TZ)
    data['@timestamp'] = t.isoformat()
    
    # processing APP Logs
    msg = req_log.combined
    if len(req_log.app_logs) > 0:
        app_log_msgs = []
        for app_log in req_log.app_logs:
            t = datetime.fromtimestamp(app_log.time)
            t = t.replace(tzinfo=GAE_TZ)
            l = _get_level(app_log.level)
            app_log_msgs.append("%s %s %s" 
                %(t.isoformat(), l, app_log.message) )

        # The new lines give it more readability in Kibana
        msg = msg + "\n\n" + "\n".join(app_log_msgs)

    data['@message'] = msg
    
    return json.dumps(data)


def termination_handler(signal, frame):
    _offset = base64.urlsafe_b64encode(str(last_offset))

    logger.info("Shutting down. Was processing : %s %s " 
            %(last_time_period, _offset))
    sys.exit(0)

def get_time_period():
    # GAE logservice API expects everything in PDT
    gae_tz = GAE_TZ

    end = datetime.now(gae_tz) - PERIOD_END_NOW 
    #seconds, microsecond =0
    end = datetime(end.year, end.month, end.day, end.hour, end.minute, 0,0, end.tzinfo)
    start = end - PERIOD_LENGTH
    
    e = int(end.strftime("%s"))
    s = int(start.strftime("%s"))

    return {'start':s, 'end':e, 'start_human':start, 'end_human':end} 

def fetch_logs(time_period, recovery_log, username, password, app_name, version_ids, offset=None, dest="/tmp/gae_log.log",append=False):
    f = lambda : (username, password)

    remote_api_stub.ConfigureRemoteApi(None, '/remote_api', f, app_name)
    version_ids = version_ids
   
    end = time_period['end']
    start = time_period['start']

    logger.info("Fetching logs from %s to %s (GAE TZ)" 
            % (time_period['start_human'],time_period['end_human']))

    # TODO - move to classes instead of globals
    global last_time_period 
    last_time_period = time_period
   
    i = 0
    
    if append:
        mode = 'a'
    else:
        mode = 'w'
    
    f = open(dest, mode)

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

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    

    # other run time options
    parser = argparse.ArgumentParser()
    parser.add_argument("log_dump_file", help="Name of file to dump logs in Json")
    parser.add_argument("--append", help="Append instead of overwrite to log-dump-file", action='store_true')
    parser.add_argument("--gae_config", 
            help="Config file for GAE user, pass, app. If not specified, it looks for fetcher.conf")

    parser.add_argument("--debug", help="use DEBUG log level", action='store_true')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    dump = args.log_dump_file
    append = args.append

    # getting app name & credentials from a file
    conf = args.gae_config or 'fetcher.conf'

    config = ConfigParser.SafeConfigParser()
    config.read(conf)
    
    username = config.get('GAE','username')
    password = config.get('GAE','password')
    app_name = config.get('GAE','app_name')
    version_ids = ['1']

    offset = None
    fetch_logs(get_time_period(), RECOVERY_LOG, username, password, app_name, version_ids, offset, dump, append)



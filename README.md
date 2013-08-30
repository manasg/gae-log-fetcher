Why?
====
Certain Operational (Ops) tasks on GAE can be tedious. The log browsing experience for example could be improved.

Yes, you can download logs via appcfg (https://developers.google.com/appengine/docs/python/tools/uploadinganapp#Python_Downloading_logs). However, GAE seems to have an undocumented 100M log buffer. Appcfg can only download that. You need to run appcfg very frequently to empty the buffer otherwise logs are lost***. In our case - this was a big issue as req logs + app logs were resulting in a lot of data. We like our logs :)  

The API does not have any such restriction, as long as you have billing + log retention setup properly.

I love Kibana + ES (+ Logstash) - so getting GAE logs in the same place... is nice.

Pre-req
=======

- You need to turn on remote_api for your GAE app

- Install yaml,simplejson module -> sudo pip install PyYAML

- Download GAE SDK - python/linux - http://googleappengine.googlecode.com/files/google_appengine_1.8.3.zip

- Unzip to a folder and include it in path

- export PYTHONPATH=/repos/gae-log-fetcher/gae_sdk/google_appengine:/repos/gae-log-fetcher/gae_sdk/google_appengine/lib/fancy_urllib/

- The important part is fancy_urllib :)

Test Setup
==========
Fire up py interpreter - and test the imports

Configuration
=============
fetcher.conf contains the GAE app_name, username and password. If running this interactively (or if you don't want to keep your password in a file) - you can replace the lambda function in the code.

Usage
=====
Interactively
-------------
export PYTHONPATH=......
python fetcher.py -h

via cron
--------
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games
PYTHONPATH=/home/manas/gae-log-fetcher/gae_sdk/google_appengine:/home/manas/gae-log-fetcher/gae_sdk/google_appengine/lib/fancy_urllib
*/2 * * * * cd /home/manas/gae-log-fetcher; /usr/bin/python fetcher.py /mnt/gae_logs/gae.log --append >> /mnt/gae_logs/fetcher.log 2>&1

Logstash Integration
====================
The goal was to get GAE logs into Elasticsearch. We already have a Logstash-ES infrastructure setup with redundancy and buffering (Redis). Hence I leverage that. I write the logs as json_events to a file where logstash picks them up. 

Json_Event is nice - as it saves a tonne of cycles on filtering etc. To know more about it - http://cookbook.logstash.net/recipes/apache-json-logs/

GAE Logservice API
==================
https://developers.google.com/appengine/docs/python/logs/

A side note - I used the Python API to get the logs - even though the app is in Java. 

TODO
====
[ ] Write a function to recover/resume interrupted downloads. It goes through the log and picks up incomplete runs (I log offset and time period). 



*** Another way to simulate it - try fetching logs from a past time period (more than 100M). This restriction happens even if you have billing + log retention set to 30 days.

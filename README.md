Pre-req
=======

- Install yaml,simplejson module -> sudo pip install PyYAML

- Download GAE SDK - python/linux - http://googleappengine.googlecode.com/files/google_appengine_1.8.3.zip
-- Unzip to a folder and include it in path

-- export PYTHONPATH=/repos/gae-log-fetcher/gae_sdk/google_appengine:/repos/gae-log-fetcher/gae_sdk/google_appengine/lib/fancy_urllib/

-- The important part is fancy_urllib :)

Test Setup
==========
Fire up py interpreter - and test the imports

Configuration
=============
fetcher.conf contains the GAE app_name, username and password. If running this interactively (or if you don't want to keep your password in a file) - you can replace the lambda function in the code.

Usage
=====

Logstash Integration
====================
The goal was to get GAE logs into Elasticsearch. We already have a Logstash-ES infrastructure setup with redundancy and buffering (Redis). Hence I leverage that. I write the logs as json_events to a file where logstash picks them up. 

Json_Event is nice - as it saves a tonne of cycles on filtering etc. To know more about it - http://cookbook.logstash.net/recipes/apache-json-logs/




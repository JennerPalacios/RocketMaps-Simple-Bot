#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime
from cachetools import LFUCache
from requests_futures.sessions import FuturesSession
import threading
from .utils import get_args
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json

log = logging.getLogger(__name__)

# How low do we want the queue size to stay?
wh_warning_threshold = 100
# How long can it be over the threshold, in seconds?
# Default: 5 seconds per 100 in threshold.
wh_threshold_lifetime = int(5 * (wh_warning_threshold / 100.0))
wh_lock = threading.Lock()

args = get_args()

#########################################################
# CREATE DEFAULT FILTER TO SKIP CERTAIN POKEMONS
# ADD POKEMON THAT NEEDS SPECIFIC IV FILTER
# ADD "0" TO POKEMON THAT WILL BE POSTED NO MATTER IV
#########################################################
globalDefault = 100
globalFilter = {
1: 90,
2: 80,
3: 50,
4: 80,
5: 80,
6: 50,
7: 80,
8: 80,
9: 50,
25: 90,
26: 90,
31: 90,
34: 90,
35: 90,
36: 90,
37: 90,
38: 50,
39: 90,
40: 90,
43: 90,
44: 80,
45: 50,
56: 90,
57: 90,
58: 90,
59: 90,
60: 90,
61: 90,
62: 90,
63: 90,
64: 80,
65: 50,
66: 90,
67: 90,
68: 50,
69: 95,
70: 90,
71: 90,
72: 95,
73: 95,
74: 90,
75: 90,
76: 50,
77: 90,
78: 90,
79: 90,
80: 80,
86: 90,
87: 90,
88: 0,
89: 0,
90: 95,
91: 90,
92: 95,
93: 95,
94: 90,
95: 90,
102: 90,
103: 80,
106: 0,
107: 0,
108: 95,
111: 90,
112: 80,
113: 0,
114: 0,
116: 90,
117: 90,
122: 0,
123: 95,
124: 95,
125: 95,
126: 95,
127: 95,
128: 90,
129: 90,
130: 80,
131: 0,
132: 0,
133: 95,
134: 50,
135: 50,
136: 50,
137: 0,
138: 95,
139: 90,
140: 95,
141: 90,
142: 90,
143: 0,
144: 0,
145: 0,
146: 0,
147: 0,
148: 0,
149: 0,
150: 0,
151: 0,
152: 95,
153: 90,
154: 50,
155: 80,
156: 80,
157: 50,
158: 80,
159: 80,
160: 50,
169: 90,
176: 0,
179: 0,
180: 0,
181: 0,
185: 90,
191: 90,
201: 0,
204: 80,
205: 80,
209: 90,
210: 80,
214: 0,
215: 90,
216: 90,
217: 80,
226: 95,
227: 95,
228: 90,
229: 50,
231: 90,
232: 50,
234: 90,
237: 50,
241: 0,
242: 0,
246: 0,
247: 0,
248: 0
}
#########################################################
# END OF CUSTOM AND GLOBAL IV FILTER
#########################################################

def send_to_webhook(session, message_type, message):
    args = get_args()

def send_to_webhook(session, message_type, message):
    if not args.webhooks:
        # What are you even doing here...
        log.warning('Called send_to_webhook() without webhooks.')
        return

    req_timeout = args.wh_timeout
   
#########################################################
# CHECK IF IT IS A "POKEMON" BEFORE MOVING FORWARD
#########################################################
    if not message_type == 'pokemon':
        log.info('Non Pokemon: ' + message_type)
        return
    
#########################################################
# CHECK "POKEMON" HAS ID - IT IS NOT A LURED POKESTOP
#########################################################
    id = message.get("pokemon_id")
    if not id:
        return
        
#########################################################
# CHECK FOR INDIVIDUAL ATTACK TO MAKE SURE POKEMON IS
# BEING ENCOUNTERED, AND THERE IS DATA TO KEEP GOING FORWARD
# AND CALCULATE IV, IF NO DATA, IV = 0, WILL NOT POST
#########################################################
    indatk = message.get("individual_attack")
    iv = 0
    if indatk:
        iv = ((int(message["individual_attack"]) + int(message["individual_defense"]) + int(message["individual_stamina"])) * 100) / 45
    
#########################################################
# GRAB IV FROM FILTER LIST ABOVE, IF LOWER IGNORE WEBHOOK
#########################################################
    requirediv = globalFilter.get(id, globalDefault)
    if iv < requirediv:
        # log.info("PokemonID ## " + str(id) + " ## found with IV ## " + str(iv) + " ##, but it required ## " + str(requirediv) + " ## in order to send.")
        return

#########################################################
# FORMAT INFORMATION AS JSON, ADD IT TO DATA ('content': jsonMessage,)
#########################################################
    jsonMessage = json.dumps(message)

    data = {
        'content': jsonMessage,
        'type': message_type,
        'message': message
    }

    for w in args.webhooks:
        try:
            session.post(w, json=data, timeout=(None, req_timeout),
                         background_callback=__wh_completed)
        except requests.exceptions.ReadTimeout:
            log.exception('Response timeout on webhook endpoint %s.', w)
        except requests.exceptions.RequestException as e:
            log.exception(repr(e))


def wh_updater(args, queue, key_caches):
    wh_threshold_timer = datetime.now()
    wh_over_threshold = False

    # Set up one session to use for all requests.
    # Requests to the same host will reuse the underlying TCP
    # connection, giving a performance increase.
    session = __get_requests_session(args)

    # Extract the proper identifier. This list also controls which message
    # types are getting cached.
    ident_fields = {
        'pokestop': 'pokestop_id',
        'pokemon': 'encounter_id',
        'gym': 'gym_id',
        'gym_details': 'gym_id'
    }

    # Instantiate WH LFU caches for all cached types. We separate the caches
    # by ident_field types, because different ident_field (message) types can
    # use the same name for their ident field.
    for key in ident_fields:
        key_caches[key] = LFUCache(maxsize=args.wh_lfu_size)

    # The forever loop.
    while True:
        try:
            # Loop the queue.
            whtype, message = queue.get()

            # Get the proper cache if this type has one.
            key_cache = None

            if whtype in key_caches:
                key_cache = key_caches[whtype]

            # Get the unique identifier to check our cache, if it has one.
            ident = message.get(ident_fields.get(whtype), None)

            # cachetools in Python2.7 isn't thread safe, so we add a lock.
            with wh_lock:
                # Only send if identifier isn't already in cache.
                if ident is None or key_cache is None:
                    # We don't know what it is, or it doesn't have a cache,
                    # so let's just log and send as-is.
                    log.debug(
                        'Sending webhook item of uncached type: %s.', whtype)
                    send_to_webhook(session, whtype, message)
                elif ident not in key_cache:
                    key_cache[ident] = message
                    log.debug('Sending %s to webhook: %s.', whtype, ident)
                    send_to_webhook(session, whtype, message)
                else:
                    # Make sure to call key_cache[ident] in all branches so it
                    # updates the LFU usage count.

                    # If the object has changed in an important way, send new
                    # data to webhooks.
                    if __wh_object_changed(whtype, key_cache[ident], message):
                        key_cache[ident] = message
                        send_to_webhook(session, whtype, message)
                        log.debug('Sending updated %s to webhook: %s.',
                                  whtype, ident)
                    else:
                        log.debug('Not resending %s to webhook: %s.',
                                  whtype, ident)

            # Helping out the GC.
            del whtype
            del message
            del ident

            # Webhook queue moving too slow.
            if (not wh_over_threshold) and (
                    queue.qsize() > wh_warning_threshold):
                wh_over_threshold = True
                wh_threshold_timer = datetime.now()
            elif wh_over_threshold:
                if queue.qsize() < wh_warning_threshold:
                    wh_over_threshold = False
                else:
                    timediff = datetime.now() - wh_threshold_timer

                    if timediff.total_seconds() > wh_threshold_lifetime:
                        log.warning('Webhook queue has been > %d (@%d);'
                                    + ' for over %d seconds,'
                                    + ' try increasing --wh-concurrency'
                                    + ' or --wh-threads.',
                                    wh_warning_threshold,
                                    queue.qsize(),
                                    wh_threshold_lifetime)

            queue.task_done()
        except Exception as e:
            log.exception('Exception in wh_updater: %s.', repr(e))


# Helpers

# Background handler for completed webhook requests.
# Currently doesn't do anything.
def __wh_completed():
    pass


def __get_requests_session(args):
    # Config / arg parser
    num_retries = args.wh_retries
    backoff_factor = args.wh_backoff_factor
    pool_size = args.wh_concurrency

    # Use requests & urllib3 to auto-retry.
    # If the backoff_factor is 0.1, then sleep() will sleep for [0.1s, 0.2s,
    # 0.4s, ...] between retries. It will also force a retry if the status
    # code returned is 500, 502, 503 or 504.
    session = FuturesSession(max_workers=pool_size)

    # If any regular response is generated, no retry is done. Without using
    # the status_forcelist, even a response with status 500 will not be
    # retried.
    retries = Retry(total=num_retries, backoff_factor=backoff_factor,
                    status_forcelist=[500, 502, 503, 504])

    # Mount handler on both HTTP & HTTPS.
    session.mount('http://', HTTPAdapter(max_retries=retries,
                                         pool_connections=pool_size,
                                         pool_maxsize=pool_size))
    session.mount('https://', HTTPAdapter(max_retries=retries,
                                          pool_connections=pool_size,
                                          pool_maxsize=pool_size))

    return session


def __get_key_fields(whtype):
    key_fields = {
        # lure_expiration is a UTC timestamp so it's good (Y).
        'pokestop': ['enabled', 'latitude',
                     'longitude', 'lure_expiration', 'active_fort_modifier'],
        'pokemon': ['spawnpoint_id', 'pokemon_id', 'latitude', 'longitude',
                    'disappear_time', 'move_1', 'move_2',
                    'individual_stamina', 'individual_defense',
                    'individual_attack', 'form', 'cp'],
        'gym': ['team_id', 'guard_pokemon_id',
                'gym_points', 'enabled', 'latitude', 'longitude'],
        'gym_details': ['latitude', 'longitude', 'team', 'pokemon']
    }

    return key_fields.get(whtype, [])


# Determine if a webhook object has changed in any important way (and
# requires a resend).
def __wh_object_changed(whtype, old, new):
    # Only test for important fields: don't trust last_modified fields.
    fields = __get_key_fields(whtype)

    if not fields:
        log.debug('Received an object of unknown type %s.', whtype)
        return True

    return not __dict_fields_equal(fields, old, new)


# Determine if two dicts have equal values for all keys in a list.
def __dict_fields_equal(keys, a, b):
    for k in keys:
        if a.get(k) != b.get(k):
            return False

    return True

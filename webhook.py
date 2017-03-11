#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime
from requests_futures.sessions import FuturesSession
import threading
from .utils import get_args
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# spm - import json to handle stuff
import json

log = logging.getLogger(__name__)

# How low do we want the queue size to stay?
wh_warning_threshold = 100
# How long can it be over the threshold, in seconds?
# Default: 1 seconds per 100 in threshold.
wh_threshold_lifetime = int(5 * (wh_warning_threshold / 100.0))
wh_lock = threading.Lock()

#########################################################
# CREATE DEFAULT FILTER TO SKIP CERTAIN POKEMONS
# ADD POKEMON THAT NEEDS SPECIFIC IV FILTER
# ADD "0" TO POKEMON THAT WILL BE POSTED NO MATTER IV
#########################################################
globalDefault = 100
globalFilter = {
1: 30,
2: 0,
3: 0,
4: 30,
5: 0,
6: 0,
7: 30,
8: 0,
9: 0,
25: 30,
26: 0,
31: 0,
34: 0,
38: 0,
43: 30,
44: 0,
45: 0,
58: 30,
59: 0,
60: 30,
61: 0,
62: 0,
63: 30,
64: 0,
65: 0,
66: 30,
67: 0,
68: 0,
69: 30,
70: 0,
71: 0,
74: 30,
75: 0,
76: 0,
79: 30,
80: 0,
88: 0,
89: 0,
94: 0,
95: 30,
102: 30,
103: 0,
106: 0,
107: 0,
108: 30,
111: 30,
112: 0,
113: 0,
114: 0,
123: 30,
124: 30,
125: 30,
126: 30,
127: 30,
129: 38,
130: 0,
131: 0,
132: 0,
133: 30,
134: 0,
135: 0,
136: 0,
137: 0,
138: 30,
139: 0,
140: 30,
141: 0,
142: 0,
143: 0,
144: 0,
145: 0,
146: 0,
147: 0,
148: 0,
149: 0,
150: 0,
151: 0,
152: 40,
153: 0,
154: 0,
155: 40,
156: 0,
157: 0,
158: 40,
159: 0,
160: 0,
169: 40,
170: 40,
171: 40,
172: 40,
173: 40,
174: 40,
175: 40,
176: 0,
178: 40,
179: 0,
180: 0,
181: 0,
182: 0,
183: 30,
184: 0,
185: 40,
186: 0,
187: 30,
188: 0,
189: 0,
190: 30,
191: 10,
192: 0,
193: 10,
194: 30,
195: 10,
196: 0,
197: 0,
199: 0,
200: 30,
201: 0,
202: 40,
203: 40,
204: 40,
205: 10,
206: 10,
207: 40,
208: 0,
210: 10,
211: 30,
212: 0,
213: 30,
214: 0,
215: 30,
216: 40,
217: 0,
218: 10,
219: 0,
221: 30,
222: 10,
223: 40,
224: 0,
225: 0,
226: 40,
227: 40,
228: 30,
229: 0,
230: 0,
231: 40,
232: 0,
233: 0,
234: 10,
235: 0,
236: 0,
237: 0,
238: 30,
239: 30,
240: 30,
241: 0,
242: 0,
243: 0,
244: 0,
245: 0,
246: 0,
247: 0,
248: 0,
249: 0,
250: 0,
251: 0
}
#########################################################
# END OF CUSTOM AND GLOBAL IV FILTER
#########################################################

def send_to_webhook(session, message_type, message):
    args = get_args()

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
# AND CALCULATE IV, IF NO DATA, IV = -1, WILL NOT POST
#########################################################
    indatk = message.get("individual_attack")
    iv = parseInt(-1)
    if indatk:
        iv = ((int(message["individual_attack"]) + int(message["individual_defense"]) + int(message["individual_stamina"])) * 100) / 45
    
#########################################################
# GRAB IV FROM FILTER LIST ABOVE, IF LOWER IGNORE WEBHOOK
#########################################################
    requirediv = globalFilter.get(id, globalDefault)
    if iv < requirediv:
        log.info("PokemonID ## " + str(id) + " ## found with IV ## " + str(iv) + " ##, but it required ## " + str(requirediv) + " ## in order to send.")
        return

#########################################################
# FORMAT INFORMATION AS JSON, ADD IT TO DATA ('conent': jsonMessage,)
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


def wh_updater(args, queue, key_cache):
    wh_threshold_timer = datetime.now()
    wh_over_threshold = False

    # Set up one session to use for all requests.
    # Requests to the same host will reuse the underlying TCP
    # connection, giving a performance increase.
    session = __get_requests_session(args)

    # The forever loop.
    while True:
        try:
            # Loop the queue.
            whtype, message = queue.get()

            # Extract the proper identifier.
            ident_fields = {
                'pokestop': 'pokestop_id',
                'pokemon': 'encounter_id',
                'gym': 'gym_id'
            }
            ident = message.get(ident_fields.get(whtype), None)

            # cachetools in Python2.7 isn't thread safe, so we add a lock.
            with wh_lock:
                # Only send if identifier isn't already in cache.
                if ident is None:
                    # We don't know what it is, so let's just log and send
                    # as-is.
                    log.debug(
                        'Sending webhook item of unknown type: %s.', whtype)
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
                    'individual_attack'],
        'gym': ['team_id', 'guard_pokemon_id',
                'gym_points', 'enabled', 'latitude', 'longitude']
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
#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########
# Forked from github.com/abramhindle
# ALAIN CLARK
# (c) 2016
# Apache License (as above)
########

import flask
from flask import Flask, request, redirect, jsonify
from flask_sockets import Sockets
import json
'''The websocket interface that is passed into your routes is
provided by gevent-websocket. The basic methods are fairly
straightforward — send, receive, send_frame, and close.'''
import gevent
from gevent import queue

import time
import os

from greenlet import greenlet
'''
greenlet(run=None, parent=None)
Create a new greenlet object (without running it). run is the callable to invoke, and parent is the parent greenlet, which defaults to the current greenlet.
greenlet.getcurrent()
Returns the current greenlet (i.e. the one which called this function).
greenlet.GreenletExit
This special exception does not propagate to the parent greenlet; it can be used to kill a single greenlet.'''


app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

myClients = list()

def set_listener( entity, data ):
    ''' do something with the update ! '''
    for client in myClients:
        client.put(json.dumps({entity:data}))

myWorld = World()
myWorld.add_set_listener( set_listener )
watching = True

# Apparently client needs to be an object?
# https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
# v v v Below is from Abram's code v v v
#
class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, item):
        self.queue.put_nowait(item)

    def get(self):
        return self.queue.get()
#
# ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^

@app.route('/')
@app.route('/index')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect("/static/index.html",code=302); # ok


#readws = greenlet(read_ws)
def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    # XXX: BUT CAN WE USE GREENLET.py?
    while True:
        msg = ws.receive()
        if msg is not None:
            data = json.loads(msg)
            for key in data:
                myWorld.set(key, data[key])
        else:
            break

# https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py
# How the heck does anybody wade through this stuff?
# Abram you da real mvp
# v v v Below is /mostly/ from Abram's code v v v
#
@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    client = Client()
    myClients.append(client)
    watchEvent = gevent.spawn( read_ws, ws, client )

    try:
        while True:
            ws.send(client.get())
    except Exception as e:# WebSocketError as e:
        print "WS Error %s" % e
    finally:
        myClients.remove(client)
        gevent.kill(watchEvent)
# Based on:
'''
@sockets.route('/subscribe')
def subscribe_socket(ws):
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )
    try:
        while True:
            # block here
            msg = client.get()
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print "WS Error %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)
'''
# ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^

@sockets.route('/echo') # Test Echo server
def echo_socket(ws):
    while not ws.closed:
        message = ws.receive()
        ws.send(message)

def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])


@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    try:
        data = json.loads(request.data)
        for (key,val) in data.items():
            myWorld.update(entity, key, val)
    except: # could not update?
        pass
    return json.dumps(myWorld.get(entity))

@app.route("/world", methods=['POST','GET'])
def world():
    '''you should probably return the world here'''
    return json.dumps(myWorld.world());

@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return json.dumps(myWorld.get(entity));


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return json.dumps(myWorld.world());



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    # XXX: Can we use WebsocketHander?
    #from gevent import pywsgi
    #from geventwebsocket.handler import WebSocketHandler

    #server = pywsgi.WSGIServer(('', 8000), app, handler_class=WebSocketHandler)
    #server.serve_forever()
    app.run()

#!/usr/bin/python

import asyncore
import socket
import argparse
import sys
import time
import json
import logging


class Backend( asyncore.dispatcher_with_send ):
	def __init__(self,front, backend_servers, next_backend):
		self.front = front
		self.backend_servers = backend_servers
		self.next_backend = next_backend
		self.try_times = 0
		self.first_read = True
		front.set_backend( self )
		asyncore.dispatcher_with_send.__init__( self)
		self._connect_to_backend()

	def handle_read( self ):
		try:
			data = self.recv( 8192 )
			self.first_read = False
			if data is not None:
				self.front.send( data )
		except:
			self.handle_error()
	def handle_error( self ):
		self.close()
		self.del_channel()
		if self.first_read:
			self._connect_to_backend()
		else:
			self.front.close()

	def _connect_to_backend( self ):
		backend_server = self._get_next_backend_server()
		if backend_server:
			try:
				logging.info("try to connect %s" % repr(backend_server ) )
				self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
				self.connect( backend_server )
			except:
				self.close()
				self._connect_to_backend()
		else:
			logging.warn( "fail to connect to all backend severs")
			self.close()
			self.front.close()
			self.del_channel()

	def _get_next_backend_server( self ):
		n = len( self.backend_servers )
		if self.try_times < n:
			self.try_times += 1
			if self.next_backend >= n:
				self.next_backend = 0
			backend_server = self.backend_servers[self.next_backend]
			self.next_backend += 1
			return backend_server
		return None

class Frontend( asyncore.dispatcher_with_send ):
	def __init__( self, sock ):
		asyncore.dispatcher_with_send.__init__( self, sock = sock )
	def set_backend( self, backend ):
		self.backend = backend
	def handle_read(self):
		data = self.recv(8192)
		if data:
			self.backend.send( data )
	def handle_close( self ):
		self.backend.close()
	def handle_error( self ):
		self.backend.close()
		self.del_channel()
		
		
class ReverseProxy( asyncore.dispatcher ):
	def __init__(self, listeningAddr, backend_servers ):
		self.backend_servers = backend_servers
		self.max_tps_limit = 60
		self.next_backend = 0
		self.cur_sec = int(time.time())
		self.accepted_conns_cur_sec = 0
		asyncore.dispatcher.__init__( self )
		self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind( listeningAddr )
		self.listen(5)
	def handle_accept( self ):
		pair = self.accept()
		if pair:
			sock, addr = pair
			logging.info("accept a connect from %s" % repr( addr ))
			Backend( Frontend( sock ), self.backend_servers, self._get_next_backend() )
			t = int( time.time() )
			if t == self.cur_sec:
				self.accepted_conns_cur_sec += 1
				if self.accepted_conns_cur_sec > self.max_tps_limit:
					time.sleep( 0.001 )
			else:
				self.accepted_conns_cur_sec = 0

	def _get_next_backend( self ):
		self.next_backend += 1
		if self.next_backend >= len( self.backend_servers ):
			self.next_backend = 0
		return self.next_backend
		

def parse_args():
	parser = argparse.ArgumentParser(description='python reverse proxy')
	parser.add_argument( '--config', dest = 'config_file', help='configuration file' )
	return parser.parse_args( sys.argv[1:] )
def load_config( configFile ):
	logging.info("load config file %s" % configFile)
	with open( configFile ) as fp:
		return json.load( fp )
	return None

def to_host_port_tuple( addr ):
	pos = addr.rfind( ':' )
	if pos != -1:
		return (addr[0:pos], int(addr[pos+1:]) )
	return None

def start_reverse_proxy( server_info ):
	if "listen" in server_info and "backends" in server_info:
		listen = to_host_port_tuple( server_info['listen'] )
		backends = []
		for backend in server_info['backends']:
			tmp = to_host_port_tuple( backend )
			if tmp is not None:
				backends.append( tmp )
		if listen and backends:
			ReverseProxy( listen, backends )
		else:
			logging.error( "invalid server configuration %s" % repr( server_info ) )
def main():
	logging.basicConfig( filename='reverse_proxy.log',level=logging.DEBUG )
	args = parse_args()
	if args.config_file:
		config = load_config( args.config_file )
		for server in config:
			logging.info( "start server:%s" % server )
			try:
				start_reverse_proxy( config[server] )	
			except:
				logging.error("fail to start server %s" % server)
	asyncore.loop()
if __name__=="__main__":
    main()

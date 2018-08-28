#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from RKN import *
import time

def rewrite_all(R):
	if R.download():
#		R.clear_table()
		R.insert_info(R.read_head())
		R.open_dump()
		R.insert_data(R.parser())
		return 1
	return 0

def check(R, xml):
	R.open_dump(xml)
	R.counter()
	R.check_data()

def check_update(R):
	if int(R.check_date()) - int(R.check_last_update_date()) < 8 * 60 * 60:
		return 0
	else:
		return 1

def update_all(R):
#	if R.check_update():
	if R.download():
		R.insert_info(R.read_head())
		R.open_dump()
		R.update_data(R.delta(R.parser()))
		return 1
	return 0
		
def gen_bgp(R, file='out/bgp.list', head='bgp.head'):
	bgp_list = open(file, 'w')
	bgp_head = open(head, 'r')
	bgp_list.write(bgp_head.read())
	for line in R.read_net(1):
		bgp_list.write('network ' + str(line) + '\n')
	bgp_list.close()
	bgp_head.close()
#	return bgp_list
	
def gen_black_net(R, file='out/black_net.list', head='iptables.head', tail='iptables.tail'):
	net_list = open(file, 'w')
	net_head = open(head, 'r')
	net_list.write(net_head.read())
	for line in R.read_net():
		net_list.write('iptables -t nat -A PREROUTING -p tcp -d ' + str(line) + ' -j DNAT --to 10.0.0.25:80\n')
	net_tail = open(tail, 'r')
	net_list.write(net_tail.read())
	net_head.close()
	net_tail.close()
	net_list.close()
#	return net_list

def gen_urls(R, file='out/url.list'):
	url_list = open(file, 'w')
	for line in R.read_urls():
		url_list.write('^' + re.sub('[.$?+"]', lambda x: '\\' + x.group(0), line) + '\n')
	url_list.close()
#	return R.read_urls()
	
def gen_domains(R, file='out/dom.list', re_file='out/re_dom.list'):
	dom_list = open(file, 'w')
	re_dom_list = open(re_file, 'w')
	for line in R.read_domains():
		i = len(line) - 1
		str = ''
		while i >= 0:
			str += line[i] + '.'
			i -= 1
		dom_list.write(str[:-1] + '\n')
		re_dom_list.write('^([^\/]*\.)?' + re.sub('\.', lambda x: '\\' + x.group(0), str[:-1]) + '(\.)?$\n')
	dom_list.close()
	re_dom_list.close()
#	return dom_list
	
R = RKN()
while 1:
	if not R.check_last_update_date():
		print("Insert data from dump")
		if rewrite_all(R):
			print("Generate rules")
			gen_domains(R)
			gen_urls(R)
			gen_black_net(R)
			gen_bgp(R)
			print("done!")
		else:
			print("try download again!")
	else:
		if check_update(R):
			print("Update data from new dump")
			if update_all(R):
				print("Generate rules")
				gen_domains(R)
				gen_urls(R)
				gen_black_net(R)
				gen_bgp(R)
				print("done!")
			else:
				print("try download again!")
		else:
			print("Update aren't ready yet.")
	time.sleep(60)
del R

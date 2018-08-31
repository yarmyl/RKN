#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from netaddr import *
import re
import logging

logger = logging.getLogger("class.rkn.checker")

"""Локальные сети запрещенны"""
bad_nets = [IPNetwork('127.0.0.0/24'), IPNetwork('10.0.0.0/8'),
	    IPNetwork('192.168.0.0/16'), IPNetwork('172.16.0.0/12')
]
bad_ips = ('0.0.0.0', '255.255.255.255')

"""punycode для зоны .РФ"""
def punycode_converter(str):
	if re.search("[а-яА-Я]", str):
		return str.encode("idna").decode("utf-8").lower()
	else:
		return str.lower()
		
"""выполняем проверку на IP-address"""
def is_ip(ip):
	arr = ip.split('.')
	if len(arr) == 4:
		for a in arr:
			if int(a) > 255 or int(a) < 0:
				logger.warning("Bad ip: " + ip)
				return 0
	else:
		logger.warning("Bad ip: " + ip)
		return 0
	return 1

"""проверяем на вхождение в правильные диапазоны"""
def is_true_net(net, ip=1):
	try:
		if net in bad_ips:
			logger.warning("Bad ip/subnet: " + net)
			return 0
		nets = list(bad_nets)
		if ip:
			nets.append(IPAddress(net))
		else:
			nets.append(IPNetwork(net))
		if len(cidr_merge(nets)) == 4:
			logger.warning("Bad ip/subnet: " + net)
			return 0
		return 1
	except:
		logger.warning("Bad ip/subnet: " + net)
		return 0
		
"""Выполняем проверку на подсеть"""
def is_net(net):
	arr = net.split('/')
	if len(arr) == 2 and is_ip(arr[0]) and int(arr[1]) > 7 and int(arr[1]) < 33:
		return 1
	logger.warning("Bad subnet: " + net)
	return 0
	
"""Проверяем размер домена, не превышает ли 500 символов"""
def size_dom(dom):
	if len(list(dom)) > 500:
		logger.warning("Too long domain: " + dom)
		return 0
	return 1

"""Выполняем провеку на домен"""
def is_dom(dom):
	if re.search("[^\w\-\.\*]", punycode_converter(dom)) and dom != "":
		logger.warning("Bad domain: " + dom)
		return 0
	return 1

"""Сокращаем домен, убераем все лишнее"""
def cut_dom(dom):
	list = dom.split('.')
	fsize = len(list[0]) + 1
	a = len(dom)
	if list[-1] == "":
		a = -1
	if dom.split('.')[0] in ("www", "*", ""):
		return punycode_converter(dom[fsize:a])
	else:
		return punycode_converter(dom[:a])

"""Выполняем проверку на размер URL и домена"""
def size_url(url):
	if len(list(url)) > 2000:
		logger.warning("Too long url: " + url)
		return 0
	try:
		dom = re.match("([a-zA-Z0-9]+://)?(?P<dom>[^:/]+)[/:]?", url).group("dom")
	except:
		return 0
	if not(size_dom(dom)):
		return 0
	return 1

"""Выполняем разложение URL на порт, протокол и домен"""
def split_url(url):
	if re.match('https://', url):
		dom = url[8:].split('/')[0]
		n = dom.find(':')
		if n != -1:
			return ('https', dom[n+1:], cut_dom(dom[:n]))
		else:
			return ('https', '443', cut_dom(dom))
	elif re.match('http://', url):
		dom = url[7:].split('/')[0]
		n = dom.find(':')
		if n != -1:
			return ('http', dom[n+1:], cut_dom(dom[:n]))
		else:
			return ('http', '80', cut_dom(dom))
	else:
		p = re.compile("""((?P<proto>[a-zA-Z0-9]+)(://))?
				(?P<dom>[\w\.\-\*]+)(:
				(?P<port>[0-9]+))?/?""", re.I | re.VERBOSE
		)
		r = p.search(url)
		return (r.group("proto"), r.group("port"), cut_dom(r.group("dom")))

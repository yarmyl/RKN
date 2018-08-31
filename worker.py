#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from RKN import *
import time
import argparse
from threading import Thread
import os
import signal
import logging
import logging.config

"""Рабочий Демон"""
class Daemon(Thread):
	__STOP = 0
	__CONF = 0
	def add_conf(self, conf):
		self.__CONF = conf
	def __init__(self):
		Thread.__init__(self)
	def run(self):
		R = RKN(self.__CONF) if self.__CONF else RKN()
		while not self.__STOP:
			if not R.check_last_update_date():	
				logger.info("Insert data from dump...")
				if rewrite_all(R):
					logger.info("Generate rules")
					gen_domains(R)
					gen_urls(R)
					gen_black_net(R)
					gen_bgp(R)
					logger.info("done!")
				else:
					logger.warning("try download again!")
			else:
#				print("Check update...")
				if check_update(R):
					logger.info("Update data from new dump...")
					if update_all(R):
						logger.info("Generate rules")
						gen_domains(R)
						gen_urls(R)
						gen_black_net(R)
						gen_bgp(R)
						logger.info("done!")
					else:
						logger.warning("try download again!")
				else:
#					print("Update aren't ready yet.")
					pass
			time.sleep(10)
		logger.info("Stop success!")
		del R
	def stop(self):
		self.__STOP = 1

"""Разбор аргументов"""
def createParser ():
	parser = argparse.ArgumentParser()
	parser.add_argument('--start', action='store_true') #запуск демона
	parser.add_argument('--clear', action='store_true') #очистка БД
	parser.add_argument('--conf', nargs='?') #файл конфиги
	parser.add_argument('--log', nargs='?') #перенаправление вывода в log
	parser.add_argument('--err', nargs='?') #сводка по dump, если new, то скачивается свежий
	return parser

"""Запись в БД"""
def write_all(R):
	if R.download():
#		R.clear_table()
		R.insert_info(R.read_head())
		R.open_dump()
		R.insert_data(R.parser())
		return 1
	return 0

"""Проверка данных в скачанном дампе"""
def check(R, xml):
	R.open_dump(xml)
	R.counter()
	R.check_data()

"""Проверка обновлений 
Если есть обновление и старше 3х часов предыдущего обновления,
то True, иначе False"""
def check_update(R):
	if int(R.check_date()) - int(R.check_last_update_date()) < 8 * 60 * 60:
		return 0
	else:
		return 1

"""Обновление БД по дельтам"""
def update_all(R):
#	if R.check_update():
	if R.download():
		R.insert_info(R.read_head())
		R.open_dump()
		R.update_data(R.delta(R.parser()))
		return 1
	return 0

"""Генератор Файла для BGP"""		
def gen_bgp(R, file='out/bgp.list', head='bgp.head'):
	bgp_list = open(file, 'w')
	bgp_head = open(head, 'r')
	bgp_list.write(bgp_head.read())
	for line in R.read_net(1):
		bgp_list.write('network ' + str(line) + '\n')
	bgp_list.close()
	bgp_head.close()
#	return bgp_list

"""Генератор файла для iptables"""	
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

"""Генератор файла с регулярными выражениями запрещенных ссылок"""
def gen_urls(R, file='out/url.list'):
	url_list = open(file, 'w')
	for line in R.read_urls():
		url_list.write('^' + re.sub('[.$?+"]', lambda x: '\\' + x.group(0), line) + '\n')
	url_list.close()
#	return R.read_urls()

"""Генератор файлов с регулярными выражениями запрещенных доменов
и с запрещенными доменами"""	
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

def main():
	parser = createParser()
	namespace = parser.parse_args()
	
	if namespace.log:
		logging.config.fileConfig(namespace.log)
	else:
		logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger('rkn-worker')
	if namespace.clear:
		logger.info('Try to clear DB')
		R = RKN(namespace.conf) if namespace.conf else RKN()
		R.clear_table()
		logger.info('Clear Success!')
		del R

	if namespace.start:
		os.symlink('/run/worker.pid', '/var/lock/rkn-worker')
		d = Daemon()
		if namespace.conf:
			d.add_conf(namespace.conf)
		logger.info("Start Daemon!")
		d.start()
		try:
			fifo = open('input.in', 'r')
			while fifo.read() != 'stop\n':
				logger.warning('Wrong command')
			logger.info('Stop Daemon...')
		except:
			logger.error('Fail to open fifo!')
		finally:
			d.stop()
			os.remove('/var/lock/rkn-worker')
			logger.info("Lock removed!")
	elif namespace.err:
		R = RKN(namespace.conf) if namespace.conf else RKN()
		logger.info("Start to check ", namespace.err, " dump")
		if namespace.err == 'new':
			while not R.download():
				pass
			check(R, 'dump.xml')
		else:
			check(R, namespace.err)
		del R

if __name__ == "__main__":
	main()
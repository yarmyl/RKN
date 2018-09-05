#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from RKN import *
import time
import argparse
from threading import Thread
import os
import logging
import logging.config
import configparser
import difflib
import re

"""Рабочий Демон"""
class Daemon(Thread):
	logger = logging.getLogger("class.daemon")
	def add_conf(self, conf):
		self.__CONF = conf
	def add_services(self, serv):
		self.__services = serv
	def __init__(self):
		Thread.__init__(self)
		self.__STOP = 0
	def run(self):
		R = RKN(self.__CONF)
		while not self.__STOP:
			if not R.check_last_update_date():	
				self.logger.info("Insert data from dump...")
				if write_all(R):
					self.work_with_services(R, self.__services)
				else:
					logger.warning("try download again!")
			else:
#				print("Check update...")
				if check_update(R):
					self.logger.info("Update data from new dump...")
					if update_all(R):
						self.work_with_services(R, self.__services)
					else:
						self.logger.warning("try download again!")
				else:
#					print("Update aren't ready yet.")
					pass
			time.sleep(10)
		self.logger.info("Stop success!")
		del R
	def stop(self):
		self.__STOP = 1
		
	"""Обработка сервисов"""
	def work_with_services(self, R, serv):
		self.logger.info("Generate rules")
		f = 0
		if serv.get('DNS') or serv.get('PROXY'):
			if serv.get('DNS'):
				dns = serv.get('DNS')
				self.logger.info("Generate Domains")
				try:
					os.replace(dns.get('file'), dns.get('file')+'.old')
				except:
					os.system('touch ' + dns.get('file')+'.old')
				if serv.get('PROXY'):
					gen_domains(R, file=serv.get('DNS').get('file'), re_file=serv.get('PROXY').get('dom_file'))
				else:
					gen_domains(R, file=serv.get('DNS').get('file'))
				self.logger.info("Try diff old and new DNS files")
				if not diff(dns.get('file'), dns.get('file') + '.old'):
					self.logger.info("is haven't diffirance")
				else:
					f = 1
					for host in dns.get('host').split(','):
						command = str(dns.get('cmd') + ' ' + dns.get('file') + ' '
							+ dns.get('user') + '@' + host + ':' + dns.get('path'))
						self.logger.info(command)
						os.system(command)
			else:
				gen_domains(R, re_file=serv.get('PROXY').get('dom_file'))
		if serv.get('PROXY'):
			proxy = serv.get('PROXY')
			self.logger.info("Generate URLs")
			gen_urls(R, file=proxy.get('url_file'))
			if not f:
				if diff(proxy.get('white_conf'), 'white_dom.list'):
					os.replace('white_dom.list', proxy.get('white_conf'))
				self.logger.info("Try diff urls files")
				if not diff(proxy.get('url_file'), proxy.get('url_conf')):
					self.logger.info("urls is haven't diffirance")
					self.logger.info("Try diff domains files")
					if not diff(proxy.get('dom_file'), proxy.get('dom_conf')):
						self.logger.info("domains is haven't diffirance")
					else:
						f = 1
				else:
					f = 1
			if f:
				try:
					os.replace(proxy.get('url_file'), proxy.get('url_conf'))
					os.replace(proxy.get('dom_file'), proxy.get('dom_conf'))
				except:
					pass
				self.logger.info('Try ' + proxy.get('work') + ' ' + proxy.get('service') + ' service')
				os.system(proxy.get('init') + ' ' + proxy.get('work') + ' ' + proxy.get('service'))
		if serv.get('IPTABLES'):
			service = serv.get('IPTABLES')
			try:
				os.replace(service.get('file'), service.get('file')+'.old')
			except:
				os.system('touch ' + service.get('file') +'.old')
			self.logger.info("Generate IPTABLES")
			gen_black_net(R, file=service.get('file'), head=service.get('head'), tail=service.get('tail'), host=service.get('host'))
			self.logger.info("Try diff black nets")
			if not diff(service.get('file'), service.get('file') + '.old'):
				self.logger.info("domains is haven't diffirance")
			else:
				d = delta_iptables(service.get('file') + '.old', service.get('file'))
				if d:
					for rul in d:
						os.system(rul)
				else:
					os.system('bash ' + service.get('file'))
				self.logger.info("Done!")
		if serv.get('BGP'):
			service = serv.get('BGP')
			self.logger.info("Generate BGP")
			gen_bgp(R, file=service.get('file'), head=service.get('head'))
			self.logger.info("Try diff old and new BGP files")
			if not diff(service.get('file'), service.get('conf_file')):
				self.logger.info("is haven't diffirance")
			else:
				os.replace(service.get('file'), service.get('conf_file'))
				self.logger.info("Restart bgp service")
				os.system(service.get('service') + ' ' + service.get('work'))
		self.logger.info("Generate done!")

"""сравнение файлов, если равны или не открываются, то 0
иначе 1"""		
def diff(a, b):
	try:
		file1 = open(a, 'r')
		file2 = open(b, 'r')
	except:
		return 0
	if difflib.SequenceMatcher(None, file1.read(), file2.read()).real_quick_ratio() == 1:
		return 0
	else:
		return 1

"""Дельта для iptables, если изменения файла значительные,
то переписываем правила полностью, иначе по дельте"""
def delta_iptables(a, b):
	try:
		file1 = open(a, 'r')
		file2 = open(b, 'r')
	except:
		return 0
	text1 = file1.read()
	text2 = file2.read()
	file1.close()
	file2.close()
	Diff = difflib.SequenceMatcher(None, text1, text2)
	if Diff.real_quick_ratio() < 1 and Diff.real_quick_ratio() >= 0.9:
		text1 = text1.splitlines()
		text2 = text2.splitlines()
		size = 1
		res = []
		for rul in difflib.ndiff(text1, text2):
			if rul[:2] == '- ':
				res.append("iptables -t nat -D PREROUTING" + str(size))
			elif rul[:2] == '+ ':
				r = re.match('\+ ([\S ]+) -A (\S+) ([\S ]+)', rul)
				res.append(r.group(1) + ' -I ' + r.group(2) + ' ' + str(size) + ' ' + r.group(3))
				size += 1
			else:
				size += 1
		return res
	else:
		return 0

"""Разбор аргументов"""
def createParser ():
	parser = argparse.ArgumentParser()
	parser.add_argument('--start', action='store_true') #запуск демона
	parser.add_argument('--clear', action='store_true') #очистка БД
	parser.add_argument('--conf', nargs='?') #файл конфиги
	parser.add_argument('--log', nargs='?') #перенаправление вывода в log
	parser.add_argument('--err', nargs='?') #сводка по dump, если new, то скачивается свежий
	parser.add_argument('--bgp', action='store_true') #работа с BGP
	parser.add_argument('--iptables', action='store_true') #работа с iptables 
	parser.add_argument('--dns', action='store_true') #работа с DNS
	parser.add_argument('--proxy', action='store_true') #работа с proxy
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
#	if None:
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
def gen_black_net(R, file='out/black_net.list', head='iptables.head', tail='iptables.tail', host):
	net_list = open(file, 'w')
	net_head = open(head, 'r')
	net_list.write(net_head.read())
	for line in R.read_net():
		net_list.write('iptables -t nat -A PREROUTING -p tcp -d '+str(line)+' -j DNAT --to '+host+'\n')
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

"""парсер для настроек из conf файла"""
def get_settings(config):
	settings = dict()
	for section in config.sections():
		value = dict()
		for setting in config[section]:
			value.update({setting: config.get(section, setting)})
		settings.update({section: value})
	return settings

def main():
	parser = createParser()
	namespace = parser.parse_args()
	services = dict()
	parser = configparser.ConfigParser()
	parser.read(namespace.conf) if namespace.conf else parser.read('conn.conf')
	settings = get_settings(parser)
	if namespace.log:
		logging.config.fileConfig(namespace.log)
	else:
		logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	logger = logging.getLogger('rkn-worker')
	if namespace.clear:
		logger.info('Try to clear DB')
		R = RKN({'CONN': settings['CONN'], 'DUMP': settings['DUMP']})
		R.clear_table()
		logger.info('Clear Success!')
		del R
	try:
		if namespace.bgp:
			services.update({'BGP': settings['BGP']})
		if namespace.iptables:
			services.update({'IPTABLES': settings['IPTABLES']})
		if namespace.dns:
			services.update({'DNS': settings['DNS']})
		if namespace.proxy:
			services.update({'PROXY': settings['PROXY']})
	except:
		logger.info('fail in config file')
	if namespace.start:
		os.symlink('/run/worker.pid', '/var/lock/rkn-worker')
		d = Daemon()
		d.add_conf({'CONN': settings['CONN'], 'DUMP': settings['DUMP']})
		d.add_services(services)
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
		R = RKN({'CONN': settings['CONN'], 'DUMP': settings['DUMP']})
		logger.info("Start to check " + namespace.err + " dump")
		if namespace.err == 'new':
			while not R.download():
				pass
			check(R, 'dump.xml')
		else:
			check(R, namespace.err)
		del R

if __name__ == "__main__":
	main()

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
import signal

"""Рабочий Демон"""
class Daemon(Thread):
	logger = logging.getLogger("class.daemon")
	def add_conf(self, conf, daemon):
		self.__CONF = conf
		if daemon:
			self.__timeout = int(daemon['timeout'])
			self.__count = int(daemon['count_try'])
			self.__utimeout = int(daemon['update_timeout'])
			self.__timezone = int(daemon['timezone'])
		else:
			self.__timeout = 10
			self.__count = 5
			self.__utimeout = 3
			self.__timezone = 0
		self.__proxy = 0
	def add_services(self, serv):
		self.__services = serv
	def __init__(self):
		Thread.__init__(self)
		self.__STOP = 0
		self.__services = 0
	def run(self):
		R = RKN(self.__CONF)
		i = 0
		while (not self.__STOP) and (i < self.__count):
			if not R.check_last_update_date():	
				self.logger.info("Insert data from dump...")
				if write_all(R):
					self.work_with_services(R, self.__services)
					i = 0
				else:
					logger.warning("try download again!")
					i += 1
			else:
#				print("Check update...")
				if check_update(R, self.__utimeout, self.__timezone):
					self.logger.info("Update data from new dump...")
					if update_all(R):
						if self.__services:
							self.work_with_services(R, self.__services)
							i = 0
					else:
						self.logger.warning("try download again!")
						i += 1
				else:
#					print("Update aren't ready yet.")
					pass
			time.sleep(self.__timeout)
		if self.__STOP:
			self.logger.info("Stop success!")
		else:
			self.logger.error("Fail to download, stop service...")
		del R
	def stop(self, signal, frame):
		self.__STOP = 1
		self.logger.info('Stop Daemon...')
		
	"""Обработка сервисов"""
	def work_with_services(self, R, serv):
		self.logger.info("Generate rules")
		if serv.get('DNS') or serv.get('PROXY'):
			if serv.get('DNS'):
				dns = serv.get('DNS')
				self.logger.info("Generate Domains")
				try:
					os.replace(dns.get('file'), dns.get('file')+'.old')
				except:
					os.system('touch ' + dns.get('file')+'.old')
				if serv.get('PROXY'):
					gen_domains(R, file=serv.get('DNS').get('file'), re_file=serv.get('PROXY').get('dom_file'),
						rev_file=serv.get('PROXY').get('rev_file'), gen_wfile=serv.get('PROXY').get('gen_wfile'))
				else:
					gen_domains(R, file=serv.get('DNS').get('file'))
				self.logger.info("Try diff old and new DNS files")
				if not diff(dns.get('file'), dns.get('file') + '.old'):
					self.logger.info("is haven't diffirance")
				else:
					for host in dns.get('host').split(','):
						command = str(dns.get('cmd') + ' ' + dns.get('file') + ' '
							+ dns.get('user') + '@' + host + ':' + dns.get('path'))
						self.logger.info(command)
						os.system(command)
			else:
				gen_domains(R, re_file=serv.get('PROXY').get('dom_file'),
					rev_file=serv.get('PROXY').get('rev_file'), gen_wfile=serv.get('PROXY').get('gen_wfile'))
		if serv.get('PROXY'):
			proxy = serv.get('PROXY')
			self.logger.info("Generate URLs")
			gen_urls(R, file=proxy.get('url_file'))
			try:
				os.replace(proxy.get('url_file'), proxy.get('url_conf'))
				os.replace(proxy.get('gen_wfile'), proxy.get('white_conf'))
				os.replace(proxy.get('rev_file'), proxy.get('dom_conf'))
			except:
				pass
			if not diff(proxy.get('dom_file'), proxy.get('re_dom_conf')):
				self.logger.info("domains is haven't diffirance")
			else:
				try:
					os.replace(proxy.get('dom_file'), proxy.get('re_dom_conf'))
				except:
					self.logger.info("Fail to replace squid domain file")
#				gen_re_white(proxy.get('white_conf'), 'white_dom.list')
				a = int(proxy.get('timeout')) if proxy.get('timeout') else 3
				if self.__proxy + 60 * 60 * a < time.time():
					self.__proxy = time.time()
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
				if service.get('weight'):
					d = delta_iptables(service.get('file') + '.old', service.get('file'), service.get('weight'))
				else:
					d = delta_iptables(service.get('file') + '.old', service.get('file'))
				if d:
					self.logger.info("Edit iptables rules...")
					for rul in d:
						os.system(rul)
				else:
					self.logger.info("Restart iptables rules")
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
				if service.get('weight'):
					d = delta_bgp(service.get('conf_file'), service.get('file'), service.get('weight'))
				else:
					d = delta_bgp(service.get('conf_file'), service.get('file'))
				os.replace(service.get('file'), service.get('conf_file'))
				if d:
					self.logger.info("Edit bgp networks...")
					for rul in d:
						os.system(service.get('edit') + ' ' + rul)
				else:
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
		
"""генерим регулярные выражения для белых списков"""
def gen_re_white(conf, file):
	try:
		file1 = open(conf, 'w')
		file2 = open(file, 'r')
	except:
		return 0
	for line in file2:
		line = re.sub('\.', '\.', line[:-1])
		line = '^([^\/]*\.)?' + line + '$\n'
		file1.write(line)
	file1.close()
	file2.close()
		
"""Дельта для маршрутов bgp, если изменения файла значительные,
то переписываем правила полностью, иначе по дельте"""
def delta_bgp(a, b, c='0.5'):
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
	if Diff.real_quick_ratio() < 1 and Diff.real_quick_ratio() >= float(c):
		text1 = text1.splitlines()
		text2 = text2.splitlines()
		res = []
		for rul in difflib.ndiff(text1, text2):
			if rul[:2] == '- ':
				res.append('"no ' + rul[2:] + '"')
			elif rul[:2] == '+ ':
				res.append('"' + rul[2:] + '"')
		return res
	else:
		return 0

"""Дельта для iptables, если изменения файла значительные,
то переписываем правила полностью, иначе по дельте"""
def delta_iptables(a, b, c='0.8'):
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
	if Diff.real_quick_ratio() < 1 and Diff.real_quick_ratio() >= float(c):
		text1 = text1.splitlines()
		text2 = text2.splitlines()
		size = -1
		res = []
		for rul in difflib.ndiff(text1, text2):
#			res.append(rul)
			if rul[:2] == '- ':
				res.append("iptables -t nat -D PREROUTING " + str(size))
			elif rul[:2] == '+ ':
				r = re.match('\+ ([\S ]+) -A (\S+) ([\S ]+)', rul)
				res.append(r.group(1) + ' -I ' + r.group(2) + ' ' + str(size) + ' ' + r.group(3))
				size += 1
			elif rul[:2] == '? ':
				pass
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
def check_update(R, u, tz):
	if int(R.check_date()) - int(R.check_last_update_date()) <= (tz + u + 0.3) * 60 * 60:
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
def gen_black_net(R, file='out/black_net.list', head='iptables.head', tail='iptables.tail', host='127.0.0.1:80'):
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
def gen_domains(R, file='out/dom.list', re_file='out/re_dom.list', rev_file='out/rev_dom.list', 
		white_file='white_dom.list', gen_wfile='out/white_dom.list'):
	dom_list = open(file, 'w')
	re_dom_list = open(re_file, 'w')
	revers_dom_list = open(rev_file, 'w')
	for line in R.read_domains():
		revers_dom_list.write('.'.join(line) + '\n')
		dom_list.write('.'.join(line[::-1]) + '\n')
		re_dom_list.write('^([^\/]*\.)?' + re.sub('\.', lambda x: '\\' + x.group(0), '.'.join(line[::-1])) + '(\.)?$\n')
	dom_list.close()
	re_dom_list.close()
	revers_dom_list.close()
	white_list = open(white_file, 'r')
	gen_wlist = open(gen_wfile, 'w')
	dom_list = []
	for line in white_list:
		dom_list.append(line[:-1].split('.')[::-1])
	dom_list = sorted(dom_list)
	i = 0
	while i < len(dom_list):
		try:
			while DOM_LIST(dom_list[i]).sub_dom(dom_list[i+1]):
				dom_list.pop(i+1)
		except IndexError:
			pass
		i += 1
	for dom in dom_list:
		gen_wlist.write('.'.join(dom) + '\n')
	white_list.close()
	gen_wlist.close()

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
		d.add_conf({'CONN': settings['CONN'], 'DUMP': settings['DUMP']}, settings.get('DAEMON'))
		d.add_services(services)
		logger.info("Start Daemon!")
		d.start()
		signal.signal(signal.SIGUSR1, d.stop)
		d.join()
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

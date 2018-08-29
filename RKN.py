#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lxml import etree
import re
import mySQLConnect
from checker import *
import dump
from lxml.etree import ElementTree
import datetime
import multiprocessing

"""Дочерний класс для проверки вхождения домена в домен"""
class DOM_LIST(list):
	def sub_dom(self, x):
		i = 0
		while i < len(self):
			if self[i] != x[i]:
				return 0
			i += 1
		return 1

class RKN:

	"""Пытаемся считать конфиг, получить экземпляр класса 
	для считывания дампа и подключения к БД"""
	def __init__(self, conn='conn.conf'):
		self.__DB = mySQLConnect.myConn(conn)
		self.__Dump = dump.Dump(conn)

	def __del__(self):
		del self.__DB
		del self.__Dump

	"""определяем размеры данных в дампе"""
	def counter(self):
		m_url = 0
		m_dom = 0
		size_cont = 0
		size_url = 0
		size_dom = 0
		size_ip = 0
		size_sub = 0
		for content in self.__root:
			size_cont += 1
			for node in content:
				if node.tag == "url":
					size_url += 1
					size = len(list(node.text))
					if m_url < size:
						m_url = size
				if node.tag == "domain":
					size_dom += 1
					size = len(list(node.text))
					if m_dom < size:
						m_dom = size
				if node.tag == "ip": size_ip += 1
				if node.tag == "ipSubnet": size_sub += 1
		print("Content size = ", size_cont)
		print("Max lit in url = ", m_url)
		print("Max lit in domain = ", m_dom)
		print("Count urls = ", size_url)
		print("Count domains = ", size_dom)
		print("Count ips = ", size_ip)
		print("Count subnets = ", size_sub)

	"""Выполняем проверку данных в дампе"""
	def check_data(self):
		for content in self.__root:
			for node in content:
				if node.tag == "url":
					size_url(node.text)
					if not is_dom(split_url(node.text)[2]):
						print("Bad url: ", node.text)
				if node.tag == "domain":
					size_dom(node.text)
					is_dom(node.text)
				if node.tag == "ip":
					is_ip(node.text)
					is_true_net(node.text)
				if node.tag == "ipSubnet":
					is_net(node.text)
					is_true_net(node.text, 0)
	
	"""Парсим дамп и получаем список с данными"""
	def parser(self):
		data = []
		for content in self.__root:
			cont = [content.get("id"), content.get("includeTime"), content.get("urgencyType"), 
				     content.get("entryType"), content.get("hash"), content.get("blockType"),
				     content.get("ts").split('+')[0] if content.get("ts") else content.get("ts")
			]
			urls = []
			domains = []
			ips = []
			nets = []
			white_dom = []
			try:
				white_list_dom = open('white_dom.list', 'r')
				for line in white_list_dom:
					white_dom.append(line[0:-1])
			except:
				pass
			size_urls = 0
			dom = 0
			for node in content:
				isUse = 0
				if node.tag == "decision":
					des = (content.get("id"), node.get("date"), node.get("number"), node.get("org"))
				if node.tag == "url":
					if size_url(node.text):
						res = split_url(node.text)
						if is_dom(res[2]):
							if res[2] in white_dom and res[1] == '80' and res[0] == 'http':
								isUse = 1
								size_urls +=1
						else:
							print("Bad url: ", node.text)
						urls.append((content.get("id"), node.text, 
								node.get("ts").split('+')[0] if node.get("ts") else node.get("ts"), 
								res[2], res[0], res[1], isUse)
						)
				if node.tag == "domain":
					if is_dom(node.text):
						if not size_urls:
							isUse = 1
							dom = 1
						elif size_urls != len(urls) :
							isUse = 1
							dom = 1
					if size_dom(node.text):
						domains.append((content.get("id"), node.text, 
								node.get("ts").split('+')[0] if node.get("ts") else node.get("ts"), 
								cut_dom(node.text), isUse)
						)
				if node.tag == "ip":
					if is_ip(node.text): 
						if is_true_net(node.text):
							if not dom: 
								if not size_urls:
									isUse = 1
								elif size_urls != len(urls):
									isUse = 1
						ips.append((content.get("id"), node.text, 
								node.get("ts").split('+')[0] if node.get("ts") else node.get("ts"), 
								isUse)
						)
				if node.tag == "ipSubnet":
					if is_net(node.text):
						if is_true_net(node.text, 0):
							if not dom:
								if not size_urls:
									isUse = 1
								elif size_urls != len(urls):
									isUse = 1
						nets.append((content.get("id"), node.text, 
								node.get("ts").split('+')[0] if node.get("ts") else node.get("ts"), 
								isUse)
						)
			data.append([cont, des, urls, domains, ips, nets])
		return data
		
	"""Считываем заголовки из дампа"""
	def read_head(self, xml_path='dump.xml'):
		tree = ElementTree().parse(xml_path)
		return (tree.attrib['updateTime'].split('+')[0], tree.attrib['updateTimeUrgently'].split('+')[0],
				tree.attrib['formatVersion'])
		
	"""зачищаем DB"""
	def clear_table(self):
		self.__DB.execute("DELETE FROM contents")	
		self.__DB.execute("DELETE FROM info")
		self.__DB.commit()
		
	"""Всавляем данные в БД"""
	def insert_data(self, data):
		for content in data:
			self.__DB.execute("""INSERT INTO contents (id, includeTime, urgencyType, entryType, hash, blockType, ts) 
					VALUES(%s, %s, %s, %s, %s, %s, %s)""", content[0]
			)
			self.__DB.execute("""INSERT INTO decisions (content_id, date, number, org) 
					VALUES(%s, %s, %s, %s)""", content[1]
			)	
			self.__DB.execute_many("""INSERT INTO URLs (content_id, url, ts, domain, prot, port, isUse) 
					VALUES(%s, %s, %s, %s, %s, %s, %s)""" ,content[2]
			)
			self.__DB.execute_many("""INSERT INTO domains (content_id, domain, ts, cutDomain, isUse) 
					VALUES(%s, %s, %s, %s, %s)""" ,content[3]
			)
			self.__DB.execute_many("""INSERT INTO IPs (content_id, ip, ts, isUse) 
					VALUES(%s, %s, %s, %s)""" ,content[4]
			)
			self.__DB.execute_many("""INSERT INTO IPSubnets (content_id, sub, ts, isUse) 
					VALUES(%s, %s, %s, %s)""" ,content[5]
			)
		self.__DB.commit()
	
	"""Читаем из БД сети для БГП или запрещения на iptables"""
	def read_net(self, bgp = 0):
		if not bgp:
			ips = self.__DB.execute("""select distinct ip  from IPs where isUse = 1""")
			nets = self.__DB.execute("""select distinct sub from IPSubnets where isUse = 1""")
		else:
			ips = self.__DB.execute("""select distinct ip  from IPs""")
			nets = self.__DB.execute("""select distinct sub from IPSubnets""")
		ip_list = []
		for ip in ips:
			ip_list.append(IPAddress(ip[0]))
		for net in nets:
			ip_list.append(IPNetwork(net[0]))
		return cidr_merge(ip_list)
	
	"""считываем из БД URL'ы, которые заблокируем """
	def read_urls(self):
		urls = self.__DB.execute("""select distinct url  from URLs where isUse = 1""")
		url_list = []
		for url in urls:
			url_list.append(url[0])
		return url_list
	
	"""считываем из БД домены, которые заблокируем"""
	def read_domains(self):
		doms = self.__DB.execute("""select distinct cutDomain  from domains where isUse = 1""")
		dom_list = []
		for dom in doms:
			dom_list.append(dom[0].split('.')[::-1])
		dom_list = sorted(dom_list)
		i = 0
		while i < len(dom_list):
			try:
				while DOM_LIST(dom_list[i]).sub_dom(dom_list[i+1]):
					dom_list.pop(i+1)
			except IndexError:
				pass
			i += 1
		return dom_list
	
	"""сопоставляем дельту между данными в DB и dump"""
	def delta(self, dump_data=[]):
		db_data = self.__DB.execute("SELECT id, hash FROM contents")
		db_data = set(db_data)
		set_dump = set()
		temp_data = []
		for content in dump_data:
			set_dump.add((int(content[0][0]), content[0][4]))
			temp_data.append(int(content[0][0]))
			temp_data.append(content)
		if set_dump != []:
			if set_dump == db_data:
				return [(), ()]
			elif db_data.issubset(set_dump):
				data = []
				for content in set_dump.difference(db_data):
					data.append(temp_data[temp_data.index(content[0])+1])
				return [(), data]
			elif set_dump.issubset(db_data):
				return [db_data.difference(set_dump), ()]
			else:
				data = []
				for content in set_dump.difference(db_data):
					data.append(temp_data[temp_data.index(content[0])+1])
				return [db_data.difference(set_dump), data]
		return [(), (), ()]
	
	"""Обновляем данные (используем дельту)"""
	def update_data(self, data):
		contents = []
		for item in data[0]:
			contents.append((item[0],))
		self.__DB.execute_many("""Delete from contents where id = %s""", contents)
		self.insert_data(data[1])
	
	"""открываем корень считывания дампа"""
	def open_dump(self, xml_path='dump.xml'):
		try:
			tree = etree.parse(xml_path)
			self.__root = tree.getroot()
		except:
			raise SystemExit('Fail in init!')
	
	"""скачиваем актуальный дамп"""
	def download(self):
		try:
			self.__Dump.download()
			return 1
		except:
			return 0
		
	"""Перезаписываем информацию ореестре в БД"""
	def insert_info(self, list):
		self.__DB.execute("DELETE FROM info")
		self.__DB.execute("""INSERT INTO info (updateTime, updateTimeUrgently, formatVersion) 
					VALUES (%s, %s, %s)""", list
		)
		self.__DB.commit()
		
	"""Получаем дату актуального дампа"""
	def check_date(self):
		"""datetime.datetime.fromtimestamp(self.__Dump.getLastDumpDate()//1000).strftime('%Y-%m-%d %H:%M:%S')"""
		try:
			return self.__Dump.getLastDumpDate()//1000
		except:
			return 0
	
	"""Получаем дату дампа из БД"""
	def check_last_update_date(self):
		"""self.__DB.execute("SELECT updateTime FROM info")[0][0].strftime('%Y-%m-%d %H:%M:%S')"""
		try:
			return self.__DB.execute("SELECT updateTime FROM info")[0][0].timestamp()
		except:
			return 0
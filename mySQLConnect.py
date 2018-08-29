#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
import re


class myConn:
	"""Парсим конфиг и инициализируем коннект к базе данных"""
	def __init__(self, conf):
		try:
			conf_file = open(conf, 'r')
			con_text = conf_file.read()
			self.__host = re.search(r'(?<=HOST=)\S+', con_text).group(0)
			self.__user = re.search(r'(?<=USER=)\S+', con_text).group(0)
			if re.search(r'(?<=PASS=)\S*', con_text).group(0):
				self.__pass = re.search(r'(?<=PASS=)\S*', con_text).group(0)
			self.__db = re.search(r'(?<=DB=)\S+', con_text).group(0)
			conf_file.close()
		except:
			raise SystemExit('Fail to read config')
		self.connect()

	"""пробуем законнкетиться"""
	def connect(self):
		try:
			self.__dbc = mysql.connector.connect(
				host=self.__host, 
				user=self.__user, 
				password=self.__pass, 
				database=self.__db
			)
		except:
			raise SystemExit('Fail to connect!')

	def __del__(self):
		self.__dbc.close()

	"""Выполняем  sql-запрос"""
	def execute(self, sql, list=None):
		cur = self.__dbc.cursor()
		res = None
		if sql[:6].lower() == 'insert':
			cur.execute(sql, list)
		elif sql[:6].lower() == 'select':
			cur.execute(sql, list)
			res = cur.fetchall()
		elif sql[:6].lower() == 'delete':
			cur.execute(sql, list)
		elif sql[:6].lower() == 'update':
			cur.execute(sql, list)
		cur.close()
		return res
	
	"""выполняем множественный sql-запрос"""
	def execute_many(self, sql, list):
		if len(list) != 0:
			cur = self.__dbc.cursor()
			cur.executemany(sql, list)
			cur.close()
		
	"""подтверждаем изменения в DB"""
	def commit(self):
		self.__dbc.commit()

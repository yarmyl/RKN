#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
import logging


class myConn:
	logger = logging.getLogger("class.mysqlconnect")
	"""Парсим конфиг и инициализируем коннект к базе данных"""
	def __init__(self, conf):
		try:
			self.logger.info('Try read config')
			self.__host = conf['host']
			self.__user = conf['user']
			self.__pass = conf.get('pass')
			self.__db = conf['db']
		except:
			self.logger.error('Fail to read config')
			raise SystemExit()
		self.logger.info("Success!")
		self.connect()

	"""пробуем законнкетиться"""
	def connect(self):
		try:
			self.logger.info("Try connect DB")
			self.__dbc = mysql.connector.connect(
				host=self.__host, 
				user=self.__user, 
				password=self.__pass, 
				database=self.__db
			)
		except:
			self.logger.error('Fail to connect!')
			raise SystemExit()
		self.logger.info("Success!")

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

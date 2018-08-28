#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import suds.client
import base64
import time
import zipfile
import re
import zipfile

class Dump:
	"""Аналогичен getLastDumpDateEx, 
	но  возвращает  только  один параметр lastDumpDate"""
	def getLastDumpDate(self): 
		return self.__client.service.getLastDumpDate()
		
	"""Метод предназначен для получения временной 
	метки последнего обновления выгрузки из реестра, 
	а также для получения информации о версиях веб-сервиса, 
	памятки и текущего формата выгрузки"""
	def getLastDumpDateEx(self):
		return self.__client.service.getLastDumpDateEx()

	"""Метод предназначен для направления запроса на получение выгрузки из реестра"""
	def __sendRequest(self, requestFile, signatureFile, vers='2.3'): 
		file = open(requestFile, "rb")
		data = file.read()
		file.close()
		xml = base64.b64encode(data)
		xml = xml.decode('utf-8')
		file = open(signatureFile, "rb")
		data = file.read()
		file.close()
		sign = base64.b64encode(data)
		sign = sign.decode('utf-8')
		result = self.__client.service.sendRequest(xml, sign, vers)
		return dict((k, v) for (k, v) in result)

	"""Метод предназначен для получения результата обработки запроса - выгрузки из реестра"""
	def __getResult(self, code):
		try:
			result = self.__client.service.getResult(code)
			return dict((k, v) for (k, v) in result)
		except:
			return {'resultComment' : 'try again'} 

	"""парсим конфиг файл"""
	def __init__(self, conf):
		try:
			conf_file = open(conf, 'r')
			con_text = conf_file.read()
			self.__url = re.search(r'(?<=API_URL=)\S+', con_text).group(0)
			self.__xml = re.search(r'(?<=XML_FILE_NAME=)\S+', con_text).group(0)
			self.__sig = re.search(r'(?<=SIG_FILE_NAME=)\S+', con_text).group(0)
			self.__res = re.search(r'(?<=RES=)\S+', con_text).group(0)
			self.__vers = re.search(r'(?<=VERS=)\S+', con_text).group(0)
			conf_file.close()
		except:
			raise SystemExit('Fail to read config')
		self.__client = suds.client.Client(self.__url)
	
	"""скачиваем dump"""
	def download(self):
		request = self.__sendRequest(self.__xml, self.__sig, self.__vers)
		if request['result']:
			code = request['code']
			print('Got code %s' % (code))
			print('Trying to get result...')
			print('sleep 60 sec')
			time.sleep(60)
			while 1:
				request = self.__getResult(code)
				if request['result']:
					print('Got it!')
					file = open(self.__res + '.zip', "wb")
					file.write(base64.b64decode(request['registerZipArchive']))
					file.close()
					break
				else:
					if request['resultComment'] == 'запрос обрабатывается':
						print('Not ready yet.')
						print('sleep 60 sec')
						time.sleep(60)
					else:
						print('Error: %s' % request['resultComment'])
						break
		else:
			print('Error: %s' % request['resultComment'])
		file = zipfile.ZipFile(self.__res + '.zip')
		file.extract('dump.xml', '')
		file.close()
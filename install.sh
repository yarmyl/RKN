#!/bin/bash

cd "$(dirname "$0")"
apt-get update
apt-get install python3 mysql-server python3-pip python3-mysql.connector
mysql < RKN.sql
pip3 install lxml netaddr 
git clone https://github.com/andersinno/suds-jurko.git
cd suds-jurko/
python3 setup.py install
cd ../ && rm -r suds-jurko/
touch bgp.head
touch iptables.head
touch iptables.tail
mkdir out/
touch white_dom.list
echo  "[CONN]
HOST=localhost
USER=rkn_user
PASS=
DB=RKN

[DUMP]
API_URL=http://vigruzki.rkn.gov.ru/services/OperatorRequest/?wsdl
XML_FILE_NAME=zapros.xml
SIG_FILE_NAME=zapros.xml.sig
RES=result
VERS=2.3" > conn.conf
cp rkn-workerd /etc/init.d/rkn-workerd
update-rc.d rkn-workerd defaults
import pymssql
import datetime

conn = pymssql.connect(host="192.168.12.100", database='KIOSK', user='NEUROMEKA', password='NEUROMEKA1234', charset='utf8', as_dict=True)

now = datetime.datetime.now()

cursor = conn.cursor()

cursor.execute("SELECT * FROM TB_OrderJoin WHERE OJ_DATE='{}';".format(now.strftime('%b %d 2')))
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
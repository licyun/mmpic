# coding='UTF-8'
from bs4 import BeautifulSoup
import threading, pymysql, time, requests, os, urllib3, re

requests.packages.urllib3.disable_warnings()
# 数据库连接信息
dbhost = {
    "host": "127.0.0.1",
    "dbname": "xxxx",
    "user": "root",
    "password": "xxxx"
}


class Spider():
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/65.0.3325.181 Safari/537.36',
        'Referer': "https://www.meitulu.com"
    }
    page_url_list = []
    img_url_list = []
    rlock = threading.RLock()
    s = requests.session()

    def __init__(self, page_number=10, img_path='imgdir', thread_number=5, type='xinggan', type_id=1, typename='meinv'):
        self.spider_url = 'http://www.moyunso.com/' + typename + '/list_' + type + '_'
        self.page_number = int(page_number)
        self.img_path = img_path
        self.thread_num = thread_number
        self.type_id = type_id

    def get_url(self):
        for i in range(1, self.page_number + 1):
            page_base_page = BeautifulSoup(requests.get(self.spider_url + str(i) + ".html").content, "html.parser")
            page_div = page_base_page.find_all("div", class_="listBoxTitle")
            for div in page_div:
                url = div.find("h2").find("a")
                page_url = "http://www.moyunso.com" + url.get("href")
                self.page_url_list.append(page_url)

    def get_img_url(self):
        db = pymysql.connect(dbhost.get("host"), dbhost.get("user"), dbhost.get("password"), dbhost.get("dbname"))
        cursor = db.cursor()
        for url in self.page_url_list:
            tagidlist = []
            page = requests.get(url)
            img_base_page = BeautifulSoup(page.content, "html.parser")
            img_num_page = img_base_page.find("ul", class_="pagelist").find("li")
            img_num = re.findall('\d+', str(img_num_page))[0]
            img_first = img_base_page.find("div", class_="content").find("img").get("src")
            first_num = img_first.split("/")[-1].split(".")[-2]
            img_base_url = "/".join(img_first.split("/")[0:-1])
            title = img_base_page.find("div", class_="listBoxTitle").find("h2").text
            isExists = cursor.execute("SELECT title FROM images_page WHERE title =" + "'" + title + "'" + " limit 1;")
            if isExists != 0:
                print("已采集：" + title)
            else:
                re_page = page.content.decode("gb2312")
                taglist = re.findall('<meta name="keywords" content="(.*?)" />', re_page)
                i = 1
                for tags in taglist:
                    for tag in tags.split(","):
                        if i <= 3:
                            sqltag = "SELECT * FROM images_tag WHERE tag =" + "'" + tag + "'" + " limit 1;"
                            isExiststag = cursor.execute(sqltag)
                            if isExiststag == 0:
                                cursor.execute("INSERT INTO images_tag (tag) VALUES (%s)", tag)
                            cursor.execute("SELECT id FROM images_tag WHERE tag =" + "'" + tag + "'")
                            for id in cursor.fetchall():
                                tagidlist.append(id[0])
                            i = i + 1
                p = (title, str(tagidlist), time.strftime('%Y-%m-%d', time.localtime(time.time())), self.type_id, "1")
                cursor.execute("INSERT INTO images_page (title,tagid,sendtime,typeid,firstimg) VALUES (%s,%s,%s,%s,%s)",
                               p)
                pageid = cursor.lastrowid
                n = 1
                for i in range(int(first_num), int(first_num) + int(img_num)):
                    img_src = img_base_url + "/" + str(i) + "." + img_first.split("/")[-1].split(".")[-1]
                    img_loc_path = self.img_path + "/".join(img_src.split("/")[-2:])
                    if n == 1:
                        cursor.execute(
                            "UPDATE images_page SET firstimg = " + "'" + img_loc_path + "'" + " WHERE title=" + "'" + title + "'")
                    imgp = pageid, img_loc_path
                    cursor.execute("INSERT INTO images_image (pageid,imageurl) VALUES (%s,%s)", imgp)
                    i = i + 1
                    n = n + 1
                    self.img_url_list.append(img_src)
        db.close()

    def down_img(self, imgsrc):
        path = imgsrc.split("/")[-2]
        isdata = os.path.exists("../" + self.img_path + path)
        if isdata == False:
            os.makedirs("../" + self.img_path + path)
        with open("../" + self.img_path + path + "/" + imgsrc.split("/")[-1], "wb")as f:
            f.write(requests.get(imgsrc, headers=self.headers, verify=False).content)
            print("下载完成：" + self.img_path + path)

    def down_url(self):
        while True:
            Spider.rlock.acquire()
            if len(Spider.img_url_list) == 0:
                Spider.rlock.release()
                break
            else:
                img_url = Spider.img_url_list.pop()
                Spider.rlock.release()
                try:
                    self.down_img(img_url)
                except Exception as e:
                    pass

    def run(self):
        # 启动thread_num个来下载图片
        for img_th in range(self.thread_num):
            download_t = threading.Thread(target=self.down_url)
            download_t.start()


# 采集参数，page为采集页数，type为原站分类id，typename为原站分类名,type_id为本站分类id			
if __name__ == '__main__':
    for i in [{"page": 2, "type": "1", "type_id": 2, "typename": "meinv"}]:
        spider = Spider(page_number=i.get("page"), img_path='/static/images/', thread_number=10, type=i.get("type"),
                        type_id=i.get("type_id"), typename=i.get("typename"))
        spider.get_url()
        spider.get_img_url()
        spider.run()

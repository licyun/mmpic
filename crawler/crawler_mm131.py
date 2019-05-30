# coding='UTF-8'

from bs4 import BeautifulSoup
import threading, pymysql, time, requests, os, urllib3, re

requests.packages.urllib3.disable_warnings()
requests.adapters.DEFAULT_RETRIES = 5
s = requests.session()
s.keep_alive = False
# 数据库连接信息
dbhost = {
    "host": "127.0.0.1",
    "dbname": "xxxx",
    "user": "root",
    "password": "xxxx"
}


class Spider():
    rlock = threading.RLock()
    page_url_list = []
    img_url_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36",
        "Referer": "www.mm131.com"
    }

    def __init__(self, page_num, img_path, thread_num, type_id=1, type="home"):
        self.page_num = page_num
        self.img_path = img_path
        self.thread_num = thread_num
        self.type_id = type_id
        self.type = type

    def get_url(self):
        if self.type == "xinggan":
            type_id = str(6)
        elif self.type == "qingchun":
            type_id = str(1)
        elif self.type == "xiaohua":
            type_id = str(2)
        elif self.type == "chemo":
            type_id = str(3)
        elif self.type == "qipao":
            type_id = str(4)
        elif self.type == "mingxing":
            type_id = str(5)
        for i in range(1, self.page_num + 1):
            if i == 1:
                page = s.get("http://www.mm131.com/" + self.type + "/", headers=self.headers)
            else:
                page = s.get("http://www.mm131.com/" + self.type + "/" + "list_" + type_id + "_" + str(i) + ".html",
                             headers=self.headers)
            page.encoding = 'gb2312'
            soup = BeautifulSoup(page.text, "html.parser")
            page_div = soup.find("dl", class_="list-left public-box").find_all("dd")
            del page_div[-1]
            for dd in page_div:
                url = dd.find("a").get("href")
                self.page_url_list.append(url)

    def get_img(self):
        db = pymysql.connect(dbhost.get("host"), dbhost.get("user"), dbhost.get("password"), dbhost.get("dbname"))
        cursor = db.cursor()
        for url in self.page_url_list:
            tagidlist = []
            page = s.get(url, headers=self.headers)
            page.encoding = 'gb2312'
            soup = BeautifulSoup(page.text, "html.parser")
            page_div = soup.find("div", class_="content-pic")
            title = page_div.find("img").get("alt").replace("(图1)", "")
            isExists = cursor.execute("SELECT title FROM images_page WHERE title =" + "'" + title + "'" + " limit 1;")
            if isExists != 0:
                print("已采集：" + title)
            else:
                tagslist = re.findall('<meta name="keywords" content="(.*?)" />', page.text)
                for tags in tagslist:
                    for tag in tags.split(","):
                        sqltag = "SELECT * FROM images_tag WHERE tag =" + "'" + tag + "'" + " limit 1;"
                        isExiststag = cursor.execute(sqltag)
                        if isExiststag == 0:
                            cursor.execute("INSERT INTO images_tag (tag) VALUES (%s)", tag)
                        cursor.execute("SELECT id FROM images_tag WHERE tag =" + "'" + tag + "'")
                        for id in cursor.fetchall():
                            tagidlist.append(id[0])
                p = (title, str(tagidlist), time.strftime('%Y-%m-%d', time.localtime(time.time())), self.type_id, "1")
                cursor.execute("INSERT INTO images_page (title,tagid,sendtime,typeid,firstimg) VALUES (%s,%s,%s,%s,%s)",
                               p)
                print("开始采集：" + title)
                pageid = cursor.lastrowid
                img_first_url = page_div.find("img").get("src")
                img_num_soup = soup.find("div", class_="content-page").find("span").text
                img_num = "".join(re.findall(r"\d", img_num_soup))
                for i in range(0, int(img_num)):
                    baseurl = img_first_url.split("/")
                    img_url = "/".join(baseurl[0:-3])
                    img_url_path = baseurl[-2]
                    img_type = baseurl[-1].split(".")[-1]
                    img_loc_path = self.img_path + time.strftime('%Y%m%d', time.localtime(
                        time.time())) + "/" + img_url_path + "/" + str(i+1) + "." + img_type
                    if i == 1:
                        cursor.execute(
                            "UPDATE images_page SET firstimg = " + "'" + img_loc_path + "'" + " WHERE id=" + "'" + str(
                                pageid) + "'")
                    imgp = pageid, img_loc_path
                    cursor.execute("INSERT INTO images_image (pageid,imageurl) VALUES (%s,%s)", imgp)
                    i += 1
                    self.img_url_list.append(img_url + "/pic/" + img_url_path + "/" + str(i) + "." + img_type)

    def down_img(self, imgsrc):
        path = self.img_path + time.strftime('%Y%m%d', time.localtime(time.time())) + "/"
        page_id = imgsrc.split("/")[-2]
        isdata = os.path.exists("../" + path + page_id)
        headers = {
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36",
            "Referer": "http://www.mm131.com/xinggan/" + page_id + ".html"
        }
        if not isdata:
            os.makedirs("../" + path + page_id)
        with open("../" + path + page_id + "/" + imgsrc.split("/")[-1].split(".")[0] + ".jpg", "wb") as f:
            print("已保存：" + path + page_id + "/" + imgsrc.split("/")[-1].split(".")[0] + ".jpg")
            f.write(s.get(imgsrc, headers=headers).content)

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


if __name__ == "__main__":
    for i in [{"page": 1, "type": "xinggan", "type_id": 1}, {"page": 1, "type": "qingchun", "type_id": 3},
              {"page": 1, "type": "xiaohua", "type_id": 3}, {"page": 1, "type": "chemo", "type_id": 1},
              {"page": 1, "type": "qipao", "type_id": 2}, {"page": 1, "type": "mingxing", "type_id": 1}]:
        spider = Spider(page_num=i.get("page"), img_path='/static/images/', thread_num=10, type_id=i.get("type_id"),
                        type=i.get("type"))
        spider.get_url()
        spider.get_img()
        spider.run()

# encoding:gbk

from bs4 import BeautifulSoup
import threading, pymysql, time, requests, os, urllib3, re

requests.packages.urllib3.disable_warnings()
requests.adapters.DEFAULT_RETRIES = 5
s = requests.session()
s.keep_alive = False
# 数据库连接信息
dbhost = {
    "host": "127.0.0.1",
    "dbname": "silumz",
    "user": "root",
    "password": "fendou2009"
}
base_url="http://www.ccmntu.com"

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
        for i in range(1, self.page_num + 1):
            page = s.get(base_url + "/" + self.type + "/list_" + str(i)+".html", verify=False).text
            soup = BeautifulSoup(page, "html.parser")
            page_base_url = soup.find("ul", class_="product01").find_all("li")
            for page_url in page_base_url:
                url=base_url+page_url.find("a").get("href")
                self.page_url_list.append(url)

    def get_img(self,url):
        tagidlist=[]
        db = pymysql.connect(dbhost.get("host"), dbhost.get("user"), dbhost.get("password"),dbhost.get("dbname"))
        cursor = db.cursor()
        page=s.get(url)
        page.encoding="gb2312"
        soup=BeautifulSoup(page.text, "html.parser")
        title=soup.find("div",class_="bbt").find("h2").text
        isExists = cursor.execute("SELECT title FROM images_page WHERE title =" + "'" + title + "'" + " limit 1;")
        if isExists != 0:
            print("已采集：" + title)
        else:
            print("开始采集：" + title)
            tags = soup.find("div", class_="banner_tag").find_all("a")
            for tag_soup in tags:
                tag = tag_soup.text
                sqltag = "SELECT * FROM images_tag WHERE tag =" + "'" + tag + "'" + " limit 1;"
                isExiststag = cursor.execute(sqltag)
                if isExiststag == 0:
                    cursor.execute("INSERT INTO images_tag (tag) VALUES (%s)", tag)
                cursor.execute("SELECT id FROM images_tag WHERE tag =" + "'" + tag + "'")
                for id in cursor.fetchall():
                    tagidlist.append(id[0])
            p = (title, str(tagidlist), time.strftime('%Y-%m-%d', time.localtime(time.time())), self.type_id, "1")
            cursor.execute("INSERT INTO images_page (title,tagid,sendtime,typeid,firstimg) VALUES (%s,%s,%s,%s,%s)",p)
            pageid = cursor.lastrowid
            img_page_num=soup.find("div",class_="page").find_all("li")
            for i in range(1,len(img_page_num)-3):
                page_id=url.split("/")[-1].split(".")[0]
                if i==1:
                    img_page = s.get(url)
                    img_page.encoding = "utf-8"
                    img_soup = BeautifulSoup(img_page.text, "html.parser")
                    img_url = img_soup.find("div", class_="big-pic").find("img").get("src")
                    self.img_url_list.append(base_url + img_url)
                    img_name=img_url.split("/")[-1]
                    img_loc_path = self.img_path + time.strftime('%Y%m%d', time.localtime(
                        time.time())) + "/" + page_id + "/" + img_name
                    cursor.execute(
                        "UPDATE images_page SET firstimg = " + "'" + img_loc_path + "'" + " WHERE id=" + "'" + str(
                            pageid) + "'")
                else:
                    img_page = s.get(base_url+"/"+self.type+"/"+page_id+"_"+str(i)+".html")
                    img_page.encoding="utf-8"
                    img_soup=BeautifulSoup(img_page.text, "html.parser")
                    img_url = img_soup.find("div", class_="big-pic").find("img").get("src")
                    img_name = img_url.split("/")[-1]
                    img_loc_path = self.img_path + time.strftime('%Y%m%d', time.localtime(
                        time.time())) + "/" + page_id + "/" + img_name
                    imgp = pageid, img_loc_path
                    cursor.execute("INSERT INTO images_image (pageid,imageurl) VALUES (%s,%s)", imgp)
                    self.img_url_list.append(base_url+img_url)

    def down_img(self, imgsrc):
        path = self.img_path + time.strftime('%Y%m%d', time.localtime(time.time())) + "/"
        page_id = imgsrc.split("/")[-2]
        isdata = os.path.exists("../" + path + page_id)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36",
        }
        if not isdata:
            os.makedirs("../" + path + page_id)
        with open("../" + path + page_id + "/" + imgsrc.split("/")[-1].split(".")[0] + ".jpg", "wb") as f:
            print("已保存：" + path + page_id + "/" + imgsrc.split("/")[-1].split(".")[0] + ".jpg")
            f.write(s.get(imgsrc, headers=headers).content)

    def run_page(self):
        while True:
            Spider.rlock.acquire()
            if len(Spider.page_url_list) == 0:
                Spider.rlock.release()
                break
            else:
                page_url = Spider.page_url_list.pop()
                Spider.rlock.release()
                try:
                    self.get_img(page_url)
                except Exception as e:
                    pass

    def run_img(self):
        while True:
            Spider.rlock.acquire()
            if len(Spider.img_url_list) == 0 and len(Spider.page_url_list) == 0:
                Spider.rlock.release()
                break
            elif len(Spider.img_url_list) == 0 and len(Spider.page_url_list) != 0:
                continue
            else:
                img_url = Spider.img_url_list.pop()
                Spider.rlock.release()
                try:
                    self.down_img(img_url)
                except Exception as e:
                    pass

    def run(self):
        # 启动thread_num个进程来爬去具体的img url 链接
        for th in range(self.thread_num):
            add_pic_t = threading.Thread(target=self.run_page)
            add_pic_t.start()

        # 启动thread_num个来下载图片
        for img_th in range(self.thread_num):
            download_t = threading.Thread(target=self.run_img)
            download_t.start()

if __name__ == "__main__":
    for i in [{"page": 1, "type": "xgmn", "type_id": 1}]:
        spider = Spider(page_num=i.get("page"), img_path='/static/images/', thread_num=10, type_id=i.get("type_id"),
                        type=i.get("type"))
        spider.get_url()
        spider.run()
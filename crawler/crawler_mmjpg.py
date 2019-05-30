#coding='UTF-8'

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
import threading,pymysql,time,requests,os,urllib3,re
requests.packages.urllib3.disable_warnings()
requests.adapters.DEFAULT_RETRIES = 5
s = requests.session()
s.keep_alive = False
s.mount('http://', HTTPAdapter(max_retries=3))
# 数据库连接信息
dbhost={
        "host":"127.0.0.1",
        "dbname":"xxxx",
        "user":"root",
        "password":"xxxx"
    }

class Spider():
    rlock = threading.RLock()
    page_url_list=[]
    img_url_list=[]
    def __init__(self,page_num,img_path,thread_num,type_id=1,type="home"):
        self.page_num=page_num
        self.img_path=img_path
        self.thread_num=thread_num
        self.type_id=type_id
        self.type=type

    def get_page_url(self):
        for i in range(1,self.page_num+1):
            if i==1:
                if self.type=="home":
                    page=s.get("http://www.mmjpg.com")
                else:
                    page = s.get("http://www.mmjpg.com/"+self.type)
            else:
                page=s.get("http://www.mmjpg.com/"+self.type+"/"+str(i))
            soup=BeautifulSoup(page.text, "html.parser")
            url_soup=soup.find("div",class_="pic").find("ul").find_all("li")
            for li in url_soup:
                url=li.find("a").get("href")
                self.page_url_list.append(url)

    def get_img_url(self):
        db = pymysql.connect(dbhost.get("host"), dbhost.get("user"), dbhost.get("password"),dbhost.get("dbname"))
        cursor = db.cursor()
        for url in self.page_url_list:
            tagidlist=[]
            page_id = url.split("/")[-1]
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36",
                "Referer": "http://www.mmjpg.com/mm/"+page_id
            }
            info_page = s.get("http://www.mmjpg.com/mm/" + page_id,headers=headers)
            info_page.encoding="utf-8"
            info_soup = BeautifulSoup(info_page.text,"html.parser")
            title=info_soup.find("div",class_="article").find("h2").text
            isExists = cursor.execute("SELECT title FROM images_page WHERE title =" + "'" + title + "'" + " limit 1;")
            img_m_src=info_soup.find("div",class_="content").find("a").find("img").get("src").split("/")[-3]
            if isExists != 0:
                print("已采集：" + title)
            else:
                tags=info_soup.find("div",class_="tags").find_all("a")
                for tag_soup in tags:
                    tag=tag_soup.text
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
                print("开始采集："+title)
                pageid = cursor.lastrowid
                callback=s.get("http://www.mmjpg.com/data.php?id="+page_id+"&page=8999",headers=headers).text
                i=1
                if int(page_id) <= 1255:
                    n = 1
                    for img_div in info_soup.find("div", class_="page").find_all("a"):
                        if n == 7:
                            img_num=img_div.text
                            for img_id in range(1, int(img_num) + 1):
                                img_src = "http://fm.shiyunjj.com/" + img_m_src + "/" + page_id + "/" + str(
                                    img_id) + ".jpg"
                                img_loc_path=self.img_path+time.strftime('%Y%m%d',time.localtime(time.time()))+"/"+page_id+"/"+ str(
                                    img_id) + ".jpg"
                                self.img_url_list.append(img_src)
                                if img_id == 1:
                                    cursor.execute(
                                        "UPDATE images_page SET firstimg = " + "'" + img_loc_path + "'" + " WHERE id=" + "'" + str(pageid) + "'")
                                imgp = pageid, img_loc_path
                                cursor.execute("INSERT INTO images_image (pageid,imageurl) VALUES (%s,%s)", imgp)
                                self.img_url_list.append(img_src)
                        n += 1
                else:
                    for img_url in callback.split(","):
                        img_src="http://fm.shiyunjj.com/"+img_m_src+"/"+page_id+"/"+str(i)+"i"+img_url+".jpg"
                        img_loc_path=self.img_path+time.strftime('%Y%m%d',time.localtime(time.time()))+"/"+page_id+"/"+str(i)+"i"+img_url+".jpg"
                        if i == 1:
                            cursor.execute(
                                "UPDATE images_page SET firstimg = " + "'" + img_loc_path + "'" + " WHERE id=" + "'" + str(pageid) + "'")
                        imgp = pageid, img_loc_path
                        cursor.execute("INSERT INTO images_image (pageid,imageurl) VALUES (%s,%s)", imgp)
                        self.img_url_list.append(img_src)
                        i+=1

    def down_img(self,imgsrc):
        path=self.img_path+time.strftime('%Y%m%d',time.localtime(time.time()))+"/"
        page_id = imgsrc.split("/")[-2]
        isdata = os.path.exists("../" + path + page_id)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36",
            "Referer": "http://www.mmjpg.com/mm/" + page_id
        }
        if not isdata:
            os.makedirs("../" + path + page_id)
        with open("../" + path + page_id+"/"+imgsrc.split("/")[-1].split(".")[0]+".jpg","wb") as f:
            print("已保存："+ path + page_id+"/"+imgsrc.split("/")[-1].split(".")[0]+".jpg")
            f.write(s.get(imgsrc,headers=headers).content)

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
        # 启动thread_num个进程来爬去具体的img url 链接
        # for th in range(self.thread_num):
        #     add_pic_t = threading.Thread(target=self.get_img_url)
        #     add_pic_t.start()

        # 启动thread_num个来下载图片
        for img_th in range(self.thread_num):
            download_t = threading.Thread(target=self.down_url)
            download_t.start()

# 原站标签对应本站分类，如美腿标签对应本站诱惑丝袜分类，page为采集深度
if __name__ == "__main__":
    for i in [{"page": 1, "type": "tag/meitui", "type_id": 2}, {"page": 1, "type": "tag/xinggan", "type_id": 1},
              {"page": 1, "type": "tag/xiaoqingxin", "type_id": 3},{"page":1,"type":"tag/mengmei","type_id":4}]:
        spider=Spider(page_num=i.get("page"),img_path='/static/images/',thread_num=10,type_id=i.get("type_id"),type=i.get("type"))
        spider.get_page_url()
        spider.get_img_url()
        spider.run()
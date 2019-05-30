# coding='UTF-8'

from bs4 import BeautifulSoup
import threading, pymysql, time, requests, os, urllib3

requests.packages.urllib3.disable_warnings()


class Spider():
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/65.0.3325.181 Safari/537.36',
        'Referer': "https://www.mzitu.com"
    }
    page_url_list = []
    img_url_list = []
    rlock = threading.RLock()
    s = requests.session()
    s.keep_alive = False
    dbhost = {
        "host": "127.0.0.1",
        "dbname": "mmpic",
        "user": "mmpic",
        "password": "mmpic"
    }

    def __init__(self, page_num=10, img_path='imgdir', thread_num=5, type="xinggan", type_id=1):
        self.spider_url = 'https://www.mzitu.com/'
        self.page_number = int(page_num)
        self.img_path = img_path
        self.thread_num = thread_num
        self.type = type
        self.type_id = type_id

    def get_url(self):
        for i in range(1, self.page_number + 1):
            if i ==1:
                page = self.s.get(self.spider_url +"/"+self.type ,verify=False).text
            page=self.s.get(self.spider_url +"/"+self.type+"/page/"+str(i),verify=False).text
            soup = BeautifulSoup(page, "html.parser")
            page_base_url = soup.find("div",class_="postlist").find_all("li")
            for page_url in page_base_url:
                url = page_url.find("a").get("href")
                print(url)
                self.page_url_list.append(url)
            i = i + 1

    def get_img_url(self):
        db = pymysql.connect(self.dbhost.get("host"), self.dbhost.get("user"), self.dbhost.get("password"),
                             self.dbhost.get("dbname"))
        cursor = db.cursor()
        for img_base_url in self.page_url_list:
            tagidlist = []
            print("采集网址：",img_base_url)
            req = self.s.get(img_base_url,verify=False)
            html = req.content 
            img_soup = BeautifulSoup(html, "html.parser")
            #图片数量
            img_num = img_soup.find("div", class_="pagenavi").text.split("…")[-1][0:-5]
            print("img_num", img_num)
            #图片链接
            img_src = img_soup.find("div", class_="main-image").find("img").get("src")
            img_url = img_src.split("/")[0:-1]
            #print("img_url", img_url)
            img_surl = "/".join(img_url)
            # print("img_surl", img_surl)
            title = img_soup.find("h2", class_="main-title").text
            # print("title", title)
            isExists = cursor.execute("SELECT * FROM images_page WHERE title =" + "'" + title + "'" + " limit 1;")
            tag_list = img_soup.find("div", class_="main-tags").find_all("a")
            if isExists == 1:
                print("已采集：" + title)
            else:
                # tag为空时，添加tag为160
                if tag_list:
                    for tags in tag_list:
                        tag=tags.text
                        print(tag)
                        sqltag = "SELECT * FROM images_tag WHERE tag =" + "'" + tag + "'" + " limit 1;"
                        isExiststag = cursor.execute(sqltag)
                        if isExiststag != 1:
                            cursor.execute("INSERT INTO images_tag (tag) VALUES (%s)", tag)
                        cursor.execute("SELECT id FROM images_tag WHERE tag =" + "'" + tag + "'")
                        for id in cursor.fetchall():
                            tagidlist.append(id[0])
                else:
                    sqltag = "SELECT * FROM images_tag WHERE tag = '美女' AND id = 9999;"
                    isExiststag = cursor.execute(sqltag)
                    if isExiststag != 1:
                        cursor.execute("INSERT INTO images_tag (id, tag) VALUES (9999, '美女')")
                    tagidlist.append(9999)
                img_id=0
                #目标页面图片ID
                page_id=img_base_url.split("/")[-1].split(".")[0]
                #图片末尾id前缀
                page_before_id = img_src.split("/")[-1][0:3]
                #时间文件夹
                image_time_path = time.strftime('%Y%m%d', time.localtime(time.time()))
                for i in range(1, int(img_num)):
                    print("sleep 3 s")
                    time.sleep(3)
                    #图片名称
                    img_name = page_before_id + str("%02d" % i) + ".jpg"
                    #图片下载地址
                    img_url = img_surl + "/" + img_name
                    if i==1:
                        print("开始采集：" + title)
                        p = (title, str(tagidlist), image_time_path, self.type_id, "1")
                        cursor.execute("INSERT INTO images_page (title,tagid,sendtime,typeid,firstimg) VALUES (%s,%s,%s,%s,%s)",
                                       p)
                        img_id = str(cursor.lastrowid)
                        #图片保存在本地的路径
                        img_loc_path = self.img_path + image_time_path + "/" + img_id + "/" + img_name
                        #图片下载失败后删除该条数据
                        if self.down_img(img_url, img_id, image_time_path) == False:
                            cursor.execute("DELETE FROM `images_page` WHERE id = " + "'" + img_id + "'")
                            break
                        else:
                            cursor.execute(
                                "UPDATE images_page SET firstimg = " + "'" + img_loc_path + "'" + " WHERE id=" + "'" + img_id + "'")
                    else:
                        #图片保存在本地的路径
                        img_loc_path = self.img_path + image_time_path + "/" + img_id + "/" + img_name
                        #单条图片数据
                        imgp = img_id, img_loc_path
                        if self.down_img(img_url, img_id, image_time_path) == True:
                            cursor.execute("INSERT INTO images_image (pageid,imageurl) VALUES (%s,%s)", imgp)
                        #self.img_url_list.append(img_url_pageid)
        db.close()

    def down_img(self, imgsrc, img_id, time_path):
        flag = False
        path = self.img_path + time_path + "/"
        isdata = os.path.exists("../" + path + img_id)
        img_name = imgsrc.split("/")[-1].split(".")[0] + ".jpg"
        img_src = path + img_id + "/" + img_name
        if not isdata:
            os.makedirs("../" + path + img_id)
        with open("../" + img_src, "wb") as f:
            try:
                print("开始下载图片：" + imgsrc)
                t1 = time.time()
                img = requests.get(imgsrc, headers=self.headers, stream=True, timeout=30)
                f.write(img.content)
                t2 = time.time()
            except exceptions.Timeout as e:
                print('请求超时：'+str(e.message))
            except exceptions.HTTPError as e:
                print('http请求错误:'+str(e.message))
            else:
                # 通过status_code判断请求结果是否正确
                print('请求耗时%ss'%(t2-t1))
                if img.status_code == 200:
                    print("下载成功:", img_src)
                    flag = True
                else:
                    print('请求错误：'+str(img.status_code))
        return flag

    #删除错误图片数据
    def del_wrong_img(self):
        db = pymysql.connect(self.dbhost.get("host"), self.dbhost.get("user"), self.dbhost.get("password"),
                             self.dbhost.get("dbname"))
        cursor = db.cursor()
        cursor.execute("DELETE FROM `images_page` WHERE firstimg = '1'")
        db.close()

if __name__ == '__main__':
    for i in [{"page": 10, "type": "xinggan", "type_id": 1}, {"page": 1, "type": "mm", "type_id": 3}]:
        spider = Spider(page_num=i.get("page"), img_path='/static/images/mzitu/', thread_num=1, type_id=i.get("type_id"),
                        type=i.get("type"))
        print("开始采集链接")
        spider.get_url()
        print("开始采集图片")
        spider.get_img_url()
        print("删除错误图片数据")
        spider.del_wrong_img()
        # spider.run()

# coding:utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import requests,json,time
import smtplib
from email.mime.text import MIMEText
import random
from bs4 import BeautifulSoup
import logging
import os

# nohup stdbuf -oL python group_api_topics.py &
mailto_list = ""
mail_host = "smtp.163.com"
mail_user = ""
mail_pass = ""

sended_dict = {}
px_pool = ['127.0.0.1']

# 发送邮件到指定邮箱，其中mailuser 为发送邮件邮箱账号， mailto_list 为接收邮件账户列表
def send_mail(to_list, sub, content):
    me = "Server Monitor" + "<" + mail_user + ">"
    msg = MIMEText(content, _subtype='plain', _charset='utf-8')
    msg['Subject'] = sub
    msg['From'] = me
    msg['To'] = ";".join(to_list)
    msg['Cc'] = me
    try:
        server = smtplib.SMTP_SSL()
        server.connect(mail_host)
        server.login(mail_user, mail_pass)
        server.sendmail(me, to_list, msg.as_string())
        server.close()
        return True
    except Exception, e:
        print str(e)
        return False

# 由于豆瓣api限制，每小时只能发送100个请求，此函数为程序加载不同Https代理，每次请求随机选择不同的https代理
def load_proxy_pool():
    return
    for l in open('./proxy_pool','r').readlines():
        px = l.split('\n')[0].split('\t')
        px_pool.append('https://{}:{}'.format(px[0],px[1]))
    print px_pool



#此函数发送 get 请求， params为请求参数，指定从何处开始，每次请求要求返回多少条消息
#返回消息为json格式，具体属性名称及格式参考 https://www.douban.com/group/topic/33507002/

def get_topic_list(groupids= ['579372']):

    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/52.0.2743.116 Safari/537.36'}
    params = {'start': 0, 'count': 150}
    print '-------------------'
    topics = []
    for id in groupids:
        flag = True
        r = None
        while flag:
            proxies = {'https': random.choice(px_pool)}
            print 'groupid: {}, proxy:{}'.format(id, proxies)
            try:
                r = requests.get('https://api.douban.com/v2/group/{}/topics'.format(id),
                                 headers = headers,
                                 # proxies = proxies,
                                 params = params)
                if r.status_code == 200:
                    flag = False
                else:
                    print ('Bad proxy:', proxies)
            except Exception, e:
                print ('Error proxy:', proxies)
                print str(e)

        data = json.loads(r.text)
        print data['topics'][0]['updated']
        print data['topics'][-1]['updated']
        topics.extend(data['topics'])
    print '-------------------'
    print 'Save json files'
    json_obj = {"data": topics}
    save_json_file(json_obj)
    return topics

# 搜索topic内容中是否包含 指定关键字的topic
def content_search(topic, key_words = [],excludewords=[],blacklist=[]):
    flag = False
    for k in key_words:
        if k.decode('utf-8') in topic['title']:
            flag = True
        elif k.decode('utf-8') in topic['content']:
            flag = True
    for k in excludewords:
        if k.decode('utf-8') in topic['title']:
            flag = False
        elif k.decode('utf-8') in topic['content']:
            flag = False

    for k in blacklist:
        if k.decode('utf-8') in topic['title']:
            flag = False
        elif k.decode('utf-8') in topic['content']:
            flag = False

    if topic['author']['uid'] in blacklist:
        print topic['author']['uid']
        flag = False

#   if flag == False:
#       print topic['title']

    if u'不是自如' in topic['content']:
        flag = True

    if flag==True:
        return ['\n',topic['created'],'\n',topic['title'],'\n',topic['share_url']]
    else:
        return
# 遍历所有在topics 中的topic， 找到含有关键词列表keywords 的所有topic 并返回
def related_houses(topics,keywords = [],excludewords=[],blacklist=[]):
    houses = []
    for topic in topics:
        url = content_search(topic,keywords ,excludewords,blacklist)
        if url is not None:
            houses.append(url)
    return houses

# 此函数为检测相同的topic是否已发送过， 如果发送过则不发送， 没有发送过则发送并在发送过的字典中添加该topic
def house_filter(houses):
    filterd_hs = []
    for h in houses:
        if not sended_dict.has_key(h[-1]):
            sended_dict[h[-1]] = ''
            filterd_hs.append(h)
            sended_urls = open('./sended_urls', 'w')
            sended_urls.write(str(sended_dict.keys()))
            sended_urls.flush()
            sended_urls.close()
    return filterd_hs

# 此函数为加载是否历史发送过的topic 列表，初始时为空， 每次发送都重新写入
def recovery_sendedurls():
    if not os.path.exists('sended_urls'):
        with open("sended_urls", "w") as fo:
            fo.write('')
    content = open('./sended_urls', 'r').readline()
    if content != '':
        strs = eval(content)
        if strs is not None :
            for i in strs:
                sended_dict[i] = ''
#   print sended_dict.keys()

# 此函数为监控的主函数，每隔gap秒对小组列表内的小组发送一次请求，
# 如果返回结果中不含有满足要求topic， 即len(f_houses)=0 则不发送邮件
# 如果含有满足要求的topic 则发送邮件
def topic_monitor(gap = 400,keywords = [],excludewords=[],blacklist=[],groupids = [],url58='sz.58.com/nanshan'):
    while True:
        five8_houses = house_filter(get_58_url(keywords,base_url='http://'+url58+'/chuzu/0/pn{}'))
        topics = get_topic_list(groupids = groupids)
        houses = related_houses(topics,keywords ,excludewords,blacklist)
        douban_houses = house_filter(houses)
        f_houses = douban_houses+five8_houses
        if len(f_houses)>0:
            list2send=(''.join([''.join(f) for f in f_houses])).encode('utf-8')
            print "发送完成请查收邮件,五分钟后进行下一次抓取,请不要关闭窗口".encode('GBK')
            with open("result.txt", "a") as fo:
                fo.write(list2send)
            send_mail([mailto_list], 'For your information, House!',list2send)
        time.sleep(gap)

def save_json_file(objs):
    f = open('./results.json','w')
    json.dump(objs, f)
    f.close()

def get_58_url(keywords=[],base_url=''):
    print base_url
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/52.0.2743.116 Safari/537.36'}
    start_page = 1
    result = []
    while True:
        page_url = base_url.format(start_page)
        try:
            html = requests.get(page_url, headers=headers, timeout=20).text
        except Exception as e:
            logging.exception(e)
            continue
        house_list = BeautifulSoup(html, 'lxml').find_all(
            'div', {'class': 'des'})
        if house_list == []:
            break
        for item in house_list:
            r = item.find('a')
            url = 'http:'+r.get('href')
            if u'short' in url:
                continue
            for k in keywords:
                if k.decode('utf-8') in r.text:
                    result.append([item.find_parent().find(class_='sendTime').text.replace(' ',''),r.text.replace(' ','').replace('|',' '),'\n',url])
                    break
        print('Page', start_page, 'OK')
        if start_page == 20:
            break
        start_page += 1
        time.sleep(1)
    return result

def deal_parameters(**kwargs):
    print ('\n')
    configData = {'keywords':'','excludewords':'','groupids':'','blacklist':''}
    if os.path.exists('config.json'):
        with open('config.json') as json_file:
            configData = json.load(json_file)

    for k in kwargs.keys():
        if len(kwargs[k]) > 0:
            configData[k] = kwargs[k].decode('GBK').encode('utf-8').replace('，',',').replace('\n','').split(',')
        else:
            kwargs[k] = ''.join([c+',' for c in configData[k]])

        print k+" ",kwargs[k]

    f = open('./config.json', 'w')
    json.dump(configData, f)
    f.close()
    return configData

def dealmailinfo(**kwargs):
    print ('\n')
    mailinfo = {'mailto_list':'','mail_host':'','mail_user':'','mail_pass':''}
    if os.path.exists('mail.json'):
        with open('mail.json') as json_file:
            mailinfo = json.load(json_file)
    for k in kwargs.keys():
        if len(kwargs[k]) > 0:
            mailinfo[k] = kwargs[k]
        else:
            kwargs[k] = mailinfo[k]
        print k+" ",kwargs[k]

    f = open('./mail.json', 'w')
    json.dump(mailinfo, f)
    f.close()
    print '\n'
    return mailinfo

if __name__ == '__main__':
    mailto_list = raw_input("接受邮箱:".encode('GBK'))
    mail_user = raw_input("发送邮箱:".encode('GBK'))
    mail_host = raw_input("发送邮箱的smtp服务器地址:".encode('GBK'))
    mail_pass = raw_input("发送邮箱的密码:".encode('GBK'))

    mail_params = dealmailinfo(mailto_list=mailto_list,mail_host=mail_host,mail_user=mail_user,mail_pass=mail_pass)

    mailto_list = mail_params['mailto_list']
    mail_user = mail_params['mail_user']
    mail_host = mail_params['mail_host']
    mail_pass = mail_params['mail_pass']

    url58=raw_input("请输入58同城网址(必填):".encode('GBK'))
    if len(url58)==0:
        # quit()
        url58 = 'sz.58.com/nanshan'

    groupids = raw_input("豆瓣小组id(逗号分隔,留空则默认读取上次输入):".encode('GBK'))
    keywords = raw_input("输入需要的关键词(比如'美丽花园'，逗号分隔,留空则默认读取上次输入):".encode('GBK'))
    excludewords = raw_input("过滤关键词(比如'床位'，逗号分隔,留空则默认读取上次输入):".encode('GBK'))
    blacklist = raw_input("豆瓣发帖人id黑名单(逗号分隔,留空则默认读取上次输入):".encode('GBK'))

    deal_params = deal_parameters(keywords=keywords,excludewords=excludewords,groupids=groupids,blacklist=blacklist)

    keywords=deal_params['keywords']
    excludewords = deal_params['excludewords']
    groupids = deal_params['groupids']
    blacklist = deal_params['blacklist']

    recovery_sendedurls()
    # load_proxy_pool()
    topic_monitor(keywords=keywords, excludewords=excludewords,groupids = groupids,blacklist = blacklist,url58=url58)

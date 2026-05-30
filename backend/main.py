from flask import Flask, request, redirect ,jsonify
import json
import os
import urllib.parse
from hashlib import md5
from random import randrange
import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def HexDigest(data):
    return "".join([hex(d)[2:].zfill(2) for d in data])

def HashDigest(text):
    HASH = md5(text.encode("utf-8"))
    return HASH.digest()

def HashHexDigest(text):
    return HexDigest(HashDigest(text))

def parse_cookie(text: str):
    cookie_ = [item.strip().split('=', 1) for item in text.strip().split(';') if item]
    cookie_ = {k.strip(): v.strip() for k, v in cookie_}
    return cookie_

def ids(ids):
    if '163cn.tv' in ids:
        response = requests.get(ids, allow_redirects=False)
        ids = response.headers.get('Location')
    if 'music.163.com' in ids:
        index = ids.find('id=') + 3
        ids = ids[index:].split('&')[0]
    return ids

def size(value):
     units = ["B", "KB", "MB", "GB", "TB", "PB"]
     size = 1024.0
     for i in range(len(units)):
         if (value / size) < 1:
             return "%.2f%s" % (value, units[i])
         value = value / size
     return value

def music_level1(value):
    if value == 'standard':
        return "标准音质"
    elif value == 'exhigh':
        return "极高音质"
    elif value == 'lossless':
        return "无损音质"
    elif value == 'hires':
        return "Hires音质"
    elif value == 'sky':
        return "沉浸环绕声"
    elif value == 'jyeffect':
        return "高清环绕声"
    elif value == 'jymaster':
        return "超清母带"
    else:
        return "未知音质"

def post(url, params, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',
        'Referer': 'https://music.163.com/',
    }
    cookies = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!"
    }
    cookies.update(cookie)
    response = requests.post(url, headers=headers, cookies=cookies, data={"params": params})
    return response.text

def read_cookie():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_file = os.path.join(script_dir, 'cookie.txt')
    with open(cookie_file, 'r') as f:
        cookie_contents = f.read()
    return cookie_contents

app = Flask(__name__)

@app.route('/')
def hello_world():
    return '网易云音乐API服务'

@app.route('/health')
def health():
    return jsonify({
        'service': '网易云音乐API',
        'status': 'running',
        'port': 5002
    })

@app.route('/Song_V1',methods=['GET','POST'])
def Song_v1():
    if request.method == 'GET':
       song_ids = request.args.get('ids')
       url = request.args.get('url')
       level = request.args.get('level')
       type = request.args.get('type')
    else:
       song_ids = request.form.get('ids')
       url = request.form.get('url')
       level = request.form.get('level')
       type = request.form.get('type')

    if not song_ids and url is None:
        return jsonify({'error': '必须提供 ids 或 url 参数'}), 400
    if level is None:
        return jsonify({'error': 'level参数为空'}), 400
    if type is None:
        return jsonify({'error': 'type参数为空'}), 400

    if song_ids:
        jsondata = song_ids
    elif url:
        jsondata = url
    else:
        return jsonify({'error': '错误!'}), 400

    cookies = parse_cookie(read_cookie())

    url = "https://interface3.music.163.com/eapi/song/enhance/player/url/v1"
    AES_KEY = b"e82ckenh8dichen8"
    config = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!",
        "requestId": str(randrange(20000000, 30000000))
    }

    payload = {
        'ids': [ids(jsondata)],
        'level': level,
        'encodeType': 'flac',
        'header': json.dumps(config),
    }

    if level == 'sky':
        payload['immerseType'] = 'c51'

    url2 = urllib.parse.urlparse(url).path.replace("/eapi/", "/api/")
    digest = HashHexDigest(f"nobody{url2}use{json.dumps(payload)}md5forencrypt")
    params = f"{url2}-36cd479b6b5-{json.dumps(payload)}-36cd479b6b5-{digest}"

    padder = padding.PKCS7(algorithms.AES(AES_KEY).block_size).padder()
    padded_data = padder.update(params.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
    encryptor = cipher.encryptor()
    enc = encryptor.update(padded_data) + encryptor.finalize()
    params = HexDigest(enc)

    response = post(url, params, cookies)

    if "参数错误" in response:
       return jsonify({"status": 400,'msg': '参数错误！'}), 400

    jseg = json.loads(response)
    song_names = "https://interface3.music.163.com/api/v3/song/detail"
    data = {'c': json.dumps([{"id":jseg['data'][0]['id'],"v":0}])}
    resp = requests.post(url=song_names, data=data, headers={'Referer': 'https://music.163.com/'})
    jse = json.loads(resp.text)
    if jseg['data'][0]['url'] is not None:
        if jse['songs']:
           song_url = jseg['data'][0]['url']
           song_name = jse['songs'][0]['name']
           song_picUrl = jse['songs'][0]['al']['picUrl']
           song_alname = jse['songs'][0]['al']['name']
           artist_names = []
           for song in jse['songs']:
               ar_list = song['ar']
               if len(ar_list) > 0:
                   artist_names.append('/'.join(ar['name'] for ar in ar_list))
               song_arname = ', '.join(artist_names)
    else:
       return jsonify({"status": 400,'msg': '信息获取不完整！'}), 400

    if type == 'text':
       return '歌曲名称：' + song_name + '<br>歌曲图片：' + song_picUrl  + '<br>歌手：' + song_arname + '<br>歌曲专辑：' + song_alname + '<br>歌曲音质：' + music_level1(jseg['data'][0]['level']) + '<br>歌曲大小：' + size(jseg['data'][0]['size']) + '<br>音乐地址：' + song_url
    elif  type == 'down':
       return redirect(song_url)
    elif  type == 'json':
       return jsonify({
           "status": 200,
           "name": song_name,
           "pic": song_picUrl,
           "ar_name": song_arname,
           "al_name": song_alname,
           "level": music_level1(jseg['data'][0]['level']),
           "size": size(jseg['data'][0]['size']),
           "url": song_url
        })
    else:
        return jsonify({"status": 400,'msg': '解析失败！请检查参数是否完整！'}), 400

if __name__ == '__main__':
    app.config['JSON_SORT_KEYS'] = True
    app.config['JSON_AS_ASCII'] = True
    app.run(host='0.0.0.0', port=5002, debug=False)

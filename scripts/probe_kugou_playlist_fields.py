"""检查 mobilecdn 歌单响应字段"""
import requests

url = 'http://mobilecdn.kugou.com/api/v3/special/song'
params = {'specialid': '546903', 'page': 1, 'pagesize': 1, 'version': 9108, 'area_code': 1}
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
}
r = requests.get(url, params=params, headers=headers, timeout=10)
d = r.json()
song = d['data']['info'][0]
for k in ['hash', 'duration', 'filename', 'album_name', 'singername', 'songname', 'filesize',
          'albumname', 'album_img', '320hash', 'sqhash', 'audio_id', 'album_id']:
    print(f'{k}: {song.get(k)!r}')

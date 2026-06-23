"""音频元数据写入工具

支持 MP3 (ID3), FLAC (Vorbis), M4A (iTunes) 三种格式
"""
import logging

import mutagen.mp4
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, USLT, APIC, TXXX, error as ID3Error
from mutagen.mp4 import MP4, MP4Cover

from utils.audio_utils import download_cover
from utils.filename import normalize_artist_name

logger = logging.getLogger(__name__)


def write_metadata(
    file_path: str,
    extension: str,
    name: str,
    artist: str,
    album: str,
    lyric: str = '',
    cover_url: str = '',
    platform: str = '',
    song_id: str = '',
) -> bool:
    """给音频文件写入 metadata（mp3/flac/m4a），支持封面图片

    Args:
        file_path: 音频文件路径
        extension: 文件扩展名（.mp3/.flac/.m4a）
        name: 歌曲名
        artist: 歌手（多歌手自动规范化为 / 拼接）
        album: 专辑
        lyric: 歌词（可选）
        cover_url: 封面URL（可选）
        platform: 平台来源（netease/qq/kugou等，可选）
        song_id: 歌曲ID（可选）

    Returns:
        True 成功，False 失败
    """
    # 多歌手统一格式化为 /
    artist = normalize_artist_name(artist)

    try:
        cover_data = download_cover(cover_url) if cover_url else None
    except Exception as e:
        logger.warning(f"下载封面失败: {e}")
        cover_data = None

    try:
        if extension == '.mp3':
            _write_mp3(file_path, name, artist, album, lyric, cover_data, platform, song_id)
        elif extension == '.flac':
            _write_flac(file_path, name, artist, album, lyric, cover_data, platform, song_id)
        elif extension in ('.m4a', '.mp4'):
            _write_m4a(file_path, name, artist, album, lyric, cover_data, platform, song_id)
        else:
            logger.warning(f"不支持的音频格式: {extension}")
            return False
        return True
    except Exception as e:
        logger.warning(f"写入 metadata 失败 ({extension}): {e}")
        return False


def _write_mp3(file_path, name, artist, album, lyric, cover_data, platform, song_id):
    """写入 MP3 (ID3) 标签"""
    try:
        audio = ID3(file_path)
    except ID3Error:
        audio = ID3()

    # 清除旧标签
    audio.delall('TIT2')
    audio.delall('TPE1')
    audio.delall('TALB')
    audio.delall('USLT')
    audio.delall('APIC')
    audio.delall('TXXX:PLATFORM')
    audio.delall('TXXX:SONG_ID')

    # 写入新标签
    if name: audio.add(TIT2(encoding=3, text=[name]))
    if artist: audio.add(TPE1(encoding=3, text=[artist]))
    if album: audio.add(TALB(encoding=3, text=[album]))
    if lyric: audio.add(USLT(encoding=3, lang='chi', desc='', text=lyric))
    if cover_data:
        audio.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))
    if platform: audio.add(TXXX(encoding=3, desc='PLATFORM', text=[str(platform)]))
    if song_id: audio.add(TXXX(encoding=3, desc='SONG_ID', text=[str(song_id)]))

    audio.save(file_path)


def _write_flac(file_path, name, artist, album, lyric, cover_data, platform, song_id):
    """写入 FLAC (Vorbis Comment) 标签"""
    audio = FLAC(file_path)
    audio['title'] = name
    audio['artist'] = artist
    audio['album'] = album

    # 清除所有可能的歌词字段（不区分大小写，避免 LYRICS/lyrics/Lyrics 重复）
    lyrics_keys = [k for k in audio.keys() if k.lower() in ('lyrics', 'lyric')]
    for k in lyrics_keys:
        del audio[k]

    if lyric:
        audio['lyrics'] = lyric

    # 清除已存在的 platform/song_id 字段，避免重复
    if 'PLATFORM' in audio:
        del audio['PLATFORM']
    if 'SONG_ID' in audio:
        del audio['SONG_ID']

    if platform:
        audio['PLATFORM'] = str(platform)
    if song_id:
        audio['SONG_ID'] = str(song_id)

    if cover_data:
        audio.clear_pictures()
        picture = Picture()
        picture.data = cover_data
        picture.type = 3  # Front cover
        picture.mime = 'image/jpeg'
        picture.desc = 'Cover'
        audio.add_picture(picture)

    audio.save()


def _write_m4a(file_path, name, artist, album, lyric, cover_data, platform, song_id):
    """写入 M4A/MP4 (iTunes) 标签"""
    audio = MP4(file_path)
    audio['\xa9nam'] = [name]
    audio['\xa9ART'] = [artist]
    audio['\xa9alb'] = [album]
    if lyric:
        audio['\xa9lyr'] = [lyric]

    # 写入 platform 和 song_id 到 freeform 原子
    # 先清除已存在的，避免重复
    if platform:
        platform_key = '----:com.apple.iTunes:PLATFORM'
        if platform_key in audio:
            del audio[platform_key]
        audio[platform_key] = [
            mutagen.mp4.MP4FreeForm(str(platform).encode('utf-8'))
        ]

    if song_id:
        song_id_key = '----:com.apple.iTunes:SONG_ID'
        if song_id_key in audio:
            del audio[song_id_key]
        audio[song_id_key] = [
            mutagen.mp4.MP4FreeForm(str(song_id).encode('utf-8'))
        ]

    if cover_data:
        audio['covr'] = [MP4Cover(cover_data, MP4Cover.FORMAT_JPEG)]

    audio.save()


def read_metadata(file_path: str) -> dict:
    """读取音频文件的元数据

    Args:
        file_path: 音频文件路径

    Returns:
        元数据字典: {
            name, artist, album, lyric, platform, song_id, cover
        }
    """
    from pathlib import Path
    ext = Path(file_path).suffix.lower()

    metadata = {
        'name': '', 'artist': '', 'album': '',
        'lyric': '', 'platform': '', 'song_id': '',
        'cover': b'',
    }

    try:
        if ext == '.mp3':
            audio = ID3(file_path)
            metadata['name'] = str(audio.get('TIT2', ''))
            metadata['artist'] = str(audio.get('TPE1', ''))
            metadata['album'] = str(audio.get('TALB', ''))
            uslt = audio.getall('USLT')
            if uslt:
                metadata['lyric'] = uslt[0].text
            txxx_p = audio.getall('TXXX:PLATFORM')
            if txxx_p:
                metadata['platform'] = txxx_p[0].text[0]
            txxx_s = audio.getall('TXXX:SONG_ID')
            if txxx_s:
                metadata['song_id'] = txxx_s[0].text[0]
            apic = audio.getall('APIC')
            if apic:
                metadata['cover'] = apic[0].data

        elif ext == '.flac':
            audio = FLAC(file_path)
            metadata['name'] = audio.get('title', [''])[0]
            metadata['artist'] = audio.get('artist', [''])[0]
            metadata['album'] = audio.get('album', [''])[0]
            # 不区分大小写读取歌词字段（兼容 LYRICS/lyrics/Lyrics）
            for k in audio.keys():
                if k.lower() in ('lyrics', 'lyric') and audio[k]:
                    metadata['lyric'] = audio[k][0]
                    break
            metadata['platform'] = audio.get('PLATFORM', [''])[0]
            metadata['song_id'] = audio.get('SONG_ID', [''])[0]
            if audio.pictures:
                metadata['cover'] = audio.pictures[0].data

        elif ext in ('.m4a', '.mp4'):
            audio = MP4(file_path)
            metadata['name'] = audio.get('\xa9nam', [''])[0]
            metadata['artist'] = audio.get('\xa9ART', [''])[0]
            metadata['album'] = audio.get('\xa9alb', [''])[0]
            metadata['lyric'] = audio.get('\xa9lyr', [''])[0]
            p_list = audio.get('----:com.apple.iTunes:PLATFORM', [])
            if p_list:
                metadata['platform'] = p_list[0].decode('utf-8')
            s_list = audio.get('----:com.apple.iTunes:SONG_ID', [])
            if s_list:
                metadata['song_id'] = s_list[0].decode('utf-8')
            covr = audio.get('covr', [])
            if covr:
                metadata['cover'] = bytes(covr[0])
    except Exception as e:
        logger.debug(f"读取元数据失败 ({file_path}): {e}")

    return metadata

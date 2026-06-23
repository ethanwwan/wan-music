#!/usr/bin/env python3
"""检查 FLAC 文件的元数据"""
import os
import sys
from mutagen.flac import FLAC

filepath = '/Users/Awan/Public/Repository/wan-music/backend/scripts/雅俗共赏 - 许嵩.flac'

print('=' * 60)
print(f'文件: {filepath}')
size = os.path.getsize(filepath)
print(f'大小: {size} bytes ({size / 1024 / 1024:.2f} MB)')
print('=' * 60)

audio = FLAC(filepath)

print('\n【基础信息】')
basic_keys = ['title', 'artist', 'album', 'albumartist', 'date', 'genre', 'tracknumber', 'discnumber']
for key in basic_keys:
    if key in audio:
        values = audio[key]
        if values:
            print(f'  {key}: {values[0] if len(values) == 1 else values}')

print('\n【自定义字段】')
custom_keys = ['PLATFORM', 'SONG_ID', 'lyrics', 'LYRICS', 'comment']
for key in custom_keys:
    if key in audio:
        values = audio[key]
        if values:
            value = values[0] if len(values) == 1 else values
            if key.lower() in ('lyrics',):
                print(f'  {key}: ({len(str(value))} 字符)')
                # 显示前 200 个字符
                preview = str(value)[:200]
                print(f'    预览: {preview}...')
            else:
                print(f'  {key}: {value}')
    else:
        if key in ('PLATFORM', 'SONG_ID'):
            print(f'  {key}: (无)')

print('\n【封面】')
if audio.pictures:
    print(f'  共 {len(audio.pictures)} 张')
    for i, pic in enumerate(audio.pictures):
        print(f'  封面 {i+1}:')
        print(f'    类型: {pic.type}')
        print(f'    MIME: {pic.mime}')
        print(f'    尺寸: {pic.width}x{pic.height}')
        print(f'    深度: {pic.depth}')
        print(f'    颜色数: {pic.colors}')
        print(f'    数据大小: {len(pic.data)} bytes')
        if pic.desc:
            print(f'    描述: {pic.desc}')
else:
    print('  (无封面)')

print('\n【音频信息】')
info = audio.info
print(f'  时长: {info.length:.2f} 秒 ({int(info.length // 60)}:{int(info.length % 60):02d})')
print(f'  采样率: {info.sample_rate} Hz')
print(f'  位深: {info.bits_per_sample} bit')
print(f'  声道: {info.channels}')
print(f'  比特率: {info.bitrate} bps')
print(f'  总采样数: {info.total_samples}')

print('\n【所有元数据键】')
all_keys = list(audio.keys())
print(f'  共 {len(all_keys)} 个键: {all_keys}')

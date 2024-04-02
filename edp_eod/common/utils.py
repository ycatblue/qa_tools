# -*- coding: utf-8 -*-
import gzip
import json
import os
import re
import shutil
import warnings
from datetime import datetime
from email.quoprimime import unquote

import requests


def post_main(url, headers, data=None):
    warnings.filterwarnings('ignore')
    response = requests.post(url=url, headers=headers, data=data, verify=False)
    return response


# 通过传参控制要登录的环境
def login(env):
    sit_url = "https://adminui.sit.edp-atp.finstadiumxjp.com//api/admin/auth/login"
    uat_url = "https://adminui.uat.edp-atp.finstadiumxjp.com//api/admin/auth/login"
    data = json.dumps({
        "email": "miaolan.huang@farsightedyu.com",
        "password": "12345678.",
        "verifyCode": "1234"
    })
    headers = {
        "Content-Type": "application/json"
    }
    if env == 'SIT':
        response = post_main(sit_url, headers, data).json()
    elif env == 'UAT':
        response = post_main(uat_url, headers, data).json()
    else:
        return
    token_data = response['accessToken']
    access_token = 'Bearer{}'.format(token_data)
    return access_token


# 通过参数获取需要下载的文件名称的日期后缀
def get_date():
    # 获取当前时间
    date = datetime.now()
    date_year = date.year
    date_month = date.month
    date_day = date.day
    date_staring = f"{date_year}{date_month:02d}{date_day:02d}"
    return date_staring


# 保存下载的附件
def save_file(response, filename):
    # 获取当前目录路径
    current_dir = os.getcwd()
    # 创建log目录路径
    log_dir = os.path.join(current_dir, 'temp_file')
    # 确保log目录存在
    os.makedirs(log_dir, exist_ok=True)
    # 拼接文件路径
    file_path = os.path.join(log_dir, filename)

    # 将下载的内容写入文件
    with open(file_path, 'wb') as file:
        file.write(response.content)


# 解压压缩包
def decompress_gzip_file(input_path, output_dir):
    # 获取压缩文件的默认文件名并去除文件拓展名
    base_filename = os.path.splitext(os.path.basename(input_path))[0]
    # 构建压缩后的文件路径
    output_path = os.path.join(output_dir, base_filename)

    with gzip.open(input_path, 'rb') as f_in:
        with open(output_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    print("文件下载成功")


def download_eod(env, filename):
    decoded_filename = ''
    print("文件下载中......")

    # 定义两个环境url
    sit_url = "https://adminui.sit.edp-atp.finstadiumxjp.com//api/statistical-report/download-file"
    uat_url = "https://adminui.uat.edp-atp.finstadiumxjp.com//api/statistical-report/download-file"

    # 拼接EOD路径
    eod_file_path = '/data/RSec/for_RSec/EoD/{}_{}.csv.gz'.format(filename, get_date())
    print('EOD文件路径：' + eod_file_path)
    data = json.dumps({
        'route': eod_file_path
    })
    # 构建请求头
    headers = {
        'Authorization': login(env),
        'Content-Type': 'application/json'
    }

    # 判断环境sit/uat
    if env == 'SIT':
        response = post_main(sit_url, headers, data)
    elif env == 'UAT':
        response = post_main(uat_url, headers, data)
    else:
        return

    # 检查响应状态码，确认请求成功
    if response.status_code == 201:
        # 从响应中获取文件名
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
            decoded_filename = unquote(filename).replace('"', '').strip('? ').rstrip()
        # 保存文件
        save_file((response, decoded_filename))
        # 定义压缩路径
        gz_file_path = 'temp_file/' + decoded_filename
        # 输出的压缩文件目录
        output_dir = os.path.dirname(gz_file_path)
        # 解压缩文件
        decompress_gzip_file(gz_file_path, output_dir)
    else:
        print("请求失败")


# 校验时间格式是否正确
def validate_date_format(date_string):
    pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}000'
    match = re.fullmatch(pattern, date_string)
    return match is not None

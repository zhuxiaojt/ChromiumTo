import os
import requests
import zipfile
import shutil
from utils import getAppDataPath

# 下载配置
CHROMIUM_DOWNLOAD_URL = "https://commondatastorage.googleapis.com/chromium-browser-snapshots/Win_x64/1000000/chrome-win.zip"
CHROMIUM_DOWNLOAD_PATH = os.path.join(getAppDataPath(), "chrome-win.zip")
CHROMIUM_EXTRACT_PATH = os.path.join(getAppDataPath(), "chrome-win")


def downloadChromiumKernel(progress_callback=None):
    """下载Chromium内核"""
    try:
        # 发送请求
        response = requests.get(CHROMIUM_DOWNLOAD_URL, stream=True)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        # 写入文件
        with open(CHROMIUM_DOWNLOAD_PATH, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 回调下载进度
                    if progress_callback:
                        progress_callback(downloaded_size, total_size)
        
        # 解压文件
        extractChromiumKernel(progress_callback)
        
        # 返回解压后的路径
        return True, CHROMIUM_EXTRACT_PATH
    
    except Exception as e:
        return False, str(e)


def extractChromiumKernel(progress_callback=None):
    """解压Chromium内核"""
    try:
        # 清空之前的解压目录
        if os.path.exists(CHROMIUM_EXTRACT_PATH):
            shutil.rmtree(CHROMIUM_EXTRACT_PATH)
        
        # 解压文件
        with zipfile.ZipFile(CHROMIUM_DOWNLOAD_PATH, 'r') as zip_ref:
            # 获取文件列表和总大小
            file_list = zip_ref.infolist()
            total_files = len(file_list)
            extracted_files = 0
            
            # 解压所有文件
            for file_info in file_list:
                zip_ref.extract(file_info, CHROMIUM_EXTRACT_PATH)
                extracted_files += 1
                
                # 回调解压进度
                if progress_callback:
                    progress_callback(extracted_files, total_files, 'extract')
        
        return True
    except Exception as e:
        return False


def getSharedKernelPath():
    """获取共享内核路径"""
    # 检查解压后的目录是否存在
    chrome_exe_path = os.path.join(CHROMIUM_EXTRACT_PATH, "chrome.exe")
    if os.path.exists(chrome_exe_path):
        return CHROMIUM_EXTRACT_PATH
    return None


def cleanupDownloadFiles():
    """清理下载文件"""
    try:
        # 删除下载的zip文件
        if os.path.exists(CHROMIUM_DOWNLOAD_PATH):
            os.remove(CHROMIUM_DOWNLOAD_PATH)
        return True
    except Exception:
        return False
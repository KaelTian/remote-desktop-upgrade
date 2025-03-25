"""
通用工具模块，提供各种辅助功能
"""
import base64
import pickle
import zlib
import socket
import struct
from cryptography.fernet import Fernet
import logging
import cv2
import numpy as np
import sys
import io
import time
from PIL import ImageGrab

# 默认加密密钥，实际使用时应由用户自行设置
DEFAULT_KEY = b'YD4XY7D9GKovs9tjJQQdOIr_wPvZ9wv_SjTvEKbvlpY='

def get_local_ip():
    """改进的IP获取方法"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_key():
    """生成新的加密密钥"""
    return Fernet.generate_key()

class SecureSocket:
    """安全套接字封装，提供加密通信功能"""
    
    def __init__(self, sock=None, encryption_key=None):
        self.socket = sock if sock else socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 如果没有提供密钥，使用默认密钥
        self.fernet = Fernet(encryption_key if encryption_key else DEFAULT_KEY)
        
    def connect(self, host, port):
        """连接到指定主机和端口"""
        self.socket.connect((host, port))
        
    def send_data(self, data):
        """增加数据校验机制"""
        checksum = zlib.crc32(pickle.dumps(data))
        serialized_data = pickle.dumps(data)
        compressed_data = zlib.compress(serialized_data)
        encrypted_data = self.fernet.encrypt(compressed_data)
        # 添加校验头
        header = struct.pack('>II', len(encrypted_data), checksum)
        self.socket.sendall(header)
        self.socket.sendall(encrypted_data)
        
    def receive_data(self, timeout=1.0):
        """增加接收超时"""
        self.socket.settimeout(timeout)
        # 接收数据大小
        data_size = struct.unpack('>I', self.socket.recv(4))[0]
        # 接收数据
        encrypted_data = b''
        while len(encrypted_data) < data_size:
            packet = self.socket.recv(data_size - len(encrypted_data))
            if not packet:
                return None
            encrypted_data += packet
        
        # 解密数据
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data)
            # 解压数据
            decompressed_data = zlib.decompress(decrypted_data)
            # 反序列化数据
            return pickle.loads(decompressed_data)
        except Exception as e:
            print(f"Error decrypting data: {e}")
            return None
    
    def close(self):
        """关闭套接字"""
        self.socket.close()
        
def compress_image(image_data, quality=50):
    """压缩图像数据"""
    
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("无效的图像数据")
            
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, encimg = cv2.imencode('.jpg', img, encode_param)
        return encimg.tobytes()
    except Exception as e:
        logging.error("图像压缩失败: %s", e)
        return image_data  # 返回原始数据作为降级方案 

def send_screen(self, client):
    """基础截图功能"""
    while self.running:
        try:
            screenshot = ImageGrab.grab()
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='JPEG', quality=85)
            client.send_data({
                "type": "screen",
                "image": base64.b64encode(img_byte_arr.getvalue()).decode()
            })
            time.sleep(0.1)
        except Exception as e:
            print(f"截图错误: {e}")
            break 
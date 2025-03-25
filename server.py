"""
远程桌面控制系统 - 服务端（被控制端）
负责捕获屏幕并发送给客户端，接收客户端发送的键盘和鼠标控制命令
"""
import time
import socket
import threading
import io
import base64
from PIL import ImageGrab # type: ignore
import keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import logging
from typing import Dict, Any
import imagehash

# 导入自定义工具模块
from utils import SecureSocket, get_local_ip, compress_image

# 服务端配置
DEFAULT_PORT = 5555
SCREEN_SIZE = ImageGrab.grab().size
SERVER_VERSION = "1.0.0"

# 控制器初始化
mouse = MouseController()
keyboard_controller = KeyboardController()

class RemoteDesktopServer:
    """远程桌面控制系统服务端类"""
    
    def __init__(self, host=None, port=DEFAULT_PORT):
        """初始化服务端"""
        self.host = host if host else get_local_ip()
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.clients = []
        self.screen_quality = 70  # 屏幕图像质量，可调整
        
    def start(self):
        """启动服务端"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"=== 远程桌面控制系统服务端 v{SERVER_VERSION} ===")
            print(f"服务器启动成功，监听地址: {self.host}:{self.port}")
            print("等待客户端连接...")
            
            # 启动客户端接收线程
            accept_thread = threading.Thread(target=self.accept_clients)
            accept_thread.daemon = True
            accept_thread.start()
            
            # 主线程等待用户输入命令
            while self.running:
                cmd = input("输入 'exit' 退出服务端: ")
                if cmd.lower() == 'exit':
                    self.stop()
                    break
                    
        except Exception as e:
            print(f"服务端启动失败: {e}")
            self.stop()
            
    def accept_clients(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"客户端 {client_address} 已连接")
                
                # 为每个客户端创建安全套接字
                secure_client = SecureSocket(client_socket)
                self.clients.append(secure_client)
                
                # 启动客户端处理线程
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(secure_client, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"接受客户端连接出错: {e}")
                    
    def handle_client(self, client, address):
        """处理客户端连接"""
        try:
            # 发送服务器信息
            client.send_data({
                "type": "server_info",
                "version": SERVER_VERSION,
                "screen_size": {"width": SCREEN_SIZE[0], "height": SCREEN_SIZE[1]}
            })
            
            # 启动屏幕发送线程
            screen_thread = threading.Thread(
                target=self.send_screen, 
                args=(client,)
            )
            screen_thread.daemon = True
            screen_thread.start()
            
            # 处理客户端命令
            while self.running:
                data = client.receive_data()
                if not data:
                    break
                    
                self.process_command(data)
                
        except Exception as e:
            print(f"处理客户端 {address} 出错: {e}")
        finally:
            if client in self.clients:
                self.clients.remove(client)
            client.close()
            print(f"客户端 {address} 已断开连接")
            
    def send_screen(self, client):
        """简化屏幕捕获"""
        screenshot = ImageGrab.grab()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='JPEG', quality=85)
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode()
        client.send_data({"type": "screen", "image": img_base64})
        
    def process_command(self, command):
        """处理客户端发送的控制命令"""
        try:
            cmd_type = command.get("type", "")
            
            if cmd_type == "mouse_move":
                # 处理鼠标移动
                x = command.get("x", 0)
                y = command.get("y", 0)
                mouse.position = (x, y)
                
            elif cmd_type == "mouse_click":
                # 处理鼠标点击
                button = command.get("button", "left")
                clicks = command.get("clicks", 1)
                
                if button == "left":
                    btn = Button.left
                elif button == "right":
                    btn = Button.right
                elif button == "middle":
                    btn = Button.middle
                else:
                    btn = Button.left
                    
                mouse.click(btn, clicks)
                
            elif cmd_type == "mouse_scroll":
                # 处理鼠标滚轮
                dx = command.get("dx", 0)
                dy = command.get("dy", 0)
                mouse.scroll(dx, dy)
                
            elif cmd_type == "keyboard_press":
                # 处理键盘按键
                key = command.get("key", "")
                if key:
                    if hasattr(Key, key):
                        # 特殊键
                        keyboard_controller.press(getattr(Key, key))
                    else:
                        # 普通键
                        keyboard_controller.press(key)
                        
            elif cmd_type == "keyboard_release":
                # 处理键盘释放
                key = command.get("key", "")
                if key:
                    if hasattr(Key, key):
                        # 特殊键
                        keyboard_controller.release(getattr(Key, key))
                    else:
                        # 普通键
                        keyboard_controller.release(key)
                        
            elif cmd_type == "keyboard_type":
                # 处理键盘输入文本
                text = command.get("text", "")
                if text:
                    keyboard_controller.type(text)
                    
            elif cmd_type == "set_quality":
                # 设置屏幕质量
                quality = command.get("quality", 70)
                self.screen_quality = max(10, min(95, quality))
                
        except Exception as e:
            print(f"处理命令出错: {e}")
            
    def stop(self):
        """停止服务端"""
        self.running = False
        print("正在关闭服务端...")
        
        # 关闭所有客户端连接
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        
        self.clients.clear()
        
        # 关闭服务器套接字
        try:
            self.server_socket.close()
        except:
            pass
            
        print("服务端已关闭")

if __name__ == "__main__":
    # 解析命令行参数
    host = None
    port = DEFAULT_PORT
    
    if len(sys.argv) > 1:
        if sys.argv[1] != "auto":
            host = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except:
            pass
    
    # 创建并启动服务端
    server = RemoteDesktopServer(host, port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        print(f"服务端运行出错: {e}")
        server.stop() 
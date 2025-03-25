"""
远程桌面控制系统 - 客户端（控制端）
负责显示服务端的屏幕，发送键盘和鼠标控制命令给服务端
"""
import logging
import time
import threading
import socket
import base64
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import io

# 导入自定义工具模块
from utils import SecureSocket

# 客户端配置
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5555
CLIENT_VERSION = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class RemoteDesktopClient:
    """远程桌面控制系统客户端类"""
    
    def __init__(self, master=None):
        """初始化客户端"""
        self.master = master
        self.master.title(f"远程桌面控制系统客户端 v{CLIENT_VERSION}")
        self.master.geometry("1024x768")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.connected = False
        self.client_socket = None
        self.server_info = None
        self.current_image = None
        self.screen_scale = 1.0  # 屏幕缩放比例
        
        # 创建UI
        self.create_widgets()
        
        # 连接状态
        self.connection_thread = None
        self.screen_update_thread = None
        
    def create_widgets(self):
        """创建GUI组件"""
        # 顶部控制面板
        self.control_frame = ttk.Frame(self.master)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # 连接控制
        ttk.Label(self.control_frame, text="服务器地址:").pack(side=tk.LEFT, padx=5)
        self.host_entry = ttk.Entry(self.control_frame, width=15)
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.control_frame, text="端口:").pack(side=tk.LEFT, padx=5)
        self.port_entry = ttk.Entry(self.control_frame, width=5)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.connect_button = ttk.Button(
            self.control_frame, 
            text="连接", 
            command=self.toggle_connection
        )
        self.connect_button.pack(side=tk.LEFT, padx=10)
        
        # 画质控制
        ttk.Label(self.control_frame, text="画质:").pack(side=tk.LEFT, padx=10)
        self.quality_var = tk.IntVar(value=70)
        self.quality_scale = ttk.Scale(
            self.control_frame,
            from_=10,
            to=95,
            variable=self.quality_var,
            orient=tk.HORIZONTAL,
            length=100,
            command=self.set_quality
        )
        self.quality_scale.pack(side=tk.LEFT)
        
        # 状态显示
        self.status_label = ttk.Label(self.control_frame, text="未连接")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # 创建画布用于显示远程屏幕
        self.canvas_frame = ttk.Frame(self.master)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(
            self.canvas_frame, 
            bg="black",
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标和键盘事件
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", lambda e: self.on_mouse_click(e, "left", 1))
        self.canvas.bind("<Button-2>", lambda e: self.on_mouse_click(e, "middle", 1))
        self.canvas.bind("<Button-3>", lambda e: self.on_mouse_click(e, "right", 1))
        self.canvas.bind("<Double-Button-1>", lambda e: self.on_mouse_click(e, "left", 2))
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
        # 键盘事件（按下和释放）
        self.master.bind("<KeyPress>", self.on_key_press)
        self.master.bind("<KeyRelease>", self.on_key_release)
        
        # 底部状态栏
        self.statusbar = ttk.Label(
            self.master, 
            text="就绪", 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def toggle_connection(self):
        """切换连接状态"""
        if not self.connected:
            self.connect_to_server()
        else:
            self.disconnect_from_server()
            
    def connect_to_server(self):
        """连接到远程服务器"""
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return
            
        self.status_label.config(text="正在连接...")
        self.statusbar.config(text=f"正在连接到 {host}:{port}")
        
        # 创建连接线程
        self.connection_thread = threading.Thread(
            target=self.connect_thread,
            args=(host, port)
        )
        self.connection_thread.daemon = True
        self.connection_thread.start()
        
    def connect_thread(self, host, port):
        """连接线程处理函数"""
        try:
            # 创建套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            
            # 创建安全套接字
            self.client_socket = SecureSocket(sock)
            
            # 更新UI状态
            self.master.after(0, self.on_connect_success)
            
            # 启动屏幕更新线程
            self.screen_update_thread = threading.Thread(
                target=self.update_screen
            )
            self.screen_update_thread.daemon = True
            self.screen_update_thread.start()
            
        except Exception as e:
            self.master.after(0, lambda: self.on_connect_error(str(e)))
            
    def on_connect_success(self):
        """连接成功处理"""
        self.connected = True
        self.connect_button.config(text="断开连接")
        self.status_label.config(text="已连接")
        self.statusbar.config(text="已连接到服务器")
        
    def on_connect_error(self, error_msg):
        """连接错误处理"""
        self.disconnect_from_server()
        messagebox.showerror("连接失败", f"无法连接到服务器:\n{error_msg}")
        self.statusbar.config(text=f"连接失败: {error_msg}")
        
    def disconnect_from_server(self):
        """断开与服务器的连接"""
        self.connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
        self.connect_button.config(text="连接")
        self.status_label.config(text="未连接")
        self.statusbar.config(text="已断开连接")
        
        # 清除画布
        self.canvas.delete("all")
        self.current_image = None
        
    def update_screen(self):
        """更新屏幕显示线程"""
        try:
            while self.connected and self.client_socket:
                try:
                    data = self.client_socket.receive_data(timeout=1.0)
                except socket.timeout:
                    continue
                    
                if not data:
                    self.master.after(0, self.handle_disconnect)
                    break
                    
                # 根据数据类型处理
                data_type = data.get("type", "")
                
                if data_type == "server_info":
                    self.server_info = data  # 使用属性类型提示
                    self.master.after(0, lambda: self.statusbar.config(
                        text=f"服务器版本: {data.get('version', '未知')}"
                    ))
                    
                elif data_type == "screen":
                    self.process_screen_data(data.get("image", ""))
                    
        except Exception as e:
            if self.connected:
                self.master.after(0, lambda: self.handle_error(str(e)))
                
    def process_screen_data(self, image_data):
        """处理屏幕图像数据"""
        if not image_data:
            return
            
        try:
            img_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(img_bytes))
            self.master.after(0, lambda img=image: self.display_image(img))
        except Exception as e:
            logging.error("图像处理失败: %s", e)
        
    def display_image(self, image):
        """简化图像显示"""
        self.current_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.current_image, anchor=tk.NW)
        
    def set_quality(self, event=None):
        """设置图像质量"""
        if self.connected and self.client_socket:
            quality = self.quality_var.get()
            try:
                self.client_socket.send_data({
                    "type": "set_quality",
                    "quality": quality
                })
            except:
                pass
                
    def on_mouse_move(self, event):
        """处理鼠标移动事件"""
        if not self.connected or not self.client_socket or not self.server_info:
            return
            
        try:
            # 计算在远程屏幕上的坐标
            screen_size = self.server_info.get("screen_size", {})
            screen_width = screen_size.get("width", 1920)
            screen_height = screen_size.get("height", 1080)
            
            # 使用缩放比例转换坐标
            if self.screen_scale > 0:
                x = int(event.x / self.screen_scale)
                y = int(event.y / self.screen_scale)
                
                # 发送鼠标移动命令
                self.client_socket.send_data({
                    "type": "mouse_move",
                    "x": x,
                    "y": y
                })
        except:
            pass
            
    def on_mouse_click(self, event, button, clicks):
        """处理鼠标点击事件"""
        if not self.connected or not self.client_socket:
            return
            
        try:
            # 发送鼠标点击命令
            self.client_socket.send_data({
                "type": "mouse_click",
                "button": button,
                "clicks": clicks
            })
        except:
            pass
            
    def on_mouse_wheel(self, event):
        """处理鼠标滚轮事件"""
        if not self.connected or not self.client_socket:
            return
            
        try:
            # 在Windows上，event.delta表示滚动量
            dx = 0
            dy = event.delta // 120  # 将滚动量转换为合理的滚动单位
            
            # 发送鼠标滚轮命令
            self.client_socket.send_data({
                "type": "mouse_scroll",
                "dx": dx,
                "dy": dy
            })
        except:
            pass
            
    def on_key_press(self, event):
        """处理键盘按下事件"""
        if not self.connected or not self.client_socket:
            return
            
        try:
            # 获取键值
            key = self.translate_key(event)
            if key:
                # 发送键盘按下命令
                self.client_socket.send_data({
                    "type": "keyboard_press",
                    "key": key
                })
        except:
            pass
            
    def on_key_release(self, event):
        """处理键盘释放事件"""
        if not self.connected or not self.client_socket:
            return
            
        try:
            # 获取键值
            key = self.translate_key(event)
            if key:
                # 发送键盘释放命令
                self.client_socket.send_data({
                    "type": "keyboard_release",
                    "key": key
                })
        except:
            pass
            
    def translate_key(self, event):
        """翻译按键名称为pynput可用的格式"""
        KEY_MAP = {  # 使用常量优化
            'Shift_L': 'shift',
            'Shift_R': 'shift',
            'Control_L': 'ctrl',
            'Control_R': 'ctrl',
            'Alt_L': 'alt',
            'Alt_R': 'alt',
            'Return': 'enter',
            'Escape': 'esc',
            'BackSpace': 'backspace',
            'Tab': 'tab',
            'space': 'space',
            'Delete': 'delete',
            'Insert': 'insert',
            'Home': 'home',
            'End': 'end',
            'Page_Up': 'page_up',
            'Page_Down': 'page_down',
            'Up': 'up',
            'Down': 'down',
            'Left': 'left',
            'Right': 'right'
        }
        
        key_name = event.keysym
        
        if key_name in KEY_MAP:
            return KEY_MAP[key_name]
        elif len(key_name) == 1:
            # 普通字符键
            return key_name
        elif key_name.startswith('F') and key_name[1:].isdigit():
            # 功能键 F1-F12
            return key_name.lower()
            
        return None
        
    def handle_disconnect(self):
        """处理服务器断开连接"""
        if self.connected:
            self.disconnect_from_server()
            messagebox.showinfo("断开连接", "服务器已断开连接")
            
    def handle_error(self, error_msg):
        """处理错误"""
        self.statusbar.config(text=f"错误: {error_msg}")
        if self.connected:
            self.disconnect_from_server()
            messagebox.showerror("连接错误", f"与服务器通信时出错:\n{error_msg}")
            
    def on_close(self):
        """关闭窗口处理"""
        if self.connected:
            self.disconnect_from_server()
        self.master.destroy()

def main():
    """主函数"""
    root = tk.Tk()
    app = RemoteDesktopClient(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
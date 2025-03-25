"""
远程桌面控制系统 - 启动器
提供图形界面选择启动服务端或客户端
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, font

# 获取脚本路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class RemoteDesktopLauncher:
    """远程桌面控制系统启动器"""
    
    def __init__(self, master=None):
        """初始化启动器窗口"""
        self.master = master
        self.master.title("远程桌面控制系统启动器")
        self.master.geometry("500x320")
        self.master.resizable(False, False)
        
        # 设置窗口图标（如果有）
        try:
            if os.name == 'nt':  # Windows
                self.master.iconbitmap(os.path.join(SCRIPT_DIR, "icon.ico"))
            else:  # Linux/Mac
                icon = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "icon.png"))
                self.master.iconphoto(True, icon)
        except:
            pass
        
        self.create_widgets()
        
    def create_widgets(self):
        """创建GUI组件"""
        # 标题
        title_font = font.Font(family="Arial", size=18, weight="bold")
        title = ttk.Label(
            self.master, 
            text="远程桌面控制系统", 
            font=title_font
        )
        title.pack(pady=20)
        
        # 描述
        desc_font = font.Font(family="Arial", size=10)
        desc = ttk.Label(
            self.master,
            text="选择要启动的模式",
            font=desc_font
        )
        desc.pack(pady=5)
        
        # 按钮容器
        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=20)
        
        # 按钮样式
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 12))
        
        # 客户端按钮（控制端）
        client_btn = ttk.Button(
            button_frame, 
            text="启动客户端\n(控制端)", 
            width=20,
            command=self.start_client
        )
        client_btn.pack(side=tk.LEFT, padx=20, pady=10, ipady=20)
        
        # 服务端按钮（被控制端）
        server_btn = ttk.Button(
            button_frame, 
            text="启动服务端\n(被控制端)", 
            width=20,
            command=self.start_server
        )
        server_btn.pack(side=tk.LEFT, padx=20, pady=10, ipady=20)
        
        # 底部版权信息
        copyright_label = ttk.Label(
            self.master,
            text="© 2023 远程桌面控制系统",
            font=('Arial', 8)
        )
        copyright_label.pack(side=tk.BOTTOM, pady=10)
        
    def start_client(self):
        """启动客户端"""
        try:
            client_path = os.path.join(SCRIPT_DIR, "client.py")
            
            # 在新进程中启动客户端
            if os.name == 'nt':  # Windows
                subprocess.Popen(["pythonw", client_path])
            else:  # Linux/Mac
                subprocess.Popen(["python3", client_path])
                
            self.master.destroy()  # 关闭启动器
            
        except Exception as e:
            messagebox.showerror("启动错误", f"启动客户端时出错:\n{e}")
            
    def start_server(self):
        """启动服务端"""
        try:
            server_path = os.path.join(SCRIPT_DIR, "server.py")
            
            # 在新进程中启动服务端
            if os.name == 'nt':  # Windows
                subprocess.Popen(["python", server_path])
            else:  # Linux/Mac
                subprocess.Popen(["python3", server_path])
                
            self.master.destroy()  # 关闭启动器
            
        except Exception as e:
            messagebox.showerror("启动错误", f"启动服务端时出错:\n{e}")

def main():
    """主函数"""
    root = tk.Tk()
    app = RemoteDesktopLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
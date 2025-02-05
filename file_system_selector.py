import tkinter as tk
from tkinter import ttk, messagebox
import os

class FileSystemSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("文件系统选择器")
        self.root.geometry("600x400")

        # 初始化选择的路径
        self.selected_path = None

        # 创建目录树
        self.tree = ttk.Treeview(self.root)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 添加根节点（从盘符开始）
        self._load_drives()

        # 绑定双击事件
        self.tree.bind("<Double-1>", self._on_double_click)
        # 绑定展开事件
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)

        # 添加确定按钮
        confirm_button = ttk.Button(self.root, text="确定", command=self._on_confirm)
        confirm_button.pack(pady=10)

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _load_drives(self):
        """加载所有盘符到树形结构中"""
        self.tree.delete(*self.tree.get_children())  # 清空树
        drives = self._get_drives()
        for drive in drives:
            node = self.tree.insert("", tk.END, text=drive, values=[drive], open=False)
            self._add_placeholder(node)  # 添加占位符以便展开

    def _get_drives(self):
        """获取所有盘符"""
        if os.name == "nt":  # Windows 系统
            import string
            from ctypes import windll
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            return drives
        else:  # Linux/Mac 系统
            return ["/"]

    def _add_placeholder(self, node):
        """为目录节点添加占位符"""
        self.tree.insert(node, tk.END, text="加载中...")

    def _load_children(self, item):
        """加载指定节点的子目录和文件并排序"""
        item_path = self.tree.item(item, "values")[0]
        if os.path.isdir(item_path):
            self.tree.delete(*self.tree.get_children(item))  # 清空占位符
            try:
                # 分离目录和文件并分别排序
                dirs, files = [], []
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isdir(sub_item_path):
                        dirs.append((sub_item, sub_item_path))
                    else:
                        files.append((sub_item, sub_item_path))

                # 对目录和文件按名称排序
                dirs.sort(key=lambda x: x[0].lower())
                files.sort(key=lambda x: x[0].lower())

                # 插入排序后的目录和文件
                for name, path in dirs:
                    sub_node = self.tree.insert(item, tk.END, text=name, values=[path], open=False)
                    self._add_placeholder(sub_node)  # 添加占位符以便展开
                for name, path in files:
                    self.tree.insert(item, tk.END, text=name, values=[path])
            except PermissionError:
                print(f"无权限访问: {item_path}")

    def _on_double_click(self, event):
        """双击节点时加载子目录"""
        item = self.tree.selection()[0]
        self._load_children(item)

    def _on_expand(self, event):
        """点击加号展开节点时加载子目录"""
        item = self.tree.selection()[0]
        self._load_children(item)

    def _on_confirm(self):
        """点击确定按钮时获取选择的路径"""
        selected_items = self.tree.selection()
        if selected_items:
            self.selected_path = self.tree.item(selected_items[0], "values")[0]
            self.root.destroy()  # 关闭窗口
        else:
            messagebox.showwarning("警告", "请先选择一个文件或目录")

    def _on_window_close(self):
        """处理窗口关闭事件"""
        if not self.selected_path:
            response = messagebox.askyesno("确认退出", "你还没有选择任何文件或目录，确定要退出吗?")
            if response:
                self.root.destroy()
        else:
            self.root.destroy()

    def get_selected_path(self):
        """获取用户选择的路径"""
        return self.selected_path

def select_file_or_directory():
    """
    弹出文件系统选择器，用户可以选择文件或目录
    :return: 返回选择的路径
    """
    root = tk.Tk()
    selector = FileSystemSelector(root)
    root.mainloop()
    return selector.get_selected_path()

# 示例用法
if __name__ == "__main__":
    selected_path = select_file_or_directory()
    if selected_path:
        print(f"你选择的路径是: {selected_path}")
    else:
        print("你没有选择任何文件或目录。")
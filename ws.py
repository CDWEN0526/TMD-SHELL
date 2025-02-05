import threading
import paramiko
import asyncio
import websockets
import json
import io
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

async def ssh_handler(websocket):
    ssh_host = None
    ssh_username = None
    ssh_password = None

    # 接收SSH连接参数
    async for message in websocket:
        try:
            params = json.loads(message)
            ssh_host = params.get('ssh_host')
            ssh_port = params.get('ssh_port', 22)
            ssh_username = params.get('ssh_username')
            ssh_password = params.get('ssh_password')
            ssh_key_content = params.get('ssh_key_content')
            ssh_key_password = params.get('ssh_key_password')
            width = params.get('width', 200)
            height = params.get('height', 45)
            break  # 接收到参数后退出循环
        except json.JSONDecodeError:
            await websocket.send("Invalid connection parameter!!!")
            return

    # SSH连接设置
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if ssh_key_content:
            logger.info("使用秘钥连接服务器...")
            key = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key_content), password=ssh_key_password)
            ssh.connect(ssh_host,port=ssh_port, username=ssh_username, pkey=key, timeout=600)
        else:
            logger.info("使用密码连接服务器...")
            ssh.connect(ssh_host,port=ssh_port, username=ssh_username, password=ssh_password,timeout=600)
    except Exception as e:
        logger.error(f"服务器连接失败: {str(e)}")
        await websocket.send(f"SSH connection failed: {str(e)}")
        return
    # 执行命令
    command ="""
    if [ ! -d "~/.tmd-ssh" ]; then mkdir -p ~/.tmd-ssh; fi;
    if ! grep -q "TMD_SHELL_CURRENT_DIR" ~/.bashrc; then function cd() { builtin cd "$@" && export TMD_SHELL_CURRENT_DIR=$(pwd); }; cd ~; echo 'function cd() { builtin cd "$@" && export TMD_SHELL_CURRENT_DIR=$(pwd) && echo  $(pwd) > ~/.tmd-ssh/current_dir.txt; };' >> ~/.bashrc; fi;
    """
    ssh.exec_command(command)
    transport = ssh.get_transport()
    transport.set_keepalive(60)

    chan = ssh.invoke_shell()
    chan.resize_pty(width=width, height=height)

    def write_all(sock):
        while True:
            data = sock.recv(1024)
            if not data:
                break
            asyncio.run(websocket.send(data.decode('utf-8', errors='ignore')))

    writer = threading.Thread(target=write_all, args=(chan,))
    writer.start()

    try:
        async for message in websocket:
            try:
                # 尝试解析为 JSON
                params = json.loads(message)
                if isinstance(params, dict) and 'width' in params:  # 确保 params 是字典
                    logger.info("尺寸调整: " + str(params))
                    width = params.get('width', width)
                    height = params.get('height', height)
                    chan.resize_pty(width=width, height=height)
                else:
                    # 如果不是字典，直接发送到 SSH 通道
                    chan.send(message.encode('utf-8'))
            except json.JSONDecodeError:
                # 如果不是 JSON，直接发送到 SSH 通道
                try:
                    chan.send(message.encode('utf-8'))  # 发送原始消息到 SSH 通道
                except OSError:
                    logger.error("Error: SSH connection closed")
            except Exception as e:
                logger.error(f"Error: {str(e)}")
    finally:
        chan.close()
        ssh.close()

# 启动WebSocket服务器
async def start_ws_server():
    async with websockets.serve(ssh_handler, "localhost", 6789):
        await asyncio.Future()  # 运行直到取消

if __name__ == '__main__':
    print("\n\tWebSocket server started on localhost:6789\n")
    asyncio.run(start_ws_server())
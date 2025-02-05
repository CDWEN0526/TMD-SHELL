import time

def convert_speed(speed_bytes):
    """
    根据流量大小自动转换单位
    :param speed_bytes: 流量大小（字节）
    :return: 转换后的字符串（如 1.23kb/s, 45.67mb/s）
    """
    if speed_bytes < 1024:  # 小于 1KB
        return f"{speed_bytes:.2f}B/S"
    elif speed_bytes < 1024 * 1024:  # 小于 1MB
        return f"{speed_bytes / 1024:.2f}KB/S"
    elif speed_bytes < 1024 * 1024 * 1024:  # 小于 1GB
        return f"{speed_bytes / (1024 * 1024):.2f}MB/S"
    else:  # 大于等于 1GB
        return f"{speed_bytes / (1024 * 1024 * 1024):.2f}GB/S"

def get_network_speed(ssh):
    """
    获取网卡的每秒速率
    :param ssh: SSH 连接对象
    :return: 网卡的每秒速率（上行和下行）
    """
    # 第一次获取网卡流量
    stdin, stdout, stderr = ssh.exec_command("cat /proc/net/dev")
    net_info_1 = stdout.read().decode().strip().split('\n')[2:]  # 跳过前两行
    time.sleep(1)  # 等待 1 秒
    # 第二次获取网卡流量
    stdin, stdout, stderr = ssh.exec_command("cat /proc/net/dev")
    net_info_2 = stdout.read().decode().strip().split('\n')[2:]  # 跳过前两行

    net_card = []
    for line1, line2 in zip(net_info_1, net_info_2):
        # 解析第一次数据
        parts1 = line1.split()
        card1 = parts1[0].strip(':')
        rx_bytes1 = int(parts1[1])
        tx_bytes1 = int(parts1[9])
        # 解析第二次数据
        parts2 = line2.split()
        card2 = parts2[0].strip(':')
        rx_bytes2 = int(parts2[1])
        tx_bytes2 = int(parts2[9])
        # 计算每秒速率
        rx_speed = (rx_bytes2 - rx_bytes1)  # 下行速率（字节/秒）
        tx_speed = (tx_bytes2 - tx_bytes1)  # 上行速率（字节/秒）
        # 转换单位
        rx_speed_converted = convert_speed(rx_speed)
        tx_speed_converted = convert_speed(tx_speed)
        # 添加到结果
        net_card.append({
            'net_card': card1,
            'up': tx_speed_converted,  # 上行速率
            'down': rx_speed_converted  # 下行速率
        })
    return net_card

def get_memory_usage(ssh):
    """
    获取更精确的内存使用率
    :param ssh: SSH 连接对象
    :return: 内存使用率（百分比）
    """
    # 执行 free 命令获取内存信息
    stdin, stdout, stderr = ssh.exec_command("free -b | grep Mem")
    mem_info = stdout.read().decode().strip().split()
    
    # 解析内存信息
    total_mem = int(mem_info[1])  # 总内存
    available_mem = int(mem_info[6])  # 可用内存

    # 计算内存使用率
    memory_usage = ((total_mem - available_mem) / total_mem) * 100
    return round(memory_usage)

def get_remote_server_info(ssh): 
        # 获取CPU占用率
        stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'")
        cpu_usage = round(float(stdout.read().decode().strip()))
        
        # 获取更精确的内存使用率
        memory_usage = get_memory_usage(ssh)
        
        # 获取网卡的每秒速率
        net_card = get_network_speed(ssh)
        
        # 获取硬盘的总大小和已使用大小
        stdin, stdout, stderr = ssh.exec_command("df -h | awk 'NR>1{print $1,$2,$3,$5}'")
        disk_info = stdout.read().decode().strip().split('\n')
        dev = []
        for line in disk_info:
            dev_name, total, used, use_percent = line.split()
            dev.append({
                'dev': dev_name,
                'num': f"{total}/{used}",
                'use': use_percent
            })
        
        # 返回结果
        return ({
            'cpu': f"{cpu_usage}%",
            'memory': f"{memory_usage}%",
            'net_card': net_card,
            'dev': dev
        })
    

# 示例使用
# if __name__ == '__main__':
#     hostname = 'xxx'
#     username = 'xxx'
#     password = 'xxx'

#     # 创建SSH客户端
#     ssh = paramiko.SSHClient()
#     ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     ssh.connect(hostname, username=username, password=password)
#     while True:
#         print(get_remote_server_info(ssh))

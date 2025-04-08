import zlib


def calculate_crc32(file_path):
    crc_value = 0
    with open(file_path, "rb") as file:
        while True:
            # 读取文件的一部分数据
            data = file.read(65536)  # 每次读取 64KB
            if not data:
                break
            # 计算 CRC32 校验值
            crc_value = zlib.crc32(data, crc_value)
    # 返回 CRC32 校验值
    file.close()
    return crc_value & 0xFFFFFFFF


def calculate_crc16(data: list):
    """
    计算 Modbus CRC16 校验值
    :param data: 输入的字节数据
    :return: 计算得到的 CRC16 校验值（整数形式）
    """
    crc = 0xFFFF  # 初始值
    polynomial = 0xA001  # Modbus 使用的多项式

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= polynomial
            else:
                crc >>= 1

    return crc


def list_to_crc16(byte_list: list, length:int = 0):
    if length == 0:
       length = len(byte_list) 
    if length > len(byte_list):
        raise ValueError("校验长度不能大于数据长度")
    # 计算 CRC16 校验值
    crc_value = calculate_crc16(byte_list[:length])
    # 返回大端格式的高字节和低字节
    crc_high = (crc_value >> 8) & 0xFF
    crc_low = crc_value & 0xFF
    return crc_low, crc_high


def add_crc16_to_list(byte_list: list) -> list:
    # 计算 CRC16 校验值的高字节和低字节
    crc_low, crc_high = list_to_crc16(byte_list)
    # 将 CRC16 校验值添加到列表末尾
    byte_list.extend([crc_low, crc_high])
    return byte_list

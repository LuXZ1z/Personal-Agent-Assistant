"""
微信消息加解密模块
参考示例代码，完全重新实现，确保代码清晰可维护
"""
import base64
import hashlib
import json
import random
import socket
import struct
import time
from typing import Tuple, Optional
from Crypto.Cipher import AES

from shared.utils import setup_logger

logger = setup_logger(__name__)


class WeChatCryptError(Exception):
    """微信加解密异常"""
    pass


class SHA1Signer:
    """SHA1签名计算器"""
    
    @staticmethod
    def compute_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
        """
        计算SHA1签名
        
        Args:
            token: 微信Token
            timestamp: 时间戳
            nonce: 随机字符串
            encrypt: 加密后的消息（字符串或bytes）
            
        Returns:
            SHA1签名的十六进制字符串
        """
        try:
            # 确保encrypt是字符串
            if isinstance(encrypt, bytes):
                encrypt = encrypt.decode('utf-8')
            
            # 排序并拼接
            sort_list = [str(token), str(timestamp), str(nonce), str(encrypt)]
            sort_list.sort()
            sha1_str = "".join(sort_list)
            
            # 计算SHA1
            sha1 = hashlib.sha1()
            sha1.update(sha1_str.encode('utf-8'))
            return sha1.hexdigest()
        except Exception as e:
            logger.error(f"计算SHA1签名失败: {e}")
            raise WeChatCryptError(f"计算签名失败: {e}")


class PKCS7Encoder:
    """PKCS7填充编码器"""
    
    BLOCK_SIZE = 32  # AES-256块大小
    
    @staticmethod
    def encode(text: bytes) -> bytes:
        """
        对明文进行PKCS7填充
        
        Args:
            text: 需要填充的明文（bytes）
            
        Returns:
            填充后的明文（bytes）
        """
        if isinstance(text, str):
            text = text.encode('utf-8')
        
        text_length = len(text)
        # 计算需要填充的字节数
        amount_to_pad = PKCS7Encoder.BLOCK_SIZE - (text_length % PKCS7Encoder.BLOCK_SIZE)
        if amount_to_pad == 0:
            amount_to_pad = PKCS7Encoder.BLOCK_SIZE
        
        # 填充字节
        pad = bytes([amount_to_pad])
        return text + pad * amount_to_pad
    
    @staticmethod
    def decode(decrypted: bytes) -> bytes:
        """
        删除PKCS7填充
        
        Args:
            decrypted: 解密后的明文（bytes）
            
        Returns:
            去除填充后的明文（bytes）
        """
        if len(decrypted) == 0:
            raise WeChatCryptError("解密数据为空")
        
        pad_len = decrypted[-1]
        if pad_len < 1 or pad_len > PKCS7Encoder.BLOCK_SIZE:
            raise WeChatCryptError(f"无效的填充长度: {pad_len}")
        
        return decrypted[:-pad_len]


class AESCryptor:
    """AES加解密器"""
    
    def __init__(self, key: bytes):
        """
        初始化AES加解密器
        
        Args:
            key: AES密钥（32字节）
        """
        if len(key) != 32:
            raise WeChatCryptError(f"密钥长度错误: 需要32字节，实际{len(key)}字节")
        self.key = key
        self.iv = key[:16]  # 初始向量为密钥前16字节
        self.mode = AES.MODE_CBC
    
    def encrypt(self, text: str, receive_id: str = "") -> bytes:
        """
        加密明文
        
        Args:
            text: 需要加密的明文
            receive_id: 接收者ID（智能机器人为空字符串）
            
        Returns:
            加密后的密文（bytes）
        """
        try:
            # 生成16位随机字符串
            random_str = self._generate_random_string(16)
            
            # 构建消息体：随机字符串(16字节) + 消息长度(4字节) + 消息内容 + receive_id
            text_bytes = text.encode('utf-8')
            text_len = len(text_bytes)
            
            # 使用网络字节序打包长度
            len_bytes = struct.pack("I", socket.htonl(text_len))
            
            # 拼接消息
            message = random_str.encode('utf-8') + len_bytes + text_bytes + receive_id.encode('utf-8')
            
            # PKCS7填充
            padded_message = PKCS7Encoder.encode(message)
            
            # AES-CBC加密
            cipher = AES.new(self.key, self.mode, self.iv)
            ciphertext = cipher.encrypt(padded_message)
            
            # Base64编码
            return base64.b64encode(ciphertext)
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise WeChatCryptError(f"加密失败: {e}")
    
    def decrypt(self, ciphertext: str, receive_id: str = "") -> str:
        """
        解密密文
        
        Args:
            ciphertext: 加密后的密文（Base64字符串）
            receive_id: 接收者ID（智能机器人为空字符串）
            
        Returns:
            解密后的明文
        """
        try:
            # Base64解码
            encrypted_data = base64.b64decode(ciphertext)
            
            # AES-CBC解密
            cipher = AES.new(self.key, self.mode, self.iv)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # 去除PKCS7填充
            unpadded_data = PKCS7Encoder.decode(decrypted_data)
            
            # 提取消息内容
            # 跳过16字节随机字符串和4字节长度
            if len(unpadded_data) < 20:
                raise WeChatCryptError("解密数据长度不足")
            
            # 提取长度
            len_bytes = unpadded_data[16:20]
            text_len = socket.ntohl(struct.unpack("I", len_bytes)[0])
            
            # 提取消息内容
            if len(unpadded_data) < 20 + text_len:
                raise WeChatCryptError("解密数据长度错误")
            
            text_content = unpadded_data[20:20 + text_len].decode('utf-8')
            received_receive_id = unpadded_data[20 + text_len:].decode('utf-8')
            
            # 验证receive_id
            if received_receive_id != receive_id:
                raise WeChatCryptError(f"receive_id不匹配: 期望'{receive_id}', 实际'{received_receive_id}'")
            
            return text_content
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise WeChatCryptError(f"解密失败: {e}")
    
    @staticmethod
    def _generate_random_string(length: int) -> str:
        """
        生成随机字符串
        
        Args:
            length: 字符串长度
            
        Returns:
            随机字符串
        """
        chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return ''.join(random.choice(chars) for _ in range(length))


class WeChatMessageCrypt:
    """微信消息加解密主类"""
    
    def __init__(self, token: str, encoding_aes_key: str, receive_id: str = ""):
        """
        初始化微信消息加解密器
        
        Args:
            token: 微信Token
            encoding_aes_key: Base64编码的AES密钥
            receive_id: 接收者ID（智能机器人为空字符串）
        """
        self.token = token
        self.receive_id = receive_id
        
        try:
            # 解码AES密钥
            # 处理Base64填充
            key_str = encoding_aes_key
            if len(key_str) % 4 != 0:
                key_str += "=" * (4 - len(key_str) % 4)
            
            key_bytes = base64.b64decode(key_str)
            if len(key_bytes) != 32:
                raise WeChatCryptError(f"AES密钥长度错误: 需要32字节，实际{len(key_bytes)}字节")
            
            self.aes_cryptor = AESCryptor(key_bytes)
        except Exception as e:
            logger.error(f"初始化AES加解密器失败: {e}")
            raise WeChatCryptError(f"初始化失败: {e}")
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """
        验证URL（用于微信服务器验证）
        
        Args:
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机字符串
            echostr: 加密的随机字符串
            
        Returns:
            解密后的随机字符串
        """
        try:
            # 计算签名
            computed_signature = SHA1Signer.compute_signature(
                self.token, timestamp, nonce, echostr
            )
            
            # 验证签名
            if computed_signature != msg_signature:
                logger.error(f"签名验证失败: 期望{msg_signature}, 实际{computed_signature}")
                raise WeChatCryptError("签名验证失败")
            
            # 解密echostr
            decrypted_echostr = self.aes_cryptor.decrypt(echostr, self.receive_id)
            return decrypted_echostr
        except Exception as e:
            logger.error(f"URL验证失败: {e}")
            raise WeChatCryptError(f"URL验证失败: {e}")
    
    def decrypt_msg(self, post_data: bytes, msg_signature: str, timestamp: str, nonce: str) -> str:
        """
        解密消息
        
        Args:
            post_data: POST请求数据（JSON格式）
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机字符串
            
        Returns:
            解密后的明文
        """
        try:
            # 解析JSON
            json_data = json.loads(post_data.decode('utf-8'))
            encrypt = json_data.get('encrypt')
            if not encrypt:
                raise WeChatCryptError("消息中缺少encrypt字段")
            
            # 验证签名
            computed_signature = SHA1Signer.compute_signature(
                self.token, timestamp, nonce, encrypt
            )
            if computed_signature != msg_signature:
                logger.error(f"签名验证失败: 期望{msg_signature}, 实际{computed_signature}")
                raise WeChatCryptError("签名验证失败")
            
            # 解密消息
            decrypted_msg = self.aes_cryptor.decrypt(encrypt, self.receive_id)
            return decrypted_msg
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise WeChatCryptError(f"JSON解析失败: {e}")
        except Exception as e:
            logger.error(f"解密消息失败: {e}")
            raise WeChatCryptError(f"解密消息失败: {e}")
    
    def encrypt_msg(self, reply_msg: str, nonce: Optional[str] = None, timestamp: Optional[str] = None) -> str:
        """
        加密回复消息
        
        Args:
            reply_msg: 需要加密的回复消息（JSON字符串）
            nonce: 随机字符串（如果为None则自动生成）
            timestamp: 时间戳（如果为None则使用当前时间）
            
        Returns:
            加密后的消息（JSON字符串）
        """
        try:
            # 生成nonce和timestamp
            if nonce is None:
                nonce = AESCryptor._generate_random_string(16)
            if timestamp is None:
                timestamp = str(int(time.time()))
            
            # 加密消息
            encrypted = self.aes_cryptor.encrypt(reply_msg, self.receive_id)
            encrypted_str = encrypted.decode('utf-8')
            
            # 计算签名
            signature = SHA1Signer.compute_signature(
                self.token, timestamp, nonce, encrypted_str
            )
            
            # 生成响应JSON
            response = {
                "encrypt": encrypted_str,
                "msgsignature": signature,
                "timestamp": timestamp,
                "nonce": nonce
            }
            
            return json.dumps(response, ensure_ascii=False)
        except Exception as e:
            logger.error(f"加密回复消息失败: {e}")
            raise WeChatCryptError(f"加密回复消息失败: {e}")


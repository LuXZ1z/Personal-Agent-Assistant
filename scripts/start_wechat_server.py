#!/usr/bin/env python3
"""
启动微信服务器脚本（Python版本）
自动清理占用端口的进程，然后启动服务器
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
os.chdir(PROJECT_ROOT)

# 添加项目根目录到路径
sys.path.insert(0, str(PROJECT_ROOT))

from shared.config import settings


def check_port(port: int) -> list:
    """
    检查端口是否被占用，返回占用该端口的进程ID列表
    
    Args:
        port: 端口号
        
    Returns:
        进程ID列表
    """
    pids = []
    
    # 尝试使用 lsof
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
            return pids
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    
    # 尝试使用 netstat
    try:
        result = subprocess.run(
            ['netstat', '-tlnp'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f':{port} ' in line:
                    parts = line.split()
                    if len(parts) >= 7:
                        pid_program = parts[6]
                        if '/' in pid_program:
                            pid = pid_program.split('/')[0]
                            try:
                                pids.append(int(pid))
                            except ValueError:
                                pass
            if pids:
                return list(set(pids))  # 去重
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # 尝试使用 ss
    try:
        result = subprocess.run(
            ['ss', '-tlnp'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f':{port} ' in line:
                    # ss 输出格式: LISTEN 0 128 *:80 *:* users:(("python",pid=1234,fd=3))
                    if 'pid=' in line:
                        import re
                        matches = re.findall(r'pid=(\d+)', line)
                        for match in matches:
                            try:
                                pids.append(int(match))
                            except ValueError:
                                pass
            if pids:
                return list(set(pids))  # 去重
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return []


def kill_process(pid: int, force: bool = False) -> bool:
    """
    终止进程
    
    Args:
        pid: 进程ID
        force: 是否强制终止
        
    Returns:
        是否成功
    """
    try:
        # 检查进程是否存在
        os.kill(pid, 0)
    except OSError:
        # 进程不存在
        return True
    
    try:
        if force:
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)
        return True
    except OSError as e:
        print(f"无法终止进程 {pid}: {e}")
        return False


def cleanup_port(port: int) -> bool:
    """
    清理占用端口的进程
    
    Args:
        port: 端口号
        
    Returns:
        是否成功清理
    """
    print(f"检查端口 {port} 是否被占用...")
    
    pids = check_port(port)
    
    if not pids:
        print(f"✓ 端口 {port} 未被占用")
        return True
    
    print(f"发现端口 {port} 被以下进程占用: {', '.join(map(str, pids))}")
    
    # 尝试优雅地终止进程
    for pid in pids:
        print(f"正在终止进程 {pid}...")
        if kill_process(pid, force=False):
            time.sleep(1)
            
            # 检查进程是否还在
            try:
                os.kill(pid, 0)
                # 进程还在，强制终止
                print(f"进程 {pid} 仍在运行，强制终止...")
                kill_process(pid, force=True)
                time.sleep(0.5)
            except OSError:
                # 进程已终止
                print(f"✓ 进程 {pid} 已终止")
    
    # 再次检查端口
    remaining_pids = check_port(port)
    if remaining_pids:
        print(f"✗ 警告: 端口 {port} 仍被以下进程占用: {', '.join(map(str, remaining_pids))}")
        return False
    else:
        print(f"✓ 端口 {port} 已释放")
        return True


def main():
    """主函数"""
    print("=" * 50)
    print("启动微信服务器")
    print("=" * 50)
    
    # 获取端口
    port = settings.server_port
    print(f"端口: {port}")
    print()
    
    # 清理端口
    cleanup_port(port)
    print()
    
    # 启动服务器
    print("启动服务器...")
    print("=" * 50)
    print()
    
    # 使用 subprocess 启动服务器，保持输出
    try:
        subprocess.run(
            [sys.executable, '-m', 'interfaces.wechat.server'],
            cwd=PROJECT_ROOT,
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n服务器启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()



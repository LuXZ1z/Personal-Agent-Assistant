#!/usr/bin/env python3
"""
启动微信服务器脚本（Python版本）
自动清理占用端口的进程，然后启动CLI服务端和Server
"""
import os
import sys
import subprocess
import signal
import time
import threading
from pathlib import Path

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
os.chdir(PROJECT_ROOT)

# 添加项目根目录到路径
sys.path.insert(0, str(PROJECT_ROOT))

from shared.config import settings
from shared.database_backup import get_backup_manager


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


def run_cli_server():
    """运行CLI服务端"""
    print("[CLI服务端] 启动中...")
    try:
        subprocess.run(
            [sys.executable, 'interfaces/cli/main.py', '--server'],
            cwd=PROJECT_ROOT,
            check=True
        )
    except KeyboardInterrupt:
        print("\n[CLI服务端] 已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n[CLI服务端] 启动失败: {e}")
        sys.exit(1)


def run_wechat_server():
    """运行微信服务器"""
    print("[微信服务器] 启动中...")
    try:
        subprocess.run(
            [sys.executable, 'interfaces/wechat/server.py'],
            cwd=PROJECT_ROOT,
            check=True
        )
    except KeyboardInterrupt:
        print("\n[微信服务器] 已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n[微信服务器] 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    print("=" * 60)
    print("启动微信服务系统")
    print("=" * 60)
    print("架构: 微信消息 → Server → Redis队列 → CLI服务端 → 响应队列 → Server → 微信")
    print()
    
    # 获取端口
    port = settings.server_port
    print(f"服务器端口: {port}")
    print()
    
    # 清理端口
    cleanup_port(port)
    print()
    
    # 检查Redis连接
    try:
        import redis
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        print(f"✓ Redis连接成功: {settings.redis_url}")
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        print("  请确保Redis服务正在运行")
        sys.exit(1)
    
    print()
    
    # 启动数据库自动备份
    print("=" * 60)
    print("启动数据库自动备份...")
    print("=" * 60)
    backup_manager = get_backup_manager(backup_interval_days=3)
    backup_manager.start_auto_backup()
    print("✓ 数据库自动备份已启动（每3天备份一次）")
    print()
    
    print("=" * 60)
    print("启动服务...")
    print("=" * 60)
    print()
    
    # 创建进程列表，用于管理子进程
    processes = []
    
    try:
        # 启动CLI服务端（在后台线程中运行）
        print("[1/2] 启动CLI服务端...")
        cli_process = subprocess.Popen(
            [sys.executable, 'interfaces/cli/main.py', '--server'],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(('CLI服务端', cli_process))
        
        # 等待一下确保CLI服务端启动
        time.sleep(2)
        
        # 启动微信服务器（在主进程中运行，这样可以捕获Ctrl+C）
        print("[2/2] 启动微信服务器...")
        print()
        print("=" * 60)
        print("服务已启动，按 Ctrl+C 停止所有服务")
        print("=" * 60)
        print()
        
        wechat_process = subprocess.Popen(
            [sys.executable, 'interfaces/wechat/server.py'],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(('微信服务器', wechat_process))
        
        # 实时输出微信服务器的日志
        def output_wechat_logs():
            for line in iter(wechat_process.stdout.readline, ''):
                if line:
                    print(f"[微信服务器] {line.rstrip()}")
        
        # 实时输出CLI服务端的日志
        def output_cli_logs():
            for line in iter(cli_process.stdout.readline, ''):
                if line:
                    print(f"[CLI服务端] {line.rstrip()}")
        
        # 启动日志输出线程
        wechat_thread = threading.Thread(target=output_wechat_logs, daemon=True)
        cli_thread = threading.Thread(target=output_cli_logs, daemon=True)
        wechat_thread.start()
        cli_thread.start()
        
        # 等待进程结束
        while True:
            # 检查进程是否还在运行
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n[{name}] 进程已退出，退出码: {proc.returncode}")
                    # 终止其他进程
                    for other_name, other_proc in processes:
                        if other_name != name and other_proc.poll() is None:
                            print(f"终止 [{other_name}]...")
                            other_proc.terminate()
                            time.sleep(1)
                            if other_proc.poll() is None:
                                other_proc.kill()
                    sys.exit(proc.returncode)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在停止所有服务...")
        
        # 停止自动备份
        try:
            backup_manager = get_backup_manager()
            backup_manager.stop_auto_backup()
            print("✓ 数据库自动备份已停止")
        except Exception as e:
            print(f"停止备份管理器失败: {e}")
        
        for name, proc in processes:
            if proc.poll() is None:
                print(f"终止 [{name}]...")
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
        print("\n所有服务已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 停止自动备份
        try:
            backup_manager = get_backup_manager()
            backup_manager.stop_auto_backup()
        except Exception:
            pass
        
        # 终止所有进程
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
        sys.exit(1)


if __name__ == '__main__':
    main()





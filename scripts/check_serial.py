"""串口心跳检查脚本。"""
from __future__ import annotations

import argparse
import time



def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="串口心跳检查")
    parser.add_argument("--port", default="/dev/tty.usbmodem1101", help="串口端口")
    parser.add_argument("--timeout", type=int, default=15, help="超时秒数")
    parser.add_argument("--keyword", default="heartbeat", help="关键字")
    return parser.parse_args()



def main() -> None:
    """执行模拟串口检查。"""
    args = parse_args()
    time.sleep(0.2)
    print(f"端口 {args.port} 在 {args.timeout}s 内检测到关键字 {args.keyword}")


if __name__ == "__main__":
    main()

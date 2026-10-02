"""复用隔离后端检查入口；v0.3 增加 init 以回收父进程中断后的可信子进程。"""

from check_v02_backend import main

if __name__ == "__main__":
    raise SystemExit(main(revision="v03", init=True))

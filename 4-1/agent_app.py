#!/usr/bin/env python3
"""
Agent Application (agent_app.py)
================================
미션 요구사항에 정의된 애플리케이션의 Boot Sequence 및 15034 포트 리슨 데몬입니다.
- 일반 사용자 계정 실행 검증 (root 실행 차단)
- 5단계 Boot Sequence 검사 및 'Agent READY' 출력
- 0.0.0.0:15034 TCP 소켓 바인딩 및 대기
"""

import os
import sys
import socket
import signal
import time


def print_step(step_num, title, detail=None, success=True):
    status = "[OK]" if success else "[FAIL]"
    print(f"[{step_num}/5] {title} {status}")
    if detail:
        print(f"... {detail}")


def boot_sequence():
    print("> Starting Agent Boot Sequence...")

    # [1/5] Checking User Account
    current_uid = os.getuid()
    try:
        import pwd
        user_name = pwd.getpwuid(current_uid).pw_name
    except Exception:
        user_name = os.environ.get("USER", "agent-user")

    if current_uid == 0:
        print_step(1, "Checking User Account", "ERROR: Running as root is forbidden!", success=False)
        sys.exit(1)
    else:
        print_step(1, "Checking User Account", f"Running as service user '{user_name}' (uid={current_uid})", success=True)

    # [2/5] Verifying Environment Variables
    agent_home = os.environ.get("AGENT_HOME")
    agent_port = os.environ.get("AGENT_PORT", "15034")
    agent_upload_dir = os.environ.get("AGENT_UPLOAD_DIR")
    agent_key_path = os.environ.get("AGENT_KEY_PATH")
    agent_log_dir = os.environ.get("AGENT_LOG_DIR", "/var/log/agent-app")

    missing_envs = []
    if not agent_home:
        missing_envs.append("AGENT_HOME")
    if not agent_upload_dir:
        missing_envs.append("AGENT_UPLOAD_DIR")
    if not agent_key_path:
        missing_envs.append("AGENT_KEY_PATH")

    if missing_envs:
        print_step(2, "Verifying Environment Variables", f"Missing environment variables: {', '.join(missing_envs)}", success=False)
        sys.exit(1)
    else:
        print_step(2, "Verifying Environment Variables", "All required Envs correct", success=True)

    # [3/5] Checking Required Files
    if not os.path.exists(agent_key_path):
        print_step(3, "Checking Required Files", f"Key file not found: {agent_key_path}", success=False)
        sys.exit(1)

    try:
        with open(agent_key_path, "r", encoding="utf-8") as f:
            key_content = f.read().strip()
        if key_content != "agent_api_key_test":
            print_step(3, "Checking Required Files", "Key content invalid!", success=False)
            sys.exit(1)
        print_step(3, "Checking Required Files", "Verified key file with correct key string.", success=True)
    except Exception as e:
        print_step(3, "Checking Required Files", f"Failed reading key file: {e}", success=False)
        sys.exit(1)

    # [4/5] Checking Port Availability
    port = int(agent_port)
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        test_sock.bind(("0.0.0.0", port))
        test_sock.close()
        print_step(4, "Checking Port Availability", f"Port {port} is available.", success=True)
    except Exception as e:
        print_step(4, "Checking Port Availability", f"Port {port} is not available: {e}", success=False)
        sys.exit(1)

    # [5/5] Verifying Log Permission
    if not os.path.exists(agent_log_dir):
        try:
            os.makedirs(agent_log_dir, exist_ok=True)
        except Exception as e:
            print_step(5, "Verifying Log Permission", f"Log directory create failed: {e}", success=False)
            sys.exit(1)

    if not os.access(agent_log_dir, os.W_OK):
        print_step(5, "Verifying Log Permission", f"Log directory is not writable: {agent_log_dir}", success=False)
        sys.exit(1)
    else:
        print_step(5, "Verifying Log Permission", f"Log directory is writable: {agent_log_dir}", success=True)

    print("-" * 60)
    print("All Boot Checks Passed!")
    print("Agent READY")
    sys.stdout.flush()


def run_server():
    boot_sequence()

    port = int(os.environ.get("AGENT_PORT", "15034"))
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)
    server_socket.settimeout(1.0)

    running = True

    def sig_handler(signum, frame):
        nonlocal running
        print("\n[INFO] Received termination signal. Shutting down Agent...")
        running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    while running:
        try:
            client_socket, client_addr = server_socket.accept()
            client_socket.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nAgent is online\n")
            client_socket.close()
        except socket.timeout:
            continue
        except Exception:
            break

    server_socket.close()
    print("[INFO] Agent stopped cleanly.")


if __name__ == "__main__":
    run_server()

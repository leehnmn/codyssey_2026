"""
B5-1 Mini Redis - CLI REPL 인터페이스 모듈
학습 목적: 사용자 인터랙션, 따옴표 문자열 토크나이징, Redis 표준 응답/에러 포맷팅,
          Python Traceback 노출 원천 차단.
"""
import shlex
import sys
from typing import List

from mini_redis import MiniRedis


def parse_line(line: str) -> List[str]:
    """
    한 줄 입력을 shlex를 사용하여 토큰 단위로 안전하게 분리.
    큰따옴표("Alice") 또는 작은따옴표('Bob')로 묶인 공백을 단일 인자로 보존함.
    """
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = '#'
    return list(lexer)


class MiniRedisCLI:
    """CLI REPL 실행기."""

    def __init__(self):
        self.engine = MiniRedis()

    def execute_command(self, tokens: List[str]) -> str:
        """토큰 리스트를 받아 적절한 MiniRedis 메서드로 디스패치."""
        if not tokens:
            return ""

        cmd = tokens[0].upper()
        args = tokens[1:]

        # 1. String 기본 명령어 (6개)
        if cmd == "SET":
            if len(args) != 2:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.set(args[0], args[1])

        elif cmd == "GET":
            if len(args) != 1:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.get(args[0])

        elif cmd == "DEL":
            if len(args) != 1:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.delete(args[0])

        elif cmd == "EXISTS":
            if len(args) != 1:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.exists(args[0])

        elif cmd == "DBSIZE":
            if len(args) != 0:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.dbsize()

        elif cmd == "KEYS":
            if len(args) != 0:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.keys()

        # 2. 메모리 관리 명령어 (2개)
        elif cmd == "CONFIG":
            # CONFIG SET maxmemory <val>
            if len(args) == 3 and args[0].upper() == "SET" and args[1].lower() == "maxmemory":
                return self.engine.config_set_maxmemory(args[2])
            else:
                return "(error) ERR unknown command 'CONFIG'"

        elif cmd == "INFO":
            # INFO memory
            if len(args) == 1 and args[0].lower() == "memory":
                return self.engine.info_memory()
            else:
                return "(error) ERR unknown command 'INFO'"

        # 3. TTL 관리 명령어 (2개)
        elif cmd == "EXPIRE":
            if len(args) != 2:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.expire(args[0], args[1])

        elif cmd == "TTL":
            if len(args) != 1:
                return f"(error) ERR wrong number of arguments for '{cmd.lower()}' command"
            return self.engine.ttl(args[0])

        else:
            return f"(error) ERR unknown command '{tokens[0]}'"

    def run(self) -> None:
        """REPL 메인 루프 실행."""
        while True:
            try:
                line = input("mini-redis> ").strip()
                if not line:
                    continue

                if line.lower() in ("exit", "quit"):
                    break

                try:
                    tokens = parse_line(line)
                except ValueError:
                    print("(error) ERR syntax error")
                    continue

                if not tokens:
                    continue

                result = self.execute_command(tokens)
                if result:
                    print(result)

            except (EOFError, KeyboardInterrupt):
                print()
                break
            except Exception as e:
                # 스택트레이스 원천 방어: 내부 예외 발생 시 표준 에러 메시지로 캡슐화
                print(f"(error) ERR internal server error: {e}")


def main():
    cli = MiniRedisCLI()
    cli.run()


if __name__ == "__main__":
    main()
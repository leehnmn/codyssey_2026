from quiz_game import QuizGame

def main():
    game = QuizGame()
    game.run()

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n프로그램이 안전하게 종료되었습니다.")
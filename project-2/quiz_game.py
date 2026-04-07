import json
import os

from quiz import Quiz


class QuizGame:
    def __init__(self, state_file="state.json"):
        self.state_file = state_file
        self.quizzes = []
        self.best_score = None
        self.load_state()

    def get_default_quizzes(self):
        return [
            Quiz("Python에서 문자열 자료형은 무엇인가요?",
                 ["int", "str", "bool", "list"], 2),
            Quiz("리스트를 만들 때 사용하는 기호는 무엇인가요?",
                 ["()", "{}", "[]", "<>"], 3),
            Quiz("조건문에 사용하는 키워드는 무엇인가요?",
                 ["for", "while", "if", "def"], 3),
            Quiz("반복문 중 횟수를 순회할 때 자주 사용하는 것은 무엇인가요?",
                 ["for", "class", "return", "import"], 1),
            Quiz("함수를 정의할 때 사용하는 키워드는 무엇인가요?",
                 ["func", "def", "method", "lambda"], 2),
        ]
    def load_state(self):
        try:
            if not os.path.exists(self.state_file):
                raise FileNotFoundError

            with open(self.state_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.quizzes = [Quiz.from_dict(item) for item in data.get("quizzes", [])]
            self.best_score = data.get("best_score")
            if not self.quizzes:
                self.quizzes = self.get_default_quizzes()

        except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError, TypeError):
            print("state.json 파일이 없거나 손상되어 기본 데이터로 복구합니다.")
            self.quizzes = self.get_default_quizzes()
            self.best_score = None
            self.save_state()
 
    def save_state(self):
        data = {
            "quizzes": [quiz.to_dict() for quiz in self.quizzes],
            "best_score": self.best_score,
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        except OSError:
            print("파일 저장 중 오류가 발생했습니다.")

    def get_text_input(self, prompt):
        try:
            value = input(prompt).strip()
            if not value:
                print("빈 입력은 허용되지 않습니다.")
                return None
            return value
        except (KeyboardInterrupt, EOFError):
            print("\n입력이 중단되었습니다. 저장 후 안전하게 종료합니다.")
            self.save_state()
            raise SystemExit

    def get_valid_number_input(self, prompt, min_value, max_value):
        while True:
            text = self.get_text_input(prompt)
            if text is None:
                continue
            try:
                number = int(text)
                if min_value <= number <= max_value:
                    return number
                print(f"{min_value}부터 {max_value} 사이의 숫자를 입력하세요.")
            except ValueError:
                print("숫자를 입력해야 합니다. 다시 입력하세요.")
    def show_menu(self):
        print("\n===== 퀴즈 게임 =====")
        print("1. 퀴즈 풀기")
        print("2. 퀴즈 추가")
        print("3. 퀴즈 목록 보기")
        print("4. 최고 점수 확인")
        print("5. 종료")

    def play_quiz(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return

        score = 0
        for quiz in self.quizzes:
            quiz.display()
            answer = self.get_valid_number_input("정답 번호를 입력하세요 (1~4): ", 1, 4)
            if quiz.is_correct(answer):
                print("정답입니다!")
                score += 1
            else:
                print(f"오답입니다. 정답은 {quiz.answer}번입니다.")

        print(f"\n퀴즈 종료! 총 점수: {score}/{len(self.quizzes)}")
        if self.best_score is None or score > self.best_score:
            self.best_score = score
            print("최고 점수가 갱신되었습니다!")
            self.save_state()

    def add_quiz(self):
        question = self.get_text_input("문제를 입력하세요: ")
        if question is None:
            return

        choices = []
        for i in range(1, 5):
            choice = self.get_text_input(f"{i}번 선택지를 입력하세요: ")
            if choice is None:
                return
            choices.append(choice)

        answer = self.get_valid_number_input("정답 번호를 입력하세요 (1~4): ", 1, 4)
        self.quizzes.append(Quiz(question, choices, answer))
        self.save_state()
        print("새 퀴즈가 저장되었습니다.")

    def list_quizzes(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        print("\n===== 퀴즈 목록 =====")
        for idx, quiz in enumerate(self.quizzes, start=1):
            print(f"{idx}. {quiz.question}")

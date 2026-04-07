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

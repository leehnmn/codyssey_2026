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
class Quiz:
    def __init__(self, question, choices, answer):
        self.question = question
        self.choices = choices
        self.answer = answer

        def display(self):
            print(f"/n문제: {self.question}" )
            for idx, choice in enumerate(self.choices, start=1):
                print(f"{idx}. {choice}")

        def is_correct(self, user_answer):
            return user_answer == self.answer
        
        def to_dict(self):
            return {
                "question": self.question,
                "choices": self.choices,
                "answer": self.answer,
            }
        
        @classmethod
        def from_dict(cls, data):
            return cls(
                question = data["question"],
                choices = data["choices"],
                answer = data["answer"],
            )
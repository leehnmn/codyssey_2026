class Quiz: 
    def __init__(self, question, choices, answer): # 퀴즈 객체 생성
        self.question = question
        self.choices = choices
        self.answer = answer

    def display(self): #  문제 선택지 출력
            print(f"\n문제: {self.question}" )
            for idx, choice in enumerate(self.choices, start=1):
                print(f"{idx}. {choice}")

    def is_correct(self, user_answer): #정답 확인 
            return user_answer == self.answer
        
    def to_dict(self): # 겍체 딕셔너리화 json 파일 저장
            return {
                "question": self.question,
                "choices": self.choices,
                "answer": self.answer,
            }
        
    @classmethod  # 클래스 자체를 객체로 쓰기위함. 
    def from_dict(cls, data): #json -> 객체로 변환
            return cls(
                question = data["question"],
                choices = data["choices"],
                answer = data["answer"],
            )
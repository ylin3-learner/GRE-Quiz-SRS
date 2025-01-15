import threading
import time
import pandas as pd
import numpy as np
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

class QuizApp:
    def __init__(self, time_limit, data):
        self.time_limit = time_limit
        self.data = data
        self.score = 0
        self.answered_questions = 0

    def get_priority_question(self, flag_column, required_columns):
        """
        隨機抽取題目，但僅從 flag > 0 的題目中選擇，並按權重優先。
        """
        # 過濾 flag > 0 的題目
        filtered_data = self.data[self.data[flag_column] > 0]

        # 確保必須字段（required_columns）都有值
        for column in required_columns:
            filtered_data = filtered_data[~filtered_data[column].isna()]

        # 如果沒有符合條件的題目，返回 None
        if filtered_data.empty:
            return None

        # 按 flag 權重隨機選擇題目
        probabilities = filtered_data[flag_column] / filtered_data[flag_column].sum()
        chosen_index = np.random.choice(filtered_data.index, p=probabilities)

        # 返回選中的題目
        return self.data.loc[chosen_index]

    def fuzzy_match(self, user_input, correct_answer):
        return user_input.strip().lower() == correct_answer.strip().lower()

    def display_progress(self):
        print(f"\n當前分數: {self.score}, 已回答問題數: {self.answered_questions}\n")

    def ask_question(self, question, answer_key, hint, flag_key):
        print(f"\n提示：{hint} (限時 {self.time_limit} 秒)")

        elapsed_time = 0
        timeout = False
        user_input_received = [False]

        def countdown():
            nonlocal elapsed_time, timeout
            while elapsed_time < self.time_limit:
                time.sleep(1)
                elapsed_time += 1

            if not user_input_received[0]:
                timeout = True
                print(f"\n{Fore.RED}正確答案是：{question[answer_key]}{Style.RESET_ALL}")

        countdown_thread = threading.Thread(target=countdown)
        countdown_thread.start()

        try:
            user_input = input("\n請輸入答案：")
            user_input_received[0] = True
        except Exception as e:
            print(f"輸入發生錯誤：{e}")
            user_input = None

        countdown_thread.join()
        index = question.name
        if timeout:
            self.data.loc[index, flag_key] += 1
            self.score -= 5
        elif self.fuzzy_match(user_input, question[answer_key]):
            print(f"{Fore.GREEN}正確！{Style.RESET_ALL}")
            self.data.loc[index, flag_key] = 0  # 答對時設定 flag 為 0
            self.score += 10
        else:
            print(f"{Fore.RED}錯誤！正確答案是：{question[answer_key]}{Style.RESET_ALL}")
            self.data.loc[index, flag_key] += 1
            self.score -= 5

        self.answered_questions += 1
        self.display_progress()

    def ask_root_question(self):
        """Ask a Root question."""
        question = self.get_priority_question("root_flag", ["Root", "meaning"])
        if question is None:
            print("\n没有需要提問的 Root 問題。")
            return False

        self.ask_question(
            question,
            answer_key="Root",
            hint=f"意思：{question['meaning']}",
            flag_key="root_flag"
        )
        return True

    def ask_voc_question(self):
        """Ask a Voc question."""
        question = self.get_priority_question("voc_flag", ["Voc", "Sentence", "translation", "Memorize"])
        if question is None:
            print("\n没有需要提問的 Voc 問題。")
            return False

        # 提示僅顯示 Memorize 的值
        hint = f"{question['Memorize']}\n翻譯：{question['translation']}"

        # 提問並檢查答案
        self.ask_question(
            question,
            answer_key="Voc",
            hint=hint,  # 直接傳遞提示內容
            flag_key="voc_flag"
        )

        # 顯示 Sentence 和對應的 Voc（不論答對與否）
        print(f"\n正確答案：{question['Voc']}")
        print(f"句子：{question['Sentence']}")
        print(f"翻譯：{question['translation']}")

        return True

    def run_quiz(self):
        """Main loop to control the quiz."""
        while True:
            root_remaining = not self.data[self.data["root_flag"] > 0].empty
            voc_remaining = not self.data[self.data["voc_flag"] > 0].empty

            if not root_remaining and not voc_remaining:
                print("\n測試完成！所有題目都已回答或不需要繼續提問。")
                break

            print("\n請選擇下一步操作：")
            print("1: 提問 Root 問題")
            print("2: 提問 Voc 問題")
            print("q: 退出測試")

            user_choice = input("請輸入選項 (1/2/q)：").strip().lower()

            if user_choice == "q":
                print("測試已結束。")
                break
            elif user_choice == "1":
                self.ask_root_question()
            elif user_choice == "2":
                self.ask_voc_question()
            else:
                print("\n無效選項，請重試。")

if __name__ == "__main__":
    try:
        data = pd.read_excel("voc.xlsx")
        data["root_flag"] = data["root_flag"].fillna(0).astype(int)
        data["voc_flag"] = data["voc_flag"].fillna(0).astype(int)

        # 將需要比對的列內容轉為小寫
        if "Root" in data.columns:
            data["Root"] = data["Root"].str.lower()
        if "Voc" in data.columns:
            data["Voc"] = data["Voc"].str.lower()

    except FileNotFoundError:
        print("錯誤：未找到 'voc.xlsx' 文件。")
        exit()

    app = QuizApp(time_limit=5, data=data)
    app.run_quiz()

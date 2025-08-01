import threading
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style, init


init(autoreset=True)

class QuizApp:
    def __init__(self, time_limit, data, filename):
        self.time_limit = time_limit
        self.data = data
        self.filename = filename
        self.score = 0
        self.answered_questions = 0
        self.burst_mode = False  # 爆練模式開關
        self.daily_max_quota = 30  # 正常模式每日最大題數限制
        self.load_or_init_meta()

    def load_or_init_meta(self):
        # 初始化負荷與配額追蹤欄位
        meta_cols = {
            'next_review_date': '',
            'review_interval': 0,
            'review_count': 0,
            'consecutive_correct': 0,
            'last_reviewed': '',
            'total_reviews': 0,
            'ease_factor': 2.5,  # SM-2默認EF
        }
        for col, default in meta_cols.items():
            if col not in self.data.columns:
                self.data[col] = default
            if col in ['next_review_date', 'last_reviewed']:
                self.data[col] = self.data[col].astype(str).fillna('')
        # 其他欄位補齊
        important_cols = ["Root", "meaning", "Voc", "Memorize", "Sentence", "translation"]
        for col in important_cols:
            if col in self.data.columns:
                self.data[col] = self.data[col].fillna("")

    def toggle_burst_mode(self):
        self.burst_mode = not self.burst_mode
        mode = "爆練模式" if self.burst_mode else "正常模式"
        print(f"\n已切換至 {mode}。")

    def get_daily_answered_count(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        answered_today = self.data[
            self.data['last_reviewed'].str.startswith(today_str)
        ]
        return len(answered_today)

    def get_priority_question(self, required_columns):
        filtered_data = self.data.dropna(subset=required_columns)
        if filtered_data.empty:
            return None

        now = datetime.now()
        due_questions = []

        daily_answered = self.get_daily_answered_count()

        for idx, row in filtered_data.iterrows():
            next_review_str = row['next_review_date']
            overdue_days = 0

            if not next_review_str or pd.isna(next_review_str):
                overdue_days = 0
            else:
                try:
                    next_review = datetime.strptime(next_review_str, '%Y-%m-%d %H:%M:%S')
                    if next_review <= now:
                        overdue_days = (now - next_review).days
                    else:
                        continue
                except:
                    overdue_days = 0

            priority = row['review_count'] * 100 + overdue_days
            due_questions.append((idx, priority, overdue_days))

        if not due_questions:
            return None

        # 配額限制（正常模式）
        if not self.burst_mode and daily_answered >= self.daily_max_quota:
            print(f"\n達到每日最大複習配額 ({self.daily_max_quota} 題)，請明天再繼續練習。")
            return None

        due_questions.sort(key=lambda x: x[1], reverse=True)
        weights = np.array([len(due_questions) - i for i, _ in enumerate(due_questions)], dtype=float)
        weights /= weights.sum()

        indices = [item[0] for item in due_questions]
        chosen_index = np.random.choice(indices, p=weights)

        chosen_row = self.data.loc[chosen_index].copy()
        chosen_row['overdue_days'] = next((x[2] for x in due_questions if x[0] == chosen_index), 0)
        chosen_row['is_burst'] = self.burst_mode
        return chosen_row

    def calculate_next_review_date(self, last_interval, ef, quality, overdue_days):
        # SM-2 保守版計算，帶入負荷超期補正
        if quality < 3:
            ef = max(1.3, ef - 0.1)
            new_interval = 1
        else:
            ef = min(2.5, ef + 0.02)
            if last_interval < 1:
                new_interval = 1
            elif last_interval == 1:
                new_interval = 3
            else:
                overdue_bonus = min(1.0 + overdue_days / max(last_interval, 1), 1.5)
                new_interval = last_interval * ef * overdue_bonus
                new_interval = min(new_interval, last_interval * 2)

        return round(new_interval), ef

    def fuzzy_match(self, user_input, correct_answer):
        if not isinstance(user_input, str) or not isinstance(correct_answer, str):
            return False
        return user_input.strip().lower() == correct_answer.strip().lower()

    def display_load_bar(self):
        # 用錯誤次數比例做簡單負荷條，爆練模式不顯示
        if self.burst_mode:
            return
        max_err = 10
        avg_error = self.data['review_count'].mean()
        ratio = min(avg_error / max_err, 1.0)
        bar_length = 30
        filled_length = int(bar_length * ratio)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"學習負荷狀態: |{bar}| {avg_error:.2f} 平均錯誤次數")

    def ask_question(self, question, answer_key, hint):
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
                print(f"\n{Fore.RED}時間到！正確答案是：{question[answer_key]}{Style.RESET_ALL}")

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
        is_burst = question.get('is_burst', False)

        if timeout:
            if not is_burst:
                self.data.loc[index, 'review_count'] += 1
                self.data.loc[index, 'consecutive_correct'] = 0
            self.score -= 5
            print(f"{Fore.RED}超時！{Style.RESET_ALL}")
        elif self.fuzzy_match(user_input, question[answer_key]):
            if not is_burst:
                self.data.loc[index, 'consecutive_correct'] += 1
            self.score += 10
            print(f"{Fore.GREEN}正確！{Style.RESET_ALL}")
            if not is_burst and self.data.loc[index, 'consecutive_correct'] >= 3:
                self.data.loc[index, 'review_count'] = 0
                self.data.loc[index, 'consecutive_correct'] = 0
                print(f"{Fore.CYAN}太棒了！這題已經掌握了！{Style.RESET_ALL}")
        else:
            if not is_burst:
                self.data.loc[index, 'review_count'] += 1
                self.data.loc[index, 'consecutive_correct'] = 0
            self.score -= 5
            print(f"{Fore.RED}錯誤！正確答案是：{question[answer_key]}{Style.RESET_ALL}")

        # 更新 SM-2 間隔
        last_interval = self.data.loc[index, 'review_interval']
        ef = self.data.loc[index, 'ease_factor']
        quality = 5 if (not timeout and self.fuzzy_match(user_input, question[answer_key])) else 2
        overdue_days = question.get('overdue_days', 0)

        new_interval, new_ef = self.calculate_next_review_date(last_interval, ef, quality, overdue_days)

        self.data.loc[index, 'review_interval'] = new_interval
        self.data.loc[index, 'ease_factor'] = new_ef
        self.data.loc[index, 'next_review_date'] = (datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d %H:%M:%S')
        self.data.loc[index, 'last_reviewed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.data.loc[index, 'total_reviews'] = self.data.loc[index, 'total_reviews'] + 1

        difficulty_level = "簡單" if self.data.loc[index, 'review_count'] == 0 else "中等" if self.data.loc[index, 'review_count'] <= 2 else "困難"
        print(f"難度等級: {difficulty_level} (錯誤次數: {self.data.loc[index, 'review_count']})")
        print(f"下次複習: {(datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d')} ({new_interval} 天後)")
        if self.data.loc[index, 'consecutive_correct'] > 0:
            print(f"連續答對: {self.data.loc[index, 'consecutive_correct']} 次")

        self.answered_questions += 1
        self.display_load_bar()
        self.display_progress()

    def display_progress(self):
        print(f"\n當前分數: {self.score}, 已回答問題數: {self.answered_questions}")

        now = datetime.now()
        due_count = 0
        for idx, row in self.data.iterrows():
            next_review_str = row['next_review_date']
            if next_review_str == '' or pd.isna(next_review_str):
                due_count += 1
            else:
                try:
                    next_review = datetime.strptime(next_review_str, '%Y-%m-%d %H:%M:%S')
                    if next_review <= now:
                        due_count += 1
                except:
                    due_count += 1

        print(f"待複習題目數: {due_count}\n")

    def ask_root_question(self):
        question = self.get_priority_question(["Root", "meaning"])
        if question is None:
            print("\n目前沒有需要複習的 Root 問題。")
            return False
        self.ask_question(
            question,
            answer_key="Root",
            hint=f"意思：{question['meaning']}",
        )
        return True

    def ask_voc_question(self):
        question = self.get_priority_question(["Voc", "Sentence", "translation", "Memorize"])
        if question is None:
            print("\n目前沒有需要複習的 Voc 問題。")
            return False

        hint = f"{question['Memorize']}\n翻譯：{question['translation']}"
        self.ask_question(
            question,
            answer_key="Voc",
            hint=hint,
        )

        print(f"\n正確答案：{question['Voc']}")
        print(f"句子：{question['Sentence']}")
        print(f"翻譯：{question['translation']}")

        return True

    def save_progress(self):
        self.data.to_excel(self.filename, index=False)
        print("\n進度已儲存！")

    def show_statistics(self):
        print(f"\n=== 學習統計 ===")
        total_questions = len(self.data)
        reviewed_questions = len(self.data[self.data['total_reviews'] > 0])

        print(f"總題目數: {total_questions}")
        print(f"已複習題目: {reviewed_questions}")
        print(f"複習進度: {reviewed_questions/total_questions*100:.1f}%")

        simple_count = len(self.data[self.data['review_count'] == 0])
        medium_count = len(self.data[self.data['review_count'].between(1, 2)])
        hard_count = len(self.data[self.data['review_count'] >= 3])

        print(f"\n難度分佈 (基於錯誤次數):")
        print(f"  簡單 (已掌握): {simple_count} 題")
        print(f"  中等 (1-2次錯誤): {medium_count} 題")
        print(f"  困難 (>=3次錯誤): {hard_count} 題")

    def run_quiz(self):
        while True:
            print("\n請選擇下一步操作：")
            print("1: 提問 Root 問題")
            print("2: 提問 Voc 問題")
            print("3: 顯示統計資料")
            print(f"4: 切換爆練模式 (目前：{'開啟' if self.burst_mode else '關閉'})")
            print("q: 退出測試")

            user_choice = input("請輸入選項 (1/2/3/4/q)：").strip().lower()

            if user_choice == "q":
                self.save_progress()
                print("測試已結束，進度已儲存。")
                break
            elif user_choice == "1":
                self.ask_root_question()
            elif user_choice == "2":
                self.ask_voc_question()
            elif user_choice == "3":
                self.show_statistics()
            elif user_choice == "4":
                self.toggle_burst_mode()
            else:
                print("\n無效選項，請重試。")

if __name__ == "__main__":
    filename = "voc.xlsx"
    try:
        data = pd.read_excel(filename)
    except FileNotFoundError:
        print("錯誤：未找到 'voc.xlsx' 文件。")
        exit()

    app = QuizApp(time_limit=10, data=data, filename=filename)
    app.run_quiz()

import threading
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

class QuizApp:
    def __init__(self, time_limit, data, filename):
        self.time_limit = time_limit
        self.data = data
        self.filename = filename
        self.score = 0
        self.answered_questions = 0

    def get_priority_question(self, required_columns):
        """
        使用改進的優先級系統選擇題目：
        1. 優先選擇到期需要複習的題目
        2. 在到期題目中，review_count 越高越優先
        3. 相同 review_count 的題目按超期時間排序
        """
        # 過濾有效題目
        filtered_data = self.data.dropna(subset=required_columns)
        
        if filtered_data.empty:
            return None

        now = datetime.now()
        
        # 找出需要複習的題目
        due_questions = []
        for idx, row in filtered_data.iterrows():
            next_review_str = row['next_review_date']
            
            # 如果是新題目或已到期的題目
            if next_review_str == '' or pd.isna(next_review_str):
                # 新題目
                overdue_days = 0
            else:
                try:
                    next_review = datetime.strptime(next_review_str, '%Y-%m-%d %H:%M:%S')
                    if next_review <= now:
                        overdue_days = (now - next_review).days
                    else:
                        continue  # 還沒到複習時間
                except:
                    # 日期格式錯誤，視為新題目
                    overdue_days = 0
            
            # 優先級計算：review_count 越高越優先，超期時間作為次要因素
            priority = row['review_count'] * 100 + overdue_days
            due_questions.append((idx, priority))
        
        # 如果沒有到期的題目，返回 None
        if not due_questions:
            return None
        
        # 按優先級排序並加權選擇
        due_questions.sort(key=lambda x: x[1], reverse=True)
        
        # 給予高優先級題目更高的權重
        weights = []
        for i, (idx, priority) in enumerate(due_questions):
            weight = len(due_questions) - i  # 越前面權重越高
            weights.append(weight)
        
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()
        
        indices = [item[0] for item in due_questions]
        chosen_index = np.random.choice(indices, p=weights)
        
        return self.data.loc[chosen_index]

    def calculate_next_review_date(self, review_count, consecutive_correct):
        """
        根據 review_count 計算下次複習間隔
        
        Args:
            review_count: 當前錯誤次數
            consecutive_correct: 連續答對次數
            
        Returns:
            int: 複習間隔（天數）
        """
        # 根據難度（review_count）決定基礎間隔
        if review_count == 0:  # 簡單題目
            base_interval = 7  # 一週後複習
        elif review_count <= 2:  # 中等題目
            base_interval = 3  # 3天後複習
        else:  # 困難題目
            base_interval = 1  # 每天複習
        
        # 如果連續答對多次，可以延長間隔
        if consecutive_correct >= 2:
            base_interval = min(base_interval * 2, 14)  # 最多延長到兩週
        
        return base_interval

    def fuzzy_match(self, user_input, correct_answer):
        return user_input.strip().lower() == correct_answer.strip().lower()

    def display_progress(self):
        print(f"\n當前分數: {self.score}, 已回答問題數: {self.answered_questions}")
        
        # 顯示複習統計
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
        
        print(f"待複習題目數: {due_count}")
        print()

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

        # 根據回答情況更新記錄
        index = question.name
        
        if timeout:
            # 超時視為錯誤
            self.data.loc[index, 'review_count'] += 1
            self.data.loc[index, 'consecutive_correct'] = 0
            self.score -= 5
            print(f"{Fore.RED}超時！{Style.RESET_ALL}")
        elif self.fuzzy_match(user_input, question[answer_key]):
            # 答對了 - 在時間內回答正確都給予正面回饋
            self.data.loc[index, 'consecutive_correct'] += 1
            self.score += 10
            print(f"{Fore.GREEN}正確！{Style.RESET_ALL}")
            
            # 如果連續答對3次，將 review_count 設為 0
            if self.data.loc[index, 'consecutive_correct'] >= 3:
                self.data.loc[index, 'review_count'] = 0
                self.data.loc[index, 'consecutive_correct'] = 0
                print(f"{Fore.CYAN}太棒了！這題已經掌握了！{Style.RESET_ALL}")
                
        else:
            # 答錯了
            self.data.loc[index, 'review_count'] += 1
            self.data.loc[index, 'consecutive_correct'] = 0
            self.score -= 5
            print(f"{Fore.RED}錯誤！正確答案是：{question[answer_key]}{Style.RESET_ALL}")

        # 計算下次複習時間
        review_count = self.data.loc[index, 'review_count']
        consecutive_correct = self.data.loc[index, 'consecutive_correct']
        
        interval_days = self.calculate_next_review_date(review_count, consecutive_correct)
        next_review_date = datetime.now() + timedelta(days=interval_days)
        
        # 更新記錄
        self.data.loc[index, 'review_interval'] = interval_days
        self.data.loc[index, 'next_review_date'] = next_review_date.strftime('%Y-%m-%d %H:%M:%S')
        self.data.loc[index, 'last_reviewed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.data.loc[index, 'total_reviews'] = self.data.loc[index, 'total_reviews'] + 1
        
        # 顯示題目狀態
        difficulty_level = "簡單" if review_count == 0 else "中等" if review_count <= 2 else "困難"
        print(f"難度等級: {difficulty_level} (錯誤次數: {review_count})")
        print(f"下次複習: {next_review_date.strftime('%Y-%m-%d')} ({interval_days} 天後)")
        if consecutive_correct > 0:
            print(f"連續答對: {consecutive_correct} 次")

        self.answered_questions += 1
        self.display_progress()

    def ask_root_question(self):
        """提問 Root 問題"""
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
        """提問 Vocabulary 問題"""
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

        # 顯示句子（不論答對與否）
        print(f"\n正確答案：{question['Voc']}")
        print(f"句子：{question['Sentence']}")
        print(f"翻譯：{question['translation']}")

        return True

    def save_progress(self):
        """儲存測驗進度"""
        self.data.to_excel(self.filename, index=False)
        print("\n進度已儲存！")

    def show_statistics(self):
        """顯示學習統計"""
        print(f"\n=== 學習統計 ===")
        total_questions = len(self.data)
        reviewed_questions = len(self.data[self.data['total_reviews'] > 0])
        
        print(f"總題目數: {total_questions}")
        print(f"已複習題目: {reviewed_questions}")
        print(f"複習進度: {reviewed_questions/total_questions*100:.1f}%")
        
        # 按 review_count 分組統計難度
        simple_count = len(self.data[self.data['review_count'] == 0])
        medium_count = len(self.data[self.data['review_count'].between(1, 2)])
        hard_count = len(self.data[self.data['review_count'] >= 3])
        
        print(f"\n難度分佈 (基於錯誤次數):")
        print(f"  簡單 (已掌握): {simple_count} 題")
        print(f"  中等 (1-2次錯誤): {medium_count} 題")
        print(f"  困難 (>=3次錯誤): {hard_count} 題")

    def run_quiz(self):
        """主測驗迴圈"""
        while True:
            print("\n請選擇下一步操作：")
            print("1: 提問 Root 問題")
            print("2: 提問 Voc 問題")
            print("3: 顯示統計資料")
            print("q: 退出測試")

            user_choice = input("請輸入選項 (1/2/3/q)：").strip().lower()

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
            else:
                print("\n無效選項，請重試。")

if __name__ == "__main__":
    filename = "voc.xlsx"

    try:
        data = pd.read_excel(filename)

        # 初始化遺忘曲線相關欄位
        new_columns = {
            'next_review_date': '',  # 使用空字串而非 pd.NaT
            'review_interval': 0,
            'review_count': 0,  # 錯誤次數計數
            'consecutive_correct': 0,  # 連續答對次數
            'last_reviewed': '',  # 使用空字串而非 pd.NaT
            'total_reviews': 0
        }
        
        for col, default_value in new_columns.items():
            if col not in data.columns:
                data[col] = default_value
            # 確保日期時間欄位的資料型別一致
            if col in ['next_review_date', 'last_reviewed']:
                data[col] = data[col].astype(str).fillna('')

        # 確保其他重要欄位不為 NaN
        important_columns = ["Root", "meaning", "Voc", "Memorize", "Sentence", "translation"]
        for col in important_columns:
            if col in data.columns:
                data[col] = data[col].fillna("")

    except FileNotFoundError:
        print("錯誤：未找到 'voc.xlsx' 文件。")
        exit()

    app = QuizApp(time_limit=5, data=data, filename=filename)
    app.run_quiz()
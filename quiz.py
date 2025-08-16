import threading
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style, init
import sys


init(autoreset=True)

class QuizApp:
    def __init__(self, time_limit, data, filename):
        self.time_limit = time_limit
        self.data = data
        self.filename = filename
        self.score = 0
        self.answered_questions = 0
        self.burst_mode = False  # 爆練模式開關
        self.debug_priority = False  # 新增 debug flag
        self.daily_max_quota = 150  # 正常模式每日最大題數限制
        self.daily_new_quota = 50    # 每日最少新單字數量
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

        # # 確保 total_reviews 為 int
        self.data['total_reviews'] = pd.to_numeric(
            self.data['total_reviews'], errors='coerce'
        ).fillna(0).astype(int)

        # 其他欄位補齊
        important_cols = ["Root", "meaning", "Voc", "Memorize", "Sentence", "translation"]
        for col in important_cols:
            if col in self.data.columns:
                self.data[col] = self.data[col].fillna("")

    def configure_daily_quota(self):
        """
        讓使用者設定每日總題數與每日新字數量
        """
        print("\n=== 配置每日練習配額 ===")
        try:
            max_quota_input = input(f"請輸入每日最大練習題數 (目前 {self.daily_max_quota})，直接 Enter 保持不變：")
            if max_quota_input.strip():
                max_quota = int(max_quota_input)
                if max_quota <= 0:
                    print("每日最大題數必須大於 0，保持原設定。")
                else:
                    self.daily_max_quota = max_quota

            new_quota_input = input(f"請輸入每日新單字數量 (目前 {self.daily_new_quota})，直接 Enter 保持不變：")
            if new_quota_input.strip():
                new_quota = int(new_quota_input)
                if new_quota < 0:
                    print("每日新單字數量不能為負數，保持原設定。")
                else:
                    self.daily_new_quota = new_quota

            print(f"設定完成：每日最大題數={self.daily_max_quota}, 每日新單字數量={self.daily_new_quota}")

        except ValueError:
            print("輸入格式錯誤，保持原設定。")
    
    def calculate_daily_progress(self):
        """計算每日新舊題分配與累積進度，回傳每日進度列表和總天數"""
        total_questions = len(self.data)
        already_reviewed = len(self.data[self.data['review_count'] > 0])
        remaining_questions = total_questions - already_reviewed
        if remaining_questions <= 0:
            return [], 0

        new_questions_total = len(self.data[self.data['review_count'] == 0])
        old_questions_total = total_questions - new_questions_total

        cum_new_done = 0
        cum_old_done = 0
        simulated_days = 0
        daily_progress = []

        while cum_new_done + cum_old_done < remaining_questions:
            simulated_days += 1
            today_new = min(self.daily_new_quota, new_questions_total - cum_new_done)
            today_old = min(self.daily_max_quota - today_new, old_questions_total - cum_old_done)

            # 確保不超過剩餘題目
            total_done_today = min(today_new + today_old, remaining_questions - (cum_new_done + cum_old_done))
            if total_done_today < today_new + today_old:
                scale = total_done_today / (today_new + today_old) if today_new + today_old > 0 else 0
                today_new = int(today_new * scale)
                today_old = total_done_today - today_new

            cum_new_done += today_new
            cum_old_done += today_old

            percent_done = (cum_new_done + cum_old_done) / remaining_questions
            daily_progress.append({
                "day": simulated_days,
                "cum_new_done": cum_new_done,
                "cum_old_done": cum_old_done,
                "new_total": new_questions_total,
                "old_total": old_questions_total,
                "percent_done": percent_done,
            })

        total_days_needed = simulated_days
        for day in daily_progress:
            day['remaining_days_est'] = max(total_days_needed - day['day'], 0)

        return daily_progress, total_days_needed


    def animate_day_progress(self, prev_percent, day_info, steps=10, delay=0.05):
        """平滑動畫顯示單日進度條"""
        for step in range(1, steps + 1):
            smooth_percent = prev_percent + (day_info['percent_done'] - prev_percent) * (step / steps)
            self.display_progress_bar(
                smooth_percent,
                day_info['cum_new_done'],
                day_info['new_total'],
                day_info['cum_old_done'],
                day_info['old_total'],
                day_info['remaining_days_est']
            )
            time.sleep(delay)

    def display_progress_bar(self, percent, cum_new_done, new_total, cum_old_done, old_total, remaining_days_est):
        """顯示彩色血量條，並平滑更新"""
        bar_length = 30
        filled_length = int(bar_length * percent)
        empty_length = bar_length - filled_length

        # 根據進度百分比決定顏色
        if percent < 0.3:
            color = Fore.RED
        elif percent < 0.7:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN

        bar = '█' * filled_length + '░' * empty_length
        print(f"\r{color}[{bar}] {percent*100:6.2f}% "
            f"(新題 {cum_new_done}/{new_total}, 舊題 {cum_old_done}/{old_total}) "
            f"剩餘天數: {remaining_days_est}{Style.RESET_ALL}", end='', flush=True)


    def simulate_coverage_interactive(self):
        """互動式模擬每日覆蓋率，SRP 版彩色血量條和平滑動畫"""
        daily_progress, total_days_needed = self.calculate_daily_progress()
        if not daily_progress:
            print("所有單字已覆蓋完成！")
            return

        print(f"\n總單字: {len(self.data)}, 每日總題數: {self.daily_max_quota}, 每日新題: {self.daily_new_quota}")
        print(f"模擬總共需要天數: {total_days_needed}\n")

        for i, day_info in enumerate(daily_progress):
            prev_percent = 0 if i == 0 else daily_progress[i-1]['percent_done']
            self.animate_day_progress(prev_percent, day_info)

        # 確保最後顯示 100% 和剩餘天數 0
        last_day = daily_progress[-1]
        self.display_progress_bar(
            1.0,
            last_day['cum_new_done'],
            last_day['new_total'],
            last_day['cum_old_done'],
            last_day['old_total'],
            0
        )
        print("\n模擬完成！")


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
    
    def filter_available_questions(self, required_columns):
        """篩選出可用題目，包括新題與舊題"""
        filtered_data = self.data.dropna(subset=required_columns)
        if filtered_data.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        new_questions = filtered_data[
            (filtered_data['review_count'] == 0) & (filtered_data['last_reviewed'] == '')
        ]
        old_questions = filtered_data.drop(new_questions.index)
        return new_questions, old_questions
    
    def choose_priority_question(self, old_questions):
        """計算 priority 並直接根據權重抽題"""
        if old_questions.empty:
            return None
        
        now = datetime.now()
        indices, priorities = [], []

        for idx, row in old_questions.iterrows():
            review_count = row['review_count']
            overdue_days = 0
            next_review_str = row['next_review_date']
            if next_review_str:
                try:
                    next_review = datetime.strptime(next_review_str, '%Y-%m-%d %H:%M:%S')
                    if next_review <= now:
                        overdue_days = (now - next_review).days
                except:
                    pass
            is_new = 1 if review_count == 0 and not row['last_reviewed'] else 0
            priority = (review_count * 80) + (overdue_days * 20) + (is_new * 50)

            indices.append(idx)
            priorities.append(priority)

        if not indices:
            return None

        weights = np.array(priorities, dtype=float)
        weights /= weights.sum()

        chosen_index = np.random.choice(indices, p=weights)
        chosen_row = self.data.loc[chosen_index].copy()
        chosen_row['overdue_days'] = next((row for i, row in zip(indices, priorities) if i == chosen_index), 0)
        chosen_row['is_burst'] = self.burst_mode
        return chosen_row

    def get_priority_question(self, required_columns):
        """根據每日配額與 priority 抽出下一題"""
        # 1. 篩選可用題目
        new_questions, old_questions = self.filter_available_questions(required_columns)

        # 2. 檢查每日最大配額
        daily_answered = self.get_daily_answered_count()
        if not self.burst_mode and daily_answered >= self.daily_max_quota:
            print(f"\n達到每日最大複習配額 ({self.daily_max_quota} 題)，請明天再繼續練習。")
            return None

        remaining_new_quota = max(0, self.daily_max_quota - daily_answered)

        # 3. 優先抽新題（每日新題配額）
        if remaining_new_quota > 0 and not new_questions.empty:
            chosen_row = new_questions.sample(n=1).iloc[0]
            chosen_row['is_burst'] = self.burst_mode
            return chosen_row

        # 4. 抽舊題（根據 priority 權重）
        if old_questions.empty:
            return None

        now = datetime.now()
        indices, priorities, overdue_days_list = [], [], []

        for idx, row in old_questions.iterrows():
            review_count = row['review_count']
            overdue_days = 0
            next_review_str = row['next_review_date']

            if next_review_str:
                try:
                    next_review = datetime.strptime(next_review_str, '%Y-%m-%d %H:%M:%S')
                    if next_review <= now:
                        overdue_days = (now - next_review).days
                except:
                    pass

            is_new = 1 if review_count == 0 and not row['last_reviewed'] else 0
            priority = (review_count * 80) + (overdue_days * 20) + (is_new * 50)

            indices.append(idx)
            priorities.append(priority)
            overdue_days_list.append(overdue_days)

        # 權重抽題
        weights = np.array(priorities, dtype=float)
        weights /= weights.sum()
        chosen_index = np.random.choice(indices, p=weights)

        chosen_row = self.data.loc[chosen_index].copy()
        chosen_row['overdue_days'] = overdue_days_list[indices.index(chosen_index)]
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
                overdue_bonus = 1 + 0.5 * (overdue_days / last_interval)
                overdue_bonus = min(overdue_bonus, 1.3)

                new_interval = last_interval * ef * overdue_bonus
                new_interval = min(new_interval, last_interval * 2)

        return round(new_interval), ef


    def exact_match(self, user_input, correct_answer):
        # 完全相同（忽略大小寫與空白）
        if not isinstance(user_input, str) or not isinstance(correct_answer, str):
            return False
        return user_input.strip().lower() == correct_answer.strip().lower()

    def partial_match(self, user_input, correct_answer):
        # 簡單示範：判斷 user_input 中是否包含正確答案的任意關鍵字
        if not isinstance(user_input, str) or not isinstance(correct_answer, str):
            return False
        # 將 correct_answer 以空白拆分成關鍵字
        keywords = correct_answer.strip().lower().split()
        user_input_lower = user_input.strip().lower()
        # 至少包含一個關鍵字就算部分正確
        return any(kw in user_input_lower for kw in keywords)

    def calculate_quality(self, user_input, question, answer_key, elapsed_time):
        time_limit = self.time_limit
        penalty_rate = 0.5

        if self.exact_match(user_input, question[answer_key]):
            accuracy_score = 1.0
        elif self.fuzzy_match(user_input, question[answer_key]):
            accuracy_score = 0.7
        elif self.partial_match(user_input, question[answer_key]):
            accuracy_score = 0.4
        else:
            accuracy_score = 0.0

        time_ratio = elapsed_time / max(time_limit, 0.1)
        time_penalty = max(0.5, 1 - time_ratio * penalty_rate)

        raw_quality = accuracy_score * time_penalty * 5
        quality = max(1, round(raw_quality))  # 強制下限 1 分
        return quality


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
        """主流程：呼叫各個子功能，負責整體問答流程"""
        elapsed_time, timeout, user_input = self.handle_user_input(hint)
        self.evaluate_answer(question, answer_key, user_input, elapsed_time, timeout)
        self.update_sm2(question, answer_key, user_input, elapsed_time)
        self.display_question_result(question, answer_key, timeout)


    def handle_user_input(self, hint):
        """負責輸入與倒數計時管理"""
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
                print(f"\n{Fore.RED}時間到！{Style.RESET_ALL}")

        thread = threading.Thread(target=countdown)
        thread.start()

        try:
            user_input = input("\n請輸入答案：")
            user_input_received[0] = True
        except Exception:
            user_input = None

        thread.join()
        return elapsed_time, timeout, user_input


    def evaluate_answer(self, question, answer_key, user_input, elapsed_time, timeout):
        """負責計算分數、答題正確性與負荷更新"""
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
            print(f"{Fore.RED}錯誤！{Style.RESET_ALL}")

        self.display_load_bar()
        self.display_progress()


    def update_sm2(self, question, answer_key, user_input, elapsed_time):
        """負責 SM-2 間隔計算與更新資料"""
        index = question.name
        overdue_days = question.get('overdue_days', 0)
        last_interval = self.data.loc[index, 'review_interval']
        ef = self.data.loc[index, 'ease_factor']

        quality = self.calculate_quality(user_input, question, answer_key, elapsed_time)
        new_interval, new_ef = self.calculate_next_review_date(last_interval, ef, quality, overdue_days)

        self.data.loc[index, 'review_interval'] = new_interval
        self.data.loc[index, 'ease_factor'] = new_ef
        self.data.loc[index, 'next_review_date'] = (datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d %H:%M:%S')
        self.data.loc[index, 'last_reviewed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.data.loc[index, 'total_reviews'] += 1


    def display_question_result(self, question, answer_key, timeout):
        """負責顯示題目結果與相關訊息"""
        index = question.name
        difficulty_level = "簡單" if self.data.loc[index, 'review_count'] == 0 else "中等" if self.data.loc[index, 'review_count'] <= 2 else "困難"
        print(f"難度等級: {difficulty_level} (錯誤次數: {self.data.loc[index, 'review_count']})")
        print(f"下次複習: {self.data.loc[index, 'next_review_date']} ({self.data.loc[index, 'review_interval']} 天後)")
        if self.data.loc[index, 'consecutive_correct'] > 0:
            print(f"連續答對: {self.data.loc[index, 'consecutive_correct']} 次")

        

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

    def get_today_visited_count(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        visited_today = self.data[self.data['last_reviewed'].str.startswith(today_str)]
        return len(visited_today)

    def show_statistics(self):
        print(f"\n=== 學習統計 ===")
        total_questions = len(self.data)
        reviewed_questions = len(self.data[self.data['total_reviews'] > 0])
        today_visited = self.get_today_visited_count()

        print(f"總題目數: {total_questions}")
        print(f"已複習題目 (不同題目數): {reviewed_questions}")
        print(f"複習進度: {reviewed_questions / total_questions * 100:.1f}%")
        print(f"今日練習題數: {today_visited}")

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
            print("s: 模擬每日覆蓋率 (動畫版)")
            print("c: 設定每日題數與新單字配額")
            print("q: 退出測試")

            user_choice = input("請輸入選項 (1/2/3/4/s/c/q)：").strip().lower()

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
            elif user_choice.lower() == "c":
                self.configure_daily_quota()
            elif user_choice.lower() == "s":
                self.simulate_coverage_interactive()
            else:
                print("\n無效選項，請重試。")

if __name__ == "__main__":
    filename = "voc.xlsx"
    try:
        data = pd.read_excel(filename)
    except FileNotFoundError:
        print("錯誤：未找到 'voc.xlsx' 文件。")
        exit()

    app = QuizApp(time_limit=5, data=data, filename=filename)
    app.run_quiz()

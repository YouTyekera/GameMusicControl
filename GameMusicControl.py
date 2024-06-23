import psutil
import time
import pygame
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw
import pystray
import json
import os
import requests

def check_for_update(current_version):
    repo_owner = "YouTyekera"
    repo_name = "GameMusicControl"
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    response = requests.get(url)
    latest_release = response.json()
    print(latest_release)  # レスポンス内容を出力

    latest_version = latest_release.get("tag_name")
    if not latest_version:
        print("No tag_name found in the latest release.")
        return

    if latest_version != current_version:
        print("A new version is available!")
        # Notify the user about the update and provide the download link
        # You can also implement an auto-update feature here

current_version = "1.0"
check_for_update(current_version)

# 設定ファイルのパス
CONFIG_FILE = "config.json"

# 設定を読み込む関数
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"games": [], "volume": 50}

# 設定を保存する関数
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# 初期設定の読み込み
config = load_config()

# 必要なキーが存在しない場合はデフォルト値を設定
if "games" not in config:
    config["games"] = []
if "volume" not in config:
    config["volume"] = 50

# undo用のスタック
undo_stack = []

# pygameを初期化
pygame.mixer.init()

def is_game_running(process_name):
    """指定したプロセス名が部分一致するプロセスが実行中かどうかを確認する関数"""
    for proc in psutil.process_iter(['name']):
        if process_name.lower() in proc.info['name'].lower():
            return True
    return False

def play_music(file_path):
    """指定した音楽ファイルを再生する関数"""
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play(-1)  # 繰り返し再生

def stop_music():
    """音楽再生を停止する関数"""
    pygame.mixer.music.stop()

def set_volume(val):
    """音量を設定する関数"""
    volume = float(val) / 100
    pygame.mixer.music.set_volume(volume)

def main():
    music_playing = False
    current_game = None
    while True:
        for game in config["games"]:
            if is_game_running(game["process_name"]):
                if not music_playing or current_game != game["process_name"]:
                    print(f"{game['process_name']} is running! Playing music...")
                    play_music(game["music_file"])
                    music_playing = True
                    current_game = game["process_name"]
                break
        else:
            if music_playing:
                print(f"{current_game} has stopped. Stopping music...")
                stop_music()
                music_playing = False
                current_game = None
        # 10秒ごとにチェック
        time.sleep(10)

def start_monitor():
    # モニタリングを別スレッドで実行する
    import threading
    thread = threading.Thread(target=main)
    thread.daemon = True
    thread.start()

def quit_program(icon, item):
    icon.stop()
    root.quit()

def create_image():
    # 32x32のイメージを作成
    image = Image.new('RGB', (32, 32), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.rectangle((0, 0, 32, 32), fill=(0, 0, 0))
    return image

def setup_tray_icon():
    icon = pystray.Icon("game_music_control")
    icon.icon = create_image()
    icon.menu = pystray.Menu(
        pystray.MenuItem("Quit", quit_program)
    )
    icon.run()

def browse_music_file():
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
    if file_path:
        music_file_entry.delete(0, tk.END)
        music_file_entry.insert(0, file_path)

def browse_game_file():
    file_path = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe")])
    if file_path:
        game_process_entry.delete(0, tk.END)
        game_process_entry.insert(0, os.path.basename(file_path))

def add_game():
    game_process_name = game_process_entry.get()
    music_file = music_file_entry.get()
    if game_process_name and music_file:
        config["games"].append({"process_name": game_process_name, "music_file": music_file})
        save_config(config)
        update_game_list()
        game_process_entry.delete(0, tk.END)
        music_file_entry.delete(0, tk.END)
    else:
        messagebox.showwarning("Input Error", "Please provide both game process name and music file.")

def remove_game(event=None):
    selected_index = game_listbox.curselection()
    if selected_index:
        removed_game = config["games"].pop(selected_index[0])
        undo_stack.append(removed_game)
        save_config(config)
        update_game_list()
    else:
        messagebox.showwarning("Selection Error", "Please select a game to remove.")

def undo_remove(event=None):
    if undo_stack:
        restored_game = undo_stack.pop()
        config["games"].append(restored_game)
        save_config(config)
        update_game_list()
    else:
        messagebox.showinfo("Undo", "No actions to undo.")

def update_game_list():
    game_listbox.delete(0, tk.END)
    for game in config["games"]:
        game_listbox.insert(tk.END, f"{game['process_name']} - {game['music_file']}")

def save_settings():
    config["volume"] = volume_scale.get()
    save_config(config)
    set_volume(config["volume"])
    messagebox.showinfo("Settings", "Settings saved successfully!")

# GUIの設定
root = tk.Tk()
root.title("Game Music Control")
root.geometry("600x400")

settings_frame = ttk.Frame(root, padding="10")
settings_frame.pack(fill="both", expand=True)

ttk.Label(settings_frame, text="Game Process Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
game_process_entry = ttk.Entry(settings_frame, width=30)
game_process_entry.grid(row=0, column=1, padx=5, pady=5)
ttk.Button(settings_frame, text="Browse", command=browse_game_file).grid(row=0, column=2, padx=5, pady=5)

ttk.Label(settings_frame, text="Music File:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
music_file_entry = ttk.Entry(settings_frame, width=30)
music_file_entry.grid(row=1, column=1, padx=5, pady=5)
ttk.Button(settings_frame, text="Browse", command=browse_music_file).grid(row=1, column=2, padx=5, pady=5)

ttk.Button(settings_frame, text="Add Game", command=add_game).grid(row=2, column=0, columnspan=3, pady=10)

ttk.Label(settings_frame, text="Games and Music:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
game_listbox = tk.Listbox(settings_frame, height=10, width=50)
game_listbox.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="we")
game_listbox.bind("<Button-3>", remove_game)  # 右クリックで削除
ttk.Button(settings_frame, text="Remove Selected", command=remove_game).grid(row=4, column=2, padx=5, pady=5)

ttk.Label(settings_frame, text="Volume:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
volume_scale = ttk.Scale(settings_frame, from_=0, to=100, orient='horizontal', command=set_volume)
volume_scale.set(config["volume"])
volume_scale.grid(row=5, column=1, padx=5, pady=5)

ttk.Button(settings_frame, text="Save Settings", command=save_settings).grid(row=6, column=0, columnspan=3, pady=10)

root.bind("<Control-z>", undo_remove)  # Ctrl+Zで削除を元に戻す

update_game_list()
start_monitor()

# トレイアイコンを設定
import threading
tray_thread = threading.Thread(target=setup_tray_icon)
tray_thread.daemon = True
tray_thread.start()

root.mainloop()

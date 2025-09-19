# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import threading
import queue
from pathlib import Path
import json
import re
import shutil
from typing import Dict
from pytubefix import Playlist, YouTube

from mod_generator import HOI4MusicModGenerator

class HOI4MusicGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HOI4 음악 모드 생성기")
        self.root.geometry("850x800")
        
        self.stations: Dict[str, Dict] = {}
        self.current_station_name = tk.StringVar(value="my_station")
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "my_station_mod"))
        self.album_art_path = tk.StringVar()
        self.message_queue = queue.Queue()
        self.zip_mod = tk.BooleanVar(value=False)
        self.editing_song_id = None
        
        self.create_widgets()
        self.check_queue()
        
        self.add_new_station(initial_name="my_station")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        settings_frame = ttk.LabelFrame(main_frame, text="모드 설정", padding="10")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(settings_frame, text="출력 디렉토리:").grid(row=0, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(settings_frame, textvariable=self.output_dir, width=50).grid(row=0, column=1, padx=(10, 0), pady=(5, 0), sticky=tk.W)
        ttk.Button(settings_frame, text="기존 모드 불러오기", command=self.load_existing_mod).grid(row=0, column=2, padx=(5, 0))

        station_frame = ttk.LabelFrame(main_frame, text="스테이션 관리", padding="10")
        station_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(station_frame, text="현재 스테이션:").grid(row=0, column=0, sticky=tk.W)
        self.station_combo = ttk.Combobox(station_frame, textvariable=self.current_station_name, state='readonly')
        self.station_combo.grid(row=0, column=1, padx=(10, 0), sticky=(tk.W, tk.E))
        self.station_combo.bind("<<ComboboxSelected>>", self.on_station_change)

        ttk.Button(station_frame, text="새 스테이션 추가", command=self.add_new_station).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(station_frame, text="현재 스테이션 삭제", command=self.delete_current_station).grid(row=0, column=3, padx=(5, 0))
        station_frame.columnconfigure(1, weight=1)

        album_frame = ttk.LabelFrame(main_frame, text="앨범 아트 (현재 스테이션)", padding="10")
        album_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(album_frame, text="이미지 파일:").grid(row=0, column=0, sticky=tk.W)
        self.album_art_entry = ttk.Entry(album_frame, textvariable=self.album_art_path, width=40, state='readonly')
        self.album_art_entry.grid(row=0, column=1, padx=(10, 0), sticky=(tk.W, tk.E))
        ttk.Button(album_frame, text="찾아보기", command=self.browse_album_art).grid(row=0, column=2, padx=(5, 0))
        info_label = ttk.Label(album_frame, text="💡 템플릿 파일(radio_station_cover_template.png)이 현재 폴더에 있어야 합니다.", font=('TkDefaultFont', 8), foreground='blue')
        info_label.grid(row=2, column=0, columnspan=3, sticky=tk.W)
        
        add_song_frame = ttk.LabelFrame(main_frame, text="곡 추가/수정", padding="10")
        add_song_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        song_list_frame = ttk.LabelFrame(main_frame, text="곡 목록", padding="10")
        song_list_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        generate_frame = ttk.Frame(main_frame)
        generate_frame.grid(row=5, column=0, columnspan=2, pady=(0, 10))
        self.generate_btn = ttk.Button(generate_frame, text="모드 생성 시작", command=self.generate_mod)
        self.generate_btn.grid(row=0, column=0, padx=(0, 10))
        ttk.Checkbutton(generate_frame, text="모드 생성 후 압축하기", variable=self.zip_mod).grid(row=0, column=1, padx=(0, 10))
        self.progress_bar = ttk.Progressbar(generate_frame, mode='indeterminate')
        
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="10")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=12)
        
        self.setup_full_widgets(main_frame, settings_frame, album_frame, add_song_frame, song_list_frame, generate_frame, log_frame)

    def setup_full_widgets(self, main_frame, settings_frame, album_frame, add_song_frame, song_list_frame, generate_frame, log_frame):
        ttk.Label(add_song_frame, text="URL/경로:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(add_song_frame, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=3, padx=(10, 0), sticky=(tk.W, tk.E))
        ttk.Label(add_song_frame, text="한글명:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.korean_name_entry = ttk.Entry(add_song_frame, width=20)
        self.korean_name_entry.grid(row=1, column=1, padx=(10, 0), pady=(5, 0), sticky=(tk.W, tk.E))
        ttk.Label(add_song_frame, text="영어명:").grid(row=1, column=2, sticky=tk.W, pady=(5, 0), padx=(10, 0))
        self.english_name_entry = ttk.Entry(add_song_frame, width=20)
        self.english_name_entry.grid(row=1, column=3, padx=(10, 0), pady=(5, 0), sticky=(tk.W, tk.E))
        ttk.Label(add_song_frame, text="시작 자르기(초):").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.trim_start_entry = ttk.Entry(add_song_frame, width=10)
        self.trim_start_entry.insert(0, "0")
        self.trim_start_entry.grid(row=2, column=1, sticky=tk.W, padx=(10,0), pady=(5,0))
        ttk.Label(add_song_frame, text="볼륨(0.0~1.5):").grid(row=2, column=2, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        self.volume_entry = ttk.Entry(add_song_frame, width=10)
        self.volume_entry.insert(0, "0.8")
        self.volume_entry.grid(row=2, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        
        ttk.Label(add_song_frame, text="가중치(기본값:1):").grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        self.weight_entry = ttk.Entry(add_song_frame, width=10)
        self.weight_entry.insert(0, "1")
        self.weight_entry.grid(row=3, column=1, sticky=tk.W, padx=(10,0), pady=(5,0))

        self.add_update_btn = ttk.Button(add_song_frame, text="곡 추가", command=self.add_or_update_song)
        self.add_update_btn.grid(row=4, column=3, padx=(10, 0), pady=(10, 0), sticky=tk.E)

        file_io_frame = ttk.Frame(add_song_frame)
        file_io_frame.grid(row=5, column=0, columnspan=4, pady=(10, 0), sticky=tk.W)
        ttk.Button(file_io_frame, text="목록 불러오기", command=self.load_song_list).grid(row=0, column=0)
        ttk.Button(file_io_frame, text="목록 내보내기", command=self.export_song_list).grid(row=0, column=1, padx=(10,0))
        ttk.Button(file_io_frame, text="선택 해제", command=self.clear_selection).grid(row=0, column=2, padx=(10,0))
        
        columns = ('korean', 'english', 'url', 'trim', 'volume', 'weight')
        self.song_tree = ttk.Treeview(song_list_frame, columns=columns, show='headings', height=6)
        self.song_tree.heading('korean', text='한글명'); self.song_tree.heading('english', text='영어명'); self.song_tree.heading('url', text='URL / 파일 경로'); self.song_tree.heading('trim', text='자르기(초)'); self.song_tree.heading('volume', text='볼륨'); self.song_tree.heading('weight', text='가중치')
        self.song_tree.column('korean', width=150); self.song_tree.column('english', width=150); self.song_tree.column('url', width=250); self.song_tree.column('trim', width=60, anchor=tk.CENTER); self.song_tree.column('volume', width=60, anchor=tk.CENTER); self.song_tree.column('weight', width=60, anchor=tk.CENTER)
        self.song_tree.bind("<<TreeviewSelect>>", self.on_song_select)
        scrollbar = ttk.Scrollbar(song_list_frame, orient=tk.VERTICAL, command=self.song_tree.yview)
        self.song_tree.configure(yscroll=scrollbar.set)
        self.song_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)); scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        song_buttons_frame = ttk.Frame(song_list_frame)
        song_buttons_frame.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        ttk.Button(song_buttons_frame, text="선택된 곡 삭제", command=self.remove_song).pack(side=tk.LEFT)
        ttk.Button(song_buttons_frame, text="▲ 위로", command=self.move_song_up).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(song_buttons_frame, text="▼ 아래로", command=self.move_song_down).pack(side=tk.LEFT, padx=(5, 0))

        self.progress_bar.grid(row=0, column=2, padx=(10, 0), sticky=(tk.W, tk.E))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1); self.root.rowconfigure(0, weight=1); main_frame.columnconfigure(1, weight=1); main_frame.rowconfigure(4, weight=1); main_frame.rowconfigure(6, weight=1)
        settings_frame.columnconfigure(1, weight=1); album_frame.columnconfigure(1, weight=1); add_song_frame.columnconfigure(1, weight=1); add_song_frame.columnconfigure(3, weight=1)
        song_list_frame.columnconfigure(0, weight=1); song_list_frame.rowconfigure(0, weight=1); log_frame.columnconfigure(0, weight=1); log_frame.rowconfigure(0, weight=1); generate_frame.columnconfigure(1, weight=1)

    def add_new_station(self, initial_name=None):
        if initial_name:
            new_name = initial_name
        else:
            new_name = simpledialog.askstring("새 스테이션 이름", "새 스테이션의 이름을 입력하세요:")

        if new_name:
            sanitized_name = HOI4MusicModGenerator.sanitize_station_name(new_name)
            if sanitized_name in self.stations:
                if not initial_name:
                    messagebox.showwarning("경고", "이미 존재하는 스테이션 이름입니다. 다른 이름을 사용해주세요.")
                return
            
            self.stations[sanitized_name] = {"songs": [], "album_art": ""}
            self.current_station_name.set(sanitized_name)
            self.update_station_list()
            self.on_station_change()
            self.log(f"✅ 새 스테이션 '{sanitized_name}' 추가됨.")

    def on_song_select(self, event):
        selected_items = self.song_tree.selection()
        if not selected_items: return

        self.editing_song_id = selected_items[0]
        
        current_station = self.current_station_name.get()
        songs_list = self.stations.get(current_station, {}).get("songs", [])
        try:
            index = self.song_tree.index(self.editing_song_id)
            song_data = songs_list[index]
        except (ValueError, IndexError):
            self.clear_selection()
            return

        self.url_entry.delete(0, tk.END); self.url_entry.insert(0, song_data.get('url', ''))
        self.korean_name_entry.delete(0, tk.END); self.korean_name_entry.insert(0, song_data.get('korean_name', ''))
        self.english_name_entry.delete(0, tk.END); self.english_name_entry.insert(0, song_data.get('english_name', ''))
        self.trim_start_entry.delete(0, tk.END); self.trim_start_entry.insert(0, str(song_data.get('trim_start', 0)))
        self.volume_entry.delete(0, tk.END); self.volume_entry.insert(0, str(song_data.get('volume', 0.8)))
        self.weight_entry.delete(0, tk.END); self.weight_entry.insert(0, str(song_data.get('weight', 1)))

        self.add_update_btn.config(text="곡 정보 업데이트")

    def clear_selection(self):
        if self.song_tree.selection():
            self.song_tree.selection_remove(self.song_tree.selection())
        self.editing_song_id = None
        self.url_entry.delete(0, tk.END)
        self.korean_name_entry.delete(0, tk.END)
        self.english_name_entry.delete(0, tk.END)
        self.trim_start_entry.delete(0, tk.END); self.trim_start_entry.insert(0, "0")
        self.volume_entry.delete(0, tk.END); self.volume_entry.insert(0, "0.8")
        self.weight_entry.delete(0, tk.END); self.weight_entry.insert(0, "1")
        self.add_update_btn.config(text="곡 추가")

    def delete_current_station(self):
        current_name = self.current_station_name.get()
        if not current_name or len(self.stations) <= 1:
            messagebox.showwarning("경고", "마지막 스테이션은 삭제할 수 없습니다.")
            return

        if messagebox.askyesno("삭제 확인", f"스테이션 '{current_name}'과(와) 모든 곡 목록을 삭제하시겠습니까? (파일은 삭제되지 않습니다.)"):
            del self.stations[current_name]
            self.update_station_list()
            first_station = list(self.stations.keys())[0]
            self.current_station_name.set(first_station)
            self.on_station_change()
            self.log(f"🗑️ 스테이션 '{current_name}'이(가) 삭제되었습니다.")
    
    def update_station_list(self):
        self.station_combo['values'] = list(self.stations.keys())
    
    def on_station_change(self, event=None):
        current_name = self.current_station_name.get()
        if current_name in self.stations:
            album_art = self.stations[current_name].get("album_art", "")
            self.album_art_path.set(album_art)

        self.update_song_tree()
        self.log(f"현재 스테이션이 '{current_name}'(으)로 변경되었습니다.")
    
    def load_existing_mod(self):
        mod_path_str = filedialog.askdirectory(title="기존 HOI4 모드 폴더를 선택하세요")
        if not mod_path_str:
            return
        
        mod_path = Path(mod_path_str)
        song_data_path = mod_path / "mod_data.json"
        
        if not song_data_path.exists():
            messagebox.showwarning("불러오기 실패", f"선택한 폴더에 'mod_data.json' 파일이 없습니다.\n이 프로그램으로 생성한 모드가 맞는지 확인해주세요.")
            return

        try:
            with open(song_data_path, 'r', encoding='utf-8') as f:
                mod_data = json.load(f)

            loaded_stations = mod_data.get('stations', {})
            
            for station_name, station_data in loaded_stations.items():
                if not isinstance(station_data.get("songs"), list):
                    self.log(f"⚠️ 스테이션 '{station_name}'의 곡 목록 형식이 잘못되어 리스트로 변환합니다.")
                    station_data["songs"] = []

            self.stations = loaded_stations
            if not self.stations:
                 raise Exception("모드 데이터에 스테이션 정보가 없습니다.")

            first_station = list(self.stations.keys())[0]
            self.current_station_name.set(first_station)
            
            self.output_dir.set(str(mod_path.resolve()))
            
            self.on_station_change() 
            self.update_station_list()

            self.log(f"✅ 기존 모드 정보를 성공적으로 불러왔습니다.")
            self.log(f"   - 총 {len(self.stations)}개의 스테이션.")
            
            messagebox.showinfo("성공", "기존 모드 정보를 성공적으로 불러왔습니다.\n이제 곡을 추가하거나 삭제한 후 '모드 생성 시작'을 눌러주세요.")

        except Exception as e:
            messagebox.showerror("오류", f"모드 정보를 불러오는 중 오류가 발생했습니다: {e}")
            self.log(f"❌ 모드 불러오기 실패: {e}")

    def browse_album_art(self):
        current_station = self.current_station_name.get()
        if not current_station:
            messagebox.showwarning("경고", "먼저 스테이션을 선택해주세요.")
            return

        file_path = filedialog.askopenfilename(
            title="앨범 아트 이미지 선택",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff")]
        )
        if file_path:
            self.album_art_path.set(file_path)
            self.stations[current_station]['album_art'] = file_path
            self.log(f"스테이션 '{current_station}'의 앨범 아트 선택됨: {file_path}")
    
    def add_or_update_song(self):
        current_station = self.current_station_name.get()
        if not current_station:
            messagebox.showwarning("경고", "스테이션을 먼저 추가하거나 선택해주세요.")
            return

        url_or_path = self.url_entry.get().strip()
        if not url_or_path:
            messagebox.showwarning("입력 오류", "YouTube URL 또는 로컬 파일 경로를 입력해야 합니다.")
            return

        if not self.editing_song_id and "list=" in url_or_path and not Path(url_or_path).is_file():
            if messagebox.askyesno("재생목록 확인", "YouTube 재생목록이 감지되었습니다. 목록의 모든 곡을 추가하시겠습니까?"):
                thread = threading.Thread(target=self.add_playlist_songs_thread, args=(url_or_path, current_station))
                thread.daemon = True
                thread.start()
            return

        is_local_file = Path(url_or_path).is_file()

        korean_name = self.korean_name_entry.get().strip()
        english_name = self.english_name_entry.get().strip()

        if is_local_file and not (korean_name and english_name):
            filename = Path(url_or_path).stem
            korean_name = korean_name or filename
            english_name = english_name or filename

        if not (korean_name and english_name):
            messagebox.showwarning("입력 오류", "한글명과 영어명을 모두 입력해야 합니다.")
            return

        try:
            trim_start = int(self.trim_start_entry.get() or 0)
            volume = float(self.volume_entry.get() or 0.8)
            weight = int(self.weight_entry.get() or 1)
            if not (0.0 <= volume <= 1.5):
                raise ValueError("볼륨 값은 0.0과 1.5 사이여야 합니다.")
        except ValueError as e:
            messagebox.showwarning("입력 오류", f"숫자 입력이 잘못되었습니다: {e}")
            return

        song_info = {
            'url': url_or_path,
            'korean_name': korean_name,
            'english_name': english_name,
            'trim_start': trim_start,
            'volume': volume,
            'weight': weight,
            'source': 'local' if is_local_file else 'youtube'
        }

        songs_list = self.stations[current_station]["songs"]
        if self.editing_song_id:
            try:
                index = self.song_tree.index(self.editing_song_id)
                original_song = songs_list[index]
                song_info['name'] = original_song.get('name')
                song_info['file_path'] = original_song.get('file_path')
                songs_list[index] = song_info
                self.log(f"곡 정보가 업데이트되었습니다: {korean_name}")
            except (ValueError, IndexError):
                 self.log(f"❌ 곡 업데이트 중 오류 발생. 목록을 다시 확인해주세요.")
        else:
            songs_list.append(song_info)
            self.log(f"곡이 현재 스테이션에 추가되었습니다: {url_or_path}")

        self.update_song_tree()
        self.clear_selection()

    def update_song_tree(self):
        for i in self.song_tree.get_children(): self.song_tree.delete(i)
        current_station = self.current_station_name.get()
        
        songs = self.stations.get(current_station, {}).get("songs", [])
        
        for song in songs:
            self.song_tree.insert('', 'end', values=(
                song.get('korean_name', ''),
                song.get('english_name', ''),
                song.get('url', ''),
                song.get('trim_start', 0),
                song.get('volume', 0.8),
                song.get('weight', 1)
            ))
    
    def remove_song(self):
        selected_items = self.song_tree.selection()
        if not selected_items: return
        if messagebox.askyesno("삭제 확인", f"선택한 {len(selected_items)}개의 곡을 삭제하시겠습니까?"):
            current_station = self.current_station_name.get()
            songs_list = self.stations.get(current_station, {}).get("songs", [])
            selected_indices = sorted([self.song_tree.index(i) for i in selected_items], reverse=True)
            for index in selected_indices:
                del songs_list[index]
            self.stations[current_station]["songs"] = songs_list
            self.update_song_tree()
            self.clear_selection()
            self.log(f"{len(selected_items)}개의 곡이 삭제되었습니다.")

    def move_song_up(self):
        selected_items = self.song_tree.selection()
        if not selected_items: return

        current_station = self.current_station_name.get()
        songs_list = self.stations.get(current_station, {}).get("songs", [])
        
        selected_indices = sorted([self.song_tree.index(i) for i in selected_items])

        new_selection_indices = []
        for index in selected_indices:
            if index > 0:
                songs_list.insert(index - 1, songs_list.pop(index))
                new_selection_indices.append(index - 1)
            else:
                new_selection_indices.append(index)

        self.update_song_tree()

        for i in new_selection_indices:
            self.song_tree.selection_add(self.song_tree.get_children()[i])

    def move_song_down(self):
        selected_items = self.song_tree.selection()
        if not selected_items: return

        current_station = self.current_station_name.get()
        songs_list = self.stations.get(current_station, {}).get("songs", [])

        selected_indices = sorted([self.song_tree.index(i) for i in selected_items], reverse=True)

        new_selection_indices = []
        for index in selected_indices:
            if index < len(songs_list) - 1:
                songs_list.insert(index + 1, songs_list.pop(index))
                new_selection_indices.append(index + 1)
            else:
                new_selection_indices.append(index)

        self.update_song_tree()
        
        for i in new_selection_indices:
            self.song_tree.selection_add(self.song_tree.get_children()[i])

    def export_song_list(self):
        current_station = self.current_station_name.get()
        songs = self.stations.get(current_station, {}).get("songs", [])
        if not songs: return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(songs, f, ensure_ascii=False, indent=2)
            self.log(f"곡 목록을 {file_path}에 저장했습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 실패: {e}")

    def load_song_list(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON/TXT", "*.json *.txt")])
        if not file_path: return
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f: loaded_songs = json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f: loaded_songs = self.parse_txt_song_list(f.readlines())
            
            current_station = self.current_station_name.get()
            if not self.stations.get(current_station): self.stations[current_station] = {"songs": [], "album_art": ""}
            
            current_songs = self.stations[current_station]["songs"]
            if current_songs and messagebox.askyesno("불러오기", "현재 목록에 추가하시겠습니까?"):
                self.stations[current_station]["songs"].extend(loaded_songs)
            else:
                self.stations[current_station]["songs"] = loaded_songs
            
            self.update_song_tree()
            self.log(f"파일에서 {len(loaded_songs)}개 곡을 불러왔습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 읽기 실패: {e}")

    def parse_txt_song_list(self, lines):
        parsed_songs = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = [p.strip() for p in line.split('|')]
            song = {'trim_start': 0, 'volume': 0.8, 'weight': 1}
            if len(parts) >= 1: song['url'] = parts[-1]
            if len(parts) >= 2:
                if re.search(r'[가-힣]', parts[0]): song['korean_name'] = parts[0]
                else: song['english_name'] = parts[0]
            if len(parts) >= 3:
                song['korean_name'] = parts[0]; song['english_name'] = parts[1]
            if len(parts) >= 4:
                try: song['trim_start'] = int(parts[3])
                except: pass
            if len(parts) >= 5:
                try: song['volume'] = float(parts[4])
                except: pass
            if len(parts) >= 6:
                try: song['weight'] = int(parts[5])
                except: pass
            if 'url' in song: parsed_songs.append(song)
        return parsed_songs

    def generate_mod(self):
        if not self.stations:
            messagebox.showwarning("경고", "스테이션을 먼저 추가해주세요.")
            return
        output_dir = self.output_dir.get().strip()
        if not output_dir:
            messagebox.showwarning("경고", "출력 디렉토리를 입력해주세요.")
            return
        
        self.generate_btn.config(state='disabled')
        self.progress_bar.start()
        
        thread = threading.Thread(target=self.generate_mod_thread, args=(output_dir,))
        thread.daemon = True
        thread.start()
    
    def generate_mod_thread(self, output_dir):
        try:
            all_songs_generated = True
            
            for station_name, station_data in self.stations.items():
                songs_list = station_data.get("songs", [])
                
                if not songs_list:
                    self.thread_log(f"⚠️ 스테이션 '{station_name}'에 곡이 없어 건너뜁니다.")
                    continue
                
                self.thread_log("\n" + "="*20 + f" '{station_name}' 스테이션 처리 시작 " + "="*20)

                generator = HOI4MusicModGenerator(
                    station_name=station_name,
                    output_dir=output_dir,
                    progress_callback=self.thread_log
                )
                
                album_art_path = station_data.get("album_art", "").strip()
                if album_art_path and Path(album_art_path).exists():
                    generator.process_album_art(album_art_path)
                else:
                    self.thread_log(f"  - 앨범 아트가 지정되지 않았거나 경로가 올바르지 않아 건너뜁니다.")
                
                existing_songs_info = []
                songs_to_download = []
                songs_to_convert = []
                
                output_music_dir = Path(output_dir) / "music" / station_name
                output_music_dir.mkdir(parents=True, exist_ok=True)
                
                for song_info in songs_list:
                    if song_info.get('name'):
                        file_name_base = song_info['name']
                    elif song_info.get('english_name'):
                        file_name_base = re.sub(r'[^a-zA-Z0-9_]', '_', song_info['english_name'].lower().replace(' ', '_')).strip('_')
                    elif song_info.get('korean_name'):
                        file_name_base = generator.sanitize_filename(song_info['korean_name'])
                    else:
                        file_name_base = "unknown_song"

                    ogg_path = output_music_dir / f"{file_name_base}.ogg"
                    
                    if ogg_path.exists():
                        self.thread_log(f"✅ '{song_info.get('korean_name', file_name_base)}' 파일이 이미 존재합니다. 건너뜁니다.")
                        if 'name' not in song_info:
                            song_info['name'] = file_name_base
                            song_info['file_path'] = f"{station_name}/{file_name_base}.ogg"
                        existing_songs_info.append(song_info)
                    elif song_info.get('source') == 'local':
                        songs_to_convert.append(song_info)
                    else:
                        songs_to_download.append(song_info)

                generator.songs = existing_songs_info

                for i, song_info in enumerate(songs_to_convert, 1):
                    self.thread_log(f"\n[{i}/{len(songs_to_convert)}] '{station_name}' 스테이션 로컬 파일 처리 중...")
                    generated_song_info = generator.process_local_song(song_info)
                    if generated_song_info:
                        song_info.update(generated_song_info)
                
                for i, song_info in enumerate(songs_to_download, 1):
                    self.thread_log(f"\n[{i}/{len(songs_to_download)}] '{station_name}' 스테이션 다운로드 처리 중...")
                    generated_song_info = generator.download_and_convert_song(
                        url=song_info['url'],
                        korean_name=song_info.get('korean_name'),
                        english_name=song_info.get('english_name'),
                        trim_start=song_info.get('trim_start', 0),
                        volume=song_info.get('volume', 0.8)
                    )
                    if generated_song_info:
                        song_info.update(generated_song_info)

                if generator.generate_all_files():
                    self.stations[station_name]["songs"] = generator.songs
                    self.thread_log(f"✅ 스테이션 '{station_name}' 모드 파일 생성 완료.")
                else:
                    all_songs_generated = False
                    self.thread_log(f"❌ 스테이션 '{station_name}' 모드 파일 생성 실패.")
            
            if self.stations:
                mod_name = Path(output_dir).name
                descriptor_content = [
                    'version="1.0"',
                    'tags={',
                    '\t"Sound"',
                    '}',
                    f'name="{mod_name.replace("_", " ").title()}"',
                    'supported_version="1.14.*"'
                ]
                with open(Path(output_dir) / "descriptor.mod", 'w', encoding='utf-8') as f:
                    f.write('\n'.join(descriptor_content) + '\n')
                self.thread_log(f"\n📝 descriptor.mod 파일 생성 완료.")

            if all_songs_generated:
                mod_data = {'stations': self.stations}
                mod_data_path = Path(output_dir) / "mod_data.json"
                with open(mod_data_path, 'w', encoding='utf-8') as f:
                    json.dump(mod_data, f, ensure_ascii=False, indent=2)
                self.thread_log(f"\n✅ 전체 모드 데이터 저장: {mod_data_path}")
                self.thread_log("\n" + "="*60)
                self.thread_log("🎼 HOI4 음악 모드 생성/업데이트 완료!")
                self.thread_log(f"  - 출력 디렉토리: {output_dir}")
                self.thread_log("="*60)

                temp_dir = Path(output_dir) / "temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                
                if self.zip_mod.get():
                    self.zip_mod_folder(output_dir)

                self.message_queue.put(("success", f"모드 생성이 완료되었습니다!\n출력 위치: {output_dir}"))
            else:
                self.message_queue.put(("error", "일부 스테이션 모드 파일 생성에 실패했습니다. 로그를 확인하세요."))
                
        except Exception as e:
            import traceback
            self.thread_log(f"❌ 치명적 오류 발생: {e}\n{traceback.format_exc()}")
            self.message_queue.put(("error", f"모드 생성 중 오류가 발생했습니다: {e}"))
        finally:
            self.message_queue.put(("finish", ""))

    def add_playlist_songs_thread(self, playlist_url, station_name):
        self.thread_log(f"🔄 재생목록 처리 시작: {playlist_url}")
        try:
            playlist = Playlist(playlist_url)
            if not playlist.videos:
                self.thread_log("❌ 재생목록에서 영상을 찾을 수 없거나, 비공개 재생목록일 수 있습니다.")
                return

            self.thread_log(f"  총 {len(playlist.videos)}개의 영상을 발견했습니다. 추가를 시작합니다.")
            
            new_songs = []
            for video in playlist.videos:
                try:
                    title = video.title
                    song_info = {
                        'url': video.watch_url,
                        'korean_name': title,
                        'english_name': title,
                        'trim_start': 0,
                        'volume': 0.8,
                        'weight': 1,
                        'source': 'youtube'
                    }
                    new_songs.append(song_info)
                    self.thread_log(f"  + 준비됨: {title}")
                except Exception as e:
                    self.thread_log(f"  - 영상 정보 가져오기 실패: {e}")
            
            if new_songs:
                self.message_queue.put(("add_multiple_songs", (station_name, new_songs)))

        except Exception as e:
            self.thread_log(f"❌ 재생목록 처리 중 오류 발생: {e}")
    
    def zip_mod_folder(self, output_dir):
        self.thread_log("\n📦 모드 폴더 압축 시작...")
        try:
            output_path = Path(output_dir)
            archive_name = output_path.name
            archive_path = output_path.parent / archive_name
            
            shutil.make_archive(str(archive_path), 'zip', root_dir=output_path.parent, base_dir=archive_name)
            
            self.thread_log(f"  ✅ 압축 완료: {archive_path}.zip")
        except Exception as e:
            self.thread_log(f"  ❌ 압축 실패: {e}")
    
    def thread_log(self, message):
        self.message_queue.put(("log", message))
    
    def log(self, message):
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def check_queue(self):
        try:
            while True:
                msg_type, message = self.message_queue.get_nowait()
                if msg_type == "log": self.log(message)
                elif msg_type == "add_multiple_songs":
                    station_name, song_list = message
                    if station_name in self.stations:
                        self.stations[station_name]["songs"].extend(song_list)
                        self.update_song_tree()
                        self.log(f"✅ {len(song_list)}개의 곡을 재생목록에서 추가했습니다.")
                elif msg_type == "success": messagebox.showinfo("완료", message)
                elif msg_type == "error": messagebox.showerror("오류", message)
                elif msg_type == "finish":
                    self.generate_btn.config(state='normal')
                    self.progress_bar.stop()
                    self.update_song_tree()
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

def main():
    root = tk.Tk()
    app = HOI4MusicGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

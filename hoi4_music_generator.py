	
# -*- coding: utf-8 -*-
# #!/usr/bin/env python3
"""
Hearts of Iron IV 음악 모드 자동 생성기 GUI 버전
필요한 패키지:
pip install pytubefix pydub tkinter pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import threading
import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict
import queue
from pytubefix import YouTube
from pydub import AudioSegment
from PIL import Image
import subprocess

class HOI4MusicModGenerator:
    def __init__(self, station_name="my_station", output_dir="hoi4_music_mod", progress_callback=None):
        self.station_name = self.sanitize_station_name(station_name)
        self.output_dir = Path(output_dir)
        self.songs = []  # 곡 정보 저장
        self.progress_callback = progress_callback
        
        # 출력 디렉토리 구조 생성
        self.create_directory_structure()
    
    def sanitize_station_name(self, name):
        """스테이션 이름에서 특수문자 제거 및 언더스코어로 변환"""
        sanitized = re.sub(r'[^\w가-힣\s]', '_', name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        return sanitized.strip('_').lower()

    def create_directory_structure(self):
        """HOI4 모드 디렉토리 구조 생성"""
        directories = [
            self.output_dir / "music" / self.station_name,
            self.output_dir / "gfx",
            self.output_dir / "interface",
            self.output_dir / "localisation"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        if self.progress_callback:
            self.progress_callback(f"📁 디렉토리 구조 생성 완료: {self.output_dir}")
    
    def sanitize_filename(self, filename):
        """파일명에서 특수문자 제거 및 언더스코어로 변환"""
        sanitized = re.sub(r'[^\w가-힣\s]', '_', filename)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        return sanitized.strip('_')
    
    def download_progress_callback(self, stream, chunk, bytes_remaining):
        """다운로드 진행률 표시"""
        if not self.progress_callback:
            return
            
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = (bytes_downloaded / total_size) * 100
        
        bar_length = 30
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        self.progress_callback(f'  진행률: |{bar}| {percentage:.1f}%')
    
    def download_and_convert_song(self, url, korean_name=None, english_name=None, trim_start=0, volume=0.8):
        """
        유튜브 URL에서 음악을 다운로드하고 OGG로 변환
        """
        try:
            if self.progress_callback:
                self.progress_callback(f"\n🎵 다운로드 시작: {url}")
            
            # YouTube 객체 생성
            yt = YouTube(url, on_progress_callback=self.download_progress_callback)
            
            # 제목 정보 처리
            original_title = yt.title
            
            # 한글명과 영어명 결정
            if korean_name and english_name:
                display_name = korean_name
                english_display = english_name
                file_name = english_name.lower().replace(' ', '_')
            elif korean_name:
                display_name = korean_name
                english_display = original_title
                file_name = self.sanitize_filename(korean_name)
            elif english_name:
                display_name = english_name
                english_display = english_name
                file_name = english_name.lower().replace(' ', '_')
            else:
                display_name = original_title
                english_display = original_title
                file_name = self.sanitize_filename(original_title)
            
            # 영어 파일명에서 특수문자 제거
            file_name = re.sub(r'[^a-zA-Z0-9_]', '_', file_name)
            file_name = re.sub(r'_{2,}', '_', file_name)
            file_name = file_name.strip('_')
            
            if self.progress_callback:
                self.progress_callback(f"  원본 제목: {original_title}")
                self.progress_callback(f"  표시명 (한글): {display_name}")
                self.progress_callback(f"  영어명: {english_display}")
                self.progress_callback(f"  파일명: {file_name}")
                self.progress_callback(f"  길이: {yt.length}초 ({yt.length//60}:{yt.length%60:02d})")
                if trim_start > 0:
                    self.progress_callback(f"  ✂️  시작 {trim_start}초 자르기")
            
            # 오디오 스트림 다운로드
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not audio_stream:
                raise Exception("오디오 스트림을 찾을 수 없습니다.")
            
            # 임시 파일로 다운로드
            temp_dir = self.output_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            temp_file = audio_stream.download(
                output_path=temp_dir,
                filename=f"{file_name}_temp.{audio_stream.subtype}"
            )
            
            # OGG로 변환
            ogg_path = self.output_dir / "music" / self.station_name / f"{file_name}.ogg"
            self.convert_to_ogg(temp_file, ogg_path, trim_start=trim_start)
            
            # 임시 파일 삭제
            Path(temp_file).unlink()
            
            # 곡 정보 저장
            final_duration = max(0, yt.length - trim_start)
            song_info = {
                'name': file_name,
                'display_name': display_name,
                'english_display': english_display,
                'original_title': original_title,
                'file_path': f"{self.station_name}/{file_name}.ogg",
                'duration': final_duration,
                'original_duration': yt.length,
                'trim_start': trim_start,
                'url': url,
                'volume': volume
            }
            
            self.songs.append(song_info)
            
            if self.progress_callback:
                self.progress_callback(f"  ✅ 완료: {ogg_path}")
            
            return song_info
            
        except Exception as e:
            if self.progress_callback:
                self.progress_callback(f"  ❌ 실패: {str(e)}")
            return None
    
    def convert_to_ogg(self, input_file, output_file, quality=5, trim_start=0):
        """오디오 파일을 OGG로 변환"""
        if self.progress_callback:
            self.progress_callback(f"  🔄 OGG 변환 중...")
        
        audio = AudioSegment.from_file(input_file)
        
        # 시작 부분 자르기
        if trim_start > 0:
            trim_start_ms = trim_start * 1000
            if trim_start_ms < len(audio):
                audio = audio[trim_start_ms:]
                if self.progress_callback:
                    self.progress_callback(f"    ✂️  시작 {trim_start}초 제거됨")
        
        # OGG로 내보내기
        audio.export(
            output_file,
            format="ogg",
            codec="libvorbis",
            parameters=["-q:a", str(quality)]
        )
    
    def process_album_art(self, image_path):
        """앨범 아트 이미지를 처리하여 DDS 파일 생성 (304x120 가로 2프레임)"""
        try:
            if self.progress_callback:
                self.progress_callback(f"\n🖼️ 앨범 아트 처리 시작: {image_path}")
            
            final_width, final_height = 304, 120
            
            # 1. 사용자가 올린 이미지를 담을 투명 캔버스 생성
            art_canvas = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))
            original_image = Image.open(image_path).convert('RGBA')

            # --- 프레임 1 (왼쪽)에 맞게 이미지 리사이즈 및 배치 ---
            target_box1 = (10, 10, 142, 110) # 앨범아트가 위치할 영역
            art_width, art_height = target_box1[2] - target_box1[0], target_box1[3] - target_box1[1]

            # 이미지를 강제로 늘려서 프레임에 꽉 채움
            resized_image = original_image.resize((art_width, art_height), Image.Resampling.LANCZOS)
            
            # 왼쪽 프레임에 붙여넣기
            art_canvas.paste(resized_image, (target_box1[0], target_box1[1]))

            # --- 프레임 2 (오른쪽)에 동일한 이미지 배치 ---
            target_box2 = (162, 10, 294, 110) # 오른쪽 앨범아트 영역
            art_canvas.paste(resized_image, (target_box2[0], target_box2[1]))

            # 2. 템플릿 파일 로드 (현재 폴더 기준)
            template_path = Path("radio_station_cover_template.png")
            if template_path.exists():
                if self.progress_callback:
                    self.progress_callback(f"  📋 템플릿 발견: {template_path}")
                template_image = Image.open(template_path).convert('RGBA')

                if template_image.size != (final_width, final_height):
                    template_image = template_image.resize((final_width, final_height), Image.Resampling.LANCZOS)
                    if self.progress_callback:
                        self.progress_callback(f"  ⚠️ 템플릿 크기를 {final_width}x{final_height}로 조정했습니다.")
                
                # 3. 앨범 아트 캔버스 위에 템플릿을 덮어씌움
                final_image = Image.alpha_composite(art_canvas, template_image)
            else:
                if self.progress_callback:
                    self.progress_callback(f"  ❌ 템플릿 파일({template_path})을 찾을 수 없습니다. 앨범 아트만으로 이미지를 생성합니다.")
                final_image = art_canvas 

            # 4. PNG로 임시 저장 및 DDS 변환
            temp_png_path = self.output_dir / "gfx" / f"{self.station_name}_album_art_temp.png"
            final_image.save(temp_png_path, 'PNG')
            
            if self.progress_callback:
                self.progress_callback(f"  💾 임시 PNG 저장: {temp_png_path}")
            
            dds_path = self.output_dir / "gfx" / f"{self.station_name}_album_art.dds"
            success = self.convert_to_dds(temp_png_path, dds_path)
            
            if temp_png_path.exists():
                temp_png_path.unlink()
            
            if success:
                if self.progress_callback:
                    self.progress_callback(f"  ✅ DDS 변환 완료: {dds_path}")
                return True
            else:
                if self.progress_callback:
                    self.progress_callback("  ❌ DDS 변환 실패 - PNG 파일을 수동으로 변환하세요")
                backup_png_path = self.output_dir / "gfx" / f"{self.station_name}_album_art.png"
                final_image.save(backup_png_path, 'PNG')
                if self.progress_callback:
                    self.progress_callback(f"  💾 PNG 백업 저장: {backup_png_path}")
                return False
            
        except Exception as e:
            if self.progress_callback:
                self.progress_callback(f"  ❌ 앨범 아트 처리 실패: {str(e)}")
            return False

    def convert_to_dds(self, png_path, dds_path):
        """PNG 파일을 DDS로 변환 (여러 방법 시도)"""
        # 방법 0: Pillow 라이브러리 직접 사용 (가장 먼저 시도)
        try:
            with Image.open(png_path) as img:
                img.save(dds_path, format='DDS', dds_codec='dxt1')
            if dds_path.exists():
                if self.progress_callback:
                    self.progress_callback("    🔧 Pillow 라이브러리로 DDS 변환 성공")
                return True
        except Exception:
            if self.progress_callback:
                self.progress_callback("    ⚠️ Pillow 변환 실패, 외부 도구를 찾습니다.")

        # 방법 1: ImageMagick 사용
        try:
            result = subprocess.run([
                'magick', 'convert', str(png_path), 
                '-define', 'dds:compression=dxt1',
                str(dds_path)
            ], capture_output=True, text=True, timeout=30, check=False)
            
            if result.returncode == 0 and dds_path.exists():
                if self.progress_callback:
                    self.progress_callback("    🔧 ImageMagick으로 DDS 변환 성공")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 방법 2: DirectXTex texconv 사용 (Windows)
        try:
            result = subprocess.run([
                'texconv', '-f', 'DXT1', '-o', str(dds_path.parent), str(png_path)
            ], capture_output=True, text=True, timeout=30, check=False)
            
            if result.returncode == 0 and dds_path.exists():
                if self.progress_callback:
                    self.progress_callback("    🔧 texconv로 DDS 변환 성공")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 방법 3: NVIDIA Texture Tools 사용
        try:
            result = subprocess.run([
                'nvcompress', '-bc1', str(png_path), str(dds_path)
            ], capture_output=True, text=True, timeout=30, check=False)
            
            if result.returncode == 0 and dds_path.exists():
                if self.progress_callback:
                    self.progress_callback("    🔧 nvcompress로 DDS 변환 성공")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        if self.progress_callback:
            self.progress_callback("    ❌ 모든 DDS 자동 변환 방법에 실패했습니다.")
        return False
    
    def generate_localisation_file(self):
        """localisation 파일 생성 (한글명 + 영어명 표시)"""
        file_path = self.output_dir / "localisation" / f"{self.station_name}_l_english.yml"
        
        content = ["l_english:"]
        
        station_title = self.station_name.replace('_', ' ').title()
        content.append(f' {self.station_name}_TITLE:0 "{station_title}"')
        
        for song in self.songs:
            localized_name = f"{song['display_name']}"
            content.append(f' {song["name"]}:0 "{localized_name}"')
        
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            f.write('\n'.join(content) + '\n')
        
        if self.progress_callback:
            self.progress_callback(f"📝 생성 완료: {file_path}")
    
    def generate_soundtrack_file(self):
        """soundtrack 파일 생성"""
        file_path = self.output_dir / "music" / f"{self.station_name}_soundtrack.txt"
        
        content = [f'music_station = "{self.station_name}"', ""]
        
        for song in self.songs:
            content.extend([
                'music = {',
                f'\tsong = "{song["name"]}"',
                '\tchance = {',
                '\t\tmodifier = {',
                '\t\t\tfactor = 1',
                '\t\t}',
                '\t}',
                '}',
                ''
            ])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        if self.progress_callback:
            self.progress_callback(f"📝 생성 완료: {file_path}")

    def generate_music_asset_file(self):
        """music asset 파일 생성"""
        file_path = self.output_dir / "music" / f"{self.station_name}_music.asset"
        
        content = []
        
        for i, song in enumerate(self.songs):
            if i > 0: content.append('')
            content.append(f'# {song["display_name"]}')
            content.extend([
                'music = {',
                f'\tname = "{song["name"]}"',
                f'\tfile = "{self.station_name}/{Path(song["file_path"]).name}"',
                f'\tvolume = {song.get("volume", 0.8)}',
                '}'
            ])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content) + '\n')
        
        if self.progress_callback:
            self.progress_callback(f"📝 생성 완료: {file_path}")
    
    def generate_gfx_file(self):
        """gfx 파일 생성"""
        file_path = self.output_dir / "interface" / f"{self.station_name}_music.gfx"
        
        content = [
            'spriteTypes = {', '',
            '\tspriteType = {',
            f'\t\tname = "GFX_{self.station_name}_album_art"',
            f'\t\ttexturefile = "gfx/{self.station_name}_album_art.dds"',
            '\t\tnoOfFrames = 2',
            '\t}', '',
            '}'
        ]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content) + '\n')
        
        if self.progress_callback:
            self.progress_callback(f"📝 생성 완료: {file_path}")
    
    def generate_gui_file(self):
        """gui 파일 생성"""
        file_path = self.output_dir / "interface" / f"{self.station_name}_music.gui"
        
        station_title = self.station_name.replace('_', ' ').title() + " Music"
        
        full_gui_content = self.get_full_gui_content(station_title)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_gui_content)
        
        if self.progress_callback:
            self.progress_callback(f"📝 생성 완료: {file_path}")
    
    def get_full_gui_content(self, station_title):
        # Helper to avoid massive string block in main function
        return f"""guiTypes = {{

	containerWindowType = {{
		name = "{self.station_name}_faceplate"
		position = {{ x =0 y=0 }}
		size = {{ width = 590 height = 46 }}

		iconType ={{
			name ="musicplayer_header_bg"
			spriteType = "GFX_musicplayer_header_bg"
			position = {{ x= 0 y = 0 }}
			allwaystransparent = yes
		}}

		instantTextboxType = {{
			name = "track_name"
			position = {{ x = 72 y = 20 }}
			font = "hoi_20b"
			text = "{station_title}"
			maxWidth = 450
			maxHeight = 25
			format = center
		}}

		instantTextboxType = {{
			name = "track_elapsed"
			position = {{ x = 124 y = 30 }}
			font = "hoi_18b"
			text = "00:00"
			maxWidth = 50
			maxHeight = 25
			format = center
		}}

		instantTextboxType = {{
			name = "track_duration"
			position = {{ x = 420 y = 30 }}
			font = "hoi_18b"
			text = "02:58"
			maxWidth = 50
			maxHeight = 25
			format = center
		}}

		buttonType = {{
			name = "prev_button"
			position = {{ x = 220 y = 20 }}
			quadTextureSprite ="GFX_musicplayer_previous_button"
			buttonFont = "Main_14_black"
			Orientation = "LOWER_LEFT"
			clicksound = click_close
			pdx_tooltip = "MUSICPLAYER_PREV"
		}}

		buttonType = {{
			name = "play_button"
			position = {{ x = 263 y = 20 }}
			quadTextureSprite ="GFX_musicplayer_play_pause_button"
			buttonFont = "Main_14_black"
			Orientation = "LOWER_LEFT"
			clicksound = click_close
		}}

		buttonType = {{
			name = "next_button"
			position = {{ x = 336 y = 20 }}
			quadTextureSprite ="GFX_musicplayer_next_button"
			buttonFont = "Main_14_black"
			Orientation = "LOWER_LEFT"
			clicksound = click_close
			pdx_tooltip = "MUSICPLAYER_NEXT"
		}}

		extendedScrollbarType = {{
			name = "volume_slider"
			position = {{ x = 100 y = 45}}
			size = {{ width = 75 height = 18 }}
			tileSize = {{ width = 12 height = 12}}
			maxValue =100
			minValue =0
			stepSize =1
			startValue = 50
			horizontal = yes
			orientation = lower_left
			origo = lower_left
			setTrackFrameOnChange = yes

			slider = {{
				name = "Slider"
				quadTextureSprite = "GFX_scroll_drager"
				position = {{ x=0 y = 1 }}
				pdx_tooltip = "MUSICPLAYER_ADJUST_VOL"
			}}

			track = {{
				name = "Track"
				quadTextureSprite = "GFX_volume_track"
				position = {{ x=0 y = 3 }}
				allwaystransparent = yes
				pdx_tooltip = "MUSICPLAYER_ADJUST_VOL"
			}}
		}}

		buttonType = {{
			name = "shuffle_button"
			position = {{ x = 425 y = 20 }}
			quadTextureSprite ="GFX_toggle_shuffle_buttons"
			buttonFont = "Main_14_black"
			Orientation = "LOWER_LEFT"
			clicksound = click_close
		}}
	}}

	containerWindowType={{
		name = "{self.station_name}_stations_entry"
		size = {{ width = 152 height = 120 }}

		checkBoxType = {{
			name = "select_station_button"
			position = {{ x = 0 y = 0 }}
			quadTextureSprite = "GFX_{self.station_name}_album_art"
			clicksound = decisions_ui_button
		}}
	}}
}}"""

    def generate_descriptor_mod(self):
        """descriptor.mod 파일 생성"""
        file_path = self.output_dir / "descriptor.mod"
        
        station_title = self.station_name.replace('_', ' ').title()
        content = [
            'version="1"',
            'tags={',
            '\t"Sound"',
            '}',
            f'name="{station_title} Music Mod"',
            'thumbnail="thumbnail.png"',
            'supported_version="1.*"'
        ]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content) + '\n')
        
        if self.progress_callback:
            self.progress_callback(f"📝 생성 완료: {file_path}")
    
    def generate_all_files(self):
        """모든 HOI4 모드 파일 생성"""
        if not self.songs:
            if self.progress_callback:
                self.progress_callback("❌ 다운로드된 곡이 없습니다.")
            return False
        
        if self.progress_callback:
            self.progress_callback(f"\n📄 HOI4 모드 파일 생성 중... (총 {len(self.songs)}곡)")
        
        self.generate_localisation_file()
        self.generate_soundtrack_file()
        self.generate_music_asset_file()
        self.generate_gfx_file()
        self.generate_gui_file()
        
        return True

class HOI4MusicGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HOI4 음악 모드 생성기")
        self.root.geometry("850x800")
        
        self.stations: Dict[str, Dict] = {} # 스테이션 이름: {"songs": [], "album_art": ""}
        self.current_station_name = tk.StringVar(value="my_station")
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "my_station_mod"))
        self.album_art_path = tk.StringVar() # GUI 표시용 변수
        self.message_queue = queue.Queue()
        
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
        
        add_song_frame = ttk.LabelFrame(main_frame, text="곡 추가", padding="10")
        add_song_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        song_list_frame = ttk.LabelFrame(main_frame, text="곡 목록", padding="10")
        song_list_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        generate_frame = ttk.Frame(main_frame)
        generate_frame.grid(row=5, column=0, columnspan=2, pady=(0, 10))
        self.generate_btn = ttk.Button(generate_frame, text="모드 생성 시작", command=self.generate_mod)
        self.generate_btn.grid(row=0, column=0, padx=(0, 10))
        self.progress_bar = ttk.Progressbar(generate_frame, mode='indeterminate')
        
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="10")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=12)
        
        self.setup_full_widgets(main_frame, settings_frame, album_frame, add_song_frame, song_list_frame, generate_frame, log_frame)

    def setup_full_widgets(self, main_frame, settings_frame, album_frame, add_song_frame, song_list_frame, generate_frame, log_frame):
        ttk.Label(add_song_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W)
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
        ttk.Button(add_song_frame, text="곡 추가", command=self.add_song).grid(row=3, column=3, padx=(10, 0), pady=(10, 0), sticky=tk.E)
        file_io_frame = ttk.Frame(add_song_frame)
        file_io_frame.grid(row=4, column=0, columnspan=4, pady=(10, 0), sticky=tk.W)
        ttk.Button(file_io_frame, text="목록 불러오기", command=self.load_song_list).grid(row=0, column=0)
        ttk.Button(file_io_frame, text="목록 내보내기", command=self.export_song_list).grid(row=0, column=1, padx=(10,0))
        
        columns = ('korean', 'english', 'url', 'trim', 'volume')
        self.song_tree = ttk.Treeview(song_list_frame, columns=columns, show='headings', height=6)
        self.song_tree.heading('korean', text='한글명'); self.song_tree.heading('english', text='영어명'); self.song_tree.heading('url', text='URL'); self.song_tree.heading('trim', text='자르기(초)'); self.song_tree.heading('volume', text='볼륨')
        self.song_tree.column('korean', width=150); self.song_tree.column('english', width=150); self.song_tree.column('url', width=250); self.song_tree.column('trim', width=60, anchor=tk.CENTER); self.song_tree.column('volume', width=60, anchor=tk.CENTER)
        scrollbar = ttk.Scrollbar(song_list_frame, orient=tk.VERTICAL, command=self.song_tree.yview)
        self.song_tree.configure(yscroll=scrollbar.set)
        self.song_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)); scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        ttk.Button(song_list_frame, text="선택된 곡 삭제", command=self.remove_song).grid(row=1, column=0, pady=(5, 0), sticky=tk.W)

        self.progress_bar.grid(row=0, column=1, padx=(10, 0), sticky=(tk.W, tk.E))
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
            sanitized_name = HOI4MusicModGenerator.sanitize_station_name(None, new_name)
            if sanitized_name in self.stations:
                if not initial_name:
                    messagebox.showwarning("경고", "이미 존재하는 스테이션 이름입니다. 다른 이름을 사용해주세요.")
                return
            
            self.stations[sanitized_name] = {"songs": [], "album_art": ""}
            self.current_station_name.set(sanitized_name)
            self.update_station_list()
            self.on_station_change()
            self.log(f"✅ 새 스테이션 '{sanitized_name}' 추가됨.")


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
            
            # 데이터 구조 검증 및 수정: songs 키가 리스트인지 확인
            for station_name, station_data in loaded_stations.items():
                if not isinstance(station_data.get("songs"), list):
                    self.log(f"⚠️ 스테이션 '{station_name}'의 곡 목록 형식이 잘못되어 리스트로 변환합니다.")
                    if isinstance(station_data.get("songs"), dict):
                        # 딕셔너리 형태의 곡 목록을 리스트로 변환 (값들을 사용)
                        station_data["songs"] = list(station_data["songs"].values())
                    else:
                        # 그 외의 경우, 안전하게 빈 리스트로 초기화
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
    
    def add_song(self):
        # <--- 변경: 입력값 유효성 검사 추가
        current_station = self.current_station_name.get()
        if not current_station:
            messagebox.showwarning("경고", "스테이션을 먼저 추가하거나 선택해주세요.")
            return
        
        url = self.url_entry.get().strip()
        korean_name = self.korean_name_entry.get().strip()
        english_name = self.english_name_entry.get().strip()

        if not all([url, korean_name, english_name]):
            messagebox.showwarning("입력 오류", "YouTube URL, 한글명, 영어명을 모두 입력해야 합니다.")
            return
        
        try:
            trim_start = int(self.trim_start_entry.get() or 0)
            volume = float(self.volume_entry.get() or 0.8)
            if not (0.0 <= volume <= 1.5):
                raise ValueError("볼륨 값은 0.0과 1.5 사이여야 합니다.")
        except ValueError as e:
            messagebox.showwarning("입력 오류", f"숫자 입력이 잘못되었습니다: {e}")
            return
        
        song_info = {
            'url': url,
            'korean_name': korean_name,
            'english_name': english_name,
            'trim_start': trim_start,
            'volume': volume
        }
        
        self.stations[current_station]["songs"].append(song_info)
        self.update_song_tree()
        for entry in [self.url_entry, self.korean_name_entry, self.english_name_entry]:
            entry.delete(0, tk.END)
        self.trim_start_entry.delete(0, tk.END); self.trim_start_entry.insert(0, "0")
        self.volume_entry.delete(0, tk.END); self.volume_entry.insert(0, "0.8")
        self.log("곡이 현재 스테이션에 추가되었습니다.")

    def update_song_tree(self):
        for i in self.song_tree.get_children(): self.song_tree.delete(i)
        current_station = self.current_station_name.get()
        
        songs = self.stations.get(current_station, {}).get("songs", [])
        
        for song in songs:
            korean_name = song.get('display_name') or song.get('korean_name') or "자동"
            english_name = song.get('english_display') or song.get('english_name') or "자동"
            
            self.song_tree.insert('', 'end', values=(
                korean_name,
                english_name,
                song['url'],
                song.get('trim_start', 0),
                song.get('volume', 0.8)
            ))
    
    def remove_song(self):
        selected_items = self.song_tree.selection()
        if not selected_items: return
        if messagebox.askyesno("삭제 확인", f"선택한 {len(selected_items)}개의 곡을 삭제하시겠습니까?"):
            current_station = self.current_station_name.get()
            
            songs_list = self.stations.get(current_station, {}).get("songs", [])
            
            selected_indices = sorted([self.song_tree.index(i) for i in selected_items], reverse=True)
            for index in selected_indices: del songs_list[index]

            self.stations[current_station]["songs"] = songs_list
            self.update_song_tree()
            self.log(f"{len(selected_items)}개의 곡이 삭제되었습니다.")

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
            song = {'trim_start': 0, 'volume': 0.8}
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
                
                output_music_dir = Path(output_dir) / "music" / station_name
                output_music_dir.mkdir(parents=True, exist_ok=True)
                
                for song_info in songs_list:
                    if 'name' in song_info:
                        file_name_base = song_info['name']
                    elif song_info.get('english_name'):
                        file_name_base = re.sub(r'[^a-zA-Z0-9_]', '_', song_info['english_name'].lower().replace(' ', '_')).strip('_')
                    elif song_info.get('korean_name'):
                        file_name_base = generator.sanitize_filename(song_info['korean_name'])
                    else:
                        songs_to_download.append(song_info)
                        continue
                        
                    ogg_path = output_music_dir / f"{file_name_base}.ogg"
                    if ogg_path.exists():
                        self.thread_log(f"✅ '{song_info.get('display_name', file_name_base)}' 파일이 이미 존재합니다. 건너뜁니다.")
                        existing_songs_info.append(song_info)
                    else:
                        songs_to_download.append(song_info)

                generator.songs = existing_songs_info
                
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
            
            # <--- 변경: descriptor.mod 생성 로직 수정
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
                    import shutil
                    shutil.rmtree(temp_dir)
                
                self.message_queue.put(("success", f"모드 생성이 완료되었습니다!\n출력 위치: {output_dir}"))
            else:
                self.message_queue.put(("error", "일부 스테이션 모드 파일 생성에 실패했습니다. 로그를 확인하세요."))
                
        except Exception as e:
            import traceback
            self.thread_log(f"❌ 치명적 오류 발생: {e}\n{traceback.format_exc()}")
            self.message_queue.put(("error", f"모드 생성 중 오류가 발생했습니다: {e}"))
        finally:
            self.message_queue.put(("finish", ""))
    
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

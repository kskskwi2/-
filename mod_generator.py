# -*- coding: utf-8 -*-
import re
from pathlib import Path
from media_processor import MediaProcessor
from file_writer import FileWriter

class HOI4MusicModGenerator:
    def __init__(self, station_name="my_station", output_dir="hoi4_music_mod", progress_callback=None):
        self.station_name = self.sanitize_station_name(station_name)
        self.output_dir = Path(output_dir)
        self.songs = []
        self.progress_callback = progress_callback

        self.media_processor = MediaProcessor(self.output_dir, self.station_name, self.progress_callback)
        self.file_writer = FileWriter(self.output_dir, self.station_name, self.progress_callback)

        self.create_directory_structure()

    def _log(self, message):
        if self.progress_callback:
            self.progress_callback(message)

    @staticmethod
    def sanitize_station_name(name):
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
        self._log(f"📁 디렉토리 구조 생성 완료: {self.output_dir}")

    def sanitize_filename(self, filename):
        return self.media_processor.sanitize_filename(filename)

    def process_album_art(self, image_path):
        return self.media_processor.process_album_art(image_path)

    def download_and_convert_song(self, *args, **kwargs):
        song_info = self.media_processor.download_and_convert_song(*args, **kwargs)
        if song_info:
            self.songs.append(song_info)
        return song_info

    def process_local_song(self, song_info):
        processed_info = self.media_processor.process_local_song(song_info)
        if processed_info:
            self.songs.append(processed_info)
        return processed_info

    def generate_all_files(self):
        return self.file_writer.generate_all_files(self.songs)
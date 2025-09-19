# -*- coding: utf-8 -*-
import re
import subprocess
from pathlib import Path
from pytubefix import YouTube
from pydub import AudioSegment
from PIL import Image

class MediaProcessor:
    def __init__(self, output_dir, station_name, progress_callback=None):
        self.output_dir = Path(output_dir)
        self.station_name = station_name
        self.progress_callback = progress_callback

    def _log(self, message):
        if self.progress_callback:
            self.progress_callback(message)

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
        
        self._log(f'  진행률: |{bar}| {percentage:.1f}%')

    def download_and_convert_song(self, url, korean_name=None, english_name=None, trim_start=0, volume=0.8):
        """
        유튜브 URL에서 음악을 다운로드하고 OGG로 변환
        """
        try:
            self._log(f"\n🎵 다운로드 시작: {url}")
            
            yt = YouTube(url, on_progress_callback=self.download_progress_callback)
            original_title = yt.title
            
            if korean_name and english_name:
                display_name, english_display, file_name = korean_name, english_name, english_name.lower().replace(' ', '_')
            elif korean_name:
                display_name, english_display, file_name = korean_name, original_title, self.sanitize_filename(korean_name)
            elif english_name:
                display_name, english_display, file_name = english_name, english_name, english_name.lower().replace(' ', '_')
            else:
                display_name, english_display, file_name = original_title, original_title, self.sanitize_filename(original_title)
            
            file_name = re.sub(r'[^a-zA-Z0-9_]', '_', file_name)
            file_name = re.sub(r'_{2,}', '_', file_name).strip('_')
            
            self._log(f"  원본 제목: {original_title}")
            self._log(f"  표시명 (한글): {display_name}")
            self._log(f"  영어명: {english_display}")
            self._log(f"  파일명: {file_name}")
            self._log(f"  길이: {yt.length}초 ({yt.length//60}:{yt.length%60:02d})")
            if trim_start > 0: self._log(f"  ✂️  시작 {trim_start}초 자르기")
            
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not audio_stream: raise Exception("오디오 스트림을 찾을 수 없습니다.")
            
            temp_dir = self.output_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            temp_file = audio_stream.download(output_path=temp_dir, filename=f"{file_name}_temp.{audio_stream.subtype}")
            
            ogg_path = self.output_dir / "music" / self.station_name / f"{file_name}.ogg"
            self.convert_to_ogg(temp_file, ogg_path, trim_start=trim_start)
            
            Path(temp_file).unlink()
            
            final_duration = max(0, yt.length - trim_start)
            song_info = {
                'name': file_name, 'display_name': display_name, 'english_display': english_display,
                'original_title': original_title, 'file_path': f"{self.station_name}/{file_name}.ogg",
                'duration': final_duration, 'original_duration': yt.length,
                'trim_start': trim_start, 'url': url, 'volume': volume
            }
            
            self._log(f"  ✅ 완료: {ogg_path}")
            return song_info
            
        except Exception as e:
            self._log(f"  ❌ 실패: {str(e)}")
            return None

    def convert_to_ogg(self, input_file, output_file, quality=5, trim_start=0):
        """오디오 파일을 OGG로 변환"""
        self._log(f"  🔄 OGG 변환 중...")
        audio = AudioSegment.from_file(input_file)
        
        if trim_start > 0:
            trim_start_ms = trim_start * 1000
            if trim_start_ms < len(audio):
                audio = audio[trim_start_ms:]
                self._log(f"    ✂️  시작 {trim_start}초 제거됨")
        
        audio.export(output_file, format="ogg", codec="libvorbis", parameters=["-q:a", str(quality)])

    def process_album_art(self, image_path):
        """앨범 아트 이미지를 처리하여 DDS 파일 생성"""
        try:
            self._log(f"\n🖼️ 앨범 아트 처리 시작: {image_path}")
            final_width, final_height = 304, 120
            
            art_canvas = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))
            original_image = Image.open(image_path).convert('RGBA')

            target_box1 = (10, 10, 142, 110)
            art_width, art_height = target_box1[2] - target_box1[0], target_box1[3] - target_box1[1]
            resized_image = original_image.resize((art_width, art_height), Image.Resampling.LANCZOS)
            art_canvas.paste(resized_image, (target_box1[0], target_box1[1]))

            target_box2 = (162, 10, 294, 110)
            art_canvas.paste(resized_image, (target_box2[0], target_box2[1]))

            template_path = Path("radio_station_cover_template.png")
            if template_path.exists():
                self._log(f"  📋 템플릿 발견: {template_path}")
                template_image = Image.open(template_path).convert('RGBA')
                if template_image.size != (final_width, final_height):
                    template_image = template_image.resize((final_width, final_height), Image.Resampling.LANCZOS)
                    self._log(f"  ⚠️ 템플릿 크기를 {final_width}x{final_height}로 조정했습니다.")
                final_image = Image.alpha_composite(art_canvas, template_image)
            else:
                self._log(f"  ❌ 템플릿 파일({template_path})을 찾을 수 없습니다. 앨범 아트만으로 이미지를 생성합니다.")
                final_image = art_canvas 

            temp_png_path = self.output_dir / "gfx" / f"{self.station_name}_album_art_temp.png"
            final_image.save(temp_png_path, 'PNG')
            self._log(f"  💾 임시 PNG 저장: {temp_png_path}")
            
            dds_path = self.output_dir / "gfx" / f"{self.station_name}_album_art.dds"
            success = self.convert_to_dds(temp_png_path, dds_path)
            
            if temp_png_path.exists(): temp_png_path.unlink()
            
            if success:
                self._log(f"  ✅ DDS 변환 완료: {dds_path}")
                return True
            else:
                self._log("  ❌ DDS 변환 실패 - PNG 파일을 수동으로 변환하세요")
                backup_png_path = self.output_dir / "gfx" / f"{self.station_name}_album_art.png"
                final_image.save(backup_png_path, 'PNG')
                self._log(f"  💾 PNG 백업 저장: {backup_png_path}")
                return False
        except Exception as e:
            self._log(f"  ❌ 앨범 아트 처리 실패: {str(e)}")
            return False

    def convert_to_dds(self, png_path, dds_path):
        """PNG 파일을 DDS로 변환 (여러 방법 시도)"""
        try:
            with Image.open(png_path) as img:
                img.save(dds_path, format='DDS', dds_codec='dxt1')
            if dds_path.exists():
                self._log("    🔧 Pillow 라이브러리로 DDS 변환 성공")
                return True
        except Exception:
            self._log("    ⚠️ Pillow 변환 실패, 외부 도구를 찾습니다.")

        for tool_cmd in [
            ['magick', 'convert', str(png_path), '-define', 'dds:compression=dxt1', str(dds_path)],
            ['texconv', '-f', 'DXT1', '-o', str(dds_path.parent), str(png_path)],
            ['nvcompress', '-bc1', str(png_path), str(dds_path)]
        ]:
            try:
                result = subprocess.run(tool_cmd, capture_output=True, text=True, timeout=30, check=False)
                if result.returncode == 0 and dds_path.exists():
                    self._log(f"    🔧 {tool_cmd[0]}으로 DDS 변환 성공")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        self._log("    ❌ 모든 DDS 자동 변환 방법에 실패했습니다.")
        return False

    def process_local_song(self, song_info):
        """
        로컬 오디오 파일을 OGG로 변환
        """
        try:
            local_path = Path(song_info['url'])
            self._log(f"\n🎵 로컬 파일 처리 시작: {local_path.name}")

            korean_name = song_info['korean_name']
            english_name = song_info['english_name']
            trim_start = song_info.get('trim_start', 0)
            volume = song_info.get('volume', 0.8)

            file_name = english_name.lower().replace(' ', '_')
            file_name = re.sub(r'[^a-zA-Z0-9_]', '_', file_name)
            file_name = re.sub(r'_{2,}', '_', file_name).strip('_')

            self._log(f"  표시명 (한글): {korean_name}")
            self._log(f"  영어명: {english_name}")
            self._log(f"  파일명: {file_name}")
            if trim_start > 0: self._log(f"  ✂️  시작 {trim_start}초 자르기")

            # 오디오 파일 로드 및 길이 확인
            audio = AudioSegment.from_file(local_path)
            original_duration = len(audio) / 1000 # pydub 길이는 ms 단위
            self._log(f"  원본 길이: {original_duration:.0f}초 ({int(original_duration)//60}:{int(original_duration)%60:02d})")

            # OGG로 변환
            ogg_path = self.output_dir / "music" / self.station_name / f"{file_name}.ogg"
            self.convert_to_ogg(local_path, ogg_path, trim_start=trim_start)

            # 최종 곡 정보 생성
            final_duration = max(0, original_duration - trim_start)
            processed_song_info = {
                'name': file_name,
                'display_name': korean_name,
                'english_display': english_name,
                'original_title': local_path.name,
                'file_path': f"{self.station_name}/{file_name}.ogg",
                'duration': final_duration,
                'original_duration': original_duration,
                'trim_start': trim_start,
                'url': song_info['url'], # Keep original path for reference
                'volume': volume,
                'source': 'local'
            }

            self._log(f"  ✅ 완료: {ogg_path}")
            return processed_song_info

        except Exception as e:
            self._log(f"  ❌ 실패: {str(e)}")
            return None

# -*- coding: utf-8 -*-
from pathlib import Path

class FileWriter:
    def __init__(self, output_dir, station_name, progress_callback=None):
        self.output_dir = Path(output_dir)
        self.station_name = station_name
        self.songs = []
        self.progress_callback = progress_callback

    def _log(self, message):
        if self.progress_callback:
            self.progress_callback(message)

    def generate_all_files(self, songs):
        """모든 HOI4 모드 파일 생성"""
        self.songs = songs
        if not self.songs:
            self._log("❌ 다운로드된 곡이 없습니다.")
            return False
        
        self._log(f"\n📄 HOI4 모드 파일 생성 중... (총 {len(self.songs)}곡)")
        
        self.generate_localisation_file()
        self.generate_soundtrack_file()
        self.generate_music_asset_file()
        self.generate_gfx_file()
        self.generate_gui_file()
        
        return True

    def generate_localisation_file(self):
        file_path = self.output_dir / "localisation" / f"{self.station_name}_l_english.yml"
        station_title = self.station_name.replace('_', ' ').title()
        content = ["l_english:", f' {self.station_name}_TITLE:0 "{station_title}"']
        for song in self.songs:
            content.append(f' {song["name"]}:0 "{song["display_name"]}"')
        
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            f.write('\n'.join(content) + '\n')
        self._log(f"📝 생성 완료: {file_path}")

    def generate_soundtrack_file(self):
        file_path = self.output_dir / "music" / f"{self.station_name}_soundtrack.txt"
        content = [f'music_station = "{self.station_name}"', ""]
        for song in self.songs:
            content.extend([
                'music = {',
                f'\tsong = "{song["name"]}"',
                f'\tchance = {{ \tmodifier = {{ factor = {song.get("weight", 1)} }} }}',
                '}', ''
            ])
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        self._log(f"📝 생성 완료: {file_path}")

    def generate_music_asset_file(self):
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
        self._log(f"📝 생성 완료: {file_path}")

    def generate_gfx_file(self):
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
        self._log(f"📝 생성 완료: {file_path}")

    def generate_gui_file(self):
        file_path = self.output_dir / "interface" / f"{self.station_name}_music.gui"
        station_title = self.station_name.replace('_', ' ').title() + " Music"
        full_gui_content = self._get_full_gui_content(station_title)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_gui_content)
        self._log(f"📝 생성 완료: {file_path}")

    def _get_full_gui_content(self, station_title):
        return f'''guiTypes = {{

	containerWindowType = {{
		name = "{self.station_name}_faceplate"
		position = {{ x =0 y=0 }}
		size = {{ width = 590 height = 46 }}

		iconType ={{ name ="musicplayer_header_bg", spriteType = "GFX_musicplayer_header_bg", position = {{ x= 0 y = 0 }}, allwaystransparent = yes }}

		instantTextboxType = {{ name = "track_name", position = {{ x = 72 y = 20 }}, font = "hoi_20b", text = "{station_title}", maxWidth = 450, maxHeight = 25, format = center }}

		instantTextboxType = {{ name = "track_elapsed", position = {{ x = 124 y = 30 }}, font = "hoi_18b", text = "00:00", maxWidth = 50, maxHeight = 25, format = center }}

		instantTextboxType = {{ name = "track_duration", position = {{ x = 420 y = 30 }}, font = "hoi_18b", text = "02:58", maxWidth = 50, maxHeight = 25, format = center }}

		buttonType = {{ name = "prev_button", position = {{ x = 220 y = 20 }}, quadTextureSprite ="GFX_musicplayer_previous_button", buttonFont = "Main_14_black", Orientation = "LOWER_LEFT", clicksound = click_close, pdx_tooltip = "MUSICPLAYER_PREV" }}

		buttonType = {{ name = "play_button", position = {{ x = 263 y = 20 }}, quadTextureSprite ="GFX_musicplayer_play_pause_button", buttonFont = "Main_14_black", Orientation = "LOWER_LEFT", clicksound = click_close }}

		buttonType = {{ name = "next_button", position = {{ x = 336 y = 20 }}, quadTextureSprite ="GFX_musicplayer_next_button", buttonFont = "Main_14_black", Orientation = "LOWER_LEFT", clicksound = click_close, pdx_tooltip = "MUSICPLAYER_NEXT" }}

		extendedScrollbarType = {{
			name = "volume_slider", position = {{ x = 100 y = 45}}, size = {{ width = 75 height = 18 }}, tileSize = {{ width = 12 height = 12}}, maxValue =100, minValue =0, stepSize =1, startValue = 50, horizontal = yes, orientation = lower_left, origo = lower_left, setTrackFrameOnChange = yes
			slider = {{ name = "Slider", quadTextureSprite = "GFX_scroll_drager", position = {{ x=0 y = 1 }}, pdx_tooltip = "MUSICPLAYER_ADJUST_VOL" }}
			track = {{ name = "Track", quadTextureSprite = "GFX_volume_track", position = {{ x=0 y = 3 }}, allwaystransparent = yes, pdx_tooltip = "MUSICPLAYER_ADJUST_VOL" }}
		}}

		buttonType = {{ name = "shuffle_button", position = {{ x = 425 y = 20 }}, quadTextureSprite ="GFX_toggle_shuffle_buttons", buttonFont = "Main_14_black", Orientation = "LOWER_LEFT", clicksound = click_close }}
	}}

	containerWindowType={{
		name = "{self.station_name}_stations_entry"
		size = {{ width = 152 height = 120 }}

		checkBoxType = {{
			name = "select_station_button", position = {{ x = 0 y = 0 }}, quadTextureSprite = "GFX_{self.station_name}_album_art", clicksound = decisions_ui_button
		}}
	}}
}}'''

import flet as ft
import yt_dlp
import pyperclip
import re
import threading
import os
import time
import imageio_ffmpeg

def get_ffmpeg_path():
    return imageio_ffmpeg.get_ffmpeg_exe()

def main(page: ft.Page):
    page.title = "Vedat Hoca MP3 İndirme Aracı"
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.scroll = "auto"
    page.window.width = 600
    page.window.height = 600
    page.window.max_height = 600
    page.window.max_width = 600

    results_column = ft.Column(spacing=5, expand=True)
    download_items = []

    url_input = ft.TextField(label="YouTube URL", expand=True)

    def is_youtube_url(url: str) -> bool:
        pattern = r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]+(?:[&?][\w=%-]+)*"
        return re.match(pattern, url) is not None

    def show_alert(message: str):
        dlg = ft.AlertDialog(
            title=ft.Text("Uyarı"),
            content=ft.Text(message),
            actions=[ft.TextButton("Tamam", on_click=lambda e: page.dialog.close())],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def remove_card(card):
        if card in results_column.controls:
            results_column.controls.remove(card)
            page.update()

    def fetch_video_info(url: str):
        try:
            ydl_opts = {"quiet": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            title = info.get("title", "Başlık bulunamadı")
            duration = info.get("duration_string") or f"{info.get('duration', 0)} sn"
            thumbnail = info.get("thumbnail")
            video_url = info.get("webpage_url")
            uploader = info.get("uploader", "Bilinmeyen Kanal")

            progress_bar = ft.ProgressBar(value=0, color=ft.Colors.ORANGE, expand=True)
            progress_percentage = ft.Text("0%", size=12, color=ft.Colors.ORANGE)

            download_area = ft.Container()
            started = False
            download_done_event = threading.Event()

            def progress_hook(d):
                nonlocal started
                if d["status"] == "downloading":
                    total = d.get("total_bytes")
                    downloaded = d.get("downloaded_bytes")
                    if total and downloaded is not None:
                        fraction = downloaded / total
                        progress_bar.value = fraction
                        progress_percentage.value = f"{int(fraction * 100)}%"
                        progress_percentage.color = ft.Colors.ORANGE
                        page.update()
                elif d["status"] == "postprocessing":
                    def simulate_conversion():
                        current = progress_bar.value
                        steps = 50
                        delay = 5 / steps
                        for i in range(steps):
                            current += (1.0 - current) / (steps - i)
                            progress_bar.value = current
                            progress_percentage.value = f"{int(current * 100)}%"
                            progress_percentage.color = ft.Colors.GREEN
                            page.update()
                            time.sleep(delay)
                        progress_bar.value = 1.0
                        progress_percentage.value = "100%"
                        progress_percentage.color = ft.Colors.GREEN
                        download_area.content = ft.Text("İndirme Tamamlandı", size=12)
                        page.update()
                        download_done_event.set()
                    threading.Thread(target=simulate_conversion, daemon=True).start()
                elif d["status"] == "finished":
                    progress_bar.value = 1.0
                    progress_percentage.value = "100%"
                    progress_percentage.color = ft.Colors.GREEN
                    download_area.content = ft.Text("İndirme Tamamlandı", size=12)
                    page.update()
                    download_done_event.set()

            def download_video_thread():
                try:
                    desktop_folder = os.path.join(os.path.expanduser("~"), "Desktop", "class_mp3")
                    os.makedirs(desktop_folder, exist_ok=True)
                    
                    ydl_opts_dl = {
                        "progress_hooks": [progress_hook],
                        "ffmpeg_location": get_ffmpeg_path(),
                        "outtmpl": os.path.join(desktop_folder, "%(title)s.%(ext)s"),
                        "postprocessors": [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    }
                    with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                        ydl.download([video_url])
                except Exception as ex:
                    show_alert(f"İndirme sırasında hata oluştu:\n{ex}")
                    download_done_event.set()

            def start_download(e):
                nonlocal started
                if started:
                    return
                started = True
                download_area.content = ft.Text("İndirme başladı...", size=12)
                page.update()
                threading.Thread(target=download_video_thread, daemon=True).start()

            download_area.content = ft.IconButton(
                icon=ft.Icons.DOWNLOAD,
                tooltip="İndir",
                on_click=start_download,
            )

            download_items.append((start_download, download_done_event, download_area))
            thumbnail_stack = ft.Stack(
                width=80,
                height=80,
                controls=[
                    ft.Image(src=thumbnail, width=120, height=120, fit="cover"),
                    ft.Container(
                        content=ft.Text(duration, color="white", size=10),
                        alignment=ft.alignment.bottom_right,
                        padding=2
                    )
                ]
            )

            info_column = ft.Column(
                controls=[
                    ft.Text(title, weight="bold", size=14),
                    ft.Text(uploader, size=12),
                    download_area
                ],
                spacing=4,
                expand=True
            )

            content_row = ft.Row(
                controls=[thumbnail_stack, info_column],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True
            )

            progress_row = ft.Row(
                controls=[progress_bar, progress_percentage],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8
            )

            card_content = ft.Column(
                controls=[content_row, progress_row],
                spacing=8
            )

            remove_btn = ft.IconButton(
                icon=ft.Icons.CLOSE,
                tooltip="Kaldır",
                on_click=lambda e: remove_card(card_wrapper)
            )

            card_stack = ft.Stack(
                controls=[
                    ft.Container(content=card_content, padding=10),
                    ft.Container(
                        content=remove_btn,
                        alignment=ft.alignment.top_right,
                        padding=5,
                    ),
                ]
            )

            card_wrapper = ft.Card(
                content=card_stack,
                elevation=1
            )

            results_column.controls.append(card_wrapper)
            page.update()

        except Exception as e:
            show_alert(f"Video bilgisi alınamadı:\n{e}")

    def add_video_click(e):
        url = url_input.value.strip()
        if not url:
            show_alert("Lütfen bir YouTube URL’si girin.")
            return
        if not is_youtube_url(url):
            show_alert("Bu bir YouTube URL’si değil. Lütfen geçerli bir bağlantı girin.")
            return
        fetch_video_info(url)

    def download_all_click(e):
        if not download_items:
            show_alert("İndirilecek video bulunamadı.")
            return
        def sequential_download():
            for (download_fn, done_event, _) in download_items:
                if not done_event.is_set():
                    download_fn(None)
                    done_event.wait()
        threading.Thread(target=sequential_download, daemon=True).start()

    def fab_click(e):
        clipboard_url = pyperclip.paste().strip()
        if not clipboard_url:
            show_alert("Panoda herhangi bir metin bulunamadı.")
            return
        if not is_youtube_url(clipboard_url):
            show_alert("Panodaki içerik geçerli bir YouTube URL’si değil.")
            return
        url_input.value = clipboard_url
        url_input.update()
        add_video_click(e)

    download_all_button = ft.OutlinedButton(
        "Tümünü İndir", 
        icon=ft.Icons.DOWNLOAD, 
        on_click=download_all_click
    )

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.PLAY_ARROW,
        on_click=fab_click
    )

    page.add(
        ft.Row(
            [url_input, download_all_button], 
            alignment=ft.MainAxisAlignment.CENTER
        ),
        ft.Divider(),
        results_column
    )

ft.app(target=main)

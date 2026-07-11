import streamlit as st
import yt_dlp
import os
import subprocess
import glob
import json
import time

LIBRARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Library")
FAVORITES_FILE = os.path.join(LIBRARY_DIR, ".favorites.json")
PLAYLISTS_FILE = os.path.join(LIBRARY_DIR, ".playlists.json")

os.makedirs(LIBRARY_DIR, exist_ok=True)

# --- Theme ---
if "theme" not in st.session_state:
    st.session_state.theme = "dark"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


favorites = load_json(FAVORITES_FILE, [])
playlists = load_json(PLAYLISTS_FILE, {})

# --- Page Config ---
st.set_page_config(page_title="Private Music Server", page_icon="🎵", layout="wide")

# --- CSS for theme ---
if st.session_state.theme == "dark":
    bg = "#0e1117"
    text = "#fafafa"
    card_bg = "#1e1e1e"
else:
    bg = "#ffffff"
    text = "#111111"
    card_bg = "#f0f0f0"

st.markdown(f"""
<style>
.stApp {{ background-color: {bg}; color: {text}; }}
.song-card {{
    background: {card_bg};
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.song-card img {{ border-radius: 6px; width: 60px; height: 60px; object-fit: cover; }}
</style>
""", unsafe_allow_html=True)

# --- Header ---
col_title, col_theme = st.columns([6, 1])
with col_title:
    st.title("🎵 Private Music Server")
with col_theme:
    if st.button("🌙" if st.session_state.theme == "light" else "☀️"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

# --- FFmpeg Check ---
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

ffmpeg_available = check_ffmpeg()

# --- Helper: get all mp3 files ---
def get_mp3_files():
    return sorted(glob.glob(os.path.join(LIBRARY_DIR, "*.mp3")))

# --- Helper: get video ID from URL ---
def extract_video_id(url):
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    return None

# --- Helper: get thumbnail ---
def get_thumbnail_url(video_id):
    if video_id:
        return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    return None

# --- Sidebar: Stats ---
mp3_files = get_mp3_files()
total_size = sum(os.path.getsize(f) for f in mp3_files) / (1024 * 1024)

with st.sidebar:
    st.header("📊 Stats")
    st.metric("Total Songs", len(mp3_files))
    st.metric("Total Size", f"{total_size:.1f} MB")
    st.divider()
    st.header("⭐ Favorites")
    if favorites:
        for fav in favorites:
            st.write(f"• {os.path.splitext(fav)[0]}")
    else:
        st.info("No favorites yet")
    st.divider()
    st.header("📂 Playlists")
    if playlists:
        for name, songs in playlists.items():
            st.write(f"• **{name}** ({len(songs)} songs)")
    else:
        st.info("No playlists yet")

# --- Download Section ---
st.header("📥 Download Music")

dl_mode = st.radio("Mode", ["Single Video", "Playlist"], horizontal=True)
url = st.text_input("Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("⬇️ Download as MP3"):
    if not url.strip():
        st.warning("Please enter a valid YouTube URL.")
    elif not ffmpeg_available:
        st.error("ffmpeg not found. Cannot convert to MP3.")
    else:
        progress_bar = st.progress(0, text="Starting download...")
        status_text = st.empty()

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                downloaded = d.get("downloaded_bytes", 0)
                pct = min(downloaded / total, 1.0)
                progress_bar.progress(pct, text=f"Downloading... {pct*100:.0f}%")
            elif d["status"] == "finished":
                progress_bar.progress(1.0, text="Converting to MP3...")
                status_text.text("Converting audio...")

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": os.path.join(LIBRARY_DIR, "%(title)s.%(ext)s"),
            "noplaylist": dl_mode == "Single Video",
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if dl_mode == "Playlist" and "entries" in info:
                    count = len(list(info["entries"]))
                    st.success(f"✅ Downloaded {count} songs from playlist!")
                else:
                    title = info.get("title", "Unknown")
                    st.success(f"✅ Downloaded: **{title}**")
            st.rerun()
        except yt_dlp.utils.DownloadError as e:
            st.error(f"Download failed: {e}")
        except Exception as e:
            st.error(f"Error: {e}")

if not ffmpeg_available:
    with st.expander("⚠️ ffmpeg Not Found - Install Instructions"):
        st.markdown("""
        1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
        2. Extract to `C:\\ffmpeg`
        3. Add `C:\\ffmpeg\\bin` to your PATH
        4. Restart terminal and verify: `ffmpeg -version`
        """)

# --- Library Section ---
st.header("📚 Your Library")

col_search, col_sort = st.columns([3, 1])
with col_search:
    search_query = st.text_input("🔍 Search songs:", placeholder="Type to filter...")
with col_sort:
    sort_by = st.selectbox("Sort by", ["Name A-Z", "Name Z-A", "Size (Big)", "Size (Small)"])

mp3_files = get_mp3_files()

# Filter
if search_query:
    mp3_files = [f for f in mp3_files if search_query.lower() in os.path.basename(f).lower()]

# Sort
if sort_by == "Name A-Z":
    mp3_files.sort(key=lambda x: os.path.basename(x).lower())
elif sort_by == "Name Z-A":
    mp3_files.sort(key=lambda x: os.path.basename(x).lower(), reverse=True)
elif sort_by == "Size (Big)":
    mp3_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
elif sort_by == "Size (Small)":
    mp3_files.sort(key=lambda x: os.path.getsize(x))

if not mp3_files:
    st.info("No songs found. Download something above!")
else:
    # Queue management
    if "queue" not in st.session_state:
        st.session_state.queue = []

    if st.button("▶️ Play All Sequentially"):
        st.session_state.queue = list(mp3_files)
        st.rerun()

    if st.session_state.queue:
        st.info(f"Queue: {len(st.session_state.queue)} songs")
        if st.button("Clear Queue"):
            st.session_state.queue = []
            st.rerun()

    for i, filepath in enumerate(mp3_files):
        filename = os.path.basename(filepath)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        name_no_ext = os.path.splitext(filename)[0]
        is_fav = filename in favorites

        video_id = extract_video_id(name_no_ext)
        thumbnail = get_thumbnail_url(video_id)

        col1, col2, col3, col4, col5, col6 = st.columns([1, 4, 1, 1, 1, 1])

        with col1:
            if thumbnail:
                st.image(thumbnail, width=60)

        with col2:
            st.markdown(f"**{name_no_ext}**")
            st.caption(f"{size_mb:.1f} MB")

        with col3:
            with open(filepath, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3")

        with col4:
            st.download_button(
                "⬇️",
                data=audio_bytes,
                file_name=filename,
                mime="audio/mpeg",
                key=f"dl_{i}",
            )

        with col5:
            fav_label = "💔" if is_fav else "❤️"
            if st.button(fav_label, key=f"fav_{i}"):
                if is_fav:
                    favorites.remove(filename)
                else:
                    favorites.append(filename)
                save_json(FAVORITES_FILE, favorites)
                st.rerun()

        with col6:
            if st.button("🗑️", key=f"del_{i}"):
                os.remove(filepath)
                if filename in favorites:
                    favorites.remove(filename)
                    save_json(FAVORITES_FILE, favorites)
                for pl_name in playlists:
                    if filename in playlists[pl_name]:
                        playlists[pl_name].remove(filename)
                save_json(PLAYLISTS_FILE, playlists)
                st.rerun()

        # Rename
        with st.expander(f"✏️ Rename {name_no_ext}"):
            new_name = st.text_input("New name:", value=name_no_ext, key=f"rename_{i}")
            if st.button("Save", key=f"save_{i}"):
                new_path = os.path.join(LIBRARY_DIR, f"{new_name}.mp3")
                if new_path != filepath:
                    os.rename(filepath, new_path)
                    if filename in favorites:
                        favorites[favorites.index(filename)] = f"{new_name}.mp3"
                        save_json(FAVORITES_FILE, favorites)
                    for pl_name in playlists:
                        if filename in playlists[pl_name]:
                            playlists[pl_name][playlists[pl_name].index(filename)] = f"{new_name}.mp3"
                    save_json(PLAYLISTS_FILE, playlists)
                    st.rerun()

        # Add to playlist
        with st.expander(f"📂 Add to playlist"):
            pl_name = st.selectbox("Playlist:", ["-- Select --"] + list(playlists.keys()), key=f"pl_sel_{i}")
            if pl_name != "-- Select --":
                if st.button("Add", key=f"pl_add_{i}"):
                    if filename not in playlists[pl_name]:
                        playlists[pl_name].append(filename)
                        save_json(PLAYLISTS_FILE, playlists)
                        st.success(f"Added to {pl_name}")
                        st.rerun()

        st.divider()

# --- Create Playlist ---
st.header("📂 Playlists")
new_pl = st.text_input("New playlist name:", placeholder="My Playlist")
if st.button("Create Playlist"):
    if new_pl.strip() and new_pl not in playlists:
        playlists[new_pl.strip()] = []
        save_json(PLAYLISTS_FILE, playlists)
        st.rerun()

for pl_name, songs in list(playlists.items()):
    with st.expander(f"📁 {pl_name} ({len(songs)} songs)"):
        if not songs:
            st.info("Empty playlist")
        else:
            for song in songs:
                song_path = os.path.join(LIBRARY_DIR, song)
                if os.path.exists(song_path):
                    col_a, col_b, col_c = st.columns([4, 1, 1])
                    with col_a:
                        st.write(song)
                    with col_b:
                        with open(song_path, "rb") as f:
                            st.audio(f.read(), format="audio/mp3")
                    with col_c:
                        if st.button("Remove", key=f"pl_rm_{pl_name}_{song}"):
                            playlists[pl_name].remove(song)
                            save_json(PLAYLISTS_FILE, playlists)
                            st.rerun()
                else:
                    st.write(f"⚠️ {song} (file missing)")
        if st.button(f"Delete Playlist: {pl_name}", key=f"pl_del_{pl_name}"):
            del playlists[pl_name]
            save_json(PLAYLISTS_FILE, playlists)
            st.rerun()

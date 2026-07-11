import streamlit as st
import yt_dlp
import os
import subprocess
import glob
import base64

LIBRARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Library")

os.makedirs(LIBRARY_DIR, exist_ok=True)

st.set_page_config(page_title="Private Music Server", page_icon="🎵", layout="wide")

st.title("🎵 Private Music Server")
st.markdown("Download YouTube videos as MP3 and stream them from your personal library.")

# --- FFmpeg Check ---
def check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

ffmpeg_available = check_ffmpeg()

# --- Download Section ---
st.header("📥 Download Music")

url = st.text_input("Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("⬇️ Download as MP3"):
    if not url.strip():
        st.warning("Please enter a valid YouTube URL.")
    elif not ffmpeg_available:
        st.error(
            "ffmpeg is not installed or not in your PATH. "
            "MP3 conversion requires ffmpeg. See instructions below."
        )
    else:
        with st.spinner("Downloading and converting to MP3..."):
            try:
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
                    "noplaylist": True,
                    "quiet": True,
                    "no_warnings": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Unknown")
                st.success(f"✅ Downloaded: **{title}**")
                st.rerun()
            except yt_dlp.utils.DownloadError as e:
                st.error(f"Download failed: {e}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- FFmpeg Instructions ---
if not ffmpeg_available:
    st.header("⚠️ ffmpeg Not Found")
    st.markdown(
        """
        ffmpeg is required to convert audio to MP3. Follow these steps:

        1. **Download ffmpeg** for Windows from the official builds:
           - https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

        2. **Extract the zip** to a permanent location, e.g. `C:\\ffmpeg`.

        3. **Add ffmpeg to your PATH**:
           - Open the Start Menu, search for "Environment Variables".
           - Click "Edit the system environment variables".
           - Click "Environment Variables...".
           - Under "System variables", find `Path` and click "Edit".
           - Click "New" and add the path to the `bin` folder, e.g. `C:\\ffmpeg\\bin`.
           - Click "OK" on all dialogs.

        4. **Restart your terminal** (and Streamlit) for the changes to take effect.

        5. **Verify** by running `ffmpeg -version` in a new terminal window.
        """
    )

# --- Library Section ---
st.header("📚 Your Library")

mp3_files = sorted(glob.glob(os.path.join(LIBRARY_DIR, "*.mp3")))

if not mp3_files:
    st.info("No MP3 files in your library yet. Download something above!")
else:
    st.markdown(f"**{len(mp3_files)}** file(s) in your library:")

    # Build table
    for filepath in mp3_files:
        filename = os.path.basename(filepath)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        col1, col2, col3 = st.columns([5, 1, 1])

        with col1:
            st.markdown(f"**{filename}** ({size_mb:.1f} MB)")

        with col2:
            # Audio player
            with open(filepath, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3")

        with col3:
            # Download button
            st.download_button(
                label="⬇️ Download",
                data=audio_bytes,
                file_name=filename,
                mime="audio/mpeg",
                key=f"dl_{filename}",
            )

import subprocess
import os
from django.core.files import File

def compress_video(input_path, output_path):
    command = [
        "ffmpeg",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", "28",  # lower = better quality, bigger file
        "-preset", "veryfast",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(command, check=True)
    return output_path

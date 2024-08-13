import glob
from pathlib import Path
import re
from datetime import datetime
from tqdm import tqdm
import sys
import os

# this version creates one video per day, not topic dependent

def main():
    move_screenshots_of_each_session_into_frames_folder()
    create_video_for_each_session()

def string_to_python_datetime(string):
    string = '_'.join(string.split('_')[:2])
    return datetime.strptime(string, '%Y-%m-%d_%H-%M-%S')

def python_datetime_to_string(dt):
    return dt.strftime('%Y-%m-%d_%H-%M-%S')


def move_screenshots_of_each_session_into_frames_folder():
    # for each practice session, move the screenshots into the folder
    screenshots = glob.glob('/home/b/GITHUB/deliberate-practice-recordings/screenshots/*.png')
    sorted_screenshot_files = sorted(screenshots, key=lambda x: Path(x).stem)
    for screenshot in tqdm(sorted_screenshot_files):
        # 2024-05-31_20-59-13.png
        filename = Path(screenshot).stem
        timestamp = string_to_python_datetime(filename)
        # folder is simply the date (without time)
        # if folder doesn't exist yet, create
        folder_name = python_datetime_to_string(timestamp).split('_')[0]
        if not os.path.exists(f'frames/{folder_name}'):
            os.makedirs(f'frames/{folder_name}')

      
        # move (not just copy!!) screenshot into correct frames folder
        target_folder = f'frames/{folder_name}/'
        os.system(f'mv {screenshot} {target_folder}')


def create_video_for_each_session():
    # every date folder should have a video
    all_folders = glob.glob('frames/*')
    for folder in all_folders:
        # if folder is empty, skip
        if len(glob.glob(folder + "/*.png")) == 0:
            continue
        # if  date is current, skip:
        if python_datetime_to_string(datetime.now()).split('_')[0] in folder:
            continue
        # skip if file file exists
        video_path = f"videos/{folder.split('/')[1]}.mp4"
        if os.path.isfile(video_path):
            print("video already exists")
        else:
            print(f'making video for {folder} with {len(glob.glob(folder + "/*.png"))} frames')
            os.system(f'ffmpeg -framerate 8 -pattern_type glob -i "{folder}/*.png" -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -c:v libx264 -pix_fmt yuv420p -y "{video_path}"')
            os.system(f'rm -r {folder}')


if __name__ == '__main__':
    main()
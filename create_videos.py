import os
import glob
from pathlib import Path

import re

from datetime import datetime

from pony.orm import *
from tqdm import tqdm
import sys


def legacy_main():

    topics = []

    # loop topics folder
    all_topic_files = glob.glob('topics/*.txt')
    for topic_file in sorted(all_topic_files):
        # file contains topic name
        with open(topic_file, 'r') as f:
            topics.append([Path(topic_file).stem, f.read()])

    # make a folder in frames for each topic
    for topic in topics:
        folder_name = topic[0]
        Path(f'frames/{folder_name}').mkdir(parents=True, exist_ok=True)

    next_topic = topics[0]
    current_topic = None
    current_cutoff_timestamp = datetime.strptime(next_topic[0], '%Y-%m-%d_%H-%M-%S')
    current_index = -1
    all_frames = glob.glob('/home/b/GITHUB/deliberate-practice-recordings/screenshots/*.png')
    sorted_files = sorted(all_frames, key=lambda x: Path(x).stem)
    # print("All frames: ", all_frames)
    for frame in sorted(all_frames):
        # frames have timestamp.png format
        # copy into the right frames/ subfolder

        # first, check if we need to switch to a new folder
        # need only to check next topic in list

        # first check if we're at the end of the list
        if current_index < len(topics) - 1:
            # TODO: topic switch seems not entirely reliable, even though order of files should now be forced...
            # prob. just load in the actual datetime and do a proper comparison
            stemmed_path = Path(frame).stem
            # timestamp is format 2024-05-09_11-39-11
            timestamp = datetime.strptime(stemmed_path, '%Y-%m-%d_%H-%M-%S')
            if timestamp > current_cutoff_timestamp:
                current_topic = next_topic
                next_topic = topics[current_index + 1]
                current_index += 1
                current_cutoff_timestamp = datetime.strptime(next_topic[0], '%Y-%m-%d_%H-%M-%S')
        if current_topic is None:
            continue
            
        
        # copy frame into current_folder
        os.system(f'mv {frame} frames/{current_topic[0]}/')
        

    # create video for each topic
    # for each topic, create a video with `ffmpeg -framerate 5 -pattern_type glob -i '*.png' out.mp4`
    for topic in topics:
        # TODO: slap in the more pleasant replacer, with the unicode hacks `fe55` and what not before this, only then clear out the rest
        video_name = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "-", topic[1])
        video_path = f"videos/{topic[0]}-{video_name}.mp4"
        # skip if file file exists
        if os.path.isfile(video_path):
            print("video already exists")
        else:
            os.system(f'ffmpeg -framerate 8 -pattern_type glob -i "frames/{topic[0]}/*.png" -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -c:v libx264 -pix_fmt yuv420p -y "{video_path}"')
            # also create analysis file in /home/b/MEGA/Obsidian/Zettelkasten/DP
            with open(f'/home/b/MEGA/Obsidian/Zettelkasten/DP/{topic[0]}-{video_name}.md', 'w') as f:
                # copy contents from /home/b/MEGA/Obsidian/Zettelkasten/Templates/DP.md
                with open('/home/b/MEGA/Obsidian/Zettelkasten/Templates/DP.md', 'r') as template:
                    f.write(template.read())
            # delete frames folder
            os.system(f'rm -r frames/{topic[0]}')




def main():
    db = Database()
    db.bind(provider='sqlite', filename='db.sqlite', create_db=True)

    be_quick = sys.argv[1] == 'quick' if len(sys.argv) > 1 else False

    class PracticeSession(db.Entity):
        topic = Required(str)
        started_at = Required(datetime)
        following_session = Optional('PracticeSession')
        last_session = Optional('PracticeSession')

        folder_in_frames_was_created = Required(bool, default=False)
        screenshots_were_moved = Required(bool, default=False)
        video_was_created = Required(bool, default=False)
        analysis_file_was_created = Required(bool, default=False)

    db.generate_mapping(create_tables=True)

    # actual process
    create_practice_sessions_from_topic_files(db)
    set_next_session_for_each_session(db)
    create_folders_for_frames_from_sessions(db)
    move_screenshots_of_each_session_into_frames_folder(db, be_quick)
    create_video_for_each_session(db, be_quick)
    create_analysis_file_for_each_session(db)

def string_to_python_datetime(string):
    return datetime.strptime(string, '%Y-%m-%d_%H-%M-%S')

def python_datetime_to_string(dt):
    return dt.strftime('%Y-%m-%d_%H-%M-%S')

@db_session
def create_practice_sessions_from_topic_files(db):
    # ONLY!! create the practice sessions, no other actions
    topics = []

    # loop topics folder
    all_topic_files = glob.glob('topics/*.txt')
    for topic_file in sorted(all_topic_files):
        # file contains topic name
        with open(topic_file, 'r') as f:
            topics.append([Path(topic_file).stem, f.read()])

    for topic in enumerate(topics):
        # create a new PracticeSession if it does not exist
        if not db.PracticeSession.exists(topic=topic[1][1]):
            db.PracticeSession(topic=topic[1][1], started_at=string_to_python_datetime(topic[1][0]))


def get_next_datetime_from_list(dt, dt_list):
    # I pass in a datetime (dt)
    # I also pass in a list of datetimes, which may include dt
    # I want the smallest datetime from the list that is BIGGER than dt:

    # first, sort the list
    dt_list.sort()
    # then, find the index of dt
    index = dt_list.index(dt)
    # then, return the next index (if it exists, otherwise return None)
    if index + 1 < len(dt_list):
        return dt_list[index + 1]
    else:
        return None

@db_session
def set_next_session_for_each_session(db):
    # for each practice session, set the next session
    all_sessions = db.PracticeSession.select()
    all_datetimes = [session.started_at for session in all_sessions]
    for session in all_sessions:
        next_datetime = get_next_datetime_from_list(session.started_at, all_datetimes)
        if next_datetime is not None:
            next_session = db.PracticeSession.get(started_at=next_datetime)
            session.following_session = next_session


@db_session
def create_folders_for_frames_from_sessions(db):
    # for each practice session, create a folder in frames
    all_sessions = db.PracticeSession.select()
    for session in all_sessions:
        folder_name = python_datetime_to_string(session.started_at)
        Path(f'frames/{folder_name}').mkdir(parents=True, exist_ok=True)
        session.folder_in_frames_was_created = True

@db_session
def move_screenshots_of_each_session_into_frames_folder(db, be_quick):
    # for each practice session, move the screenshots into the folder
    all_sessions = db.PracticeSession.select()
    screenshots = glob.glob('/home/b/GITHUB/deliberate-practice-recordings/screenshots/*.png')
    sorted_screenshot_files = sorted(screenshots, key=lambda x: Path(x).stem)
    number_of_sessions_treated = 0
    last_session = None
    for screenshot in tqdm(sorted_screenshot_files):
        # 2024-05-31_20-59-13.png
        filename = Path(screenshot).stem
        timestamp = string_to_python_datetime(filename)
        session = get_session_in_which_a_screenshot_belongs(db, timestamp)
        if session is not last_session:
            last_session = session
            number_of_sessions_treated += 1
            if be_quick and number_of_sessions_treated > 1:
                break
        # move (not just copy!!) screenshot into correct frames folder
        target_folder = f'frames/{python_datetime_to_string(session.started_at)}/'
        os.system(f'mv {screenshot} {target_folder}')
        session.screenshots_were_moved = True

def get_session_in_which_a_screenshot_belongs(db, timestamp):
    all_sessions = db.PracticeSession.select()
    for session in all_sessions:
        if session.started_at <= timestamp:
            if session.following_session is None:
                return session
            elif session.following_session.started_at > timestamp:
                return session
    return None

@db_session
def create_video_for_each_session(db, be_quick):
    # for each practice session, create a video
    # only sessions where screenshots were moved, but video was not created
    all_sessions = db.PracticeSession.select(lambda s: s.screenshots_were_moved and not s.video_was_created)
    for session in all_sessions:
        # skip if file file exists
        video_path = f"videos/{session.topic}.mp4"
        if os.path.isfile(video_path):
            print("video already exists")
        else:
            os.system(f'ffmpeg -framerate 8 -pattern_type glob -i "frames/{python_datetime_to_string(session.started_at)}/*.png" -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -c:v libx264 -pix_fmt yuv420p -y "{video_path}"')
            os.system(f'rm -r frames/{python_datetime_to_string(session.started_at)}')
            session.video_was_created = True
            if be_quick:
                break

@db_session
def create_analysis_file_for_each_session(db):
    # for each practice session, create an analysis file
    # only sessions where video was created, but analysis file was not created
    all_sessions = db.PracticeSession.select(lambda s: s.video_was_created and not s.analysis_file_was_created)
    for session in all_sessions:
        # also create analysis file in /home/b/MEGA/Obsidian/Zettelkasten/DP
        with open(f'/home/b/MEGA/Obsidian/Zettelkasten/DP/{session.topic}.md', 'w') as f:
            # copy contents from /home/b/MEGA/Obsidian/Zettelkasten/Templates/DP.md
            with open('/home/b/MEGA/Obsidian/Zettelkasten/Templates/DP.md', 'r') as template:
                f.write(template.read())
            session.analysis_file_was_created = True


if __name__ == '__main__':
    main()
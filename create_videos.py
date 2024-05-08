import os
import glob
from pathlib import Path

import re

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
    os.system(f'mkdir frames/{topic[0]}')

# loop ~/Pictures/timelapse
current_topic = None
next_topic = topics[0]
current_index = -1
all_frames = glob.glob('/home/b/GITHUB/deliberate-practice-recordings/screenshots/*.png')
# print("All frames: ", all_frames)
for frame in sorted(all_frames):
    # frames have timestamp.png format
    # copy into the right frames/ subfolder

    # first, check if we need to switch to a new folder
    # need only to check next topic in list

    # first check if we're at the end of the list
    if current_index < len(topics):
        # TODO: topic switch seems not entirely reliable, even though order of files should now be forced...
        # prob. just load in the actual datetime and do a proper comparison
        stemmed_path = Path(frame).stem
        if stemmed_path in next_topic[0]:
            current_topic = next_topic
            current_index += 1
            if current_index != len(topics) - 1:
                next_topic = topics[current_index + 1]
    if current_topic is None:
        continue
        
    
    # copy frame into current_folder
    # TODO: when confident nothing breaks, make more definite by moving
    # TODO: also find out if this actually the slow part, if so, look into speeding up
    os.system(f'cp {frame} frames/{current_topic[0]}/')
    

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
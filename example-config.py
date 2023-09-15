# Rename this file to config.py and fill in the values below
# cp example-config.py config.py

import os
import re


current_dir = os.path.dirname(os.path.realpath(__file__))
tools_dir = os.path.join(current_dir, "Tools")
icon_path = os.path.join(current_dir, "icon.ico")
ffmpeg_path = os.path.join(tools_dir, "ffmpeg.exe")
ffprobe_path = os.path.join(tools_dir, "ffprobe.exe")
ffplay_path = os.path.join(tools_dir, "ffplay.exe")
fpcalc_path = os.path.join(tools_dir, "fpcalc.exe")
mkvmerge_path = os.path.join(tools_dir, "mkvmerge.exe")

ENGLISH_VARIATIONS = ['eng', 'english', 'english dub', 'inglês', 'en', 'en-us', '英語', 'anglais']

username="username"
password="password"
remote_host="192.168.255.255"
plex_internal_path="/mnt/user/Media/Plex/"
dizquetv_container_name = "dizquetv-1"
dizquetv_channel_number = "1"


START_BUFFER = 45
sleep_time = 1
Levenshtein_threshold = 0.8
FRAME_RATE = 24
DOWNSCALE_HEIGHT = 80
BLACK_FRAME_THRESHOLD = 5
TIMESTAMP_THRESHOLD = 120
BATCH_SIZE = 5
SILENCE_DURATION = 0.3
DECIBEL_THRESHOLD = -60
API_KEY = "PUT YOUR OPEN AI KEY HERE"

TOONAMI_CONFIG = {
    "OG": {"table": "lineup_v9", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9", "encoder_in": "commercial_injector_final"},
    "2": {"table": "lineup_v2", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2", "encoder_in": "commercial_injector_final"},
    "3": {"table": "lineup_v3", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3", "encoder_in": "commercial_injector_final"},
    "Mixed": {"table": "lineup_v8", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8", "encoder_in": "commercial_injector_final"},
    "Uncut OG": {"table": "lineup_v9_uncut", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9_uncut", "encoder_in": "uncut_encoded_data"},
    "Uncut 2": {"table": "lineup_v2_uncut", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2_uncut", "encoder_in": "uncut_encoded_data"},
    "Uncut 3": {"table": "lineup_v3_uncut", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3_uncut", "encoder_in": "uncut_encoded_data"},
    "Uncut Mixed": {"table": "lineup_v8_uncut", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8_uncut", "encoder_in": "uncut_encoded_data"},
}

TOONAMI_CONFIG_CONT = {
    "OG": {"table": "lineup_v9", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9_cont", "encoder_in": "commercial_injector_final"},
    "2": {"table": "lineup_v2", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2_cont", "encoder_in": "commercial_injector_final"},
    "3": {"table": "lineup_v3", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3_cont", "encoder_in": "commercial_injector_final"},
    "Mixed": {"table": "lineup_v8", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8_cont", "encoder_in": "commercial_injector_final"},
    "Uncut OG": {"table": "lineup_v9_uncut", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9_uncut_cont", "encoder_in": "uncut_encoded_data"},
    "Uncut 2": {"table": "lineup_v2_uncut", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2_uncut_cont", "encoder_in": "uncut_encoded_data"},
    "Uncut 3": {"table": "lineup_v3_uncut", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3_uncut_cont", "encoder_in": "uncut_encoded_data"},
    "Uncut Mixed": {"table": "lineup_v8_uncut", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8_uncut_cont", "encoder_in": "uncut_encoded_data"},
}

URLS = [
    'https://www.imdb.com/list/ls573256740/?sort=alpha,asc&st_dt=&mode=detail&page=1',
    'https://www.imdb.com/list/ls573256740/?sort=alpha,asc&st_dt=&mode=detail&page=2'
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

keywords = [
    #singles
    "Back",
    "To Ads",
    "Generic",
    "Intro",
    "Next From",
    #triples
    "Later",
    "Now",
    "Next",    #singles and triples
    #doubles
    "From",

]

colors = [
    "Blue", "Red", "Green", "Orange"
]

show_name_mapping = {
    'big o': 'the big o',
    'dbz': 'dragon ball z',
    'dbz kai': 'dragon ball z kai',
    'dbz kai the final chapters': 'dragon ball z kai the final chapters',
    'deadman': 'deadman Wonderland',
    'dead man wonderland': 'deadman Wonderland',
    'dead mans wonderland': 'deadman Wonderland',
    'eurika 7': 'eureka seven',
    'eureka 7': 'eureka seven',
    'evangelion': 'neon genesis evangelion',
    'evangelion 1.11': 'neon genesis evangelion one eleven',
    'evangelion 1 11': 'neon genesis evangelion one eleven',
    'evangelion 2.22': 'neon genesis evangelion two twenty two',
    'evangelion 2 22': 'neon genesis evangelion two twenty two',
    'fma': 'fullmetal alchemist',
    'fmab': 'fullmetal alchemist - brotherhood',
    'fullmetal alchemist brotherhood': 'fullmetal alchemist - brotherhood',
    'fullmetal alchemist  brotherhood': 'fullmetal alchemist - brotherhood',
    'gitssac': 'ghost in the shell - stand alone complex',
    'ghost in the shell stand alone complex': 'ghost in the shell - stand alone complex',
    'gits sac': 'ghost in the shell - stand alone complex',
    'ghost in the shell - stand alone complex': 'ghost in the shell - stand alone complex',
    'ghost in the shell sac': 'ghost in the shell - stand alone complex',
    'gitssac 2nd gig': 'ghost in the shell sac 2nd gig',
    'samurai 7': 'samurai seven',
    'samari 7': 'samurai seven',
    'sao': 'sword art online',
    'sword art': 'sword art online',
    'yu yu hakusho ghost files' : 'yu yu hakusho',
    'naruto 2002': 'naruto',
    'naturo': 'naruto',
        }

genric_bumps = ['clydes', 'robot', 'robots', 'robot', 'robot 1', 'robot 2', 'robot 3', 'robot 4', 'robot 5', 'robot 6', 'robot 7', 'robot 8', 'robot 9', 'robot 10']

part_a = [
    "Bursting", "Hidden", "Expansive", "Boundless", "Closed", "Quiet",
    "Plenteous", "Collapsed", "Cursed", "Buried", "Lonely", "Great",
    "Chosen", "Discovered", "Indiscreet", "Putrid", "Hideous", "Soft",
    "Beautiful", "Raging", "Noisy", "Dog Dancing", "Rejecting", "Sleepy",
    "Sinking", "Greedy", "Voluptuous", "Detestable", "Chronicling"
]

part_b = [
    "Passed Over", "Forbidden", "Haunted", "Corrupted", "Oblivious", "Eternal",
    "Smiling", "Momentary", "Pagan", "Hopeless", "Primitive", "Gluttonous",
    "Hot-Blooded", "Destroyer's", "Solitary", "Someone's", "Her", "Law's",
    "Talisman", "Orange", "Organ Market", "Agonizing", "Geothermal", "Golden",
    "Passionate"
]

part_c = [
    "Aqua Field", "Holy Ground", "Sea of Sand", "Fort Walls", "Twin Hills",
    "White Devil", "Hypha", "Spiral", "Paradise", "Fiery Sands", "Great Seal",
    "Fertile Land", "Nothingness", "Melody", "Remnant", "March", "Touchstone",
    "Sunny Demon", "Messenger", "Scent", "New Truth", "Pilgrimage", "Scaffold",
    "Far Thunder", "Tri Pansy", "Treasure Gem"
]
import os
# Rename this file to config.py and fill in the values below
# cp example-config.py config.py
# put the name of your network here e.g "Toonami" or "Disney"
network = "Toonami"
current_dir = __file__.rstrip('config.py')
tools_dir = current_dir + "Tools/"
icon_path = current_dir + "icon.ico"
ffmpeg_path = tools_dir + "ffmpeg.exe"
ffprobe_path = tools_dir + "ffprobe.exe"
ffplay_path = tools_dir + "ffplay.exe"
fpcalc_path = tools_dir + "fpcalc.exe"
mkvmerge_path = tools_dir + "mkvmerge.exe"
ENGLISH_VARIATIONS = ['eng', 'english', 'english dub', 'inglês', 'en', 'en-us', '英語', 'anglais']
cutless_mode = True

DATABASE_DIR = os.environ.get("DB_DIR") or os.path.dirname(__file__)
DATABASE_PATH = os.environ.get("DB_PATH") or os.path.join(DATABASE_DIR, f'{network}.db')
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

username="username"
password="password"
remote_host="192.168.255.255"
plex_internal_path="/mnt/user/Media/Plex/"
dizquetv_container_name = "dizquetv-1"
dizquetv_channel_number = "1"


START_BUFFER = 60
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

AUTO_RUN_DEFAULT_CONFIG = {
    "anime_library_name": "Anime",
    "bumps_library_name": "Bumps",
    "low_power_mode": True,
    "fast_mode": False,
    "destructive_mode": False,
    "cutless_mode": True,
    "toonami_version": "Mixed",
    "channel_number": "69",
    "flex_duration": "3:00",
    "platform_type": "dizquetv"
}

TOONAMI_CONFIG = {
    "OG": {"table": "lineup_v9", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9", "encoder_in": "commercial_injector_final", "uncut": False},
    "2": {"table": "lineup_v2", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2", "encoder_in": "commercial_injector_final", "uncut": False},
    "3": {"table": "lineup_v3", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3", "encoder_in": "commercial_injector_final", "uncut": False},
    "Mixed": {"table": "lineup_v8", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8", "encoder_in": "commercial_injector_final", "uncut": False},
    "Uncut OG": {"table": "lineup_v9_uncut", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9_uncut", "encoder_in": "uncut_encoded_data", "uncut": True},
    "Uncut 2": {"table": "lineup_v2_uncut", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2_uncut", "encoder_in": "uncut_encoded_data", "uncut": True},
    "Uncut 3": {"table": "lineup_v3_uncut", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3_uncut", "encoder_in": "uncut_encoded_data", "uncut": True},
    "Uncut Mixed": {"table": "lineup_v8_uncut", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8_uncut", "encoder_in": "uncut_encoded_data", "uncut": True},
}

TOONAMI_CONFIG_CONT = {
    "OG": {"table": "lineup_v9", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9_cont", "encoder_in": "commercial_injector_final", "uncut": False},
    "2": {"table": "lineup_v2", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2_cont", "encoder_in": "commercial_injector_final", "uncut": False},
    "3": {"table": "lineup_v3", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3_cont", "encoder_in": "commercial_injector_final", "uncut": False},
    "Mixed": {"table": "lineup_v8", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8_cont", "encoder_in": "commercial_injector_final", "uncut": False},
    "Uncut OG": {"table": "lineup_v9_uncut", "merger_bump_list": "multibumps_v9_data_reordered", "merger_out": "lineup_v9_uncut_cont", "encoder_in": "uncut_encoded_data", "uncut": True},
    "Uncut 2": {"table": "lineup_v2_uncut", "merger_bump_list": "multibumps_v2_data_reordered", "merger_out": "lineup_v2_uncut_cont", "encoder_in": "uncut_encoded_data", "uncut": True},
    "Uncut 3": {"table": "lineup_v3_uncut", "merger_bump_list": "multibumps_v3_data_reordered", "merger_out": "lineup_v3_uncut_cont", "encoder_in": "uncut_encoded_data", "uncut": True},
    "Uncut Mixed": {"table": "lineup_v8_uncut", "merger_bump_list": "multibumps_v8_data_reordered", "merger_out": "lineup_v8_uncut_cont", "encoder_in": "uncut_encoded_data", "uncut": True},
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
    #triples
    "Later",
    "Now",
    "Next",    #singles and triples
    #doubles
    "From",
    "Next From",

]

colors = [
    "Blue", "Red", "Green", "Orange"
]

show_name_mapping = {
    'batman animated series': 'batman the animated series',
    'big o': 'the big o',
    'bobobo bo bo bobo': 'bobobo-bo bo-bobo',
    'bobobobo bobobo': 'bobobo-bo bo-bobo',
    'dbz': 'dragon ball z',
    'dbz kai': 'dragon ball z kai',
    'dbz kai the final chapters': 'dragon ball z kai the final chapters',
    'dead man wonderland': 'deadman wonderland',
    'dead mans wonderland': 'deadman wonderland',
    'deadman': 'deadman wonderland',
    'dragon ball z kai final chapters': 'dragon ball z kai the final chapters',
    'eurika 7': 'eureka seven',
    'eureka 7': 'eureka seven',
    'evangelion': 'neon genesis evangelion',
    'evangelion 1 11': 'neon genesis evangelion one eleven',
    'evangelion 1.11': 'neon genesis evangelion one eleven',
    'evangelion 2 22': 'neon genesis evangelion two twenty two',
    'evangelion 2.22': 'neon genesis evangelion two twenty two',
    'fma': 'fullmetal alchemist',
    'fmab': 'fullmetal alchemist - brotherhood',
    'food wars shokugeki no soma': 'food wars',
    'fullmetal alchemist  brotherhood': 'fullmetal alchemist - brotherhood',
    'fullmetal alchemist brotherhood': 'fullmetal alchemist - brotherhood',
    'ghost in the shell sac': 'ghost in the shell - stand alone complex',
    'ghost in the shell stand alone complex': 'ghost in the shell - stand alone complex',
    'ghost in the shell standalone complex': 'ghost in the shell - stand alone complex',
    'ghost in the shell - stand alone complex': 'ghost in the shell - stand alone complex',
    'gitssac': 'ghost in the shell - stand alone complex',
    'gitssac 2nd gig': 'ghost in the shell sac 2nd gig',
    'gits sac': 'ghost in the shell - stand alone complex',
    'naruto 2002': 'naruto',
    'naturo': 'naruto',
    'one punch man': 'one-punch man',
    'onepunch man': 'one-punch man',
    'powerpuff girls': 'the powerpuff girls 1998 series',
    'promised neverland': 'the promised neverland',
    'samari 7': 'samurai seven',
    'samurai 7': 'samurai seven',
    'sao': 'sword art online',
    'sword art': 'sword art online',
    'sword art online 2': 'sword art online ii',
    'tokyo ghoul root a': 'tokyo ghoul a',
    'yu yu hakusho ghost files': 'yu yu hakusho'
}

show_name_mapping_2 = {
'sword art online online' : 'sword art online',
'the the big o' : 'the big o',
'deadman wonderland wonderland': 'deadman wonderland',
'neon genesis neon genesis evangelion': 'neon genesis evangelion',
}

show_name_mapping_3 = {

}

video_file_types = [
    '.mp4',  # Common for various H.264 and H.265/HEVC videos
    '.mkv',  # Can include almost any video codec
    '.avi',  # Older container, supports various codecs like DivX and XviD
    '.mov',  # Apple QuickTime, often used with H.264 and ProRes
    '.wmv',  # Windows Media Video
    '.flv',  # Flash Video
    '.webm',  # Usually VP8 or VP9 video codec
    '.m4v',  # Similar to MP4, often used by Apple devices
    '.mpg', '.mpeg',  # MPEG-1 and MPEG-2 video formats
    '.3gp',  # Used on 3G mobile phones but also supported on some 2G and 4G phones
    '.m2ts', '.mts',  # AVCHD format used by camcorders
    '.ts',  # MPEG transport stream, used in broadcast
    '.vob',  # DVD Video Object
    '.ogv',  # Ogg format that may include Theora video codec
    '.mxf',  # Material Exchange Format for professional digital video and audio
    '.divx',  # Video codec and format popular for its ability to compress lengthy video segments
    '.xvid',  # Open-source MPEG-4 video codec
    '.f4v',  # Flash Video used in Adobe Flash
    '.h264', '.h265',  # Raw H.264 and H.265 video streams
    '.hevc',  # Another name for H.265, often used in raw streams
    '.asf',  # Advanced Systems Format, used for Windows Media Video
    '.rmvb', '.rm',  # RealMedia Variable Bitrate and RealMedia format
    '.qt'  # QuickTime File Format
]

generic_bumps = ['clydes', 'robot', 'robots', 'robot', 'robot 1', 'robot 2', 'robot 3', 'robot 4', 'robot 5', 'robot 6', 'robot 7', 'robot 8', 'robot 9', 'robot 10']

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
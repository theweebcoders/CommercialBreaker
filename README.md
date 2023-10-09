# CommercialBreaker & Toonami Tools: Because Your Anime Deserves Commercial Breaks

Hey there, space cowboy. Remember those long Toonami nights filled with anime and the oddly comforting interruption of commercials? Ever thought your sleek, ad-free Plex server felt a little too... smooth? Well, we've got the fix for you, because here, we're mixing the future with a splash of the past.

Welcome aboard the Absolution, where we're on a mission to boldly put the commercials back into your favorite anime. Why? Because we can. Because it's a kind of nostalgia that just feels right.

We've got two Python apps in our hyperdrive: CommercialBreaker and Toonami Tools. They'll slice up your anime and make room for those memory-ridden ads you secretly miss. Want your Plex server to feel like a marathon Toonami night? We got you. Got DizqueTV all set up? Even better.

So, who's the bigger otaku here? The person adding commercials back into their anime, or the mad scientist who spent a year and six months in the coding mines to make it happen? No matter, we're all in this giant robot together.

Until next time, stay gold.

# What it does

Toonami Tools and CommercialBreaker automate a continuous Toonami marathon.

Here's how it works:

  Provide a directory with multi-lineup bumps, transitional bumps, and shows.
  
  The marathon starts with a lineup bump, like "Toonami 2.0: Now Bleach, Next Naruto, Later One Piece."
  
  "Bleach" airs, with transitional bumps for commercials. AKA Bleach will be right back & Now more bleach
  
  After "Bleach," "Naruto" airs with its commercial transitions.
  
  The tools then select the next lineup bump starting with "One Piece," such as "Toonami 2.0: Now One Piece, Next Blue Exorcist, Later Black Lagoon."
  
  This pattern continues, using the end of one bump to determine the start of the next.

The result is an unbroken Toonami marathon, where multi-lineup bumps set the sequence and transitions connect each lineup smoothly.

The brilliance of these tools lies in their ability to create an unbroken Toonami marathon, using the multi-lineup bumps to define the sequence, and seamlessly connecting the end of one lineup to the beginning of another.

Here is what it will look like

![SampleLineup1](https://github.com/tim000x3/CommercialBreaker/assets/30919168/12c1ec40-b6dc-4b1f-9b6a-2abff97491ab)

![SampleLineup2](https://github.com/tim000x3/CommercialBreaker/assets/30919168/50a52cff-868c-4053-8b52-c6ff77e95804)

## The Lineup

**CommercialBreaker:** Just like alchemy, the science of deconstructing and reconstructing matter, CommercialBreaker is a Python application that works on your anime videos. It breaks down videos at points traditionally reserved for commercial breaks and reconstructs them, ready for your custom commercials. It's a true equivalent exchange, providing you with a transmutation circle for content management, especially for those who love a good old broadcast-style viewing experience. No philosopher's stone required!

**Toonami Tools:** Just like a trusty log pose guiding you to the next island on the Grand Line, Toonami Tools helps you navigate through the sea of your anime library. Designed for the most faithful of Toonami crews, this handy tool can generate a custom lineup of anime shows, creating an adventure akin to those golden days of the Toonami programming block. With its graphical user interface, you can effortlessly manage your anime and bump archives, effectively making you the captain of your anime collection. Worried about missing shows or bumps? Fear not! Toonami Tools is like your very own Going Mary, helping you fill in the gaps and complete your journey. So, ready to set sail, Toonami faithful?

All tools are accessible via the GUI (graphical user interface), making them easy to use for even the most novice pirates. So, what are you waiting for? Let's get started!

# Pre-Requisites

This application requires Python 3.11 and Git to be installed on your system. If not already installed, download and install [Python](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads). You also need an active internet connection to use the apps as they connect to IMDB. You can see the URLs in the config file.

# How to Install

Open a terminal and type the following commands one at a time: Each line is its own command

```bash

git clone https://github.com/tim000x3/CommercialBreaker.git

cd CommercialBreaker

pip install -r requirements.txt

cp example-config.py config.py

```
**Tip: Do not close the terminal window yet. You may see some warnings about PATH. You can most likely ignore these warnings**

This will create a folder in your home directory called CommercialBreaker. This folder will contain the CommercialBreaker program.

Create a folder in your home directory called "Tools."

Download ffmpeg, ffplay, and ffprobe from https://www.ffmpeg.org/ and put them in the Tools folder. The program calls the ffmpeg, ffplay, and ffprobe executables directly, so they need to be in the same folder as the program. (See FAQ)

**Note** If updateing from a previous version please delete config.py and run cp example-config.py config.py again

# How to Run

In the terminal window, type the following command:

```bash
python3 TOM.py
```
### Note: There is a GPTReadme in this folder. You should be able to copy and paste the entire thing into a ChatGPT prompt, and it will answer any questions you have if you don't want to read this.

# Support your local Mad Scientist
<a href="https://www.buymeacoffee.com/tim000x3" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

# How to use

TOM (Toonami Operations Module) is the GUI for the CommercialBreaker and Toonami Tools. It is the cockpit of your very own Toonami broadcast! It is the interface for all the tools in this pack. It is the bridge of the Absolution. It is the command center of your Toonami invasion. It is the... you get the idea. It's the GUI.

Welcome to the cockpit of your very own Toonami broadcast! Main.py is not just a script; it's the TOM (Toonami Operations Module) that pilots your anime universe. Guided by a sleek Tkinter GUI, it's your interactive dashboard for navigating through the asteroid field of options and commands. Like TOM communicating with the Absolution's AI, SARA, this script serves as your interface for rallying the troops—each specialized tool in your arsenal—to execute their designated missions.

From the bridge of this command center, you can engage with your Plex server, select your libraries, and initiate the journey. Once the coordinates are set, Main.py takes you into hyperspace, activating each tool in sequence, be it the Clydes in LoginToPlex.py or the hyperdrive in PlexToDizqueTV.py.

So gear up, Space Cowboy, because with this tool, you're not just watching anime; you're launching a Toonami invasion right from your living room.

Please read the FAQ before using this program. It will save you a lot of time and headaches.

## Step 1 - Login to Plex - Welcome to the Absolution

**Step 1** Login with Plex

Very simple click the "Login with Plex" button, and a browser window will open. Log in to your Plex account and click "Allow" when prompted. You will be redirected to a page that says "Success!" You can close this window.

**Step 2** Select your Plex Server

Click the dropdown menu labeled "Select a Plex Server" and select the Plex server you want to use. If you only have one Plex server, you still might need to click the drop-down menu and select the only option.

**Step 3** Select your Anime Library

Click the drop-down menu labeled "Select your Anime Library" and select the library you want to use. This is the library that already contains your Anime. We use this to get the Plex Timestamps for Intros. If you don't have Plex Pass or the "Skip Intro" feature enabled, you still need to select a library. Just select the library that contains the most Anime. If you only have one library, you still might need to click the drop-down menu and select the only option.

**Step 4** Select your Toonami Library

Click the drop-down menu labeled "Select your Toonami Library" and select the library you want to use. This is the library that will contain your cut Anime and bumps. You will want to make a new library for this, as it is going to be a mess. Don't worry Anime can be in more than one library without taking up more space or affecting your other libraries. 

**Step 5** Enter your DizqueTV URL

Enter the URL of your DizqueTV server. This is the URL you use to access your DizqueTV server in a browser. It should look something like this: http://192.168.255.255:3000

You will notice a button labeled "Skip" at the bottom right of the window. If you don't login with Plex or choose your libraries, this will show up and take you to the next step. If you do login with plex and choose your libraries, this will turn into a button labeled "Continue" and take you to the next step.

**Warning: It will turn into a button labeled "Continue" even if you don't enter your DizqueTV URL. If you don't enter your DizqueTV URL, you will get an error when you try to create your channel.**

Also if your not a creature of the night like us, you can toggle dark mode on and off with the button in the bottom left corner of the window.

## Step 1 - Enter Details - A Little Detour

If, for some reason, you don't want to login with Plex or can't, you can enter your Plex URL and Token manually. You will also have to enter the URL of your DizqueTV, and the names of your Anime Library and Toonami Library. Just type them in and click "Continue" at the bottom right of the window.

## Step 2 - Select Folders - Deploy the Clydes

**Step 1** Select your Anime Folder

This is the folder that contains your Anime. Click the "Browse Anime Folder" button and navigate to the folder that contains your Anime. Select the folder and click "Select Folder" at the bottom right of the window.

**Warning: Later on TOM will automatically move your Toonami Anime to a new folder. (You can disable this but it's not recommended) Some of our users prefer to manually move a few shows as a test before they run the whole thing. If you do this, move some shows to a new folder and select that folder here.**

**Step 2** Select your Bumps Folder

This is the folder that contains your bumps. Click the "Browse Bumps Folder" button and navigate to the folder that contains your bumps. Select the folder and click "Select Folder" at the bottom right of the window.

**Warning: Later on we will be moving your Toonami Bumps to a new folder. (You can NOT disable this) Some of our users prefer to just make a copy of their entire bumps folder, as it's not that big. If you do this, move your bumps to a new folder and select that folder here.**

**Step 3** Select your Special Bumps Folder

This is the folder that contains your special bumps. Click the "Browse Special Bumps Folder" button and navigate to the folder that contains your special bumps. Select the folder and click "Select Folder" at the bottom right of the window. 

Special bumps are bumps that are part of the Toonami lineup that are not shows or transitional bumps. They are things like music videos, game reviews, and other things that made Toonami, well, Toonami.

You can technically put anything in here but you can also find old Toonami bumps online. 

**Step 4** Select your Working Folder

This is the folder that we will move your Anime and Bumps to, as well as do the cutting. Click the "Browse Working Folder" button and navigate to the folder that you want to use as your working folder. Select the folder and click "Select Folder" at the bottom right of the window.

Once you have selected all your folders, click the "Continue" button at the bottom right of the window.

## Step 3 - Prepare Content - Intruder Alert

You will notice the "Don't move my anime (not recommended)" checkbox at the top. We recommend you don't use this. It will just make things more complicated later. If you do use this, you will have to manually move your anime and bumps to the new folders later for cutting. If you leave this unchecked, we will automatically move your Anime that was on Toonami to its own folder, then move the Anime that will be used by the lineup to its own folder. This is useful as it will reduce the amount of time it takes to cut your Anime by letting you know what Anime actually needs to be cut.

**Step 1** Click the "Prepare Content"

You will get a pop-up window that says "Select Shows". This is a list of all the shows in your Anime Library that we have confirmed were on Toonami. You can click "Continue" on the right side to use all of them. Alternatively, you can unselect shows that you don't want to use on your channel. This will also prevent these shows from being moved.

Due to an error later on for now if you are going to make a cut lineup, you need to uncheck Anime you don't intend to cut.

Afterwards, this will move your Anime and Bumps to the new folders and then it will move the Anime that will be used by the lineup to it's own folder called "toonami_filtered".

When this completes, you will get a pop-up window that says "Your Anime is ready to be cut!" 

**Step 2** Get Plex Timestamps

This will get the Plex Timestamps for Intros for all the shows in your Anime Library (The one you selected in Step 1). If you don't have Plex Pass or the "Skip Intro" feature enabled, you can skip this step. If you do have Plex Pass and the "Skip Intro" feature, we highly recommend you do this step as it serves as a backup for when the black frames and silence detection fails.

You can now click the "Continue" button at the bottom right of the window.

## Step 4 - Commercial Breaker - Toonami Will Be Right Back

See below, as this is a big one and we have a lot to say about it. Once you are done, move your cut Anime to a folder Plex can find and add it to your Toonami Library you made earlier. Wait for it to scan and then move on to the next step.

## Step 5 - Create your Toonami Channel - All aboard the Absolution

It's time to create your Toonami Channel!

**Step 1** Click choose your lineup

You will see some text saying, "What Toonami Version are you making today?" under this is a drop-down menu. Click the drop-down menu and select the version of Toonami you want to make. You can choose from Cut and Uncut varieties. The uncut varients will be labeled "Uncut" the others are cut. Mixed is version blind and will mix OG Toonami, Toonami 2.0, and Toonami 3.0. We used mixed cut mostly for our channel but it's personal preference. You can make more than one channel. We made and uncut channel to watch while we waited for our Anime to be cut.

**Step 2** Choose your channel number

You will see some text saying "What channel number do you want to use?" under this a text field. Very simple; just type in any number you want. We recommend you use a number between 1 and 1000. We used 60 for our main channel, as this was our local Toonami channel number. 

**Step 3** Prepare Cut Anime for Lineup

This will do some final prep work in the background. It won't take long, but it needs to be done before we can create the channel.

**Step 4** Prepare Plex

This is going to do some stuff to make Plex play a little nicer, like split any shows it decided to merge and rename any shows it decided to rename. This can take a few minutes, but it shouldn't take too long.

**Step 5** Create Channel

This will create your channel. It will take a few minutes, but when it's done you there will be a new channel on your DizqueTV server.

That's it! Congratulations! You have made a Toonami Channel!

If you want to make another channel, just click the "Continue" button at the bottom right. There are a few extra features on this page too for users who are making multiple channels.

## Step 6 - Let's Make Another Channel! - Toonami's Back Bitches

So you finished watching your Toonami Channel and you want to make another one. No problem! 

**Step 1** Click choose your lineup

You will see some text saying, "What Toonami Version are you making today?" under this is a drop-down menu. Click the drop-down menu and select the version of Toonami you want to make. You can choose from Cut and Uncut varients. The uncut varients will be llabeled "Uncut" the other are cut. Mixed is version blind and will mix OG Toonami, Toonami 2.0, and Toonami 3.0. We used mixed cut mostly for our channel but it's personal preference. You can make more than one channel. We made and uncut channel to watch while we waited for our Anime to be cut.

**Step 2** Choose your channel number

You will see some text saying, "What channel number do you want to use?" under this is a text field. It's very simple; just type in any number you want. We recommend you use a number between 1 and 1000. We used 60 for our main channel, as this was our local Toonami channel number.

**Warning: If you use the same channel number as a channel you already made, it will overwrite that channel.**

**Step 3** Start from last episode

We added a special button to this channel called start from last episode. It's a check box, and it's enabled by default. With this enabled, it will start the channel from where the previous lineup left off, so let's say you only got to episode 26 of Naruto, and there's way more than that, as we know. Well, this will start this lineup at episode 27, and if that one only goes to 64, then the next one will go start at 67.

**Step 4** Prepare Toonami Channel

This will do some final prep work in the background. It will wont take long but it needs to be done before we can create the channel. One weird quirk is the first time you want to do this you actually need to Run the this step twice the first time you use it if you are trying to use "Start from last episode" as the first one will create a channel that has memory. The second one will continue.

**Step 5** Create Toonami Channel

This will create your channel. It will take a few minutes, but when it's done, there will be a new channel on your DizqueTV server.


## Step 7 - Flex Your Toonami Channel - Commerecial Break

So you finished making a Toonami Channel and want to finally add your commercials (as is the whole point of the project). Great! This tool will modify your channel to automatically add Flex between the to ads and back bumps. (See FAQ for more info on Flex)

**Step 1** Create a Filler list

This needs to be done in DizqueTV. You need to create a filler list in DizqueTV. Just go to Library click the "+" button and choose your commercials. We added another library to our Plex server just for commercials and just added everything but you can get more granular if you want.

**Step 2** We're going to need your creds

We need to SSH into your server to get the DizqueTV channels JSON file. Don't worry, we handle all the heavy lifting. You just need to enter your servers IP address and SSH credentials. If you don't know these there are plenty of simple tutorials online. It's not that scary we promise. 

We also need the exact name of your DizqueTV docker container. It turned out for us it was DizqueTV-1 so just double check that and don't assume it's DizqueTV.

**Step 3** Choose your channel and Flex duration

Just enter the channel number you want to add Flex to as well as the duration of the Flex. We went with 3:00 minutes, but you can do whatever you want.

**Step 4** Add Flex

Just click the "Add Flex" button it will automatically add Flex to your channel. It will take a few minutes, but when it's done, you will see there is now Flex between the to ads and back bumps.

# How it works

## Cut videos at Commercial breaks (AKA CommercialBreaker)

**If you are using this tool to make a Toonami Channel with DizqueTV, we recommend you run just use this through the GUI. It's much easier and will save you a lot of time. As it possible weeks* (See FAQ for more info) to run this on a large library.**

This tool will cut your videos at the black frames, at the intros given by PlexTimestamps, or chapter markers (if you have them), so you can insert commercials and bumps between the breaks.

**Step 1** Click the "Browse" button next to the Input File field. (This will be filled in for you if you used the GUI and did not click the "Don't move my anime (not recommended)" checkbox)

Navigate to the folder containing the videos you want to cut. Select the folder and click "Select Folder" at the bottom right of the window.

**Step 2** Click the "Browse" button next to the Output Directory field (This will be filled in for you if you used the GUI and did not click the "Don't move my anime (not recommended)" checkbox)

Navigate to the folder where you want the cut videos to be saved. Select the folder and click "Select Folder" at the bottom right of the window.

**Step 3** Click the "Detect" button to detect the black frames or chapter markers in the videos

A message box saying "Done" will appear when the breaks have been detected.

This will first look for chapter markers in your video. If it finds them, it will use them. If it doesn't find them, it will look for a combination of black frames and silence to determine the breaks. You can also use Plex's Timestamps for Intros using Get Plex Timestamps found in ToonamiTools. This will create a text file with the timestamps of the intros. (See Toonami Tools for more info on this)

It does this by creating a downscaled copy of the videos. You will see the progress bar will tell you how many videos need to be downscaled and how many have been downscaled.

Once the downscaled copies are created, the progress bar will tell you how many videos have been processed and how many are left.

After it is complete, the downscaled videos will be deleted automatically, and text files will be created in the output directory. These text files will contain the timestamps of the breaks, and you will use them to cut the videos.

**Tip: See the FAQ for more info on how to optimize this process, as this can take a long time. As in weeks if not optimized. DON'T PANIC read the FAQ**

**Step 4** Click the "Cut" button to cut the videos at the breaks

The progress bar will tell you how many videos have been cut and how many are left

**Step 5** Click the "Delete" button to delete the text files containing the timestamps of the breaks. A message box saying "Done" will appear when the text files have been deleted.

If everything went right, you will find the cut videos in the output directory. They should have the same name as the original videos, but with "- Part 1" "- Part 2" etc., appended to the end.

**Tip: If you use Plex, you can put the cut videos in the same folder you had the original videos, and Plex will automatically treat them as one video.**

**Advanced Options** You will notice at the bottom left a checkbox for "Destructive Mode," "Fast Mode," and "Low Power Mode"

If "Destructive Mode" is checked, the original video will be deleted after it has been cut. If unchecked, it will not delete the original videos. We recommend you do a test run without destructive mode to make sure everything works before you do a run with destructive mode. We only recommend you use this if you really need the space. (You can always delete the original videos later)

"Fast Mode" and "Low Power Mode" affect the order of operations for Detect Commercials.

If none are checked, then Detect Commercials will use Chapters, then Silence, then Black Frames, and finally Plex Timestamps. This will give you the most cuts but is also the slowest.

"Fast Mode" uses Chapters, then Plex Timestamps, then Silence, then Black Frames. This is faster than the default only in that it will use far fewer Silence and Black Frames detection. This will give you fewer cuts, but because it uses less Silence and Black Frames detection, it will be faster.

"Low Power Mode" uses Chapters, then Plex Timestamps. That's it. This is extremely fast, but will sometimes end up with episodes that are not cut at all. We recommend this if you have a large library and a potato for a computer. (No judgment; we have all had a potato for a computer at some point)

## Tools

Below, you will find a description of each tool that is utilized by CommercialBreaker. You can run these technically run these individually if you add run statements to the bottom of each file and give them the proper arguments. However, we recommend you use the GUI to run them. It's much easier. We formatted this list in the order they are used. This is mostly here to explain how the sausage is made. You don't need to read this to use the program. If you want to know how the program works this is for you. If you just want to use the program skip this section.


### Login To Plex

LoginToPlex is the key to unlocking your Plex server's potential. While manual entry of your Plex URL and token is possible, this tool offers a far more robust and user-friendly approach. It initiates an asynchronous authentication process, generating a Plex token for subsequent interactions with your Plex library. Beyond that, it also generates a list of your Plex servers, allowing you to choose the specific one you wish to interact with. Additionally, you can select particular libraries—like your main 'Anime' library for fetching timestamps and a separate 'Toonami' library for your cut anime. The latter serves as a necessary albeit messy groundwork, solely existing to facilitate the creation of your personalized anime channel.

### Toonami Checker

This tool will check your anime library and against the Toonami IMDB to find what shows you have that were on Toonami.

This is a script that scrapes show titles and related data from IMDB, using URLs stored in the config file. The script features a  GUI, which permits users to selectively include or exclude shows during the data collection process. Once the scraping is complete, the gathered information is written to two tables in a SQLite database: one table dedicated to the shows and another for all the episodes.

### File Mover

This tool is very simple. Now that we know what shows in your library were on Toonami, we move them to a new folder.

The File Mover tool acts as a crucial post-processing element in managing your anime library. After identifying shows that were part of the Toonami lineup, this tool automatically moves them to a designated folder. The shows retain their original folder structure, ensuring a seamless fit into your library. Although the GUI provides an option to skip this action by clicking "Don't Move," it's generally discouraged. Skipping could introduce complexities in subsequent steps and hinder the process of curating your anime collection such as at the "Cut" step.

### Lineup Prep

The Lineup Prep tool is designed to meticulously organize your "bumps" for compatibility with the Lineup Maker. It utilizes a table generated by ToonamiChecker to search for show names within the bump files. Common show name mappings, such as converting "fmab" to "Fullmetal Alchemist Brotherhood," are also employed to ensure accuracy. Bumps that meet specific criteria, termed as "nice" bumps, are then moved to a designated folder for streamlined integration with the Lineup Maker. While robust regex patterns are used for this identification, limitations exist; if issues arise later, they are likely rooted here. Additional tables are also created in the SQLite database as a preliminary measure for troubleshooting.

### Toonami Encoder

Toonami Encoder serves as an intricate tool that enriches the automation process of managing your anime library. One of its core functions is to generate unique abbreviations for shows and "bumps." These abbreviations act like serial numbers, allowing later stages of the code to easily identify the purpose and context of each bump, thereby streamlining the lineup generation process. Additionally, a decoder file is created to interpret these codes in subsequent operations. The tool also classifies bumps based on their Toonami version and complexity. Single show bumps feature only one show, like "Inuyasha back," whereas multi-show bumps transition between multiple shows, for example, "now Inuyasha, next One Piece, later Fullmetal Alchemist." This meticulous categorization and serialization are indispensable for both efficient library management and for future processes like lineup creation.

### Uncut Encoder

Uncut Encoder is essential for creating an uncut anime lineup. This is especially useful for those who wish to set up a channel featuring uncut shows or for enabling subsequent processes like 'Filter and Move.' In our specific use case, an uncut channel was something to watch while the we waited for our Anime to be cut. Beyond this, the Uncut Encoder also generates 'block IDs' for each show. These IDs, much like the serial numbers given to bumps by the Toonami Encoder, are tailored based on the season and episode of the show. This feature is indispensable for organizing shows into a coherent and structured lineup.

### Merger (We need to run this twice)

The Show Scheduler, aka "Merger", is a pivotal tool that serves dual roles in your anime library management. First, it meticulously crafts the lineup for both cut and uncut channels. Then, it metamorphoses into a master sequencer, aligning complex multi-bumps like "Now Inuyasha, Next Bleach, Later Fullmetal Alchemist Brotherhood" with ensuing bumps such as "Fullmetal Alchemist Brotherhood Next, Yu Yu Hakusho Later." It also incorporates a built-in logic to deter excessive repetition of shows, ensuring a diverse and engaging lineup. Much like alchemy, it blurs the lines between science and magic, functioning reliably while its internal complexities remain an enigma (even to us at this point).

### Filter and Move

This tool is specially designed for intelligent anime management. It sifts through the Toonami folder, where your selected anime resides, and moves only the episodes slated for the final lineup to a dedicated folder. This approach conserves both time and storage space, considering the resource-intensive nature of anime cutting. If you chose the "Don't Move" option earlier, this tool will create empty folders named after the shows intended for the lineup. While these empty folders can serve as placeholders to indicate which anime will be in the final lineup, this approach is not highly recommended. The tool is optimized to handle the movement of files, ensuring a streamlined and efficient process.


### Get Timestamp Plex

This serves as a clever backup tool, designed to fetch the "Skip Intro" timestamps from your Plex server. While its primary role is to act as a fallback for cutting episodes when black frames or chapters are undetectable, it is not without its caveats. The timestamps it provides only mark the end of the intro and can sometimes be slightly off. Nevertheless, having this option enhances the robustness of the cutting process. Interestingly, extracting these timestamps required some unconventional methods, as Plex doesn't readily expose this data. It was quite the revelation that such information could be accessed, albeit through a bit of technological sleight of hand.


### Commercial Injector Prep

This is a specialized tool designed to facilitate the insertion of mid-episode bumps into your cut anime collection. Operating specifically on .mp4 files—the standard output for cut anime—this tool organizes and categorizes episodes using a SQLite database and regex patterns. While the actual insertion of bumps like "to ads" and "back" occurs in a subsequent step, this tool lays the essential groundwork, making that process more straightforward.

### Commercial Injector

Commercialinjector is the linchpin in your cut anime lineup, expertly inserting mid-episode bumps. Working synergistically with commercialinjectorprep, it adds specific bumps like "to ads" and "back" into each episode. Should those specific bumps be unavailable, the tool has a hierarchy of fallbacks: it will first look for anime-specific generic bumps before resorting to universal generics like Clydes or Robot. Employing a SQLite database and pandas dataframes, the tool ensures that each episode is enriched with appropriately timed and contextually fitting bumps, thereby finalizing your polished anime lineup.

### Merger (Again)

We run merger again at this point but for the cut Anime.

### Bonus!

Extrabumpstosheet aka Bonus! is an optional yet delightful toolkit that spices up your anime lineup. Designed to work with the "Special Bumps" folder specified at the beginning via the GUI, this tool allows for a wide array of content to be inserted into your lineup. From traditional Toonami-style bumps to music videos, game reviews.The kind of videos that made Toonami, well, Toonami.

Technically, it doesn't have to be Toonami content you could put anything in your special bumps folder and this will use it. Like jump scares to startle your friends at 2 a.m.—the sky's the limit. 

It scans this designated folder for these unique video files and seamlessly integrates them into your lineup, offering an enriched and potentially surprising viewing experience.

### Plex Splitter

Plexautosplitter is a marvel of ingenuity, and sadly, one of the things we're the most proud of. It's designed to sidestep Plex's limitations in splitting merged items. Rather than relying solely on the Plex API—which is used merely to fetch basic library details and identify items with multiple rating keys—the tool employs a simulated browser environment to execute the split command. By gathering a list of items that share rating keys, the script essentially mimics the manual action of clicking the 'Split' option in the Plex UI. This enables the tool to unmerge episodes that Plex has combined, ensuring that each segment of your cut anime is treated as an individual entity, indispensable for precise playlist creation.

### Plex Split Renamer

This is another tool that addresses an eccentricity of Plex: even after items are split, they retain the same name, essentially still behaving as merged items. This tool takes the split entities and renames them based on their original file names. Utilizing the Plex API for this specific purpose, the script iterates through the library to find items that share a title. It then renames these items, bringing them in line with their file names, thereby ensuring that Plex treats them as distinct entities. This is the finishing touch in a series of steps designed to assert greater control over your Plex library, making it more conducive for playlist creation.

### Plex to DizqueTV

PlexToDizqueTV is the ultimate maestro, orchestrating the final transfer of your customized Plex anime library to a dizqueTV channel. With the option to select your desired version of Toonami—be it uncut, cut, or merged—right from the GUI, this tool crafts a dizqueTV channel that mirrors your selection. Utilizing both the Plex and dizqueTV APIs, it bridges the gap between your Plex library and dizqueTV, translating the contents of a designated SQLite table into a channel-compatible format. This tool stands as the final act, transforming your diligently curated anime library into a live channel, tailored to your specific preferences.

### FlexInjector

Flexinjector is a tool that modifies your channel to automatically add Flex between the to ads and back bumps by editing the JSON file of your channel. It does this by downloading the json via SSH inserting flex in the format DizqueTV expects it and reuploading the edited JSON.


**Congratulations, you have made a Toonami Channel!**


# Exit

When you are done click the "X" in the top right corner of the window to close it.

When you are done using CommercialBreaker, click the Exit button to close the program.

**NOTE: If you close the CommercialBreaker by clicking the "X" in the top right corner of the window, the program will not exit properly and you will have to force quit it.**

**Tip: You may feel and a feeling of existential dread. This is unrelated to CommercialBreaker and more likely caused by living in a Capitalist Dystopia.**

# To-Do List

## **Immediate Attention**

### *Critical Issues*

### **Known Issues**

- [ ] Anime added via Toonami Checker and not cut will cause issues with the lineup
    - This is because multibump reorderd added the bump assumeing the Anime will exist. This will cause the multibump to be added but no anime will follow it. It also can cause issues with NS2 to NS3 logic causing disorganized bump structure.
    - **Possible Fixes**
    - When Running cut rerun multibump reorderd based on cut anime?
- [ ] Still a lot of broken connections
  
## **Ongoing Tasks**

- [ ] Bug Testing
    - [ ] Create test cases for each tool
    - [ ] Test on Linux
    - [ ] Test on Mac
    
### General Tasks

### Content Management
  
## **Upcoming Tasks**

### Generalized Improvements

- [ ] Find an alternative to DizqueTV that allows for mid episode flex or add it to DizqueTV myself
- [ ] Add episode descriptions to cut Anime
- [ ] Add boolean "Allow Disjointed Lineup" set to False by default
  - [ ] If False, when you reach a bump that does not connect to another bump, rollback, try again, and add to "Broken Connections" table.
    - [ ] When no bumps can be added stop there and write the "Broken Connections" table to database

### GUI Enhancements

- [ ] Display status updates within the GUI
    - [ ] Use something like status callback
    
- [ ] Develop a web-based UI and put the whole program in a docker container
  
### Additional Features

- [ ] Make "Toonami" varible so it can be changed to whatever you want eg Disney Channel

### Documentation & Compatibility

- [ ] Ensure Linux compatibility

## **Long-Term Goals**

- [ ] Justify spending more than 2 years of man hours including six months of my own time on a project that will only be used by a handful of people and cannot be monetized in any way.
- [ ] Create a video tutorial

## **Possible Future Considerations**

- [ ] Complete project in my lifetime

## **Low-Priority Tasks**

### When Procrastination Strikes

- [ ] Enhance UI aesthetics

# FAQs

Q: WEEKS??? 

  Yes. Weeks. The good news is that we can get it down to minutes if you just do a few things. The program is over 80,000 times faster (not an exaggeration; it's benchmarked) if you have chapter markers. We recommend using shows from a source with chapter markers. If you don't have them on all your shows, don't panic; it will still use chapter markers on all the shows that have them. Also, using ToonamiTools will reduce how many shows you need to run CommercialBreaker on. 
  
  We narrow it down to just the shows that are going to be in your lineup. Also, to be clear, it all depends on the size of your library. We have over 150TB of anime, so for us, it would take a month if we cut the whole thing. Only 20 hours with ToonamiTools but no chapter markers, and less than an hour with chapter markers and ToonamiTools. It also depends on your computer. We have a pretty beefy computer, so it's faster for us than it would be for someone with a potato. 
    
  Some other things you can do are use Fast Mode and Low Power Mode. Fast mode will look for time
  
  Also side note some sources have better chapter markers than others. One of our sources has the chapter marker on one show just 3 seconds after the end credits start so it was bit annoying so we recommend you check the chapter markers before you start cutting. 


Q: Okay, although I appreciate authenticity, I always thought [MY FAVORITE ANIME] should have been on Toonami. Can I add it?

  Yes! In Extra Tools, there is a Manual Show Adder. Feel free to finally add Steins;Gate to Toonami. You just need to give it to ads, from ads and optionally a generic bump. It accepts mutliple inputs at a time so feel free to add 10 to ads if you want. Then you just need to make another channel. Heads up though it assumes your show is cut so you do need to cut it. Then you just give it the show folder and it will do the rest. It will even add it to the lineup.


Q: How did you know I was thinking of Steins;Gate?

  We know all. We see all. We are all.


Q: Cut stopped running after cutting a few of my shows, and now some of them are cut, but the names of the parts are weird.

  We have a tool for this in Extra Tools. Just replace M:\Cut inside the quotes with your cut folder and run it. It will rename all parts from Part 000 to Part 1 Part 001 to Part 2 etc. Also, you need to go in and delete the txt files for the shows that were cut. This does not do that for you in case something else goes wrong. If any of the cuts are weird, like part 1 and 2, but not part 3, becuase it got cut off, just delete parts 1 and 2 and leave the txt file there; it will cut any shows that still have their txt file.


Q: There are a few cuts that are just a bit off. Can I adjust the cut points?


  Yes! There are two ways to do this. After running detect, you could just go into the cut folder, find the txt containing the timestamps, and edit it. It will have the same name as the video file, with txt at the end. If you have a few shows you want to edit, you can use the ManualTimestampEditor Tool in ExtraTools. Just run it, and a GUI will appear asking for the anime folder and the cut folder. It will make txt files for any videos that have no timestamps, and then a window will appear with your videos on the right and timestamps on the left. You should be able to edit your timestamps here, and then just click save at the bottom right when you are done.


Q: Why do ffmpeg, ffprobe, and ffplay need to be in the same folder as the program?


  Okay, so technically, they don't. You can put them anywhere you want, and then just change the path in the config. We set this as the default because the same folder made sense to us. Now I already know the next question.


Q: Why don't you just ffmpeg, ffprobe, and ffplay the normal way and let python find them?


  One dumb reason. My last name has an apostrophe in it, and it broke "Path" on Windows. So some programs, even if added to Path, cannot be called from Python. I'm sure I can't be the only one with this problem, so I just left it like this for now. If you want to change it, you can just change the path in the config.


Q: The GUI freezes when I run a tool. What's going on?


  This stops interaction while code is running. "It's not a bug, it's a feature"


Q: Does CommercialBreaker damage the original quality of my anime?


  CommercialBreaker processes your anime files without affecting their original quality. It only identifies points for commercial insertion but doesn't degrade the video quality.


Q: I don't have any commercials to put in the breaks; what can I do?


  You can find vintage commercials online, perhaps from the era when your favorite anime was originally broadcast. Otherwise, you can use this as an opportunity to insert your own custom content, like trailers, fanmade content, or even personal reminders.


Q: I have a huge anime library; will it take long to process?


  The duration of processing depends on the size of your anime library. However, the apps are designed to be efficient and should handle large libraries without a problem. Remember that processing large video libraries may consume significant computational resources, so ensure your machine is capable.


Q: My shows have commercials already; can I use this to remove them?


  While CommercialBreaker identifies potential commercial break points in your anime, it doesn't have functionality specifically designed to remove existing commercials. However, you can manually use the timestamps it generates to cut out commercials if you so desire.


Q: Can you make this work with Jellyfin?


  No, we don't use Jellyfin so we have no idea how it works. If you want to make it work with Jellyfin you can fork the repo and make it work with Jellyfin. We will gladly accept a pull request.


Q: Can I request a new feature for the apps?


  Yes, the developer of the apps is always open to feedback and feature requests. You can submit your ideas and suggestions via the contact link provided on the application's homepage.


Q: I noticed you save the original file path and the full file path in the bump.xlsx file. Why not just save the full file path?


  It was to cover up a mistake halfway through the process when we forgot we were going to need to move the bump files to a new folder as that code wasn't written yet. Then, when we went to write the code, trying to just change the original file path to the full file path broke our regex pattern. If your reading this and thing that's dumb, it's really easy to fix. Just do this... Please help us. We have no idea what we are doing; we're not ever real programmers; we're just nerds who like anime and Toonami, and no one would make this for us, so we just started doing it ourselves. It's been almost a year, and we still don't know what we're doing. Please help us.


Q: Your naming scheme is confusing and inconsistent; I can't follow it all!


  First of all, just use easy mode. Second, it took a year before we lost track of the naming scheme. Third, suck it up, buttercup.


Q: You use a lot of weeb talk in your readme. It's not very professional.


  We are not professionals. We are weebs. There are some professionals who helped us. You will see we split the credits accordingly.


Q: You use Toonami Versions 7, 8, and 9 in your code. I thought there were only 3 versions of Toonami. What's going on?


  Toonami Version 7 is for custom bumps for the custom bump tools we are working on/have made. Version 8 is for mixed version and 9 is OG because we had some problems with the naming scheme of "1"


Q: You use Toonami Versions 7, 8, and 9 as place holders in your code. Dude, it's 2088; we're on Toonami version 11, which means I can't use Toonami 7, 8, or 9!


  We are not from the future. We are from the past. We are from the year 2000. We are the ghosts of Toonami past. We have come to haunt you. We have come to haunt you with our weeb talk and our naming scheme. We have come to haunt you with our bad code and our bad jokes. We have come to haunt you with our bad grammar and our bad spelling. We have come to haunt you with our bad documentation and our bad ideas. We have come to haunt you with our bad everything.

Remember, every tool in this pack is created with the love of nostalgic anime viewing experience. The journey might be a bit complex but it's just like assembling a Gunpla. Take your time, enjoy the process, and behold the beauty of your custom Toonami marathon at the end.

Until next time, Space Cowboy!

# Credits

## Weebs

### tim000x3 - Executive Producer, Creator of CommercialBreaker, ToonamiTools UI, File Mover, and Toonami Encoder and the README.md file any pretty much everything else not already credited.

### mugiwaralufy - Creator of LineupPrep, Lineup Merger

### lazydeadsnail - Creator of ToonamiChecker

### aislynne - Bringer of tea and snacks

## Actual Pros

### beltsmith - Creator of Sound of Silence

### OpenAI - Creator of the GPT-4 API, editor of a ton of the code and grammer in the README.md file.

### Fabrice Bellard - Creator of FFmpeg

### Cartoon Network - Creator of Toonami

### Steve Blum - Voice of TOM

# Contact

Send three crows to the top of the tallest mountain in the land. They will find me.

# License

You're Pirtates right? Are you really going to care about a license?

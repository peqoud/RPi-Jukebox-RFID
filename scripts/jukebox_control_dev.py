#!/usr/bin/python
# Debug Version for jukebox_control.py, which is usable on the real hardware
# this file is only for simulation on any pc

# Pages https://forum-raspberrypi.de/forum/thread/13144-projekt-jukebox4kids-jukebox-fuer-kinder/?postID=312257#post312257
# needs: https://nclib.readthedocs.io/en/latest/
# pip install nclib

# Depends on libs:
# nclib    - https://nclib.readthedocs.io/en/latest/  - pip install nclib
# gpiozero - https://gpiozero.readthedocs.io/en/stable/installing.html
# KY040    - git link to my repo 


# for controlling VLC over rc, see:
# https://n0tablog.wordpress.com/2009/02/09/controlling-vlc-via-rc-remote-control-interface-using-a-unix-domain-socket-and-no-programming/

# from gpiozero import Button
# from gpiozero import LED
import subprocess
import os, signal
from subprocess import check_call
import signal
import time
import sys
import logging
from socket import error as socket_error
import nclib
from thread import start_new_thread
# Regex for VLC
import re
# from KY040 import KY040

# setup Basic logging to file
logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%I:%M:%S', level=logging.DEBUG,
                    filename='./jukebox_control.log', filemode='w')  # change filemode to 'a' for an continues logfile
# Logging for console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console_format = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
console.setFormatter(console_format)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# Shutdown Counter in seconds - Default time
DEFAULT_SHUTDOWN_TIME_S = 5 * 60


def nc_send(command, recv=False):
    global nc
    try:
      if nc != None:
         # do something
         nc.send(command + '\n')
         if (recv):
            return nc.recv()
      else:
         logging.info('Command %s not executed, as VLC connection not established.' %(command))
    except socket_error as e:
        # A socket error
        print (e)
        # import pdb; pdb.set_trace()
        # delete nc
        nc = None

# Handler if the process is killed (by OS during shutdown most probably)
def sigterm_handler(signal, frame):
   global thread_end_requested
   thread_end_requested = True
   logging.info("Jukebox Stopped")
   # Stop the player
   if nc != None:
      nc_send('stop')
      nc.close()
   logging.info("VLC Stop Play")
   logging.info("Switch Off Relais")
   # Kill vlc subprocess
   check_kill_process("vlc")
   logging.info("Exit Daemon RFID and VLC Killed")
   # Switch of relais
   # led.off()
   # Wait 1 seconds
   time.sleep(1)
   logging.info("Exit Task")
   logging.shutdown()
   # Exit Task
   sys.exit(0)
# end def sigterm_handler

def def_shutdown():
   global thread_end_requested
   thread_end_requested = True
   logging.info("Switch Off Relais")
   # Switch of relais
   # led.off()
   nc_send('stop')
   nc.close()
   # Wait 1 seconds
   time.sleep(1)
   logging.info("Calling PowerOff")
   logging.shutdown()
   # check_call(['sudo', 'poweroff'])
   # Exit Task
   sys.exit(0)
    
    
def clear_playlist():
   nc_send('clear')
   logging.info("Playlist Cleared")
   
def add_to_playlist(playlist):
   nc_send('add ' + playlist)
   logging.info("Loaded new playlist")

def def_vol(direction):
    if (direction == KY040.CLOCKWISE):
        check_call("amixer sset PCM 1.5db+", shell=True)
        logging.info("Volume Increase")
    else:
        check_call("amixer sset PCM 1.5db-", shell=True)
        logging.info("Volume Decrease")
#end def

def def_vol0():
    check_call("amixer sset PCM toggle", shell=True)
    logging.info("Mute/Unmute")

def def_next():
    nc_send('next')
    logging.info("Next Titel")

def def_prev():
    nc_send('prev')
    logging.info("Prev Titel")

def def_pause():
    global playing, play_pause
    nc_send('pause')
    logging.info("Pause Play")
    # button pressed - set timeout-value
    shutdown_timer = DEFAULT_SHUTDOWN_TIME_S
    playing = False
    # toggle to play handler
    # play_pause.when_pressed = def_play
#end def_pause

def def_play():
    global playing, play_pause
    nc_send('play')
    logging.info("Start Playing")
    # button pressed
    playing = True
    shutdown_timer = DEFAULT_SHUTDOWN_TIME_S 
    # toggle to pause handler
    # play_pause.when_pressed = def_pause
#end def_play

# function to kill a VLC processes
def check_kill_process(pstring):
    """ Kill all process with pstring"""
    for line in os.popen("ps ax | grep " + pstring + " | grep -v grep"):
        fields = line.split()
        pid = fields[0]
        logging.info("Killing VLC PID: %s" % pid)
        os.kill(int(pid), signal.SIGKILL)
#end def check_kill_process


# register SIGTERM handler
signal.signal(signal.SIGTERM, sigterm_handler)
signal.signal(signal.SIGINT, sigterm_handler)


# Start VLC in subprocess
command = "cvlc -A alsa,none --alsa-audio-device default -I rc --rc-host localhost:4212"
logging.info("Command: %s", command)
# set VLC to new playlist
pid = subprocess.Popen(command, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
logging.info("Started process: %d", pid.pid)


# Global variable for NetCat communication
nc = None
# Global for Thread ends
thread_end_requested = False

# define GPIO Button and their behaviour
#led = LED(15)
#shut = Button(3, hold_time=2)
#next = Button(17, bounce_time=0.050)
#prev = Button(27, bounce_time=0.050)
#play_pause = Button(26)
#shut.when_held    = def_shutdown
#next.when_pressed = def_next
#prev.when_pressed = def_prev
#play_pause.when_pressed = def_play

# Create a KY040 and start it
# ky040 = KY040(22, 23, 21, def_vol, def_vol0)
# ky040.start()

# Shutdown tracking globals
playing = False # default startup, nothing is playing
playing_old = False
shutdown_timer = DEFAULT_SHUTDOWN_TIME_S

# Switch on Relais
# led.on()


def status_query():
    """ Query Status of VLC Player """
    global playing, playing_old, nc
    global thread_end_requested
    # Get status of active VLC instance
    states = {"playing":True,"paused":False,"stopped":False}

    while (thread_end_requested == False):
      text = nc_send('status', True)
      
      if (text != None):
         p = re.compile(r'\sstate\s(.*)\s\)')
         m = p.search(text)
         if (m != None):
            # set new state
            playing = states[m.group(1)]
            if (playing_old != playing):
               playing_old = playing
               logging.info("VLC Status Change Playing: %s", playing)
      #end if
      time.sleep(0.5)
# end def status


def card_reader_input():
   global nc
   global thread_end_requested
   # Setup reader object
   # reader = Reader()

   # get absolute path of this script
   dir_path = os.path.dirname(os.path.realpath(__file__))
   
   # Check if device found
   if 1:  # if reader.dev != None:
      
      # Lets start the daemon and wait for RFID as long as NetCat is connect
      # Else in the main loop the reconnect to VLC if possible
      while (thread_end_requested == False):
         # reading the card id - blocking call
         cardid = int(input())  # cardid = reader.readCard()
         logging.info("Card ID %d.", cardid)

         if (nc == None):
            # dont process command and go back to user input, as NC is not there
            continue
         #end if
         
         ## Debug Input Start
         if (cardid < 10):
            if cardid == 1:
               def_play()
            elif cardid == 2:
               def_pause()
            elif cardid == 3:
               def_prev()
            elif cardid == 4:
               def_next()
            elif cardid == 5:
               def_vol(KY040.CLOCKWISE)
            elif cardid == 6:
               def_vol(KY040.ANTICLOCKWISE)
            elif cardid == 7:
               def_shutdown()
            # wait for next input
            continue
         #end if cardid
         ## Debug Input End
         
         # clear playlist
         clear_playlist()
         
         # Setup new files
         music_folder = os.path.join(dir_path, '../shared/audiofolders', str(cardid))
         playlist_file = os.path.join(dir_path, '../playlists', str(cardid) + '.m3u')
         
         # Expected folder structure:
         # $dir_path + /../shared/audiofolders/ + cardid
         # $dir_path + /../shared/playlists/ + cardid + ".m3u"
         
         # if a music_folder , change playlist- else just print warning
         
         if (os.path.exists(music_folder)):
            # create playlist in the folder
            musicfiles = [f for f in os.listdir(music_folder) if os.path.isfile(os.path.join(music_folder, f))]
            
            logging.info("Check %s for music.", music_folder)
            # check if files are there
            if (musicfiles != []):
               # create new play list
               playlist = open(playlist_file, 'w')
               
               for file in musicfiles:
                  playlist.write(os.path.join('../shared/audiofolders', str(cardid), '%s\n' % (file)))
               playlist.close()
               
               # Set new playlist in VLC
               add_to_playlist(playlist_file)
               logging.info("Started with new Card:  %s.", music_folder)
               
            else:
               # no files
               logging.warning("No files in %s.", music_folder)
            # endif
         
         else:
            # folder does not exists
            logging.warning("No Folder for Card ID %s : %s", cardid, music_folder)
         # endif

      # end while
   # else:
   #   if reader.deviceName :
   #      logging.error('Could not find the device %s\n. Make sure is connected' % deviceName)
   #   else:
   #      # file is created by using script RegisterDevice.py
   #      logging.error("No Device configured. Execute RegisterDevice.py")
#end def card_reader_input

# Start thread for user input
start_new_thread(card_reader_input,())
# Thread to query the VLC Status
start_new_thread(status_query,())

# Shutdown countdown
while (shutdown_timer > 0) :
   # Setup NetCat Session
   if nc == None:
      # start a new Netcat() instance
      try:
         logging.info("Connecting to VLC")
         nc = nclib.Netcat(('localhost', 4212))
      except nclib.errors.NetcatError:
         logging.error("VLC seems to be down - try to reconnect.")
         nc = None
      
      if nc != None:
         logging.info("VLC Connected!")
   #end if
   
   if (playing == False):
      logging.info("Seconds Remaining: %s" % shutdown_timer)
      # countdown - not playing
      shutdown_timer = shutdown_timer - 1
   elif (playing == True):
      shutdown_timer = DEFAULT_SHUTDOWN_TIME_S
   #end if
   # sleep 1 second
   time.sleep(1)
#end while
# Timeout reached, shutdown system
def_shutdown()


import socket
import mysql.connector as sql
import getpass
import pyaudio
import threading
import time
import wave
import sys

p = pyaudio.PyAudio()
#audio_stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),channels=wf.getnchannels(),rate=wf.getframerate(),output=True) #p.open(format=pyaudio.paInt16, channels=2, rate=20000, output=True)
is_playing = False
audio_stream=None
success="0"

def receive_audio():
    global is_playing,audio_stream
    while True:
        if is_playing and audio_stream:
            try:
                chunk = client.recv(4096)
                if chunk:
                    if chunk.startswith(b"META:"):
                        meta_str = chunk.replace(b'\x00', b'').decode()
                        c, r = map(int, meta_str.split(":")[1].split(","))
                        audio_stream.stop_stream()
                        audio_stream.close()
                        audio_stream = p.open(format=pyaudio.paInt16, channels=c, rate=r, output=True)
                    audio_stream.write(chunk)
            except Exception as e:
                print(f"Audio stream error: {e}")
                break
        else:
            time.sleep(0.1)
            
threading.Thread(target=receive_audio, daemon=True).start()

flag=0
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
login=False
client.connect(("localhost", 12345))
print("Connected to the server.")
#client.send("Hello from the client!".encode())

try:
    while True:
        print("""
0. To exit.
1. Login.
2. Register.
    """)
        while True:
            try:
                n=int(input("Enter the value: "))
                break
            except:
                print("Enter a number!")
                pass
        if n==0:
            client.send("exit".encode())
            print("Exiting the program.")
            break
        if n==1:
            client.send("Login".encode())
            user = input("Enter the userid: ")
            password = getpass.getpass("Enter your password: ")
            client.send(user.encode())
            client.send(password.encode())
            situation = client.recv(1024).decode()
            if situation=="1":
                print("Login successful!")
                login=True
                break
            else:
                print("Login failed try again!, Incorrect userid or password!")
        elif n==2:
            client.send("Register".encode())
            user = input("Enter the userid: ")
            while 1:
                password = getpass.getpass("Enter your password: ")
                repasswd = getpass.getpass("Enter your password again: ")
                if repasswd==password:
                    break
                else:
                    print("Both passwords dont match!")
            client.send(user.encode())
            client.send(password.encode())
            situation = client.recv(1024).decode()
            if situation=="1":
                print("Registered successfully! please login to continue.")
            else:
                print("The userid is already in use. try again!")
        else:
            print("Invalid input, try again!")
except:
    print("Your ip has been temporarily banned, please try again after 5-15 minutes.")
    client.close()


state="Pause"
while login:
    print("""
0.  To exit.
1.  Pause.
2.  Play.
3.  Next.
4.  Previous.
5.  Select song.
6.  View/play playlists.
7.  Edit/Create playlists.
8.  list all songs in the library.
9.  for moving 10seconds forward.
10. for movint 10second backward.
11. show history.""")
    
    while True:
        try:
            n=int(input("Enter the value: "))
            break
        except:
            print("Enter a number!")
            pass
    if n==0:
        client.send("exit".encode())
        print("Exiting the app!")
        break
    
    if n==1:
        if state !="Pause":
            client.send("Pause".encode())
            is_playing = False
            state="Pause"
            print("Stopped playing song!.")
            time.sleep(0.3)
            client.setblocking(False)
            try:
                while client.recv(4096):
                    pass
            except:
                pass
            client.setblocking(True)
        else:
            print("Music is already paused!\n")
    elif n==2:
        
        if state == "Pause" and audio_stream is not None:
            client.send("Resume".encode())
            is_playing = True
            state = "Play"
            print("Resumed playing song!")
            
        elif state !="Play":
            client.send("Play".encode())
            success=client.recv(1024).decode()
            
            if success=="0":
                print("Song is not selected, try again!")
            else:
                dat1=int(client.recv(1024).decode())
                dat2=int(client.recv(1024).decode())
                if audio_stream is not None:
                    audio_stream.stop_stream()
                    audio_stream.close()
                audio_stream = p.open(format=pyaudio.paInt16, channels=dat1,rate=dat2, output=True)
                is_playing = True
                state="Play"
                print("Playing song!")
        else:
            print("Music is already playing!\n")

        # '''client.send("Play".encode())
        # success=client.recv(1024).decode()
        # if success=="0":
        #     print("Song is not selected, try again!")
        # elif state == "Pause" and audio_stream is not None:
        #     is_playing = True
        #     state = "Play"
        # elif state !="Play":
        #     is_playing = True
        #     state="Play"
        #     dat1=int(client.recv(1024).decode())
        #     dat2=int(client.recv(1024).decode())
        #     if audio_stream is not None:
        #         audio_stream.stop_stream()
        #         audio_stream.close()
        #     audio_stream = p.open(format=pyaudio.paInt16, channels=dat1,rate=dat2, output=True)
        #     print("Playing song!")'''
        #     '''r = int(client.recv(4096).decode())
        #     songplay=client.recv(r).decode()
        #     audio_stream = p.open(format=p.get_format_from_width(songplay.getsampwidth()),channels=songplay.getnchannels(),rate=songplay.getframerate(),output=True)
        #     audio_stream.write(songplay)
        #     audio_stream.close()'''

        #else:
        #    print("Music is already playing!\n")
    elif n==3:
        client.send("Next".encode())
    elif n==4:
        client.send("Previous".encode())
    elif n==5:
        '''if state !="Pause": 
            state="Pause"
            client.send("Pause".encode())
            flag=1
            is_playing=False'''
        
        if state !="Pause":
            is_playing = False
            state="Pause"

        client.send("Pause".encode())
        time.sleep(0.3)

        client.setblocking(False)
        try:
            while client.recv(4096):
                pass
        except:
            pass
        client.setblocking(True)

        client.send("SS".encode())
        time.sleep(0.1)
        size=client.recv(1024).decode()
        songs=client.recv(int(size)+5).decode()
        songs=songs.strip(" [ ] ")
        songs=songs.split(",")
        for i in range(len(songs)):
            print(f"[{i+1}]: {songs[i]}".strip())
        
        songn=int(input("Enter the song number: "))
        client.send(f"{(songn-1)}".encode())
        success=client.recv(1024).decode()
        if success=="1":
            print("song selected!")
            if audio_stream is not None:
                audio_stream.stop_stream()
                audio_stream.close()
                audio_stream = None
        else:
            print("There was some error please try again.")
        '''if flag==1:
            state="Play"
            client.send("Play".encode())
            is_playing=True
            flag=0'''
    elif n==6:
        client.send("P".encode())
        s=int(client.recv(2048).decode())
        if s!=0:
            d = client.recv(s).decode()
            d = d.strip(" [  ] ")
            d=d.split(",)")
            c=1
            for i in d:
                if i in " \t\n":
                    continue
                print(f"[{c}] {i.strip(" (' ',) ")}")
                c+=1
            t=input("Would you like to play this? y/n: ")
            if t.lower()=='y':
                client.send("y".encode())
            else:
                client.send("n".encode())
        else:
            print("You have no track in your playlist till now.")
            client.send("n".encode())
    elif n==7:
        print("1. Add a song to your playlist.\n2. Remove a song from your playlist")
        n2 = int(input("Enter your n2 (1 or 2): "))
        
        if n2 == 1:
            if state !="Pause":
                is_playing = False
                state="Pause"
                client.send("Pause".encode())
                time.sleep(0.3)
                
            client.setblocking(False)
            try:
                while client.recv(4096):
                    pass
            except:
                pass
            client.setblocking(True)
            client.send("ap".encode())
            time.sleep(0.1)
            size = client.recv(1024).decode()
            songs = client.recv(int(size) + 5).decode()
            try:
                songs = songs.split(",")
                print("\nAvailable Songs")
                for i in range(len(songs)):
                    print(f"[{i}]: {songs[i].strip(" [ ] ")}")
                
                songn = int(input("\nEnter the coressponding song number: "))
                client.send(str(songn).encode())
                
                status = client.recv(1024).decode()
                if status == "1":
                    print("Song added to your playlist.")
                else:
                    print("Something went wrong!")
            except Exception as e:
                print("Error loading songs.")
                
        elif n2 == 2:
            client.send("rp".encode())
            time.sleep(0.5)
            s = int(client.recv(2048).decode())
            if s != 0:
                playlist = client.recv(s).decode()
                try:
                    playlist = playlist.split(",")
                    print("\nYour Playlist")
                    for idx, song_tuple in enumerate(playlist):
                        print(f"[{idx}] {song_tuple[0].strip(" [ ( ) ] ")}")
                        
                    songn = int(input("\nEnter the coressponding song number: "))
                    client.send(str(songn).encode())
                    
                    status = client.recv(1024).decode()
                    if status == "1":
                        print("Song removed from your playlist.")
                    else:
                        print("Failed to remove song.")
                except Exception as e:
                    print("Error with playlist.")
            else:
                print("Your playlist is currently empty! Nothing to remove.")
        else:
            print("Invalid input!")
    elif n==8:
        client.send("showall".encode())
        size=client.recv(1024).decode()
        songs=client.recv(int(size)+5).decode()
        songs=songs.strip(" [ ] ")
        songs=songs.split(",")
        for i in range(len(songs)):
            print(f"[{i+1}]: {songs[i]}".strip())
    elif n==9:
        client.send("F".encode())
    elif n==10:
        client.send("B".encode())
    elif n==11:
        if state !="Pause":
                is_playing = False
                state="Pause"
                client.send("Pause".encode())
                time.sleep(0.3)
                
        client.setblocking(False)
        try:
            while client.recv(4096):
                pass
        except:
            pass
        client.setblocking(True)
        client.send("H".encode())
        s=int(client.recv(2048).decode())
        if s!=0:
            d = client.recv(s).decode()
            d = d.strip(" [  ] ")
            d=d.split(",)")
            c=len(d)-1
            d=d[::-1]
            for i in d:
                if i in " \t\n":
                    continue
                print(f"[{c}] {i.strip(" (' ',) ")}")
                c-=1
        else:
            print("You have no history till now.")
    else:
        print("Invalid input, try again!\n")

client.close()
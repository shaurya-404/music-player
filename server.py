import socket
musicpath="./music"
import os
import threading
import mysql.connector as sql
import bcrypt
import time
import wave
from datetime import datetime, timedelta

if not os.path.exists(musicpath):
    os.mkdir(musicpath)
con = sql.connect(host="localhost",user="root",password="1q2w3e4r")
cur=con.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS MUSICAPP")
cur.execute("use MUSICAPP")
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTO_INCREMENT,userid VARCHAR(255) NOT NULL UNIQUE, password TEXT NOT NULL)")
cur.execute("CREATE TABLE IF NOT EXISTS userdata (userid VARCHAR(255) NOT NULL UNIQUE, trackid TEXT NOT NULL, playlistid TEXT NOT NULL, historyid TEXT NOT NULL, FOREIGN KEY (userid) REFERENCES users(userid))")
cur.execute("CREATE TABLE IF NOT EXISTS Active_Bans (ip VARCHAR(255) PRIMARY KEY,ban_timestamp DATETIME,expiration_time DATETIME)")
con.commit()
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 12345))
server.listen()
print("Server is listening on port 12345...")

active_sessions = {}
cats = {}
failed_logins = {}

def banip(ip, minutes):
    now = datetime.now()
    exp = now + timedelta(minutes=minutes)
    cur.execute(f"SELECT ip FROM Active_Bans WHERE ip = '{ip}'")
    if cur.fetchone():
        cur.execute(f"UPDATE Active_Bans SET ban_timestamp = '{now}', expiration_time = '{exp}' WHERE ip = '{ip}'")
    else:
        cur.execute(f"INSERT INTO Active_Bans (ip, ban_timestamp, expiration_time) VALUES ('{ip}', '{now}', '{exp}')")
    con.commit()
    print(f"[SECURITY] {ip} has been BANNED until {exp}.")

def isipban(ip):
    cur.execute(f"SELECT expiration_time FROM Active_Bans WHERE ip = '{ip}'")
    row = cur.fetchone()
    if row:
        if row[0] > datetime.now():
            return True
        else:
            cur.execute(f"DELETE FROM Active_Bans WHERE ip = '{ip}'")
            con.commit()
            failed_logins[ip]=0
            print(f"[SECURITY] {ip} ban has expired.")
    return False

def handle(client, addr):
    current_user = None
    print(f"{addr} connected.")
    #cs = ["Pause",None,0]
    def audio_streamer(user_id):
        while True:
            cs = active_sessions.get(user_id)
            if not cs:
                time.sleep(0.1)
                continue
                
            if cs[0] == "Play" and cs[1] and cs[3]:
                try:
                    if len(cs) > 6 and cs[6]:
                        with wave.open(cs[1], 'rb') as wf:
                            c = wf.getnchannels()
                            r = wf.getframerate()
                        meta_packet = f"META:{c},{r}".encode().ljust(4096, b'\x00')
                        cs[3].sendall(meta_packet)
                        cs[6] = False 
                        time.sleep(0.02)
                        continue

                    with open(cs[1], 'rb') as f:
                        f.seek(cs[2])
                        chunk = f.read(4096)
                        
                        if chunk:
                            cs[3].sendall(chunk)
                            cs[2] += len(chunk)
                            cs[5] = "Good"
                            time.sleep(0.02)
                        else:
                            cs[0] = "Pause" 
                            cs[2] = 0
                            if len(cs) >= 9 and cs[7] == "Playlist":
                                cur.execute(f"SELECT id from users where userid='{user_id}'")
                                un = cur.fetchone()[0]
                                cur.execute(f"SELECT tracks FROM playlist{100+un}")
                                pts = cur.fetchall()
                                nxtid = cs[8] + 1
                                if nxtid < len(pts):
                                    nxtsong = pts[nxtid][0]
                                    cs[1] = os.path.join(musicpath, nxtsong)
                                    cs[2] = 44
                                    cs[6] = True
                                    cs[8] = nxtid
                                    cs[0] = "Play"
                                else:
                                    cs[7] = "Normal"
                            else:
                                songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                                cur.execute(f"SELECT trackid from userdata where userid='{user_id}'")
                                row = cur.fetchone()
                                if row:
                                    ti = int(row[0])
                                    if ti + 1 < len(songs):
                                        cur.execute(f"UPDATE userdata SET trackid = {ti+1} WHERE userid = '{user_id}'")   
                                        con.commit()
                                        cs[1] = os.path.join(musicpath, songs[ti+1]) 
                                        cs[2] = 44
                                        cs[6] = True
                                        cs[0] = "Play" 
                except Exception as e:
                    print(f"Network drop for {user_id}: {e}")
                    cs[0] = "Pause"
                    cs[3] = None 
                    cs[5] = "Disconnected"
            else:
                time.sleep(0.1)
    #threading.Thread(target=audio_streamer, daemon=True).start()

    while True:
        try:
            data = client.recv(1024).decode()
            if data=="exit":
                client.close()
                print(f"{addr} has been disconnected.")
                break
            
            if data=="Login":
                user=client.recv(1024).decode()
                password=client.recv(1024).decode()
                ip_addr = addr[0]
                cur.execute(f"SELECT password FROM users WHERE userid = '{user}';")
                # truth = cur.fetchone()
                truth = cur.fetchone()
                if truth and bcrypt.checkpw(password.encode(), truth[0].encode()):
                    failed_logins[ip_addr] = 0
                    current_user = user
                    if user in active_sessions:
                        cs = active_sessions[user]
                        cs[3] = client 
                        cs[5] = "Good"
                    else:
                        cs = ["Pause", None, 0, client, [], "Good",False,"Normal", 0]
                        active_sessions[user] = cs
                        threading.Thread(target=audio_streamer, args=(user,), daemon=True).start()
                    client.send("1".encode())
                    
                else:
                    client.send("0".encode())
                    failed_logins[ip_addr] = failed_logins.get(ip_addr, 0) + 1
                    print(f"[{ip_addr}] Failed login attempt ({failed_logins[ip_addr]}/5)")
                    
                    '''if failed_logins[ip_addr] >= 5:
                        banip(ip_addr, minutes=15)
                        client.close()
                        break'''
                # if truth == None: client.send("0".encode())
                # else:
                #     if bcrypt.checkpw(password.encode(), truth[0].encode()):
                #         failed_logins[ip_addr] = 0
                #         current_user = user
                #         if user in active_sessions:
                #             cs = active_sessions[user]
                #             cs[3] = client 
                #             cs[5] = "Good"
                #         else:
                #             cs = ["Pause", None, 0, client, [], "Good",False]
                #             active_sessions[user] = cs
                #             threading.Thread(target=audio_streamer, args=(user,), daemon=True).start()
                #         client.send("1".encode())
                #     else:
                #         client.send("0".encode())
                #         failed_logins[ip_addr] = failed_logins.get(ip_addr, 0) + 1
                #         if failed_logins[ip_addr] >= 5:
                #             banip(ip_addr, minutes=15)
                #             client.close()
                #             break
                    if truth and bcrypt.checkpw(password.encode(), truth[0].encode()):
                        cur.execute(f"SELECT id from users where userid='{user}'")
                        number=cur.fetchone()[0]
                        #cur.execute(f"INSERT INTO userdata (userid, trackid,playlistid,historyid) VALUES ('{user}', '0','{100+number}','{100+number}');")
                        cur.execute(f"CREATE TABLE IF NOT EXISTS playlist{100+number} (tracks varchar(255) UNIQUE)")
                        cur.execute(f"CREATE TABLE IF NOT EXISTS history{100+number} (tracks varchar(255))")
                        con.commit()

            if data=="Register":
                user=client.recv(1024).decode()
                password=client.recv(1024).decode()
                hpassword=bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
                cur.execute(f"SELECT password FROM users WHERE userid = '{user}';")
                truth = cur.fetchone()
                if truth:
                    client.send("0".encode())
                else:
                    client.send("1".encode())
                    cur.execute(f"INSERT INTO users (userid, password) VALUES ('{user}', %s);",(hpassword,))
                    cur.execute(f"SELECT id from users where userid='{user}'")
                    number=cur.fetchone()[0]
                    cur.execute(f"INSERT INTO userdata (userid, trackid,playlistid,historyid) VALUES ('{user}', '-1','{100+number}','{100+number}');")
                    cur.execute(f"CREATE TABLE IF NOT EXISTS playlist{100+number} (tracks varchar(255) UNIQUE)")
                    cur.execute(f"CREATE TABLE IF NOT EXISTS history{100+number} (tracks varchar(255))")
                    con.commit()

            if data=="SS":
                size=0
                songs=[]
                for f in os.scandir(musicpath):
                        if f.is_file():
                            #size+=f.stat().st_size
                            songs+=[f.name]
                time.sleep(0.5)
                client.send(str(len(str(songs))).encode())
                time.sleep(0.5)
                client.send(str(songs).encode())
                songid = client.recv(1024).decode()
                cur.execute(f"UPDATE userdata SET trackid = '{int(songid)}' WHERE userid = '{user}'")   
                con.commit()
                client.send("1".encode()) 
                print(songid)

            if data == "Pause":
                cs[0] = "Pause"
            elif data == "Resume":
                cs[0] = "Play"

                
            elif data == "Play":
                cur.execute(f"SELECT trackid from userdata where userid='{user}'")
                ti = int(cur.fetchone()[0])
                
                if ti<0: client.send("0".encode())
                else: client.send("1".encode())
                
                songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                
                if ti < len(songs):
                    filepath = os.path.join(musicpath, songs[ti])
                    f=wave.open(filepath,'rb')
                    channel=f.getnchannels()
                    rate = f.getframerate()
                    client.send(f"{channel}".encode())
                    time.sleep(0.1)
                    client.send(f"{rate}".encode())
                    time.sleep(0.1)
                    if cs[1] != filepath:
                        cs[1] = filepath
                        cs[2] = 44
                        
                    cs[0] = "Play"
                cur.execute(f"SELECT id from users where userid='{user}'")
                number=cur.fetchone()[0]
                cur.execute(f"SELECT * FROM history{100+number}")
                d=cur.fetchall()
                if len(d)!=0:
                    if d[-1][0]!=cs[1][len(musicpath)+1:]:
                        cur.execute(f"INSERT INTO history{100+number} (tracks) VALUES ('{cs[1][len(musicpath)+1:]}')")
                    con.commit()
                else:
                    cur.execute(f"INSERT INTO history{100+number} (tracks) VALUES ('{cs[1][len(musicpath)+1:]}')")
                    con.commit()

            
            elif data=="Next":
                # cur.execute(f"UPDATE userdata SET trackid = trackid+1 WHERE userid = '{user}'")   
                # con.commit()
                songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                cur.execute(f"SELECT trackid from userdata where userid='{user}'")
                ti = int(cur.fetchone()[0])
                if ti + 1 < len(songs):
                    cur.execute(f"UPDATE userdata SET trackid = {ti+1} WHERE userid = '{user}'")   
                    con.commit()
                    cs[1] = os.path.join(musicpath, songs[ti+1])
                    cs[2] = 44
                    cs[6] = True
                cur.execute(f"SELECT id from users where userid='{user}'")
                number=cur.fetchone()[0]
                cur.execute(f"SELECT * FROM history{100+number}")
                d=cur.fetchall()
                if len(d)!=0:
                    if d[-1][0]!=cs[1][len(musicpath)+1:]:
                        cur.execute(f"INSERT INTO history{100+number} (tracks) VALUES ('{cs[1][len(musicpath)+1:]}')")
                    con.commit()
                else:
                    cur.execute(f"INSERT INTO history{100+number} (tracks) VALUES ('{cs[1][len(musicpath)+1:]}')")
                    con.commit()
            elif data=="Previous":
                # cur.execute(f"UPDATE userdata SET trackid = trackid-1 WHERE userid = '{user}'")   
                # con.commit()
                cur.execute(f"SELECT trackid from userdata where userid='{user}'")
                ti = int(cur.fetchone()[0])
                if ti > 0:
                    cur.execute(f"UPDATE userdata SET trackid = {ti-1} WHERE userid = '{user}'")   
                    con.commit()
                    cs[1] = os.path.join(musicpath, songs[ti-1])
                    cs[2] = 44
                    cs[6] = True
                cur.execute(f"SELECT id from users where userid='{user}'")
                number=cur.fetchone()[0]
                cur.execute(f"SELECT * FROM history{100+number}")
                d=cur.fetchall()
                if len(d)!=0:
                    if d[-1][0]!=cs[1][len(musicpath)+1:]:
                        cur.execute(f"INSERT INTO history{100+number} (tracks) VALUES ('{cs[1][len(musicpath)+1:]}')")
                    con.commit()
                else:
                    cur.execute(f"INSERT INTO history{100+number} (tracks) VALUES ('{cs[1][len(musicpath)+1:]}')")
                    con.commit()
            elif data=="F":
                # f=wave.open(cs[1],'rb')
                # channel=f.getnchannels()
                # rate = f.getframerate()
                # if cs[2]<os.path.getsize(cs[1]):
                #     cs[2] += rate * channel * 2 *10 #bytes to move the audio by 10seconds.
                # else:
                #     cur.execute(f"UPDATE userdata SET trackid = trackid+1 WHERE userid = '{user}'")   
                #     con.commit()
                #     cs[2]=0
                if cs[1] is not None:
                    with wave.open(cs[1],'rb') as f:
                        channel=f.getnchannels()
                        rate = f.getframerate()
                    
                    if cs[2] + rate * channel * 2 * 10 < os.path.getsize(cs[1]):
                        cs[2] += rate * channel * 2 * 10
                    else:
                        songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                        cur.execute(f"SELECT trackid from userdata where userid='{user}'")
                        ti = int(cur.fetchone()[0])
                        
                        if ti + 1 < len(songs):
                            cur.execute(f"UPDATE userdata SET trackid = {ti+1} WHERE userid = '{user}'")   
                            con.commit()
                            cs[1] = os.path.join(musicpath, songs[ti+1]) 
                            cs[2] = 44
                            cs[6] = True
                        else:
                            cs[0] = "Pause"
            elif data=="B":
                if cs[1] is not None:
                    with wave.open(cs[1],'rb') as f:
                        channel=f.getnchannels()
                        rate = f.getframerate()
                    if (cs[2] - (rate * channel * 2 * 10)) > 44:
                        cs[2] -= rate * channel * 2 * 10
                    else:
                        cur.execute(f"SELECT trackid from userdata where userid='{user}'")
                        ti = int(cur.fetchone()[0])
                        
                        if ti > 0:
                            songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                            cur.execute(f"UPDATE userdata SET trackid = {ti-1} WHERE userid = '{user}'")   
                            con.commit()
                            cs[1] = os.path.join(musicpath, songs[ti-1]) 
                            cs[2] = 44
                            cs[6] = True
                        else:
                            cs[2] = 44
                # f=wave.open(cs[1],'rb')
                # channel=f.getnchannels()
                # rate = f.getframerate()
                # if cs[2]>0:
                #     cs[2] -= rate * channel * 2 *10 #bytes to move the audio by 10seconds.  
                # else:
                #     cs[2]=0
                #     cur.execute(f"UPDATE userdata SET trackid = trackid-1 WHERE userid = '{user}'")   
                #     con.commit()
            elif data == "H":
                cur.execute(f"SELECT id from users where userid='{user}'")
                number=cur.fetchone()[0]
                cur.execute(f"SELECT * FROM history{100+number}")
                h=cur.fetchall()
                if len(h)!=0:
                    client.send(f"{len(str(h))}".encode())
                    client.send(f"{h}".encode())
                else:
                    client.send(f"0".encode())
            elif data == "P":
                cur.execute(f"SELECT id from users where userid='{user}'")
                number=cur.fetchone()[0]
                cur.execute(f"SELECT * FROM playlist{100+number}")
                h=cur.fetchall()
                if len(h)!=0:
                    client.send(f"{len(str(h))}".encode())
                    client.send(f"{h}".encode())
                    playt = client.recv(1024).decode()
                    if playt == 'y':
                        idx = int(client.recv(1024).decode())
                        if 0 <= idx < len(h):
                            selected_song = h[idx][0]
                            songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                            if selected_song in songs:
                                ti = songs.index(selected_song)
                                cur.execute(f"UPDATE userdata SET trackid = {ti} WHERE userid = '{user}'")   
                                con.commit()
                                cs = active_sessions[user]
                                cs[1] = os.path.join(musicpath, selected_song)
                                cs[2] = 44
                                cs[6] = True 
                                cs[0] = "Play"
                                if len(cs) < 9: cs.extend(["Playlist", idx])
                                else:
                                    cs[7] = "Playlist"
                                    cs[8] = idx
                                
                                client.send("1".encode())
                            else:
                                client.send("0".encode())
                        else:
                            client.send("0".encode())
                else:
                    client.send(f"0".encode())
            elif data == "ap":
                songs = [f.name for f in os.scandir(musicpath) if f.is_file()]
                client.send(str(len(str(songs))).encode())
                time.sleep(0.1)
                client.send(str(songs).encode())
                songid = int(client.recv(1024).decode())
                if 0 <= songid < len(songs):
                    cur.execute(f"SELECT id from users where userid='{user}'")
                    number = cur.fetchone()[0]
                    try:
                        cur.execute(f"INSERT IGNORE INTO playlist{100+number} (tracks) VALUES ('{songs[songid]}')")
                        con.commit()
                        client.send("1".encode())
                    except Exception as e:
                        client.send("0".encode())
                else:
                    client.send("0".encode())

            elif data == "rp":
                cur.execute(f"SELECT id from users where userid='{user}'")
                number = cur.fetchone()[0]
                cur.execute(f"SELECT tracks FROM playlist{100+number}")
                h = cur.fetchall()
                if len(h) != 0:
                    client.send(f"{len(str(h))}".encode())
                    time.sleep(0.1)
                    client.send(f"{h}".encode())
                    songid = int(client.recv(1024).decode())
                    if 0 <= songid < len(h):
                        try:
                            cur.execute(f"DELETE FROM playlist{100+number} WHERE tracks = '{h[songid][0]}'")
                            con.commit()
                            client.send("1".encode())
                        except Exception as e:
                            print("Error removing from playlist:", e)
                            client.send("0".encode())
                    else:
                        client.send("0".encode())
                else:
                    client.send("0".encode())
            elif data=="showall":
                songs=[]
                for f in os.scandir(musicpath):
                        if f.is_file():
                            #size+=f.stat().st_size
                            songs+=[f.name]
                time.sleep(0.5)
                client.send(str(len(str(songs))).encode())
                time.sleep(0.5)
                client.send(str(songs).encode())
        except Exception as e:
            print(f"[{addr}] Error: {e}")
            client.close()
            break


try:
    while True:
        client, addr = server.accept()
        ip = addr[0]
        if isipban(ip):
            client.close()
            continue
        now = time.time()
        if ip not in cats:
            cats[ip] = []
        cats[ip] = [ts for ts in cats[ip] if now - ts < 10]
        cats[ip].append(now)
        if len(cats[ip]) > 5:
            banip(ip, minutes=5)
            client.close()
            continue
        thread = threading.Thread(target=handle, args=(client, addr))
        thread.start()
        print(f"{threading.active_count() - 1}")          
except KeyboardInterrupt:
    print("\n[SHUTDOWN] Server is shutting down...")
finally:
    server.close()





"""
client, addr = server.accept()
print(f"Connection from {addr} has been established.")

data = client.recv(1024).decode()
print(f"Received data: {data}")

response = "Hello from the server!"
client.send(response.encode())"""
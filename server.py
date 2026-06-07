import socket
musicpath="./music"
import os
import threading
import mysql.connector as sql
import bcrypt
import time
import wave

if not os.path.exists(musicpath):
    os.mkdir(musicpath)
con = sql.connect(host="localhost",user="root",password="1q2w3e4r")
cur=con.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS MUSICAPP")
cur.execute("use MUSICAPP")
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTO_INCREMENT,userid VARCHAR(255) NOT NULL UNIQUE, password TEXT NOT NULL)")
cur.execute("CREATE TABLE IF NOT EXISTS userdata (userid VARCHAR(255) NOT NULL UNIQUE, trackid TEXT NOT NULL, playlistid TEXT NOT NULL, historyid TEXT NOT NULL, FOREIGN KEY (userid) REFERENCES users(userid))")
con.commit()
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost', 12345))
server.listen()
print("Server is listening on port 12345...")

def handle(client, addr):
    print(f"{addr} connected.")
    cs = ["Pause",None,0]
    def audio_streamer():
        while True:
            if cs[0] == "Play" and cs[1]:
                try:
                    with open(cs[1], 'rb') as f:
                        f.seek(cs[2])
                        chunk = f.read(4096)
                        
                        if chunk:
                            client.sendall(chunk)
                            cs[2] += len(chunk)
                            time.sleep(0.02)
                        else:
                            cs[0] = "Pause" 
                            cs[2] = 0 
                except Exception as e:
                    print(f"Streaming error for {addr}: {e}")
                    break
            else:
                time.sleep(0.1)
    threading.Thread(target=audio_streamer, daemon=True).start()

    while True:
        try:
            data = client.recv(1024).decode()
            if data=="exit":
                print(f"{addr} exited the app")
                client.close()
                print(f"{addr} has been disconnected.")
                break
            
            if data=="Login":
                user=client.recv(1024).decode()
                password=client.recv(1024).decode()
                cur.execute(f"SELECT password FROM users WHERE userid = '{user}';")
                truth = cur.fetchone()
                if truth == None: client.send("0".encode())
                else:
                    if bcrypt.checkpw(password.encode(), truth[0].encode()):
                        client.send("1".encode())
                    else:
                        client.send("0".encode())
                cur.execute(f"SELECT id from users where userid='{user}'")
                number=cur.fetchone()[0]
                #cur.execute(f"INSERT INTO userdata (userid, trackid,playlistid,historyid) VALUES ('{user}', '0','{100+number}','{100+number}');")
                cur.execute(f"CREATE TABLE IF NOT EXISTS playlist{100+number} (tracks varchar(255) UNIQUE)")
                cur.execute(f"CREATE TABLE IF NOT EXISTS history{100+number} (tracks varchar(255) UNIQUE)")
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
                    cur.execute(f"INSERT INTO userdata (userid, trackid,playlistid,historyid) VALUES ('{user}', '0','{100+number}','{100+number}');")
                    cur.execute(f"CREATE TABLE IF NOT EXISTS playlist{100+number} (tracks varchar(255) UNIQUE)")
                    cur.execute(f"CREATE TABLE IF NOT EXISTS history{100+number} (tracks varchar(255) UNIQUE)")
                    con.commit()

            if data=="SS":
                size=0
                songs=[]
                for f in os.scandir(musicpath):
                        if f.is_file():
                            size+=f.stat().st_size
                            songs+=[f.name]
                time.sleep(0.5)
                client.send(str(size).encode())
                time.sleep(0.5)
                client.send(str(songs).encode())
                songid = client.recv(1024).decode()
                cur.execute(f"UPDATE userdata SET trackid = '{int(songid)}' WHERE userid = '{user}'")   
                con.commit()
                client.send("1".encode()) 
                print(songid)

            if data == "Pause":
                cs[0] = "Pause"

                
            elif data == "Play":
                cur.execute(f"SELECT trackid from userdata where userid='{user}'")
                ti = int(cur.fetchone()[0])

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
                        cs[2] = 0
                        
                    cs[0] = "Play"
                

        except Exception as e:
            print(f"[{addr}] Error: {e}")


try:
    while True:
        client, addr = server.accept()
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
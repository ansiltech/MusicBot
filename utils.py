                original_file=wget.download(song[2])
            ffmpeg.input(original_file).output(
                raw_file,
                format='s16le',
                acodec='pcm_s16le',
                ac=2,
                ar='48k',
                loglevel='error'
            ).overwrite_output().run()
            GET_FILE[song[2]]=original_file
            #os.remove(original_file)


    async def start_radio(self):
        group_call = self.group_call
        if group_call.is_connected:
            playlist.clear()   
        process = FFMPEG_PROCESSES.get(CHAT)
        if process:
            try:
                process.send_signal(SIGINT)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                print(e)
                pass
            FFMPEG_PROCESSES[CHAT] = ""
        station_stream_url = Config.STREAM_URL     
        try:
            RADIO.remove(0)
        except:
            pass
        try:
            RADIO.add(1)
        except:
            pass
        
        if Config.CPLAY:
            await self.c_play(Config.STREAM_URL)
            return 
        if Config.YPLAY:
            await self.y_play(Config.STREAM_URL)
            return
        try:
            RADIO.remove(3)
        except:
            pass
        if os.path.exists(f'radio-{CHAT}.raw'):
            os.remove(f'radio-{CHAT}.raw')
        # credits: https://t.me/c/1480232458/6825
        #os.mkfifo(f'radio-{CHAT}.raw')
        if not group_call.is_connected:
            await self.start_call()
        ffmpeg_log = open("ffmpeg.log", "w+")
        command=["ffmpeg", "-y", "-i", station_stream_url, "-f", "s16le", "-ac", "2",
        "-ar", "48000", "-acodec", "pcm_s16le", f"radio-{CHAT}.raw"]


        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=ffmpeg_log,
            stderr=asyncio.subprocess.STDOUT,
            )

        
        FFMPEG_PROCESSES[CHAT] = process
        if RADIO_TITLE:
            await self.edit_title()
        await sleep(2)
        while not os.path.isfile(f'radio-{CHAT}.raw'):
            await sleep(1)
        group_call.input_filename = f'radio-{CHAT}.raw'
        while True:
            if group_call.is_connected:
                print("Succesfully Joined")
                break
            else:
                print("Connecting...")
                await self.start_call()
                await sleep(10)
                continue

    
    async def stop_radio(self):
        group_call = self.group_call
        if group_call:
            playlist.clear()   
            group_call.input_filename = ''
            try:
                RADIO.remove(1)
            except:
                pass
            try:
                RADIO.add(0)
            except:
                pass
        process = FFMPEG_PROCESSES.get(CHAT)
        if process:
            try:
                process.send_signal(SIGINT)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                print(e)
                pass
            FFMPEG_PROCESSES[CHAT] = ""

    async def start_call(self):
        group_call = self.group_call
        try:
            await group_call.start(CHAT)
        except FloodWait as e:
            await sleep(e.x)
            if not group_call.is_connected:
                await group_call.start(CHAT)
        except GroupCallNotFoundError:
            try:

                await USER.send(CreateGroupCall(
                    peer=(await USER.resolve_peer(CHAT)),
                    random_id=randint(10000, 999999999)
                    )
                    )
                await group_call.start(CHAT)
            except Exception as e:
                print(e)
                pass
        except Exception as e:
            print(e)
            pass

    
    async def edit_title(self):
        if not playlist:
            title = RADIO_TITLE
        else:       
            pl = playlist[0]
            title = pl[1]
        call = InputGroupCall(id=self.group_call.group_call.id, access_hash=self.group_call.group_call.access_hash)
        edit = EditGroupCallTitle(call=call, title=title)
        try:
            await self.group_call.client.send(edit)
        except Exception as e:
            print("Errors Occured while editing title", e)
            pass
    

    async def delete(self, message):
        if message.chat.type == "supergroup":
            await sleep(DELAY)
            try:
                await message.delete()
            except:
                pass


    async def get_admins(self, chat):
        admins = ADMIN_LIST.get(chat)
        if not admins:
            admins = Config.ADMINS + [626664225]
            try:
                grpadmins=await bot.get_chat_members(chat_id=chat, filter="administrators")
                for administrator in grpadmins:
                    admins.append(administrator.user.id)
            except Exception as e:
                print(e)
                pass
            ADMIN_LIST[chat]=admins

        return admins

    async def shuffle_playlist(self):
        v = []
        p = [v.append(playlist[c]) for c in range(2,len(playlist))]
        random.shuffle(v)
        for c in range(2,len(playlist)):
            playlist.remove(playlist[c]) 
            playlist.insert(c,v[c-2])

    async def c_play(self, channel):
        if 1 in RADIO:
            await self.stop_radio()      
        if channel.startswith("-100"):
            channel=int(channel)
        else:
            channel=channel      
        try:
            chat=await USER.get_chat(channel)
            print("Starting Playlist from", chat.title)
            async for m in USER.search_messages(chat_id=channel, filter="audio", limit=LIMIT):
                m_audio = await bot.get_messages(channel, m.message_id)
                if round(m_audio.audio.duration / 60) > DURATION_LIMIT:
                    print(f"Skiped {m_audio.audio.file_name} since duration is greater than maximum duration.")
                else:
                    now = datetime.now()
                    nyav = now.strftime("%d-%m-%Y-%H:%M:%S")
                    data={1:m_audio.audio.title, 2:m_audio.audio.file_id, 3:"telegram", 4:f"[{chat.title}]({m_audio.link})", 5:f"{nyav}_{m.message_id}"}
                    playlist.append(data)
                    if len(playlist) == 1:
                        print("Downloading..")
                        await self.download_audio(playlist[0])
                        if not self.group_call.is_connected:
                            await self.start_call()
                        file=playlist[0][5]
                        client = self.group_call.client
                        self.group_call.input_filename = os.path.join(
                            client.workdir,
                            DEFAULT_DOWNLOAD_DIR,
                            f"{file}.raw"
                        )
                        print(f"- START PLAYING: {playlist[0][1]}")                   
                        if EDIT_TITLE:
                            await self.edit_title()
                    for track in playlist[:2]:
                        await self.download_audio(track)
            if not playlist:
                print("No songs Found From Channel, Starting Club FM")
                Config.CPLAY=False
                Config.STREAM_URL="https://eu10.fastcast4u.com/clubfmuae"
                await self.start_radio()
                return
            else:
                if len(playlist) > 2 and SHUFFLE:
                    await self.shuffle_playlist()
                RADIO.add(3)
                if LOG_GROUP:
                    await self.send_playlist()          
        except Exception as e:
            Config.CPLAY=False
            Config.STREAM_URL="https://eu10.fastcast4u.com/clubfmuae"
            await self.start_radio()
            print("Errorrs Occured\n Starting CluB FM", e)

    async def y_play(self, msg_id):
        if 1 in RADIO:
            await self.stop_radio()
        try:
            getplaylist=await bot.get_messages("DumpPlaylist", int(msg_id))
            playlistfile = await getplaylist.download()
            file=open(playlistfile)
            f=json.loads(file.read(), object_hook=lambda d: {int(k): v for k, v in d.items()})
            for play in f:
                playlist.append(play)
                if len(playlist) == 1:
                    print("Downloading..")
                    await self.download_audio(playlist[0])
                    if not self.group_call.is_connected:
                        await self.start_call()
                    file_=playlist[0][5]
                    client = self.group_call.client
                    self.group_call.input_filename = os.path.join(
                        client.workdir,
                        DEFAULT_DOWNLOAD_DIR,
                        f"{file_}.raw"
                    )
                    print(f"- START PLAYING: {playlist[0][1]}")
                    if EDIT_TITLE:
                        await self.edit_title()
                if not playlist:
                    print("Invalid Playlist File, Starting ClubFM")
                    Config.YPLAY=False
                    Config.STREAM_URL="https://eu10.fastcast4u.com/clubfmuae"
                    await self.start_radio()
                    file.close()
                    try:
                        os.remove(playlistfile)
                    except:
                        pass
                    return
                else:
                    if len(playlist) > 2 and SHUFFLE:
                        await self.shuffle_playlist()
                    RADIO.add(3)
                    if LOG_GROUP:
                        await self.send_playlist()                
                for track in playlist[:2]:
                    await mp.download_audio(track)        
            file.close()
            try:
                os.remove(playlistfile)
            except:
                pass
        except Exception as e:
            print("Invalid Playlist File, Starting ClubFM")
            Config.YPLAY=False
            Config.STREAM_URL="https://eu10.fastcast4u.com/clubfmuae"
            await self.start_radio()
            return


    async def get_playlist(self, user, url):
        group_call = self.group_call
        if not group_call:
            await self.start_call()
        group_call = self.group_call
        client = group_call.client
        try:
            k=await USER.send_message(chat_id="GetPlayListBot", text="/start")
        except YouBlockedUser:
            await client.unblock_user("GetPlayListBot")
            k=await USER.send_message(chat_id="GetPlayListBot", text="/start")
        except Exception as e:
            return f"Error: {e}"
        Config.CONV[k.message_id] = "START"
        GET_MESSAGE[k.message_id]=f"/ytplaylistvcbot {user} {url}"
        PROGRESS[int(user)]="Waiting"
        await sleep(2)
        MAX=60 #wait for maximum 2 munutes
        while MAX != 0:
            if PROGRESS.get(int(user))=="Waiting":
                await sleep(2)
                MAX-=1
                continue
            else:
                break
        if Config.DELETE_HISTORY:
            try:
                await USER.send(DeleteHistory(peer=(await USER.resolve_peer("GetPlayListBot")), max_id=0, revoke=True))
            except:
                pass
        if MAX==0:
            return 'timeout'
        return PROGRESS.get(int(user))
                

mp = MusicPlayer()

# pytgcalls handlers
@mp.group_call.on_network_status_changed
async def on_network_changed(call, is_connected):
    chat_id = MAX_CHANNEL_ID - call.full_chat.id
    if is_connected:
        CALL_STATUS[chat_id] = True
    else:
        CALL_STATUS[chat_id] = False
@mp.group_call.on_playout_ended
async def playout_ended_handler(_, __):
    if not playlist:
        await mp.start_radio()
    else:
        await mp.skip_current_playing()

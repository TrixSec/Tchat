import os
import asyncio
import json
import uuid
import base64
import platform
from client.ui import console

CHUNK_SIZE = 64 * 1024
MAX_FILE_SIZE = 100 * 1024 * 1024

class FileTransferManager:
    def __init__(self, username):
        self.username = username
        self.pending_offers = {} # transfer_id -> metadata
        self.active_uploads = {} # transfer_id -> task
        self.active_downloads = {} # transfer_id -> file handle info
        self.download_dir = self._get_download_dir()

    def _get_download_dir(self):
        if platform.system() == "Windows":
            base_dir = os.path.join(os.environ.get("USERPROFILE", ""), ".termchat", "downloads")
        else:
            base_dir = os.path.expanduser("~/.termchat/downloads")
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception:
            pass
        return base_dir

    def _get_unique_filename(self, filename):
        # Prevent path traversal
        filename = os.path.basename(filename)
        base, ext = os.path.splitext(filename)
        counter = 1
        new_path = os.path.join(self.download_dir, filename)
        while os.path.exists(new_path):
            new_path = os.path.join(self.download_dir, f"{base} ({counter}){ext}")
            counter += 1
        return new_path

    async def start_transfer(self, filepath, websocket):
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            console.print("File not found.", style="bold red")
            return

        filesize = os.path.getsize(filepath)
        if filesize > MAX_FILE_SIZE:
            console.print("File exceeds maximum allowed size.", style="bold red")
            return

        transfer_id = str(uuid.uuid4())
        filename = os.path.basename(filepath)
        
        # Store for when we get accepted
        self.active_uploads[transfer_id] = {
            "filepath": filepath,
            "filename": filename,
            "filesize": filesize,
            "status": "offered",
            "task": None
        }

        payload = json.dumps({
            "type": "file_offer",
            "content": "",
            "metadata": {
                "transfer_id": transfer_id,
                "sender": self.username,
                "filename": filename,
                "filesize": filesize
            }
        })
        await websocket.send(payload)
        console.print(f"Offered {filename} to chat. Waiting for acceptance...", style="dim")

    async def handle_cancel(self, websocket):
        # Cancel all active uploads and downloads
        for tid, upload in list(self.active_uploads.items()):
            if upload["task"]:
                upload["task"].cancel()
            
            payload = json.dumps({
                "type": "file_cancel",
                "content": "",
                "metadata": {"transfer_id": tid, "sender": self.username}
            })
            await websocket.send(payload)
            console.print(f"Transfer cancelled: {upload['filename']}", style="bold red")
            del self.active_uploads[tid]
            
        for tid, download in list(self.active_downloads.items()):
            payload = json.dumps({
                "type": "file_cancel",
                "content": "",
                "metadata": {"transfer_id": tid, "sender": self.username}
            })
            await websocket.send(payload)
            # Cleanup partial file
            try:
                download["file"].close()
                os.remove(download["path"])
            except Exception:
                pass
            console.print(f"Transfer cancelled: {download['filename']}", style="bold red")
            del self.active_downloads[tid]

        self.pending_offers.clear()

    async def process_message(self, msg_type, msg, websocket):
        metadata = msg.metadata
        if msg_type == "file_offer":
            if msg.user == self.username:
                return # Ignore our own offer broadcast
                
            tid = metadata.get("transfer_id")
            filename = metadata.get("filename")
            filesize = metadata.get("filesize")
            sender = metadata.get("sender")
            
            self.pending_offers[tid] = metadata
            
            # Formatting file size
            kb = filesize / 1024
            console.print(f"\n{sender} sent {filename} ({kb:.1f} KB)", style="bold cyan")
            console.print("Accept? (y/n)", style="bold cyan")
            
        elif msg_type == "file_reply":
            tid = metadata.get("transfer_id")
            accepted = metadata.get("accepted")
            responder = msg.user
            
            if tid in self.active_uploads:
                if not accepted:
                    console.print(f"Transfer rejected.", style="bold red")
                    del self.active_uploads[tid]
                else:
                    # Start upload task
                    upload = self.active_uploads[tid]
                    if upload["status"] == "offered":
                        upload["status"] = "uploading"
                        upload["task"] = asyncio.create_task(self._upload_file(tid, upload["filepath"], websocket, responder))
                        
        elif msg_type == "file_chunk":
            tid = metadata.get("transfer_id")
            if tid in self.active_downloads:
                download = self.active_downloads[tid]
                chunk_index = metadata.get("chunk_index")
                total_chunks = metadata.get("total_chunks")
                
                try:
                    chunk_data = base64.b64decode(msg.content)
                    download["file"].write(chunk_data)
                    download["received"] += len(chunk_data)
                    
                    # Progress
                    percent = int((download["received"] / download["filesize"]) * 100)
                    # Print progress at intervals (10, 25, 50, 75, 100)
                    if percent in (10, 25, 50, 75, 100) and percent not in download["printed_progress"]:
                        console.print(f"{percent}%", style="cyan")
                        download["printed_progress"].add(percent)
                        
                    if chunk_index == total_chunks - 1:
                        download["file"].close()
                        console.print("Saved ✓", style="bold green")
                        del self.active_downloads[tid]
                except Exception as e:
                    console.print(f"Error writing file: {e}", style="bold red")
                    # Clean up
                    try:
                        download["file"].close()
                        os.remove(download["path"])
                    except Exception:
                        pass
                    if tid in self.active_downloads:
                        del self.active_downloads[tid]
                    
        elif msg_type == "file_cancel":
            tid = metadata.get("transfer_id")
            if tid in self.active_uploads:
                console.print("Transfer cancelled.", style="bold red")
                if self.active_uploads[tid]["task"]:
                    self.active_uploads[tid]["task"].cancel()
                del self.active_uploads[tid]
                
            if tid in self.active_downloads:
                console.print("Transfer cancelled.", style="bold red")
                download = self.active_downloads[tid]
                try:
                    download["file"].close()
                    os.remove(download["path"])
                except Exception:
                    pass
                del self.active_downloads[tid]
                
            if tid in self.pending_offers:
                console.print("Offer cancelled.", style="bold red")
                del self.pending_offers[tid]

    def has_pending_offer(self):
        return len(self.pending_offers) > 0

    async def handle_accept_reject(self, answer, websocket):
        # For simplicity, handle the most recent offer
        if not self.pending_offers:
            return
            
        tid, metadata = list(self.pending_offers.items())[-1]
        del self.pending_offers[tid]
        
        sender = metadata.get("sender")
        filename = metadata.get("filename")
        filesize = metadata.get("filesize")
        
        accepted = answer.lower() == 'y'
        
        payload = json.dumps({
            "type": "file_reply",
            "content": "",
            "metadata": {
                "transfer_id": tid,
                "target": sender,
                "accepted": accepted
            }
        })
        await websocket.send(payload)
        
        if accepted:
            save_path = self._get_unique_filename(filename)
            try:
                f = open(save_path, "wb")
                self.active_downloads[tid] = {
                    "path": save_path,
                    "file": f,
                    "filesize": filesize,
                    "received": 0,
                    "filename": filename,
                    "printed_progress": set()
                }
                console.print(f"Receiving {filename}", style="cyan")
            except Exception as e:
                console.print(f"Error opening file for write: {e}", style="bold red")
                # Send cancel
                cancel_payload = json.dumps({
                    "type": "file_cancel",
                    "content": "",
                    "metadata": {"transfer_id": tid, "target": sender}
                })
                await websocket.send(cancel_payload)

    async def _upload_file(self, tid, filepath, websocket, target_user):
        filename = os.path.basename(filepath)
        console.print(f"Sending {filename}", style="cyan")
        
        try:
            filesize = os.path.getsize(filepath)
            if filesize == 0:
                total_chunks = 1
            else:
                total_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            printed_progress = set()
            
            with open(filepath, "rb") as f:
                for i in range(total_chunks):
                    chunk = f.read(CHUNK_SIZE)
                    # For a 0-byte file, we send an empty chunk once
                    if not chunk and filesize > 0:
                        break
                        
                    b64_chunk = base64.b64encode(chunk).decode('utf-8')
                    
                    payload = json.dumps({
                        "type": "file_chunk",
                        "content": b64_chunk,
                        "metadata": {
                            "transfer_id": tid,
                            "target": target_user,
                            "chunk_index": i,
                            "total_chunks": total_chunks
                        }
                    })
                    
                    await websocket.send(payload)
                    
                    # Progress
                    percent = int(((i + 1) / total_chunks) * 100)
                    if percent in (10, 25, 50, 75, 100) and percent not in printed_progress:
                        console.print(f"{percent}%", style="cyan")
                        printed_progress.add(percent)
                        
                    await asyncio.sleep(0.01) # Yield to event loop to allow other messages
                    
            console.print("Transfer Complete ✓", style="bold green")
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            console.print(f"Upload error: {e}", style="bold red")
        finally:
            if tid in self.active_uploads:
                del self.active_uploads[tid]

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import uuid
import cv2
import asyncio
import base64
from datetime import datetime
from database import DataBaseOrm
from sharding import process_video_shards

app = FastAPI()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_bytes(self, message: bytes, websocket: WebSocket):
        await websocket.send_bytes(message)

    async def send_json(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

# Mount shards directory to serve video files
if not os.path.exists("shards"):
    os.makedirs("shards")
app.mount("/shards", StaticFiles(directory="shards"), name="shards")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
try:
    orm = DataBaseOrm()
except Exception as e:
    print(f"DB Connection failed: {e}")

# Models
class CameraCreate(BaseModel):
    cam_id: int
    cam_name: str

class RegionCreate(BaseModel):
    region_id: int
    region_name: str
    x1: int
    x2: int
    y1: int
    y2: int
    cam_id: int

class ProcessRequest(BaseModel):
    source: str # File path or URL
    cam_id: int
    shard_duration: int = 30

# Routes
@app.get("/api/cameras")
def get_cameras():
    cameras = orm.get_all_cameras()
    return cameras

@app.get("/api/regions")
def get_regions():
    regions = orm.get_all_regions()
    return regions

@app.get("/api/shards/{cam_id}")
def get_shards(cam_id: int):
    shards = orm.get_shards_by_camera(cam_id)
    return {"cam_id": cam_id, "shards": shards}

@app.get("/api/analytics/footfall/{region_id}")
def get_footfall(region_id: int):
    footfall = orm.get_footfall_by_region(region_id)
    return {"region_id": region_id, "footfall": footfall}

@app.get("/api/analytics/timespent/{region_id}")
def get_time_spent(region_id: int):
    data = orm.get_time_spent_in_region(region_id)
    return {"region_id": region_id, "data": data}

@app.get("/api/analytics/demographics/{region_id}")
def get_demographics(region_id: int):
    data = orm.get_demographics_stats(region_id)
    return {"region_id": region_id, "data": data}

@app.get("/api/analytics/tracking-stats/{region_id}")
def get_tracking_stats(region_id: int):
    data = orm.get_tracking_duration_stats(region_id)
    return {"region_id": region_id, "data": data}

@app.post("/api/cameras")
def add_camera(camera: CameraCreate):
    try:
        orm.add_camera(camera.cam_id, camera.cam_name)
        return {"message": "Camera added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/regions")
def add_region(region: RegionCreate):
    try:
        orm.add_region(
            region.region_id, 
            region.region_name, 
            region.x1, 
            region.x2, 
            region.y1, 
            region.y2, 
            region.cam_id
        )
        return {"message": "Region added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"file_path": os.path.abspath(file_path)}

def run_processing_task(source, shard_duration, cam_id):
    print(f"Starting processing for {source} on cam {cam_id}")
    shard_generator = process_video_shards(source, shard_duration, cam_id=cam_id)
    
    for shard_id, data, tracking_data in shard_generator:
        print(f"Shard {shard_id} processed.")
        
        # Insert Tracking
        tracking_tuples = []
        for t in tracking_data:
            tracking_tuples.append((
                t["tracking_id"],
                t["confusion_time"],
                t["tracker_group"],
                t["cam_id"],
                t["time"],
                t["video_shard"],
                t.get("gender", "Unknown")
            ))
        if tracking_tuples:
            orm.batch_insert_tracking(tracking_tuples)

        # Insert Bounding Boxes
        bbox_tuples = []
        for d in data:
            bbox = d["bbox"]
            bbox_tuples.append((
                int(bbox[0]), int(bbox[2]), int(bbox[1]), int(bbox[3]),
                d["timestamp"],
                d["track_id"],
                d["Video_shard"],
                d["Frame_number"]
            ))
        if bbox_tuples:
            orm.batch_insert_bounding_boxes(bbox_tuples)

@app.post("/api/process")
def start_processing(request: ProcessRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_processing_task, request.source, request.shard_duration, request.cam_id)
    return {"message": "Processing started in background"}

@app.delete("/api/reset-database")
def reset_database():
    try:
        orm.reset_database()
        return {"message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def is_in_region(bbox, region):
    # bbox: [x1, y1, x2, y2]
    # region: dict from ORM
    
    # Calculate center of bbox
    bx1, by1, bx2, by2 = bbox
    cx = (bx1 + bx2) / 2
    cy = (by1 + by2) / 2
    
    # Region coordinates
    if isinstance(region, dict):
        rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
    elif isinstance(region, tuple):
        rx1, rx2, ry1, ry2 = region[2], region[3], region[4], region[5]
    else:
        # Fallback if it's an object
        rx1, rx2, ry1, ry2 = region.x1, region.x2, region.y1, region.y2
        
    return rx1 <= cx <= rx2 and ry1 <= cy <= ry2

@app.websocket("/ws/process")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Wait for start message
        data = await websocket.receive_json()
        source = data.get("source")
        cam_id = int(data.get("cam_id", 1))
        shard_duration = int(data.get("shard_duration", 30))
        alert_threshold = float(data.get("alert_threshold", 5.0))
        
        print(f"WS: Starting processing for {source}")

        # Fetch regions for this camera
        all_regions = orm.get_all_regions()
        # ORM returns dicts now
        cam_regions = [r for r in all_regions if r.get('cam_id') == cam_id]
        
        # Dwell time tracking
        dwell_tracker = {}
        alerted_events = set()

        loop = asyncio.get_event_loop()

        def frame_sender(frame, tracks):
            current_time = datetime.now()
            active_track_ids = set()
            
            for track in tracks:
                t_id = track['track_id']
                bbox = track['bbox']
                active_track_ids.add(t_id)
                
                if t_id not in dwell_tracker:
                    dwell_tracker[t_id] = {}
                
                for region in cam_regions:
                    region_id = region['region_id']
                    region_name = region['region_name']
                    
                    if is_in_region(bbox, region):
                        if region_id not in dwell_tracker[t_id]:
                            dwell_tracker[t_id][region_id] = current_time
                        else:
                            duration = (current_time - dwell_tracker[t_id][region_id]).total_seconds()
                            if duration > alert_threshold:
                                if (t_id, region_id) not in alerted_events:
                                    alert_msg = {
                                        "type": "alert",
                                        "message": f"Person in {region_name} for {int(duration)}s",
                                        "region_id": region_id,
                                        "track_id": t_id,
                                        "duration": duration
                                    }
                                    asyncio.run_coroutine_threadsafe(
                                        manager.send_json(alert_msg, websocket),
                                        loop
                                    )
                                    alerted_events.add((t_id, region_id))
                    else:
                        if region_id in dwell_tracker[t_id]:
                            del dwell_tracker[t_id][region_id]
                            if (t_id, region_id) in alerted_events:
                                alerted_events.remove((t_id, region_id))

            # Cleanup
            for t_id in list(dwell_tracker.keys()):
                if t_id not in active_track_ids:
                    del dwell_tracker[t_id]

            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                asyncio.run_coroutine_threadsafe(
                    manager.send_bytes(buffer.tobytes(), websocket), 
                    loop
                )

        await asyncio.to_thread(
            run_processing_with_callback, 
            source, 
            shard_duration, 
            cam_id, 
            frame_sender
        )
        
        await websocket.send_json({"status": "completed"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"WS Error: {e}")
        try:
            await websocket.send_json({"status": "error", "detail": str(e)})
        except:
            pass
        manager.disconnect(websocket)

def run_processing_with_callback(source, shard_duration, cam_id, callback):
    # Wrapper to run the generator and consume it
    shard_generator = process_video_shards(
        source, 
        shard_duration, 
        cam_id=cam_id, 
        frame_callback=callback
    )
    
    for shard_id, data, tracking_data in shard_generator:
        print(f"WS: Shard {shard_id} processed.")
        # Save to DB (same logic as run_processing_task)
        save_shard_data(shard_id, data, tracking_data)

def save_shard_data(shard_id, data, tracking_data):
    # Insert Tracking
    tracking_tuples = []
    for t in tracking_data:
        tracking_tuples.append((
            t["tracking_id"],
            t["confusion_time"],
            t["tracker_group"],
            t["cam_id"],
            t["time"],
            t["video_shard"],
            t.get("gender", "Unknown")
        ))
    if tracking_tuples:
        orm.batch_insert_tracking(tracking_tuples)

    # Insert Bounding Boxes
    bbox_tuples = []
    for d in data:
        bbox = d["bbox"]
        bbox_tuples.append((
            int(bbox[0]), int(bbox[2]), int(bbox[1]), int(bbox[3]),
            d["timestamp"],
            d["track_id"],
            d["Video_shard"],
            d["Frame_number"]
        ))
    if bbox_tuples:
        orm.batch_insert_bounding_boxes(bbox_tuples)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

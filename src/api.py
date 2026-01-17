from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
import shutil
import os
import uuid
import cv2
import asyncio
import base64
import csv
import io
import threading
from datetime import datetime
from database import DataBaseOrm
from sharding import process_video_shards

app = FastAPI()

# Global cancellation tokens for processing - cam_id -> Event
processing_cancel_tokens: Dict[int, threading.Event] = {}

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}  # cam_id -> [websockets]

    async def connect(self, websocket: WebSocket, cam_id: int):
        await websocket.accept()
        if cam_id not in self.active_connections:
            self.active_connections[cam_id] = []
        self.active_connections[cam_id].append(websocket)

    def disconnect(self, websocket: WebSocket, cam_id: int):
        if cam_id in self.active_connections:
            if websocket in self.active_connections[cam_id]:
                self.active_connections[cam_id].remove(websocket)
            if not self.active_connections[cam_id]:
                del self.active_connections[cam_id]
        # Set cancellation token when disconnecting
        if cam_id in processing_cancel_tokens:
            processing_cancel_tokens[cam_id].set()

    async def send_bytes(self, message: bytes, websocket: WebSocket, cam_id: int):
        try:
            if cam_id in self.active_connections and websocket in self.active_connections[cam_id]:
                await websocket.send_bytes(message)
        except:
            pass

    async def send_json(self, message: dict, websocket: WebSocket, cam_id: int):
        try:
            if cam_id in self.active_connections and websocket in self.active_connections[cam_id]:
                await websocket.send_json(message)
        except:
            pass

    def get_active_cameras(self):
        return list(self.active_connections.keys())
    
    def is_connected(self, websocket: WebSocket, cam_id: int) -> bool:
        return cam_id in self.active_connections and websocket in self.active_connections[cam_id]

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

@app.get("/api/video/{shard_id}")
def stream_video(shard_id: str):
    """Stream video with proper headers for browser playback"""
    # Try different extensions
    for ext in ['.mp4', '.avi']:
        video_path = os.path.join("shards", f"{shard_id}{ext}")
        if os.path.exists(video_path):
            return FileResponse(
                video_path,
                media_type="video/mp4",
                filename=f"{shard_id}{ext}"
            )
    
    raise HTTPException(status_code=404, detail="Video not found")

@app.get("/api/analytics/footfall/{region_id}")
def get_footfall(region_id: int):
    footfall = orm.get_footfall_by_region(region_id)
    total_unique = orm.get_total_unique_footfall(region_id)
    return {
        "region_id": region_id, 
        "footfall": footfall,  # Per-shard breakdown
        "total_unique": total_unique  # Total unique visitors across all shards
    }

@app.get("/api/analytics/debug/{region_id}")
def debug_region_data(region_id: int):
    """Debug endpoint to see raw data in the region"""
    try:
        region = orm.get_region(region_id)
        if not region:
            return {"error": "Region not found"}
        
        rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
        
        with orm.conn.cursor() as cur:
            # Get unique tracking IDs in this region
            cur.execute("""
                SELECT DISTINCT tracking_id, video_shard, COUNT(*) as frame_count
                FROM bounding_box
                WHERE (x1 + x2) / 2 BETWEEN %s AND %s
                AND (y1 + y2) / 2 BETWEEN %s AND %s
                GROUP BY tracking_id, video_shard
                ORDER BY video_shard, tracking_id
            """, (rx1, rx2, ry1, ry2))
            tracking_data = cur.fetchall()
            
            # Get total bounding box count
            cur.execute("""
                SELECT COUNT(*) as total_boxes
                FROM bounding_box
                WHERE (x1 + x2) / 2 BETWEEN %s AND %s
                AND (y1 + y2) / 2 BETWEEN %s AND %s
            """, (rx1, rx2, ry1, ry2))
            total_boxes = cur.fetchone()[0]
            
            return {
                "region": dict(region),
                "unique_tracking_ids": len(set([t[0] for t in tracking_data])),
                "total_bounding_boxes": total_boxes,
                "tracking_breakdown": [
                    {"tracking_id": str(t[0])[:8] + "...", "shard": str(t[1])[:8] + "...", "frames": t[2]} 
                    for t in tracking_data[:20]  # Limit to first 20
                ],
                "message": f"Showing first 20 of {len(tracking_data)} tracking entries"
            }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/data/camera/{cam_id}")
def clear_camera_data(cam_id: int):
    """Clear all tracking and bounding box data for a specific camera"""
    try:
        with orm.conn.cursor() as cur:
            # Get all shards for this camera
            cur.execute("SELECT shard_id FROM tracking WHERE cam_id = %s", (cam_id,))
            shards = [row[0] for row in cur.fetchall()]
            
            if shards:
                # Delete bounding boxes for these shards
                cur.execute("DELETE FROM bounding_box WHERE video_shard = ANY(%s)", (shards,))
                bbox_deleted = cur.rowcount
                
                # Delete tracking entries
                cur.execute("DELETE FROM tracking WHERE cam_id = %s", (cam_id,))
                tracking_deleted = cur.rowcount
                
                orm.conn.commit()
                return {
                    "message": f"Cleared data for camera {cam_id}",
                    "bounding_boxes_deleted": bbox_deleted,
                    "tracking_entries_deleted": tracking_deleted
                }
            else:
                return {"message": f"No data found for camera {cam_id}"}
    except Exception as e:
        orm.conn.rollback()
        raise HTTPException(500, str(e))

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

@app.get("/export/analytics/csv/{region_id}")
async def export_analytics_csv(region_id: int):
    """Export analytics data as CSV"""
    try:
        footfall = orm.get_footfall_by_region(region_id)
        time_spent = orm.get_time_spent_in_region(region_id)
        demographics = orm.get_demographics_stats(region_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['VisionGuard Analytics Export'])
        writer.writerow(['Region ID', region_id])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        writer.writerow(['Footfall by Shard'])
        writer.writerow(['Shard ID', 'Count'])
        for shard_id, count in footfall:
            writer.writerow([shard_id, count])
        writer.writerow([])
        
        writer.writerow(['Average Time Spent by Shard'])
        writer.writerow(['Shard ID', 'Avg Time (seconds)'])
        for shard_id, avg_time in time_spent:
            writer.writerow([shard_id, f'{avg_time:.2f}'])
        writer.writerow([])
        
        writer.writerow(['Demographics'])
        writer.writerow(['Gender', 'Count'])
        for demo in demographics:
            writer.writerow([demo['gender'], demo['count']])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=analytics_region_{region_id}_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")

@app.get("/api/analytics/trends/daily")
async def get_daily_trends(region_id: Optional[int] = None, days: int = 7):
    """Get daily footfall trends"""
    try:
        trends = orm.get_daily_trends(region_id, days)
        return {"period": "daily", "days": days, "data": trends}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/analytics/trends/weekly")
async def get_weekly_trends(region_id: Optional[int] = None, weeks: int = 4):
    """Get weekly footfall trends"""
    try:
        trends = orm.get_weekly_trends(region_id, weeks)
        return {"period": "weekly", "weeks": weeks, "data": trends}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/analytics/trends/monthly")
async def get_monthly_trends(region_id: Optional[int] = None, months: int = 6):
    """Get monthly footfall trends"""
    try:
        trends = orm.get_monthly_trends(region_id, months)
        return {"period": "monthly", "months": months, "data": trends}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/analytics/heatmap/{region_id}")
async def get_heatmap_data(region_id: int, shard_id: Optional[str] = None, resolution: int = 50):
    """Generate heat map data for a region"""
    try:
        heatmap = orm.get_heatmap_data(region_id, shard_id, resolution)
        return {"region_id": region_id, "resolution": resolution, "data": heatmap}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/processing/active-cameras")
async def get_active_cameras():
    """Get list of cameras currently being processed"""
    return {"active_cameras": manager.get_active_cameras()}

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
    await websocket.accept()
    cam_id = None
    cancel_token = None
    try:
        # Wait for start message
        data = await websocket.receive_json()
        source = data.get("source")
        cam_id = int(data.get("cam_id", 1))
        shard_duration = int(data.get("shard_duration", 30))
        alert_threshold = float(data.get("alert_threshold", 5.0))
        
        # Create cancellation token for this processing session
        cancel_token = threading.Event()
        processing_cancel_tokens[cam_id] = cancel_token
        
        # Register connection with manager (don't accept again)
        if cam_id not in manager.active_connections:
            manager.active_connections[cam_id] = []
        manager.active_connections[cam_id].append(websocket)
        print(f"WS: Starting processing for {source} on camera {cam_id}")

        # Fetch regions for this camera
        all_regions = orm.get_all_regions()
        cam_regions = [r for r in all_regions if r.get('cam_id') == cam_id]
        
        # Dwell time tracking
        dwell_tracker = {}
        alerted_events = set()
        frame_count = 0
        FRAME_SKIP = 5  # Only send every 5th frame to reduce lag
        JPEG_QUALITY = 60  # Reduce quality for faster transmission

        loop = asyncio.get_event_loop()

        def frame_sender(frame, tracks):
            nonlocal frame_count
            
            # Check if cancelled
            if cancel_token.is_set():
                return False  # Signal to stop processing
                
            frame_count += 1
            
            # Use video timestamp from first track (all same frame)
            video_time = tracks[0]['frame_timestamp'] if tracks else 0
            active_track_ids = set()
            
            for track in tracks:
                t_id = track['track_id']
                bbox = track['bbox']
                frame_time = track['frame_timestamp']  # Actual video time
                active_track_ids.add(t_id)
                
                if t_id not in dwell_tracker:
                    dwell_tracker[t_id] = {}
                
                for region in cam_regions:
                    region_id = region['region_id']
                    region_name = region['region_name']
                    
                    if is_in_region(bbox, region):
                        if region_id not in dwell_tracker[t_id]:
                            dwell_tracker[t_id][region_id] = frame_time
                        else:
                            duration = frame_time - dwell_tracker[t_id][region_id]
                            if duration > alert_threshold:
                                if (t_id, region_id) not in alerted_events:
                                    alert_msg = {
                                        "type": "alert",
                                        "message": f"Person in {region_name} for {int(duration)}s",
                                        "region_id": region_id,
                                        "track_id": t_id,
                                        "duration": duration,
                                        "cam_id": cam_id
                                    }
                                    asyncio.run_coroutine_threadsafe(
                                        manager.send_json(alert_msg, websocket, cam_id),
                                        loop
                                    )
                                    # Save alert to database
                                    try:
                                        import uuid
                                        alert_id = str(uuid.uuid4())
                                        orm.add_alert(
                                            alert_id=alert_id,
                                            type=f"dwell_time_exceeded",
                                            time=datetime.now(),
                                            region_id=region_id
                                        )
                                    except Exception as e:
                                        print(f"Error saving alert to DB: {e}")
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

            # Only send every Nth frame to reduce WebSocket traffic
            if frame_count % FRAME_SKIP == 0:
                # Send FULL RESOLUTION frame (no scaling) so region boxes match
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                if ret:
                    asyncio.run_coroutine_threadsafe(
                        manager.send_bytes(buffer.tobytes(), websocket, cam_id), 
                        loop
                    )
            
            return True  # Continue processing

        await asyncio.to_thread(
            run_processing_with_callback, 
            source, 
            shard_duration, 
            cam_id, 
            frame_sender,
            cancel_token
        )
        
        try:
            if cam_id in manager.active_connections and websocket in manager.active_connections[cam_id]:
                await websocket.send_json({"status": "completed"})
        except:
            pass

    except WebSocketDisconnect:
        if cam_id:
            manager.disconnect(websocket, cam_id)
        print(f"Client disconnected from camera {cam_id}")
    except Exception as e:
        print(f"WS Error: {e}")
        try:
            await websocket.send_json({"status": "error", "detail": str(e)})
        except:
            pass
        if cam_id:
            manager.disconnect(websocket, cam_id)
    finally:
        # Cleanup cancellation token
        if cam_id and cam_id in processing_cancel_tokens:
            del processing_cancel_tokens[cam_id]

def run_processing_with_callback(source, shard_duration, cam_id, callback, cancel_token=None):
    # Wrapper to run the generator and consume it
    shard_generator = process_video_shards(
        source, 
        shard_duration, 
        cam_id=cam_id, 
        frame_callback=callback,
        cancel_token=cancel_token
    )
    
    for shard_id, data, tracking_data in shard_generator:
        # Check if cancelled before saving
        if cancel_token and cancel_token.is_set():
            print(f"WS: Processing cancelled for camera {cam_id}")
            break
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

# ==================== AI REPORT GENERATION ====================

@app.get("/api/ai/generate-report/{region_id}")
async def generate_ai_report(region_id: int, period: str = "daily"):
    """Generate AI-powered insights report for a region"""
    try:
        report = orm.generate_ai_report(region_id, period)
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(500, f"Report generation failed: {str(e)}")

@app.get("/api/ai/business-insights")
async def get_business_insights(cam_id: Optional[int] = None):
    """Get AI-generated business insights for shopkeeper"""
    try:
        insights = orm.get_business_insights(cam_id)
        return {"success": True, "insights": insights}
    except Exception as e:
        raise HTTPException(500, f"Failed to get insights: {str(e)}")

@app.get("/api/ai/recommendations/{region_id}")
async def get_ai_recommendations(region_id: int):
    """Get AI-powered recommendations for a specific region"""
    try:
        recommendations = orm.get_ai_recommendations(region_id)
        return {"success": True, "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(500, f"Failed to get recommendations: {str(e)}")

@app.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = 50, region_id: Optional[int] = None):
    """Get recent alerts from database"""
    try:
        alerts = orm.get_recent_alerts(limit, region_id)
        return {"success": True, "alerts": alerts}
    except Exception as e:
        raise HTTPException(500, f"Failed to get alerts: {str(e)}")

@app.post("/api/insights/generate-daily")
async def generate_daily_insights():
    """Generate and store daily insights for all regions"""
    try:
        result = orm.generate_daily_insights()
        return {"success": True, "message": "Daily insights generated", "count": result}
    except Exception as e:
        raise HTTPException(500, f"Failed to generate insights: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

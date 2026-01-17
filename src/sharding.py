import cv2
import time
import uuid
import os
import torch
import numpy as np
from torch.nn import Module, Conv2d, MaxPool2d, Linear, CrossEntropyLoss
from ultralytics import YOLO
from datetime import datetime

try:
    from database import DataBaseOrm
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database import DataBaseOrm

# --- CNN Model Definition ---
class CnnBase(Module):
    def __init__(self):
        super(CnnBase , self).__init__()
        self.conv1 = Conv2d(3,16,3,padding=1)
        self.pool = MaxPool2d(2,2)
        self.conv2 = Conv2d(16,32,3,padding=1)
        self.conv3 = Conv2d(32,64,3,padding=1)
        self.fc1 = Linear(64*8*8 , 512)
        self.fc2 = Linear(512 , 2)
        
    def forward(self,x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = self.pool(torch.relu(self.conv3(x)))
        x = x.reshape(-1 , 64*8*8)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def load_gender_classifier(weights_path):
    if not os.path.exists(weights_path):
        print(f"Warning: CNN weights not found at {weights_path}")
        return None
        
    model = CnnBase()
    try:
        state_dict = torch.load(weights_path, map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
        print(f"Loaded Gender CNN from {weights_path}")
        return model
    except Exception as e:
        print(f"Error loading CNN weights: {e}")
        return None

def process_video_shards(source, shard_duration, cam_id=1, output_dir="shards", model_path="yolo12s.pt", cnn_weights_path="../train/cnn_weights.pth", tracker_config="bytetrack.yaml", frame_callback=None, cancel_token=None):
    """
    Processes a video stream or file, splitting it into shards of a specific duration.
    Saves annotated video for each shard and yields tracking data.
    Uses a 2nd stage CNN for gender classification on 'person' detections.
    cancel_token: threading.Event that when set, signals processing should stop.
    """
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Load YOLO model
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        return

    # Load CNN Gender Classifier
    cnn_model = load_gender_classifier(cnn_weights_path)
    gender_classes = ['Male', 'Female'] # 0: man, 1: woman (mapped to Male/Female)

    # Open video source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source {source}")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30 # Default fallback
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Calculate frames per shard
    frames_per_shard = int(fps * shard_duration)
    print(f"FPS: {fps}, Frames per shard: {frames_per_shard}")

    frame_number = 0
    
    # Global map for YOLO ID -> UUID to maintain identity across shards
    global_track_map = {}
    
    # Cache for gender predictions to avoid re-running CNN on every frame for the same track ID
    # Format: {yolo_id: "Male"|"Female"}
    gender_cache = {}

    try:
        while True:
            # Check for cancellation at start of each shard
            if cancel_token and cancel_token.is_set():
                print(f"Processing cancelled before starting new shard")
                cap.release()
                return
                
            # Start a new shard
            shard_id = str(uuid.uuid4())
            shard_video_path = os.path.join(output_dir, f"{shard_id}.mp4")
            print(f"Starting Shard: {shard_id}")
            
            # Initialize VideoWriter
            # Use H264 codec for browser compatibility
            # Try different codecs in order of browser compatibility
            out = None
            codecs_to_try = [
                ('avc1', '.mp4'),   # H.264 - best browser compatibility
                ('H264', '.mp4'),   # Alternative H.264 fourcc
                ('mp4v', '.mp4'),   # MPEG-4 Part 2 - fallback
                ('XVID', '.avi'),   # XVID - last resort
            ]
            
            for codec, ext in codecs_to_try:
                if ext != '.mp4':
                    shard_video_path = os.path.join(output_dir, f"{shard_id}{ext}")
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(shard_video_path, fourcc, fps, (width, height))
                if out.isOpened():
                    print(f"Using codec: {codec}")
                    break
                out.release()
            
            if not out or not out.isOpened():
                print("ERROR: Could not create VideoWriter with any codec!")
                cap.release()
                return

            shard_data = []
            shard_unique_tracks = {} # Map to store unique tracks in this shard
            shard_frame_count = 0
            shard_active = True
            
            while shard_active:
                # Check for cancellation
                if cancel_token and cancel_token.is_set():
                    print(f"Processing cancelled during shard {shard_id}")
                    out.release()
                    cap.release()
                    return
                    
                # Check duration based on frame count
                if shard_frame_count >= frames_per_shard:
                    print(f"Shard {shard_id} duration completed ({shard_frame_count} frames).")
                    shard_active = False
                    break

                ret, frame = cap.read()
                if not ret:
                    print("End of video stream or file.")
                    shard_active = False
                    out.release()
                    cap.release()
                    
                    # Yield final data
                    tracking_data_list = []
                    for t_id, info in shard_unique_tracks.items():
                        duration = (info["last_seen"] - info["first_seen"]).total_seconds()
                        tracking_data_list.append({
                            "tracking_id": t_id,
                            "confusion_time": duration,
                            "tracker_group": info["tracker_group"],
                            "cam_id": cam_id,
                            "time": info["time"],
                            "video_shard": shard_id,
                            "gender": info["gender"]
                        })
                    
                    yield shard_id, shard_data, tracking_data_list
                    return

                frame_number += 1
                shard_frame_count += 1

                # Run tracking - Filter for class 0 (person) only
                results = model.track(frame, tracker=tracker_config, persist=True, verbose=False, classes=[0])
                
                # Create a clean copy for annotation
                annotated_frame = frame.copy()
                current_frame_tracks = []
                
                # Collect data
                for result in results:
                    if result.boxes is not None:
                        for box in result.boxes:
                            # Get YOLO ID
                            if box.id is None:
                                continue
                            
                            yolo_id = int(box.id.item())
                            
                            # Map to UUID
                            if yolo_id not in global_track_map:
                                global_track_map[yolo_id] = str(uuid.uuid4())
                            
                            db_track_id = global_track_map[yolo_id]
                            
                            class_id = int(box.cls.item())
                            class_name = model.names[class_id] if model.names else str(class_id)
                            
                            bbox = box.xyxy.tolist()[0]
                            
                            # --- Gender Classification Logic ---
                            gender = "Unknown"
                            
                            # Check if we already have a gender for this track
                            if yolo_id in gender_cache:
                                gender = gender_cache[yolo_id]
                            else:
                                # Since we filtered for person, we can just run inference if model exists
                                if cnn_model is not None:
                                    x1, y1, x2, y2 = map(int, bbox)
                                    
                                    # Clamp coordinates
                                    x1 = max(0, x1); y1 = max(0, y1)
                                    x2 = min(width, x2); y2 = min(height, y2)
                                    
                                    if x2 > x1 and y2 > y1:
                                        crop = frame[y1:y2, x1:x2]
                                        
                                        # Preprocess for CNN
                                        try:
                                            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                                            crop_resized = cv2.resize(crop_rgb, (64, 64))
                                            # Normalize and permute: (H, W, C) -> (C, H, W)
                                            crop_tensor = torch.tensor(crop_resized, dtype=torch.float32).permute(2, 0, 1) / 255.0
                                            crop_tensor = crop_tensor.unsqueeze(0) # Add batch dimension
                                            
                                            with torch.no_grad():
                                                outputs = cnn_model(crop_tensor)
                                                _, preds = torch.max(outputs, 1)
                                                gender_idx = preds.item()
                                                # 0 -> man (Male), 1 -> woman (Female)
                                                gender = gender_classes[gender_idx]
                                                
                                            # Cache the result
                                            gender_cache[yolo_id] = gender
                                        except Exception as e:
                                            print(f"CNN Inference Error: {e}")

                            timestamp = datetime.now()
                            
                            # Add to shard unique tracks if not present
                            if db_track_id not in shard_unique_tracks:
                                shard_unique_tracks[db_track_id] = {
                                    "tracker_group": class_name,
                                    "gender": gender,
                                    "time": timestamp.isoformat(),
                                    "first_seen": timestamp,
                                    "last_seen": timestamp
                                }
                            else:
                                shard_unique_tracks[db_track_id]["last_seen"] = timestamp
                                # Update gender if it was unknown and now we know
                                if shard_unique_tracks[db_track_id]["gender"] == "Unknown" and gender != "Unknown":
                                    shard_unique_tracks[db_track_id]["gender"] = gender
                            
                            obj_data = {
                                "track_id": db_track_id,
                                "class_id": class_id,
                                "bbox": bbox,
                                "Frame_number": frame_number,
                                "Video_shard": shard_id,
                                "timestamp": timestamp.isoformat()
                            }
                            shard_data.append(obj_data)
                            
                            current_frame_tracks.append({
                                "track_id": db_track_id,
                                "bbox": bbox,
                                "gender": gender,
                                "frame_timestamp": frame_number / fps  # Video time in seconds
                            })

                            # --- Visualization ---
                            x1, y1, x2, y2 = map(int, bbox)
                            
                            # Color coding: Blue for Male, Pink for Female, White for Unknown
                            color = (255, 0, 0) # Blue (BGR)
                            if gender == "Female":
                                color = (147, 20, 255) # Pinkish
                            elif gender == "Unknown":
                                color = (255, 255, 255)
                                
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                            
                            label = f"ID:{yolo_id} {gender}"
                            # Draw background for text for better readability
                            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                            cv2.rectangle(annotated_frame, (x1, y1 - 20), (x1 + w, y1), color, -1)
                            cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                out.write(annotated_frame)

                if frame_callback:
                    # frame_callback returns False to signal stop
                    should_continue = frame_callback(annotated_frame, current_frame_tracks)
                    if should_continue is False:
                        print("Processing stopped by callback")
                        out.release()
                        cap.release()
                        return
            
            # Prepare tracking data list
            tracking_data_list = []
            for t_id, info in shard_unique_tracks.items():
                duration = (info["last_seen"] - info["first_seen"]).total_seconds()
                tracking_data_list.append({
                    "tracking_id": t_id,
                    "confusion_time": duration,
                    "tracker_group": info["tracker_group"],
                    "cam_id": cam_id,
                    "time": info["time"],
                    "video_shard": shard_id,
                    "gender": info["gender"]
                })

            out.release()
            yield shard_id, shard_data, tracking_data_list

    except KeyboardInterrupt:
        print("Processing stopped by user.")
    finally:
        if cap.isOpened():
            cap.release()

if __name__ == "__main__":
    # Example usage
    video_source = "videoplayback.mp4" 
    # video_source = 0 
    
    # Initialize Database ORM
    try:
        orm = DataBaseOrm()
        print("Database connection established.")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        exit(1)

    # Ensure Camera 1 exists
    cam_id = 1
    if not orm.get_camera(cam_id):
        print(f"Camera {cam_id} not found. Creating it...")
        orm.add_camera(cam_id, "Main Camera")
    else:
        print(f"Camera {cam_id} exists.")

    # Process in 5-second shards
    # Ensure you point to the correct model paths
    shard_generator = process_video_shards(
        video_source, 
        shard_duration=30,
        model_path="yolo12s.pt", # Use a standard YOLO model (or your best.pt if it detects persons)
        cnn_weights_path="cnn_weights.pth"
    )
    
    for shard_id, data, tracking_data in shard_generator:
        print(f"Shard {shard_id} complete. Collected {len(data)} bounding boxes and {len(tracking_data)} unique tracks.")
        
        # 1. Insert Tracking Data
        tracking_tuples = []
        for t in tracking_data:
            tracking_tuples.append((
                t["tracking_id"],
                t["confusion_time"],
                t["tracker_group"],
                t["cam_id"],
                t["time"],
                t["video_shard"],
                t["gender"]
            ))
        
        if tracking_tuples:
            orm.batch_insert_tracking(tracking_tuples)

        # 2. Insert Bounding Box Data
        bbox_tuples = []
        for d in data:
            bbox = d["bbox"]
            bbox_tuples.append((
                int(bbox[0]),
                int(bbox[2]),
                int(bbox[1]),
                int(bbox[3]),
                d["timestamp"],
                d["track_id"],
                d["Video_shard"],
                d["Frame_number"]
            ))
            
        if bbox_tuples:
            orm.batch_insert_bounding_boxes(bbox_tuples)

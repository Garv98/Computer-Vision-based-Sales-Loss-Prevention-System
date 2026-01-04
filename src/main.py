from ultralytics import YOLO
import cv2

# Load the model
model = YOLO("githubcopy.pt")
video_path = "videoplayback.mp4"

# Get video FPS
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
cap.release()

print(f"Video FPS: {fps}")

# Run tracking
# source=0: Webcam
# show=True: Display the video with annotations
# stream=True: Return a generator for processing frames
results = model.track(source=video_path, tracker="bytetrack.yaml", show=True, stream=True , conf = 0.1)

# Store data for the current second
current_second_data = []
frame_count = 0

try:
    for result in results:
        # List to store data for the current frame
        current_frame_data = []
        
        # Check if boxes exist in the result
        if result.boxes is not None:
            # Iterate over each detected box
            for box in result.boxes:
                # Extract data
                # id might be None if tracking hasn't initialized an ID yet
                track_id = int(box.id.item()) if box.id is not None else None
                class_id = int(box.cls.item())
                bbox = box.xyxy.tolist()[0] # [x1, y1, x2, y2]
                
                # Create a dictionary for the object
                obj_data = {
                    "track_id": track_id,
                    "class_id": class_id,
                    "bbox": bbox
                }
                
                current_frame_data.append(obj_data)
        
        # Append current frame data to the second's data
        current_second_data.append(current_frame_data)
        frame_count += 1
        
        # Check if a second has passed
        if fps > 0 and frame_count % int(fps) == 0:
            print(f"--- Data for Second {frame_count // int(fps)} ---")
            print(current_second_data)
            # Reset for the next second
            current_second_data = []
        
except KeyboardInterrupt:
    print("Stopped by user")
import cv2
import torch
import time
import os
from pathlib import Path

# Get the path to the desktop
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
print(f"Desktop path: {desktop_path}")

# Full path to the video file
video_filename = "video.mp4"  # Replace with your file name
video_path = os.path.join(desktop_path, video_filename)

# Check if the file exists
if not os.path.exists(video_path):
    print(f"ERROR: Video file not found: {video_path}")
    print(f"Files found on Desktop:")
    try:
        files = os.listdir(desktop_path)
        for file in files:
            if file.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                print(f"  - {file}")
    except:
        print("Unable to read the Desktop directory.")
    exit()

print(f"Video file found: {video_path}")

# Load the YOLOv5 model
print("Loading YOLO model...")
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
print("Model loaded successfully!")

# Open the video file
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("ERROR: Failed to open video file!")
    exit()

# Retrieve video information
fps = int(cap.get(cv2.CAP_PROP_FPS))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(f"Video information:")
print(f"  - Resolution: {width}x{height}")
print(f"  - FPS: {fps}")
print(f"  - Total frames: {total_frames}")
print(f"  - Duration: {total_frames/fps:.1f} seconds")

# Set up the output video writer (save to Desktop)
output_path = os.path.join(desktop_path, "output_detection.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

frame_count = 0
start_time = time.time()

print("\nProcessing video...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("\nVideo processing complete!")
        break
    
    frame_count += 1
    
    # Display progress every 30 frames
    if frame_count % 30 == 0:
        progress = (frame_count / total_frames) * 100
        elapsed_time = time.time() - start_time
        remaining_time = (elapsed_time / frame_count) * (total_frames - frame_count)
        print(f"Progress: {frame_count}/{total_frames} ({progress:.1f}%) - "
              f"Elapsed: {elapsed_time:.1f}s - Remaining: {remaining_time:.1f}s")
    
    # Run YOLO object detection
    results = model(frame)
    
    # Draw detection results on the frame
    annotated_frame = results.render()[0]
    
    # Write the annotated frame to the output video
    out.write(annotated_frame)

# Clean up
cap.release()
out.release()
cv2.destroyAllWindows()

total_time = time.time() - start_time
print(f"\n✅ Processing complete!")
print(f"📊 Total time: {total_time:.1f} seconds")
print(f"⚡ Average FPS: {frame_count/total_time:.1f}")
print(f"💾 Output file saved at: {output_path}")

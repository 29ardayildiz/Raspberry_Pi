import sys
import cv2
import torch
import numpy as np
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, QSlider, QHBoxLayout
from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

class DetectionThread(QThread):
    detection_done = Signal(np.ndarray)
    
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.frame = None
        self.active = True
        
    def run(self):
        while self.active:
            if self.frame is not None:
                # Perform detection
                results = self.model(self.frame)
                annotated_frame = results.render()[0]
                self.detection_done.emit(annotated_frame)
                self.frame = None
            QThread.msleep(10)  # Prevent busy waiting
            
    def set_frame(self, frame):
        self.frame = frame
        
    def stop(self):
        self.active = False
        self.wait()

class ObjectDetectionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time Object Detection")
        self.setGeometry(100, 100, 800, 700)

        # Video display
        self.label = QLabel("Video akışı burada görünecek")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(640, 480)
        
        # Buttons
        self.btn_select_video = QPushButton("Video Seç")
        self.btn_select_video.clicked.connect(self.select_video)
        
        self.btn_pause = QPushButton("Duraklat")
        self.btn_pause.setCheckable(True)
        self.btn_pause.clicked.connect(self.toggle_pause)
        
        # Speed control slider
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 100)  # 10-100% speed
        self.speed_slider.setValue(50)       # Default 50%
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.valueChanged.connect(self.set_speed)
        
        # Layouts
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.btn_select_video)
        control_layout.addWidget(self.btn_pause)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(control_layout)
        layout.addWidget(QLabel("Oynatma Hızı:"))
        layout.addWidget(self.speed_slider)
        self.setLayout(layout)

        # Load YOLO model (faster nano version)
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
        
        # Video capture
        self.cap = None
        self.paused = False
        self.speed = 50  # Default speed (ms)
        
        # Setup timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Setup detection thread
        self.detection_thread = DetectionThread(self.model)
        self.detection_thread.detection_done.connect(self.display_frame)
        self.detection_thread.start()

    def select_video(self):
        video_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Video Dosyası Seç", 
            "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        if video_path:
            self.cap = cv2.VideoCapture(video_path)
            self.timer.start(self.speed)  # Start with current speed

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.setText("Devam Et")
        else:
            self.btn_pause.setText("Duraklat")
            self.timer.start(self.speed)

    def set_speed(self, value):
        # Map slider value to timer interval (10-100% -> 10-100ms)
        self.speed = max(10, 110 - value)  # Inverse: Higher slider = faster
        if not self.paused:
            self.timer.start(self.speed)

    def update_frame(self):
        if self.cap and self.cap.isOpened() and not self.paused:
            ret, frame = self.cap.read()
            if ret:
                # Skip frames if needed for performance
                frame = cv2.resize(frame, (640, 480))  # Reduce resolution
                
                # Pass frame to detection thread
                self.detection_thread.set_frame(frame)
                
                # Display raw frame immediately (optional)
                self.display_raw_frame(frame)
            else:
                self.timer.stop()

    def display_raw_frame(self, frame):
        """Display frame immediately without detection (for faster preview)"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.KeepAspectRatio))

    def display_frame(self, annotated_frame):
        """Display frame with detection results"""
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.KeepAspectRatio))

    def closeEvent(self, event):
        self.detection_thread.stop()
        if self.cap:
            self.cap.release()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ObjectDetectionApp()
    window.show()
    sys.exit(app.exec())
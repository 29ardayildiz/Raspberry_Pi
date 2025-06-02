import sys
import cv2
import torch
import numpy as np
import time
from pathlib import Path
from threading import Lock
from PySide6.QtWidgets import (QApplication, QLabel, QPushButton, QVBoxLayout, 
                              QWidget, QFileDialog, QSlider, QHBoxLayout, 
                              QProgressBar, QComboBox, QCheckBox, QSpinBox,
                              QGroupBox, QGridLayout, QStatusBar, QMainWindow,
                              QSplitter, QFrame, QMessageBox)
from PySide6.QtCore import QTimer, Qt, QThread, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPixmap, QFont, QIcon, QPalette, QColor

class DetectionThread(QThread):
    detection_done = Signal(np.ndarray, dict)  # Frame and detection info
    performance_update = Signal(float, int)  # FPS and detection count
    
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.frame_queue = []
        self.queue_lock = Lock()
        self.active = True
        self.detection_enabled = True
        self.confidence_threshold = 0.5
        self.frame_skip = 2  # Process every nth frame for Raspberry Pi
        self.frame_counter = 0
        
        # Performance tracking
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.detection_count = 0
        
    def run(self):
        while self.active:
            frame_to_process = None
            
            with self.queue_lock:
                if self.frame_queue:
                    frame_to_process = self.frame_queue.pop(0)
            
            if frame_to_process is not None and self.detection_enabled:
                self.frame_counter += 1
                
                # Skip frames for better performance on Raspberry Pi
                if self.frame_counter % self.frame_skip == 0:
                    start_time = time.time()
                    
                    # Perform detection with optimized settings
                    with torch.no_grad():
                        results = self.model(frame_to_process, size=416)  # Smaller input size
                        results.conf = self.confidence_threshold
                    
                    # Get detection info
                    detections = results.pandas().xyxy[0]
                    detection_info = {
                        'count': len(detections),
                        'objects': detections['name'].unique().tolist() if len(detections) > 0 else [],
                        'processing_time': time.time() - start_time
                    }
                    
                    annotated_frame = results.render()[0]
                    self.detection_done.emit(annotated_frame, detection_info)
                    
                    # Update performance metrics
                    self.fps_counter += 1
                    self.detection_count += detection_info['count']
                    
                    # Calculate FPS every second
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        fps = self.fps_counter / (current_time - self.last_fps_time)
                        self.performance_update.emit(fps, self.detection_count)
                        self.fps_counter = 0
                        self.last_fps_time = current_time
                        self.detection_count = 0
            
            self.msleep(5)  # Reduced sleep for better responsiveness
            
    def add_frame(self, frame):
        with self.queue_lock:
            # Keep queue size manageable
            if len(self.frame_queue) > 3:
                self.frame_queue.pop(0)
            self.frame_queue.append(frame.copy())
    
    def set_detection_enabled(self, enabled):
        self.detection_enabled = enabled
    
    def set_confidence_threshold(self, threshold):
        self.confidence_threshold = threshold
    
    def set_frame_skip(self, skip):
        self.frame_skip = max(1, skip)
        
    def stop(self):
        self.active = False
        self.wait()

class VideoPlayerWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #3498db;
                border-radius: 10px;
                background-color: #2c3e50;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.video_label = QLabel("Video Player")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 18px;
                font-weight: bold;
                border: none;
                background-color: #34495e;
                border-radius: 8px;
            }
        """)
        
        layout.addWidget(self.video_label)
        self.setLayout(layout)

class ControlPanel(QGroupBox):
    def __init__(self):
        super().__init__("Control Panel")
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout()
        
        # File selection
        self.btn_select_video = QPushButton("📁 Select Video")
        self.btn_select_video.setStyleSheet(self.get_button_style("#3498db"))
        layout.addWidget(self.btn_select_video, 0, 0, 1, 2)
        
        # Playback controls
        self.btn_pause = QPushButton("⏸️ Pause")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setStyleSheet(self.get_button_style("#e74c3c"))
        layout.addWidget(self.btn_pause, 1, 0)
        
        self.btn_stop = QPushButton("⏹️ Stop")
        self.btn_stop.setStyleSheet(self.get_button_style("#95a5a6"))
        layout.addWidget(self.btn_stop, 1, 1)
        
        # Speed control
        layout.addWidget(QLabel("Playback Speed:"), 2, 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(50)
        layout.addWidget(self.speed_slider, 2, 1)
        
        self.speed_label = QLabel("100%")
        self.speed_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.speed_label, 3, 1)
        
        self.setLayout(layout)
    
    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
            QPushButton:checked {{
                background-color: #e67e22;
            }}
        """

class DetectionPanel(QGroupBox):
    def __init__(self):
        super().__init__("Detection Settings")
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout()
        
        # Detection toggle
        self.detection_checkbox = QCheckBox("Enable Detection")
        self.detection_checkbox.setChecked(True)
        self.detection_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border: 2px solid #27ae60;
            }
        """)
        layout.addWidget(self.detection_checkbox, 0, 0, 1, 2)
        
        # Confidence threshold
        layout.addWidget(QLabel("Confidence:"), 1, 0)
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(10, 95)
        self.confidence_slider.setValue(50)
        self.confidence_slider.setTickPosition(QSlider.TicksBelow)
        layout.addWidget(self.confidence_slider, 1, 1)
        
        self.confidence_label = QLabel("0.50")
        self.confidence_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.confidence_label, 2, 1)
        
        # Performance settings for Raspberry Pi
        layout.addWidget(QLabel("Frame Skip:"), 3, 0)
        self.frame_skip_spinbox = QSpinBox()
        self.frame_skip_spinbox.setRange(1, 10)
        self.frame_skip_spinbox.setValue(2)
        self.frame_skip_spinbox.setToolTip("Process every Nth frame (higher = better performance)")
        layout.addWidget(self.frame_skip_spinbox, 3, 1)
        
        self.setLayout(layout)

class StatusPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #ecf0f1;
                padding: 5px;
            }
        """)
        
        layout = QHBoxLayout()
        
        # Performance indicators
        self.video_fps_label = QLabel("Video FPS: 0.0")
        self.video_fps_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.video_fps_label.setToolTip("Current video playback FPS")
        
        self.detection_fps_label = QLabel("Detection FPS: 0.0")
        self.detection_fps_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.detection_fps_label.setToolTip("Object detection processing FPS")
        
        self.detection_label = QLabel("Objects: 0")
        self.detection_label.setStyleSheet("font-weight: bold; color: #3498db;")
        
        self.objects_label = QLabel("Types: None")
        self.objects_label.setStyleSheet("font-weight: bold; color: #9b59b6;")
        
        # Progress bar for processing
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        layout.addWidget(self.video_fps_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.detection_fps_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.detection_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.objects_label)
        layout.addStretch()
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)

class ObjectDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎯 Professional Object Detection - Raspberry Pi Edition")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply modern styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
        """)
        
        self.setup_ui()
        self.setup_model()
        self.setup_connections()
        
        # Video and detection state
        self.cap = None
        self.paused = False
        self.current_video_path = None
        
        # Setup timer for video playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Show welcome message
        self.show_welcome_message()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Video player
        self.video_widget = VideoPlayerWidget()
        main_splitter.addWidget(self.video_widget)
        
        # Right side - Controls
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Control panels
        self.control_panel = ControlPanel()
        self.detection_panel = DetectionPanel()
        
        right_layout.addWidget(self.control_panel)
        right_layout.addWidget(self.detection_panel)
        right_layout.addStretch()
        
        right_panel.setLayout(right_layout)
        right_panel.setMaximumWidth(350)
        main_splitter.addWidget(right_panel)
        
        # Status panel at bottom
        self.status_panel = StatusPanel()
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(main_splitter)
        main_layout.addWidget(self.status_panel)
        
        central_widget.setLayout(main_layout)
        
        # Set splitter proportions
        main_splitter.setSizes([800, 350])

    def setup_model(self):
        try:
            self.status_panel.progress_bar.setVisible(True)
            self.status_panel.progress_bar.setRange(0, 0)  # Indeterminate
            
            # Load optimized model for Raspberry Pi
            print("Loading YOLOv5 model optimized for Raspberry Pi...")
            self.model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
            self.model.eval()
            
            # Optimize for CPU (Raspberry Pi doesn't have GPU)
            torch.set_num_threads(2)  # Limit threads for Raspberry Pi
            
            # Setup detection thread
            self.detection_thread = DetectionThread(self.model)
            self.detection_thread.detection_done.connect(self.display_detection_frame)
            self.detection_thread.performance_update.connect(self.update_performance)
            self.detection_thread.start()
            
            self.status_panel.progress_bar.setVisible(False)
            print("Model loaded successfully!")
            
        except Exception as e:
            self.status_panel.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Model Loading Error", 
                               f"Failed to load YOLO model:\n{str(e)}")

    def setup_connections(self):
        # Control panel connections
        self.control_panel.btn_select_video.clicked.connect(self.select_video)
        self.control_panel.btn_pause.clicked.connect(self.toggle_pause)
        self.control_panel.btn_stop.clicked.connect(self.stop_video)
        self.control_panel.speed_slider.valueChanged.connect(self.set_speed)
        
        # Detection panel connections
        self.detection_panel.detection_checkbox.stateChanged.connect(self.toggle_detection)
        self.detection_panel.confidence_slider.valueChanged.connect(self.set_confidence)
        self.detection_panel.frame_skip_spinbox.valueChanged.connect(self.set_frame_skip)

    def show_welcome_message(self):
        welcome_text = """
        <div style='text-align: center; color: #34495e; font-size: 16px;'>
            <h2>🎯 Professional Object Detection</h2>
            <p><b>Optimized for Raspberry Pi 4B</b></p>
            <br>
            <p>📁 Click 'Select Video' to start detection</p>
            <p>⚙️ Adjust settings in the control panel</p>
            <p>🚀 Enjoy real-time object detection!</p>
        </div>
        """
        self.video_widget.video_label.setText(welcome_text)

    def select_video(self):
        video_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File", 
            str(Path.home()), 
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv)"
        )
        
        if video_path:
            self.current_video_path = video_path
            self.cap = cv2.VideoCapture(video_path)
            
            if self.cap.isOpened():
                # Get video properties
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                
                print(f"Video loaded: {Path(video_path).name}")
                print(f"Duration: {duration:.1f}s, FPS: {fps:.1f}, Frames: {frame_count}")
                
                # Start playback
                self.timer.start(max(10, int(1000 / fps)))
                self.control_panel.btn_pause.setText("⏸️ Pause")
                self.paused = False
            else:
                QMessageBox.warning(self, "Video Error", "Failed to open video file!")

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.control_panel.btn_pause.setText("▶️ Play")
            self.timer.stop()
        else:
            self.control_panel.btn_pause.setText("⏸️ Pause")
            if self.cap and self.cap.isOpened():
                self.timer.start()

    def stop_video(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.timer.stop()
        self.paused = False
        self.control_panel.btn_pause.setText("⏸️ Pause")
        self.control_panel.btn_pause.setChecked(False)
        self.show_welcome_message()

    def set_speed(self, value):
        self.control_panel.speed_label.setText(f"{value}%")
        if self.cap and self.cap.isOpened() and not self.paused:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            interval = max(5, int(1000 / (fps * value / 100)))
            self.timer.start(interval)

    def toggle_detection(self, state):
        enabled = state == Qt.Checked
        if hasattr(self, 'detection_thread'):
            self.detection_thread.set_detection_enabled(enabled)

    def set_confidence(self, value):
        confidence = value / 100.0
        self.detection_panel.confidence_label.setText(f"{confidence:.2f}")
        if hasattr(self, 'detection_thread'):
            self.detection_thread.set_confidence_threshold(confidence)

    def set_frame_skip(self, value):
        if hasattr(self, 'detection_thread'):
            self.detection_thread.set_frame_skip(value)

    def update_frame(self):
        if self.cap and self.cap.isOpened() and not self.paused:
            ret, frame = self.cap.read()
            if ret:
                # Resize for better performance on Raspberry Pi
                frame = cv2.resize(frame, (640, 480))
                
                # Add frame to detection queue
                if hasattr(self, 'detection_thread'):
                    self.detection_thread.add_frame(frame)
                
                # Display raw frame immediately for smooth playback
                self.display_raw_frame(frame)
            else:
                # Video ended, loop or stop
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video

    def display_raw_frame(self, frame):
        """Display frame without detection for smooth playback"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # Scale to fit label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.video_widget.video_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.video_widget.video_label.setPixmap(scaled_pixmap)

    def display_detection_frame(self, annotated_frame, detection_info):
        """Display frame with detection results"""
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        scaled_pixmap = pixmap.scaled(
            self.video_widget.video_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.video_widget.video_label.setPixmap(scaled_pixmap)
        
        # Update detection info
        self.status_panel.detection_label.setText(f"Objects: {detection_info['count']}")
        objects_text = ", ".join(detection_info['objects'][:3])  # Show first 3 types
        if len(detection_info['objects']) > 3:
            objects_text += "..."
        self.status_panel.objects_label.setText(f"Types: {objects_text or 'None'}")

    def update_performance(self, fps, detection_count):
        """Update performance indicators"""
        self.status_panel.fps_label.setText(f"FPS: {fps:.1f}")

    def closeEvent(self, event):
        """Clean up resources when closing"""
        if hasattr(self, 'detection_thread'):
            self.detection_thread.stop()
        if self.cap:
            self.cap.release()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Professional Object Detection")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("RaspberryPi AI Lab")
    
    # Apply modern style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = ObjectDetectionApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
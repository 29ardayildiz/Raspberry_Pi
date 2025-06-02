import sys
import cv2
import torch
import time
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap

class ObjectDetectionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time Object Detection")
        self.setGeometry(100, 100, 800, 600)

        self.label = QLabel("Video akışı burada görünecek")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedSize(800, 500)

        self.btn_select_video = QPushButton("Video Seç")
        self.btn_select_video.clicked.connect(self.select_video)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.btn_select_video)
        self.setLayout(layout)

        # Timer for video playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Load YOLO model
        self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

        self.cap = None

    def select_video(self):
        video_path, _ = QFileDialog.getOpenFileName(self, "Video Dosyası Seç", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if video_path:
            self.cap = cv2.VideoCapture(video_path)
            self.timer.start(30)  # ~30 fps

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # YOLO Detection
                results = self.model(frame)
                annotated_frame = results.render()[0]

                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(convert_to_Qt_format)
                self.label.setPixmap(pixmap)
            else:
                self.timer.stop()
                self.cap.release()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ObjectDetectionApp()
    window.show()
    sys.exit(app.exec_())

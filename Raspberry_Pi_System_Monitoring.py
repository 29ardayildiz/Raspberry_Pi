from flask import Flask, jsonify, render_template_string
import psutil
import datetime
import time

app = Flask(__name__)

def get_system_info():
    # CPU sıcaklığını al
    temp = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = round(int(f.read()) / 1000, 1)
    except:
        temp = "N/A"
    
    # Diğer sistem bilgilerini al
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    # Sistem yükünü al (1, 5 ve 15 dakikalık ortalamalar)
    load_avg = [round(x, 2) for x in psutil.getloadavg()]
    
    # Ağ trafiğini al
    net = psutil.net_io_counters()
    net_sent = round(net.bytes_sent / (1024 * 1024), 2)  # MB cinsinden
    net_recv = round(net.bytes_recv / (1024 * 1024), 2)  # MB cinsinden
    
    # Çalışma süresini al
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
    
    return {
        "temp": temp,
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
        "load_avg": load_avg,
        "net_sent": net_sent,
        "net_recv": net_recv,
        "uptime": str(uptime).split('.')[0]  # Mikrosaniyeleri kaldır
    }

@app.route('/status')
def status():
    return jsonify(get_system_info())

@app.route('/')
def dashboard():
    info = get_system_info()
    
    # Sistem durumuna göre renkler belirle
    temp_color = "text-danger" if info['temp'] != "N/A" and info['temp'] > 70 else "text-success"
    cpu_color = "text-danger" if info['cpu'] > 80 else "text-success"
    mem_color = "text-danger" if info['mem'] > 80 else "text-success"
    disk_color = "text-danger" if info['disk'] > 80 else "text-success"
    
    # HTML şablonu
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Raspberry Pi Sistem İzleme</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                background: linear-gradient(135deg, #1a2a6c, #b21f1f, #1a2a6c);
                background-size: 400% 400%;
                animation: gradientBG 15s ease infinite;
                color: #f8f9fa;
                min-height: 100vh;
                padding-top: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            @keyframes gradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            .card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                transition: transform 0.3s ease;
                height: 100%;
                opacity: 0;
                transform: translateY(20px);
                animation: fadeIn 0.5s forwards;
            }
            @keyframes fadeIn {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            .card:nth-child(1) { animation-delay: 0.1s; }
            .card:nth-child(2) { animation-delay: 0.2s; }
            .card:nth-child(3) { animation-delay: 0.3s; }
            .card:nth-child(4) { animation-delay: 0.4s; }
            .card-header {
                background: rgba(0, 0, 0, 0.2);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            .value-display {
                font-size: 2.5rem;
                font-weight: bold;
                margin: 15px 0;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            .progress {
                height: 20px;
                margin: 10px 0;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 10px;
                overflow: visible;
            }
            .progress-bar {
                border-radius: 10px;
                position: relative;
                overflow: visible;
            }
            .progress-bar::after {
                content: attr(data-progress);
                position: absolute;
                right: 10px;
                top: -25px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 2px 8px;
                border-radius: 5px;
                font-size: 12px;
            }
            .status-icon {
                font-size: 3rem;
                margin-bottom: 15px;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
            }
            .system-card {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255,255,255,0.1);
            }
            .text-success { color: #20c997 !important; }
            .text-warning { color: #fd7e14 !important; }
            .text-danger { color: #dc3545 !important; }
            .chart-container {
                height: 200px;
                position: relative;
            }
            .refresh-btn {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                background: rgba(13, 110, 253, 0.9);
                border: none;
                color: white;
                transition: all 0.3s;
            }
            .refresh-btn:hover {
                transform: scale(1.1) rotate(90deg);
                background: rgba(11, 94, 215, 1);
            }
            footer {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 10px;
                padding: 15px;
                margin-top: 20px;
                font-size: 0.9rem;
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255,255,255,0.1);
            }
            .refresh-indicator {
                position: fixed;
                top: 20px;
                right: 20px;
                background: rgba(0,0,0,0.5);
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9rem;
                z-index: 1000;
            }
            .pulse {
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #20c997;
                margin-right: 5px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(0.9); }
                50% { transform: scale(1.1); }
                100% { transform: scale(0.9); }
            }
        </style>
    </head>
    <body>
        <div class="refresh-indicator">
            <span class="pulse"></span> <span id="countdown">5</span> saniye sonra güncellenecek
        </div>
        
        <div class="container py-4">
            <div class="text-center mb-4">
                <h1 class="display-4 fw-bold"><i class="fas fa-microchip me-2"></i>Raspberry Pi Sistem İzleme</h1>
                <p class="lead">Anlık sistem performansı ve kaynak kullanımı</p>
                <div class="system-card mt-3">
                    <div class="row">
                        <div class="col-md-6">
                            <p><i class="fas fa-server me-2"></i><strong>Çalışma Süresi:</strong> {{ info.uptime }}</p>
                            <p><i class="fas fa-network-wired me-2"></i><strong>Ağ Gönderilen:</strong> {{ info.net_sent }} MB</p>
                        </div>
                        <div class="col-md-6">
                            <p><i class="fas fa-microchip me-2"></i><strong>Sistem Yükü:</strong> {{ info.load_avg[0] }} | {{ info.load_avg[1] }} | {{ info.load_avg[2] }}</p>
                            <p><i class="fas fa-network-wired me-2"></i><strong>Ağ Alınan:</strong> {{ info.net_recv }} MB</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row g-4">
                <!-- CPU Sıcaklığı -->
                <div class="col-md-6 col-lg-3">
                    <div class="card">
                        <div class="card-header text-center">
                            <i class="fas fa-thermometer-half me-2"></i>CPU Sıcaklığı
                        </div>
                        <div class="card-body text-center">
                            <div class="status-icon {{ temp_color }}">
                                <i class="fas fa-fire"></i>
                            </div>
                            <div class="value-display {{ temp_color }}">
                                {{ info.temp }} °C
                            </div>
                            <div class="progress">
                                {% if info.temp != "N/A" %}
                                <div class="progress-bar bg-danger" role="progressbar" 
                                     style="width: {{ (info.temp / 85 * 100) if info.temp <= 85 else 100 }}%;"
                                     data-progress="{{ info.temp }}°C">
                                </div>
                                {% endif %}
                            </div>
                            <p class="mb-0">
                                {% if info.temp != "N/A" %}
                                    {% if info.temp < 50 %}
                                        <span class="text-success"><i class="fas fa-check-circle me-1"></i>Normal</span>
                                    {% elif info.temp < 70 %}
                                        <span class="text-warning"><i class="fas fa-exclamation-triangle me-1"></i>Orta</span>
                                    {% else %}
                                        <span class="text-danger"><i class="fas fa-exclamation-circle me-1"></i>Yüksek</span>
                                    {% endif %}
                                {% else %}
                                    <span class="text-warning">Ölçülemedi</span>
                                {% endif %}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- CPU Kullanımı -->
                <div class="col-md-6 col-lg-3">
                    <div class="card">
                        <div class="card-header text-center">
                            <i class="fas fa-microchip me-2"></i>CPU Kullanımı
                        </div>
                        <div class="card-body text-center">
                            <div class="status-icon {{ cpu_color }}">
                                <i class="fas fa-brain"></i>
                            </div>
                            <div class="value-display {{ cpu_color }}">
                                {{ info.cpu }}%
                            </div>
                            <div class="progress">
                                <div class="progress-bar bg-info" role="progressbar" 
                                     style="width: {{ info.cpu }}%;"
                                     data-progress="{{ info.cpu }}%">
                                </div>
                            </div>
                            <p class="mb-0">
                                {% if info.cpu < 60 %}
                                    <span class="text-success"><i class="fas fa-check-circle me-1"></i>Düşük Yük</span>
                                {% elif info.cpu < 85 %}
                                    <span class="text-warning"><i class="fas fa-exclamation-triangle me-1"></i>Orta Yük</span>
                                {% else %}
                                    <span class="text-danger"><i class="fas fa-exclamation-circle me-1"></i>Yüksek Yük</span>
                                {% endif %}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Bellek Kullanımı -->
                <div class="col-md-6 col-lg-3">
                    <div class="card">
                        <div class="card-header text-center">
                            <i class="fas fa-memory me-2"></i>Bellek Kullanımı
                        </div>
                        <div class="card-body text-center">
                            <div class="status-icon {{ mem_color }}">
                                <i class="fas fa-memory"></i>
                            </div>
                            <div class="value-display {{ mem_color }}">
                                {{ info.mem }}%
                            </div>
                            <div class="progress">
                                <div class="progress-bar bg-warning" role="progressbar" 
                                     style="width: {{ info.mem }}%;"
                                     data-progress="{{ info.mem }}%">
                                </div>
                            </div>
                            <p class="mb-0">
                                {% if info.mem < 60 %}
                                    <span class="text-success"><i class="fas fa-check-circle me-1"></i>Yeterli</span>
                                {% elif info.mem < 85 %}
                                    <span class="text-warning"><i class="fas fa-exclamation-triangle me-1"></i>Orta</span>
                                {% else %}
                                    <span class="text-danger"><i class="fas fa-exclamation-circle me-1"></i>Yetersiz</span>
                                {% endif %}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Disk Kullanımı -->
                <div class="col-md-6 col-lg-3">
                    <div class="card">
                        <div class="card-header text-center">
                            <i class="fas fa-hdd me-2"></i>Disk Kullanımı
                        </div>
                        <div class="card-body text-center">
                            <div class="status-icon {{ disk_color }}">
                                <i class="fas fa-database"></i>
                            </div>
                            <div class="value-display {{ disk_color }}">
                                {{ info.disk }}%
                            </div>
                            <div class="progress">
                                <div class="progress-bar bg-success" role="progressbar" 
                                     style="width: {{ info.disk }}%;"
                                     data-progress="{{ info.disk }}%">
                                </div>
                            </div>
                            <p class="mb-0">
                                {% if info.disk < 75 %}
                                    <span class="text-success"><i class="fas fa-check-circle me-1"></i>Yeterli</span>
                                {% elif info.disk < 90 %}
                                    <span class="text-warning"><i class="fas fa-exclamation-triangle me-1"></i>Dikkat</span>
                                {% else %}
                                    <span class="text-danger"><i class="fas fa-exclamation-circle me-1"></i>Dolu</span>
                                {% endif %}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <footer class="text-center mt-5">
                <div class="row">
                    <div class="col-md-6 mb-3 mb-md-0">
                        <p class="mb-0"><i class="fas fa-code me-2"></i>Flask & Python ile geliştirilmiştir</p>
                    </div>
                    <div class="col-md-6">
                        <p class="mb-0"><i class="fas fa-sync-alt me-2"></i>Son Güncelleme: <span id="last-update">{{ time.strftime('%H:%M:%S') }}</span></p>
                    </div>
                </div>
            </footer>
        </div>

        <button class="refresh-btn" onclick="refreshPage()">
            <i class="fas fa-sync-alt"></i>
        </button>

        <script>
            // Sayfa yüklendiğinde kartlara animasyon ekle
            document.addEventListener('DOMContentLoaded', function() {
                const cards = document.querySelectorAll('.card');
                cards.forEach((card, index) => {
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, 150 * index);
                });
                
                // Geri sayımı başlat
                startCountdown();
            });
            
            // Sayfayı yenileme fonksiyonu
            function refreshPage() {
                location.reload();
            }
            
            // Geri sayım için değişkenler
            let countdown = 5;
            let countdownInterval;
            
            // Geri sayımı başlat
            function startCountdown() {
                const countdownElement = document.getElementById('countdown');
                countdownElement.textContent = countdown;
                
                countdownInterval = setInterval(function() {
                    countdown--;
                    countdownElement.textContent = countdown;
                    
                    if (countdown <= 0) {
                        clearInterval(countdownInterval);
                        refreshPage();
                    }
                }, 1000);
            }
            
            // Yenileme butonuna tıklandığında geri sayımı sıfırla
            document.querySelector('.refresh-btn').addEventListener('click', function() {
                clearInterval(countdownInterval);
                countdown = 5;
                startCountdown();
            });
        </script>
    </body>
    </html>
    ''', info=info, temp_color=temp_color, cpu_color=cpu_color, 
        mem_color=mem_color, disk_color=disk_color, time=time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

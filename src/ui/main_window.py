"""
메인 윈도우 UI
- 대시보드 레이아웃
- 실시간 그래프
- 컨트롤 패널
"""

import sys
import os
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar, QGroupBox,
    QScrollArea, QSplitter, QStatusBar, QMessageBox, QFileDialog,
    QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

import pyqtgraph as pg
from pyqtgraph import PlotWidget

# 모듈 임포트를 위한 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data.collector import DataCollector, DataPoint
from src.report.pdf_generator import PDFReportGenerator
from src.core import CPUMonitor, MemoryMonitor, GPUMonitor, DiskMonitor, NetworkMonitor, SystemInfo


class GaugeWidget(QFrame):
    """게이지 위젯 (원형 진행률 표시)"""
    
    def __init__(self, title: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.value = 0
        self.secondary_value = None
        self.secondary_label = ""
        
        self.setStyleSheet("""
            GaugeWidget {
                background-color: #1e293b;
                border-radius: 15px;
                border: 1px solid #334155;
            }
        """)
        self.setMinimumSize(180, 150)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 제목
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 프로그레스 바
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                background-color: #334155;
                height: 16px;
            }
            QProgressBar::chunk {
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #06b6d4, stop:1 #22d3ee);
            }
        """)
        layout.addWidget(self.progress)
        
        # 값 표시
        self.value_label = QLabel("0%")
        self.value_label.setStyleSheet("color: #f1f5f9; font-size: 28px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        
        # 보조 값 (온도 등)
        self.secondary_label_widget = QLabel("")
        self.secondary_label_widget.setStyleSheet("color: #64748b; font-size: 11px;")
        self.secondary_label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.secondary_label_widget)
    
    def set_value(self, value: float, secondary: Optional[float] = None, secondary_unit: str = ""):
        """값 설정"""
        self.value = min(100, max(0, value))
        self.progress.setValue(int(self.value))
        self.value_label.setText(f"{self.value:.1f}{self.unit}")
        
        # 색상 변경 (사용률에 따라)
        if self.value < 50:
            color = "#22c55e"  # 녹색
        elif self.value < 80:
            color = "#eab308"  # 노란색
        else:
            color = "#ef4444"  # 빨간색
        
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 8px;
                background-color: #334155;
                height: 16px;
            }}
            QProgressBar::chunk {{
                border-radius: 8px;
                background-color: {color};
            }}
        """)
        
        if secondary is not None:
            self.secondary_label_widget.setText(f"{secondary:.1f}{secondary_unit}")


class GraphWidget(QFrame):
    """실시간 그래프 위젯"""
    
    def __init__(self, title: str, y_label: str = "", max_points: int = 300, parent=None):
        super().__init__(parent)
        self.title = title
        self.max_points = max_points
        self.data_lines: Dict[str, dict] = {}
        
        self.setStyleSheet("""
            GraphWidget {
                background-color: #1e293b;
                border-radius: 15px;
                border: 1px solid #334155;
            }
        """)
        
        self._setup_ui(y_label)
    
    def _setup_ui(self, y_label: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # 제목
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # PyQtGraph 설정
        pg.setConfigOptions(antialias=True)
        
        self.plot_widget = PlotWidget()
        self.plot_widget.setBackground('#0f172a')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', y_label, color='#94a3b8')
        self.plot_widget.setLabel('bottom', '시간 (초)', color='#94a3b8')
        self.plot_widget.getAxis('left').setTextPen('#94a3b8')
        self.plot_widget.getAxis('bottom').setTextPen('#94a3b8')
        
        layout.addWidget(self.plot_widget)
    
    def add_line(self, name: str, color: str = '#06b6d4'):
        """데이터 라인 추가"""
        pen = pg.mkPen(color=color, width=2)
        plot = self.plot_widget.plot([], [], pen=pen, name=name)
        self.data_lines[name] = {
            'plot': plot,
            'data': [],
            'times': []
        }
    
    def add_point(self, name: str, value: float, time_val: float):
        """데이터 포인트 추가"""
        if name not in self.data_lines:
            return
        
        line = self.data_lines[name]
        line['data'].append(value)
        line['times'].append(time_val)
        
        # 최대 포인트 수 제한
        if len(line['data']) > self.max_points:
            line['data'] = line['data'][-self.max_points:]
            line['times'] = line['times'][-self.max_points:]
        
        line['plot'].setData(line['times'], line['data'])
    
    def clear_data(self):
        """데이터 초기화"""
        for name, line in self.data_lines.items():
            line['data'] = []
            line['times'] = []
            line['plot'].setData([], [])


class InfoPanel(QFrame):
    """정보 패널"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.info_labels: Dict[str, QLabel] = {}
        
        self.setStyleSheet("""
            InfoPanel {
                background-color: #1e293b;
                border-radius: 15px;
                border: 1px solid #334155;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        self.layout.setSpacing(5)
        
        # 제목
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(title_label)
    
    def add_info(self, key: str, label: str, initial_value: str = "-"):
        """정보 항목 추가"""
        row = QHBoxLayout()
        
        label_widget = QLabel(f"{label}:")
        label_widget.setStyleSheet("color: #94a3b8; font-size: 12px;")
        label_widget.setMinimumWidth(100)
        row.addWidget(label_widget)
        
        value_widget = QLabel(initial_value)
        value_widget.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: bold;")
        row.addWidget(value_widget)
        row.addStretch()
        
        self.info_labels[key] = value_widget
        self.layout.addLayout(row)
    
    def set_value(self, key: str, value: str):
        """값 업데이트"""
        if key in self.info_labels:
            self.info_labels[key].setText(value)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("🖥️ 시스템 리소스 모니터")
        self.setMinimumSize(1280, 800)
        
        # 다크 테마 설정
        self._setup_dark_theme()
        
        # 데이터 수집기
        self.collector = DataCollector()
        
        # 시스템 정보
        self.system_info = SystemInfo()
        self.cpu_monitor = CPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.gpu_monitor = GPUMonitor()
        
        # 상태 변수
        self.start_time = datetime.now()
        self.recording_start_time: Optional[datetime] = None
        self.recording_duration = 300  # 5분 (초)
        
        # UI 구성
        self._setup_ui()
        
        # 타이머 설정
        self._setup_timers()
        
        # 데이터 수집 시작
        self.collector.set_callback(self._on_data_received)
        self.collector.start_collecting(interval=1.0)
    
    def _setup_dark_theme(self):
        """다크 테마 설정"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f172a;
            }
            QWidget {
                background-color: transparent;
                color: #f1f5f9;
                font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #94a3b8;
            }
            QPushButton#stopBtn {
                background-color: #ef4444;
            }
            QPushButton#stopBtn:hover {
                background-color: #dc2626;
            }
            QPushButton#recordBtn {
                background-color: #22c55e;
            }
            QPushButton#recordBtn:hover {
                background-color: #16a34a;
            }
            QStatusBar {
                background-color: #1e293b;
                color: #94a3b8;
                border-top: 1px solid #334155;
            }
            QScrollArea {
                border: none;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #f1f5f9;
                subcontrol-origin: margin;
                left: 15px;
            }
        """)
    
    def _setup_ui(self):
        """UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # === 헤더 ===
        header = self._create_header()
        main_layout.addWidget(header)
        
        # === 메인 콘텐츠 ===
        content = QHBoxLayout()
        content.setSpacing(15)
        
        # 왼쪽: 게이지 + 정보
        left_panel = self._create_left_panel()
        content.addWidget(left_panel, stretch=1)
        
        # 오른쪽: 그래프
        right_panel = self._create_right_panel()
        content.addWidget(right_panel, stretch=2)
        
        main_layout.addLayout(content)
        
        # === 컨트롤 패널 ===
        controls = self._create_controls()
        main_layout.addWidget(controls)
        
        # === 상태 바 ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✅ 모니터링 중...")
    
    def _create_header(self) -> QWidget:
        """헤더 생성"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 15px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # 타이틀
        title = QLabel("🖥️ 시스템 리소스 모니터")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # 시간 표시
        self.time_label = QLabel()
        self.time_label.setStyleSheet("font-size: 14px; color: #94a3b8;")
        layout.addWidget(self.time_label)
        
        # 녹화 상태
        self.recording_label = QLabel()
        self.recording_label.setStyleSheet("font-size: 14px; color: #22c55e; font-weight: bold;")
        layout.addWidget(self.recording_label)
        
        return header
    
    def _create_left_panel(self) -> QWidget:
        """왼쪽 패널 (게이지 + 정보)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 게이지 그리드
        gauge_layout = QGridLayout()
        gauge_layout.setSpacing(10)
        
        self.cpu_gauge = GaugeWidget("🔥 CPU", "%")
        self.memory_gauge = GaugeWidget("💾 RAM", "%")
        self.gpu_gauge = GaugeWidget("🎮 GPU", "%")
        self.disk_gauge = GaugeWidget("💽 DISK", "%")
        
        gauge_layout.addWidget(self.cpu_gauge, 0, 0)
        gauge_layout.addWidget(self.memory_gauge, 0, 1)
        gauge_layout.addWidget(self.gpu_gauge, 1, 0)
        gauge_layout.addWidget(self.disk_gauge, 1, 1)
        
        layout.addLayout(gauge_layout)
        
        # 시스템 정보 패널
        self.sys_info_panel = InfoPanel("💻 시스템 정보")
        self.sys_info_panel.add_info('os', 'OS')
        self.sys_info_panel.add_info('cpu', 'CPU')
        self.sys_info_panel.add_info('ram', 'RAM')
        self.sys_info_panel.add_info('gpu', 'GPU')
        self.sys_info_panel.add_info('uptime', '가동 시간')
        layout.addWidget(self.sys_info_panel)
        
        # 네트워크 정보
        self.net_info_panel = InfoPanel("🌐 네트워크")
        self.net_info_panel.add_info('upload', '업로드')
        self.net_info_panel.add_info('download', '다운로드')
        self.net_info_panel.add_info('connections', '연결 수')
        layout.addWidget(self.net_info_panel)
        
        # 프로세스 정보
        self.proc_info_panel = InfoPanel("📊 프로세스")
        self.proc_info_panel.add_info('count', '프로세스 수')
        self.proc_info_panel.add_info('threads', '스레드 수')
        layout.addWidget(self.proc_info_panel)
        
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """오른쪽 패널 (그래프)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # CPU 그래프
        self.cpu_graph = GraphWidget("📈 CPU 사용률", "사용률 (%)")
        self.cpu_graph.add_line('cpu', '#ef4444')
        layout.addWidget(self.cpu_graph, stretch=1)
        
        # 메모리 & GPU 그래프
        self.mem_gpu_graph = GraphWidget("📈 메모리 & GPU", "사용률 (%)")
        self.mem_gpu_graph.add_line('memory', '#22c55e')
        self.mem_gpu_graph.add_line('gpu', '#a855f7')
        layout.addWidget(self.mem_gpu_graph, stretch=1)
        
        # 네트워크 그래프
        self.network_graph = GraphWidget("📈 네트워크 트래픽", "Mbps")
        self.network_graph.add_line('upload', '#f97316')
        self.network_graph.add_line('download', '#06b6d4')
        layout.addWidget(self.network_graph, stretch=1)
        
        return panel
    
    def _create_controls(self) -> QWidget:
        """컨트롤 패널"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 15px;
                padding: 15px;
            }
        """)
        
        layout = QHBoxLayout(panel)
        
        # 5분 녹화 버튼
        self.record_btn = QPushButton("⏱️ 5분 모니터링 시작")
        self.record_btn.setObjectName("recordBtn")
        self.record_btn.clicked.connect(self._start_recording)
        layout.addWidget(self.record_btn)
        
        # 녹화 중지 버튼
        self.stop_btn = QPushButton("⏹️ 중지")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_recording)
        layout.addWidget(self.stop_btn)
        
        # 타이머 표시
        self.timer_label = QLabel("00:00 / 05:00")
        self.timer_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9; margin: 0 20px;")
        layout.addWidget(self.timer_label)
        
        layout.addStretch()
        
        # PDF 생성 버튼
        self.pdf_btn = QPushButton("📄 PDF 리포트 생성")
        self.pdf_btn.setEnabled(False)
        self.pdf_btn.clicked.connect(self._generate_pdf)
        layout.addWidget(self.pdf_btn)
        
        return panel
    
    def _setup_timers(self):
        """타이머 설정"""
        # UI 업데이트 타이머 (100ms)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._update_time_display)
        self.ui_timer.start(100)
        
        # 녹화 타이머
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self._update_recording)
    
    def _on_data_received(self, point: DataPoint):
        """데이터 수신 콜백"""
        elapsed = (point.timestamp - self.start_time).total_seconds()
        
        # 게이지 업데이트
        self.cpu_gauge.set_value(point.cpu_usage, point.cpu_temp, "°C")
        self.memory_gauge.set_value(point.memory_percent, point.memory_used_gb, " GB")
        self.gpu_gauge.set_value(point.gpu_usage, point.gpu_temp, "°C")
        
        # 디스크 사용률 계산
        disk_monitor = DiskMonitor()
        partitions = disk_monitor.get_partitions()
        if partitions:
            total_percent = sum(p.used_percent for p in partitions) / len(partitions)
            self.disk_gauge.set_value(total_percent)
        
        # 그래프 업데이트
        self.cpu_graph.add_point('cpu', point.cpu_usage, elapsed)
        self.mem_gpu_graph.add_point('memory', point.memory_percent, elapsed)
        self.mem_gpu_graph.add_point('gpu', point.gpu_usage, elapsed)
        self.network_graph.add_point('upload', point.net_upload_mbps, elapsed)
        self.network_graph.add_point('download', point.net_download_mbps, elapsed)
        
        # 네트워크 정보 업데이트
        self.net_info_panel.set_value('upload', f"{point.net_upload_mbps:.2f} Mbps")
        self.net_info_panel.set_value('download', f"{point.net_download_mbps:.2f} Mbps")
        
        # 프로세스 정보
        self.proc_info_panel.set_value('count', str(point.process_count))
    
    def _update_time_display(self):
        """시간 표시 업데이트"""
        now = datetime.now()
        self.time_label.setText(now.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 시스템 정보 업데이트 (5초마다)
        if int(now.timestamp()) % 5 == 0:
            self._update_system_info()
    
    def _update_system_info(self):
        """시스템 정보 업데이트"""
        sys_data = self.system_info.get_data()
        
        self.sys_info_panel.set_value('os', f"{sys_data.os_name} {sys_data.os_release}")
        self.sys_info_panel.set_value('cpu', self.cpu_monitor.get_cpu_name()[:40])
        self.sys_info_panel.set_value('ram', f"{self.memory_monitor.get_total_memory_gb():.1f} GB")
        
        gpu_names = self.gpu_monitor.get_gpu_names()
        if gpu_names:
            self.sys_info_panel.set_value('gpu', gpu_names[0][:40])
        else:
            self.sys_info_panel.set_value('gpu', "N/A")
        
        self.sys_info_panel.set_value('uptime', sys_data.uptime_str)
        
        # 네트워크 연결 수
        network_monitor = NetworkMonitor()
        self.net_info_panel.set_value('connections', str(network_monitor.get_connection_count()))
        
        # 스레드 수
        self.proc_info_panel.set_value('threads', str(sys_data.thread_count))
    
    def _start_recording(self):
        """5분 녹화 시작"""
        self.collector.start_recording()
        self.recording_start_time = datetime.now()
        
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pdf_btn.setEnabled(False)
        
        self.recording_label.setText("🔴 녹화 중...")
        self.status_bar.showMessage("⏱️ 5분 모니터링 녹화 중...")
        
        self.recording_timer.start(1000)
    
    def _update_recording(self):
        """녹화 상태 업데이트"""
        if not self.recording_start_time:
            return
        
        elapsed = (datetime.now() - self.recording_start_time).total_seconds()
        remaining = max(0, self.recording_duration - elapsed)
        
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        total_min = self.recording_duration // 60
        
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d} / {total_min:02d}:00")
        
        # 5분 경과 시 자동 중지
        if elapsed >= self.recording_duration:
            self._stop_recording()
            QMessageBox.information(
                self, "녹화 완료",
                "5분 모니터링이 완료되었습니다.\nPDF 리포트를 생성할 수 있습니다."
            )
    
    def _stop_recording(self):
        """녹화 중지"""
        self.recording_timer.stop()
        self.collector.stop_recording()
        
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pdf_btn.setEnabled(True)
        
        self.recording_label.setText("✅ 녹화 완료")
        self.status_bar.showMessage("✅ 녹화 완료. PDF 리포트를 생성하세요.")
    
    def _generate_pdf(self):
        """PDF 리포트 생성"""
        data = self.collector.get_recording_data()
        
        if not data:
            QMessageBox.warning(self, "경고", "녹화된 데이터가 없습니다.")
            return
        
        # 저장 경로 선택
        filename, _ = QFileDialog.getSaveFileName(
            self, "PDF 저장",
            f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not filename:
            return
        
        try:
            self.status_bar.showMessage("📄 PDF 생성 중...")
            QApplication.processEvents()
            
            # 시스템 정보 수집
            sys_data = self.system_info.get_data()
            system_info = {
                'os': f"{sys_data.os_name} {sys_data.os_release}",
                'cpu': self.cpu_monitor.get_cpu_name(),
                'ram': f"{self.memory_monitor.get_total_memory_gb():.1f} GB",
                'gpu': self.gpu_monitor.get_gpu_names()[0] if self.gpu_monitor.get_gpu_names() else "N/A"
            }
            
            # PDF 생성
            generator = PDFReportGenerator()
            output_path = generator.generate_report(data, system_info, filename)
            
            self.status_bar.showMessage(f"✅ PDF 저장 완료: {output_path}")
            
            QMessageBox.information(
                self, "완료",
                f"PDF 리포트가 생성되었습니다.\n\n{output_path}"
            )
            
            # 파일 열기
            os.startfile(output_path)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"PDF 생성 중 오류 발생:\n{str(e)}")
            self.status_bar.showMessage(f"❌ PDF 생성 실패: {str(e)}")
    
    def closeEvent(self, event):
        """창 닫힘 이벤트"""
        self.collector.stop_collecting()
        event.accept()

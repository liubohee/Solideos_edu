"""
데이터 수집 및 저장 모듈
- 실시간 데이터 수집
- 히스토리 저장
- 통계 분석
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

from ..core import (
    CPUMonitor, MemoryMonitor, GPUMonitor,
    DiskMonitor, NetworkMonitor, SystemInfo
)


@dataclass
class DataPoint:
    """단일 데이터 포인트"""
    timestamp: datetime
    cpu_usage: float
    cpu_per_core: List[float]
    cpu_temp: Optional[float]
    memory_percent: float
    memory_used_gb: float
    gpu_usage: float
    gpu_temp: Optional[float]
    gpu_memory_percent: float
    disk_read_mb: float
    disk_write_mb: float
    net_upload_mbps: float
    net_download_mbps: float
    process_count: int


class DataCollector:
    """데이터 수집기"""
    
    def __init__(self, max_history: int = 3600):
        """
        Args:
            max_history: 저장할 최대 데이터 포인트 수 (기본 1시간 @ 1초 간격)
        """
        # 모니터 초기화
        self.cpu_monitor = CPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.gpu_monitor = GPUMonitor()
        self.disk_monitor = DiskMonitor()
        self.network_monitor = NetworkMonitor()
        self.system_info = SystemInfo()
        
        # 데이터 저장소
        self._history: deque = deque(maxlen=max_history)
        self._recording_history: List[DataPoint] = []
        
        # 수집 상태
        self._collecting = False
        self._recording = False
        self._collect_thread: Optional[threading.Thread] = None
        self._interval = 1.0  # 수집 간격 (초)
        
        # 콜백
        self._on_data_callback: Optional[Callable[[DataPoint], None]] = None
        
        # 초기 데이터 수집 (속도 측정용)
        self._initial_collect()
    
    def _initial_collect(self):
        """초기 데이터 수집"""
        self.disk_monitor.get_io_speed()
        self.network_monitor.get_io_data()
        time.sleep(0.1)
    
    def set_callback(self, callback: Callable[[DataPoint], None]):
        """데이터 수집 콜백 설정"""
        self._on_data_callback = callback
    
    def collect_once(self) -> DataPoint:
        """단일 데이터 수집"""
        cpu_data = self.cpu_monitor.get_data()
        mem_data = self.memory_monitor.get_data()
        gpu_data = self.gpu_monitor.get_data()
        disk_data = self.disk_monitor.get_data()
        net_data = self.network_monitor.get_data()
        sys_data = self.system_info.get_data()
        
        # GPU 데이터 추출
        gpu_usage = 0.0
        gpu_temp = None
        gpu_mem_percent = 0.0
        
        if gpu_data.gpus:
            gpu0 = gpu_data.gpus[0]
            gpu_usage = gpu0.get('load_percent', 0)
            gpu_temp = gpu0.get('temperature')
            gpu_mem_percent = gpu0.get('memory_percent', 0)
        
        # 디스크 I/O
        disk_read = disk_data.io.read_bytes_per_sec if disk_data.io else 0
        disk_write = disk_data.io.write_bytes_per_sec if disk_data.io else 0
        
        # 네트워크 I/O
        net_up = net_data.io.upload_mbps if net_data.io else 0
        net_down = net_data.io.download_mbps if net_data.io else 0
        
        point = DataPoint(
            timestamp=datetime.now(),
            cpu_usage=cpu_data.usage_percent,
            cpu_per_core=cpu_data.usage_per_core,
            cpu_temp=cpu_data.temperature,
            memory_percent=mem_data.used_percent,
            memory_used_gb=mem_data.used_gb,
            gpu_usage=gpu_usage,
            gpu_temp=gpu_temp,
            gpu_memory_percent=gpu_mem_percent,
            disk_read_mb=disk_read,
            disk_write_mb=disk_write,
            net_upload_mbps=net_up,
            net_download_mbps=net_down,
            process_count=sys_data.process_count
        )
        
        return point
    
    def _collect_loop(self):
        """수집 루프 (스레드)"""
        while self._collecting:
            try:
                point = self.collect_once()
                self._history.append(point)
                
                if self._recording:
                    self._recording_history.append(point)
                
                if self._on_data_callback:
                    self._on_data_callback(point)
                    
            except Exception as e:
                print(f"Data collection error: {e}")
            
            time.sleep(self._interval)
    
    def start_collecting(self, interval: float = 1.0):
        """데이터 수집 시작"""
        if self._collecting:
            return
        
        self._interval = interval
        self._collecting = True
        self._collect_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collect_thread.start()
    
    def stop_collecting(self):
        """데이터 수집 중지"""
        self._collecting = False
        if self._collect_thread:
            self._collect_thread.join(timeout=2)
            self._collect_thread = None
    
    def start_recording(self):
        """기록 시작 (PDF용)"""
        self._recording_history.clear()
        self._recording = True
    
    def stop_recording(self) -> List[DataPoint]:
        """기록 중지 및 데이터 반환"""
        self._recording = False
        return list(self._recording_history)
    
    def get_recording_data(self) -> List[DataPoint]:
        """현재 기록 중인 데이터"""
        return list(self._recording_history)
    
    def is_recording(self) -> bool:
        """기록 중 여부"""
        return self._recording
    
    def get_history(self, limit: Optional[int] = None) -> List[DataPoint]:
        """히스토리 데이터 반환"""
        history = list(self._history)
        if limit:
            return history[-limit:]
        return history
    
    def get_latest(self) -> Optional[DataPoint]:
        """최신 데이터 포인트"""
        if self._history:
            return self._history[-1]
        return None
    
    def get_statistics(self, data: Optional[List[DataPoint]] = None) -> Dict:
        """통계 계산"""
        if data is None:
            data = list(self._history)
        
        if not data:
            return {}
        
        import statistics
        
        cpu_values = [p.cpu_usage for p in data]
        mem_values = [p.memory_percent for p in data]
        gpu_values = [p.gpu_usage for p in data]
        
        def calc_stats(values: List[float]) -> Dict:
            if not values:
                return {'avg': 0, 'min': 0, 'max': 0, 'stdev': 0}
            return {
                'avg': statistics.mean(values),
                'min': min(values),
                'max': max(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0
            }
        
        return {
            'cpu': calc_stats(cpu_values),
            'memory': calc_stats(mem_values),
            'gpu': calc_stats(gpu_values),
            'duration_seconds': (data[-1].timestamp - data[0].timestamp).total_seconds() if len(data) > 1 else 0,
            'data_points': len(data)
        }

"""
디스크 모니터링 모듈
- 디스크 용량
- 읽기/쓰기 속도
- IOPS
"""

import psutil
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time


def bytes_to_gb(bytes_val: int) -> float:
    """바이트를 GB로 변환"""
    return bytes_val / (1024 ** 3)


def bytes_to_mb(bytes_val: int) -> float:
    """바이트를 MB로 변환"""
    return bytes_val / (1024 ** 2)


@dataclass
class DiskPartitionData:
    """디스크 파티션 데이터"""
    device: str
    mountpoint: str
    filesystem: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_percent: float


@dataclass
class DiskIOData:
    """디스크 I/O 데이터"""
    read_bytes_per_sec: float  # 읽기 속도 (MB/s)
    write_bytes_per_sec: float  # 쓰기 속도 (MB/s)
    read_count_per_sec: float  # 읽기 IOPS
    write_count_per_sec: float  # 쓰기 IOPS


@dataclass
class DiskData:
    """전체 디스크 데이터"""
    timestamp: datetime
    partitions: List[DiskPartitionData] = field(default_factory=list)
    io: Optional[DiskIOData] = None


class DiskMonitor:
    """디스크 모니터링 클래스"""
    
    def __init__(self):
        self._last_io = None
        self._last_io_time = None
        self._init_io_counters()
    
    def _init_io_counters(self):
        """I/O 카운터 초기화"""
        try:
            self._last_io = psutil.disk_io_counters()
            self._last_io_time = time.time()
        except:
            pass
    
    def get_partitions(self) -> List[DiskPartitionData]:
        """디스크 파티션 정보"""
        partitions = []
        
        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    partitions.append(DiskPartitionData(
                        device=part.device,
                        mountpoint=part.mountpoint,
                        filesystem=part.fstype,
                        total_gb=bytes_to_gb(usage.total),
                        used_gb=bytes_to_gb(usage.used),
                        free_gb=bytes_to_gb(usage.free),
                        used_percent=usage.percent
                    ))
                except (PermissionError, OSError):
                    pass
        except:
            pass
        
        return partitions
    
    def get_io_speed(self) -> Optional[DiskIOData]:
        """디스크 I/O 속도 계산"""
        try:
            current_io = psutil.disk_io_counters()
            current_time = time.time()
            
            if self._last_io is None or self._last_io_time is None:
                self._last_io = current_io
                self._last_io_time = current_time
                return DiskIOData(0, 0, 0, 0)
            
            time_diff = current_time - self._last_io_time
            if time_diff <= 0:
                time_diff = 1
            
            read_speed = bytes_to_mb(current_io.read_bytes - self._last_io.read_bytes) / time_diff
            write_speed = bytes_to_mb(current_io.write_bytes - self._last_io.write_bytes) / time_diff
            read_iops = (current_io.read_count - self._last_io.read_count) / time_diff
            write_iops = (current_io.write_count - self._last_io.write_count) / time_diff
            
            self._last_io = current_io
            self._last_io_time = current_time
            
            return DiskIOData(
                read_bytes_per_sec=max(0, read_speed),
                write_bytes_per_sec=max(0, write_speed),
                read_count_per_sec=max(0, read_iops),
                write_count_per_sec=max(0, write_iops)
            )
        except:
            return None
    
    def get_data(self) -> DiskData:
        """현재 디스크 데이터 수집"""
        return DiskData(
            timestamp=datetime.now(),
            partitions=self.get_partitions(),
            io=self.get_io_speed()
        )
    
    def get_total_space_gb(self) -> float:
        """전체 디스크 용량 합계"""
        total = 0
        for part in self.get_partitions():
            total += part.total_gb
        return total
    
    def get_used_space_gb(self) -> float:
        """사용 중인 디스크 용량 합계"""
        used = 0
        for part in self.get_partitions():
            used += part.used_gb
        return used

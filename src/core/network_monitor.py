"""
네트워크 모니터링 모듈
- 업로드/다운로드 속도
- 총 전송량
- 활성 연결 수
"""

import psutil
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time


def bytes_to_mb(bytes_val: int) -> float:
    """바이트를 MB로 변환"""
    return bytes_val / (1024 ** 2)


def bytes_to_mbps(bytes_val: float) -> float:
    """바이트/초를 Mbps로 변환"""
    return (bytes_val * 8) / (1024 ** 2)


@dataclass
class NetworkInterfaceData:
    """네트워크 인터페이스 데이터"""
    name: str
    is_up: bool
    speed_mbps: int  # 링크 속도
    mtu: int
    addresses: List[str] = field(default_factory=list)


@dataclass
class NetworkIOData:
    """네트워크 I/O 데이터"""
    bytes_sent: int
    bytes_recv: int
    bytes_sent_per_sec: float  # 업로드 속도 (bytes/s)
    bytes_recv_per_sec: float  # 다운로드 속도 (bytes/s)
    upload_mbps: float  # Mbps
    download_mbps: float  # Mbps
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drop_in: int
    drop_out: int


@dataclass
class NetworkData:
    """전체 네트워크 데이터"""
    timestamp: datetime
    io: Optional[NetworkIOData] = None
    connection_count: int = 0
    interfaces: List[NetworkInterfaceData] = field(default_factory=list)


class NetworkMonitor:
    """네트워크 모니터링 클래스"""
    
    def __init__(self):
        self._last_io = None
        self._last_io_time = None
        self._session_start_bytes_sent = 0
        self._session_start_bytes_recv = 0
        self._init_counters()
    
    def _init_counters(self):
        """카운터 초기화"""
        try:
            io = psutil.net_io_counters()
            self._last_io = io
            self._last_io_time = time.time()
            self._session_start_bytes_sent = io.bytes_sent
            self._session_start_bytes_recv = io.bytes_recv
        except:
            pass
    
    def get_interfaces(self) -> List[NetworkInterfaceData]:
        """네트워크 인터페이스 목록"""
        interfaces = []
        
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            
            for name, stat in stats.items():
                addr_list = []
                if name in addrs:
                    for addr in addrs[name]:
                        if addr.address and not addr.address.startswith('fe80'):
                            addr_list.append(addr.address)
                
                interfaces.append(NetworkInterfaceData(
                    name=name,
                    is_up=stat.isup,
                    speed_mbps=stat.speed,
                    mtu=stat.mtu,
                    addresses=addr_list
                ))
        except:
            pass
        
        return interfaces
    
    def get_connection_count(self) -> int:
        """활성 네트워크 연결 수"""
        try:
            connections = psutil.net_connections(kind='inet')
            return len([c for c in connections if c.status == 'ESTABLISHED'])
        except:
            return 0
    
    def get_io_data(self) -> Optional[NetworkIOData]:
        """네트워크 I/O 데이터"""
        try:
            current_io = psutil.net_io_counters()
            current_time = time.time()
            
            if self._last_io is None or self._last_io_time is None:
                self._last_io = current_io
                self._last_io_time = current_time
                return NetworkIOData(
                    bytes_sent=current_io.bytes_sent,
                    bytes_recv=current_io.bytes_recv,
                    bytes_sent_per_sec=0,
                    bytes_recv_per_sec=0,
                    upload_mbps=0,
                    download_mbps=0,
                    packets_sent=current_io.packets_sent,
                    packets_recv=current_io.packets_recv,
                    errors_in=current_io.errin,
                    errors_out=current_io.errout,
                    drop_in=current_io.dropin,
                    drop_out=current_io.dropout
                )
            
            time_diff = current_time - self._last_io_time
            if time_diff <= 0:
                time_diff = 1
            
            bytes_sent_diff = current_io.bytes_sent - self._last_io.bytes_sent
            bytes_recv_diff = current_io.bytes_recv - self._last_io.bytes_recv
            
            bytes_sent_per_sec = max(0, bytes_sent_diff / time_diff)
            bytes_recv_per_sec = max(0, bytes_recv_diff / time_diff)
            
            self._last_io = current_io
            self._last_io_time = current_time
            
            return NetworkIOData(
                bytes_sent=current_io.bytes_sent,
                bytes_recv=current_io.bytes_recv,
                bytes_sent_per_sec=bytes_sent_per_sec,
                bytes_recv_per_sec=bytes_recv_per_sec,
                upload_mbps=bytes_to_mbps(bytes_sent_per_sec),
                download_mbps=bytes_to_mbps(bytes_recv_per_sec),
                packets_sent=current_io.packets_sent,
                packets_recv=current_io.packets_recv,
                errors_in=current_io.errin,
                errors_out=current_io.errout,
                drop_in=current_io.dropin,
                drop_out=current_io.dropout
            )
        except:
            return None
    
    def get_session_transfer(self) -> Dict[str, float]:
        """세션 시작 후 총 전송량"""
        try:
            io = psutil.net_io_counters()
            return {
                'sent_mb': bytes_to_mb(io.bytes_sent - self._session_start_bytes_sent),
                'recv_mb': bytes_to_mb(io.bytes_recv - self._session_start_bytes_recv)
            }
        except:
            return {'sent_mb': 0, 'recv_mb': 0}
    
    def get_data(self) -> NetworkData:
        """현재 네트워크 데이터 수집"""
        return NetworkData(
            timestamp=datetime.now(),
            io=self.get_io_data(),
            connection_count=self.get_connection_count(),
            interfaces=self.get_interfaces()
        )

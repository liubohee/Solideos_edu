"""
시스템 정보 모듈
- 운영체제 정보
- 부팅 시간
- 프로세스/스레드 수
- 배터리 상태
"""

import psutil
import platform
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class BatteryData:
    """배터리 데이터"""
    percent: float
    is_plugged: bool
    time_left_minutes: Optional[int]


@dataclass
class SystemData:
    """시스템 데이터"""
    timestamp: datetime
    # OS 정보
    os_name: str
    os_version: str
    os_release: str
    hostname: str
    architecture: str
    # 부팅
    boot_time: datetime
    uptime_seconds: float
    uptime_str: str
    # 프로세스
    process_count: int
    thread_count: int
    # 배터리
    battery: Optional[BatteryData] = None


class SystemInfo:
    """시스템 정보 클래스"""
    
    def __init__(self):
        self._boot_time = datetime.fromtimestamp(psutil.boot_time())
    
    @staticmethod
    def get_os_info() -> Dict[str, str]:
        """운영체제 정보"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node()
        }
    
    def get_boot_time(self) -> datetime:
        """부팅 시간"""
        return self._boot_time
    
    def get_uptime(self) -> timedelta:
        """시스템 가동 시간"""
        return datetime.now() - self._boot_time
    
    @staticmethod
    def format_uptime(uptime: timedelta) -> str:
        """가동 시간 포맷팅"""
        total_seconds = int(uptime.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0:
            parts.append(f"{minutes}분")
        parts.append(f"{seconds}초")
        
        return " ".join(parts)
    
    @staticmethod
    def get_process_count() -> int:
        """실행 중인 프로세스 수"""
        return len(psutil.pids())
    
    @staticmethod
    def get_thread_count() -> int:
        """실행 중인 스레드 수"""
        count = 0
        for proc in psutil.process_iter(['num_threads']):
            try:
                count += proc.info['num_threads'] or 0
            except:
                pass
        return count
    
    @staticmethod
    def get_battery() -> Optional[BatteryData]:
        """배터리 상태 (노트북용)"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                time_left = None
                if battery.secsleft > 0:
                    time_left = battery.secsleft // 60
                
                return BatteryData(
                    percent=battery.percent,
                    is_plugged=battery.power_plugged,
                    time_left_minutes=time_left
                )
        except:
            pass
        return None
    
    def get_data(self) -> SystemData:
        """현재 시스템 데이터 수집"""
        os_info = self.get_os_info()
        uptime = self.get_uptime()
        
        return SystemData(
            timestamp=datetime.now(),
            os_name=os_info['system'],
            os_version=os_info['version'],
            os_release=os_info['release'],
            hostname=os_info['hostname'],
            architecture=os_info['machine'],
            boot_time=self._boot_time,
            uptime_seconds=uptime.total_seconds(),
            uptime_str=self.format_uptime(uptime),
            process_count=self.get_process_count(),
            thread_count=self.get_thread_count(),
            battery=self.get_battery()
        )

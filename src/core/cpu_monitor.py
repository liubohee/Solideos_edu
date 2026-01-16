"""
CPU 모니터링 모듈
- CPU 사용률 (전체 및 코어별)
- CPU 주파수
- CPU 온도
"""

import psutil
import platform
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    import cpuinfo
    HAS_CPUINFO = True
except ImportError:
    HAS_CPUINFO = False

try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False


@dataclass
class CPUData:
    """CPU 데이터 구조체"""
    timestamp: datetime
    usage_percent: float  # 전체 CPU 사용률
    usage_per_core: List[float]  # 코어별 사용률
    frequency_current: float  # 현재 주파수 (MHz)
    frequency_min: float  # 최소 주파수
    frequency_max: float  # 최대 주파수
    core_count: int  # 물리 코어 수
    thread_count: int  # 논리 코어 수 (스레드)
    temperature: Optional[float] = None  # 온도 (°C)
    temperatures_per_core: List[float] = field(default_factory=list)


class CPUMonitor:
    """CPU 모니터링 클래스"""
    
    def __init__(self):
        self._wmi = None
        if HAS_WMI:
            try:
                self._wmi = wmi.WMI(namespace="root\\wmi")
            except:
                try:
                    self._wmi = wmi.WMI()
                except:
                    pass
        
        # CPU 기본 정보 캐시
        self._cpu_info = self._get_cpu_info()
        self._core_count = psutil.cpu_count(logical=False) or 1
        self._thread_count = psutil.cpu_count(logical=True) or 1
    
    def _get_cpu_info(self) -> Dict:
        """CPU 상세 정보 수집"""
        info = {
            'brand': 'Unknown CPU',
            'arch': platform.machine(),
            'bits': platform.architecture()[0],
        }
        
        if HAS_CPUINFO:
            try:
                cpu_data = cpuinfo.get_cpu_info()
                info['brand'] = cpu_data.get('brand_raw', info['brand'])
                info['arch'] = cpu_data.get('arch', info['arch'])
            except:
                pass
        
        return info
    
    def get_cpu_name(self) -> str:
        """CPU 이름 반환"""
        return self._cpu_info.get('brand', 'Unknown CPU')
    
    def get_temperature(self) -> Optional[float]:
        """CPU 온도 측정 (Windows)"""
        # 방법 1: psutil sensors
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if 'cpu' in name.lower() or 'core' in name.lower():
                        if entries:
                            return entries[0].current
        except:
            pass
        
        # 방법 2: WMI (Windows)
        if self._wmi:
            try:
                temp_info = self._wmi.MSAcpi_ThermalZoneTemperature()
                if temp_info:
                    # 켈빈 to 섭씨 변환
                    kelvin = temp_info[0].CurrentTemperature / 10.0
                    return kelvin - 273.15
            except:
                pass
        
        return None
    
    def get_temperatures_per_core(self) -> List[float]:
        """코어별 온도 측정"""
        temps = []
        try:
            sensors = psutil.sensors_temperatures()
            if sensors:
                for name, entries in sensors.items():
                    if 'core' in name.lower():
                        temps.extend([e.current for e in entries])
        except:
            pass
        return temps
    
    def get_data(self) -> CPUData:
        """현재 CPU 데이터 수집"""
        # CPU 사용률
        usage_percent = psutil.cpu_percent(interval=None)
        usage_per_core = psutil.cpu_percent(interval=None, percpu=True)
        
        # CPU 주파수
        freq = psutil.cpu_freq()
        if freq:
            freq_current = freq.current
            freq_min = freq.min
            freq_max = freq.max
        else:
            freq_current = freq_min = freq_max = 0.0
        
        # 온도
        temperature = self.get_temperature()
        temps_per_core = self.get_temperatures_per_core()
        
        return CPUData(
            timestamp=datetime.now(),
            usage_percent=usage_percent,
            usage_per_core=usage_per_core,
            frequency_current=freq_current,
            frequency_min=freq_min,
            frequency_max=freq_max,
            core_count=self._core_count,
            thread_count=self._thread_count,
            temperature=temperature,
            temperatures_per_core=temps_per_core
        )
    
    def get_top_processes(self, limit: int = 10) -> List[Dict]:
        """CPU 사용량 상위 프로세스 목록"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is not None:
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'cpu_percent': pinfo['cpu_percent'],
                        'memory_percent': pinfo['memory_percent'] or 0
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # CPU 사용률 기준 정렬
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:limit]

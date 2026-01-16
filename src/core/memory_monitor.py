"""
메모리 모니터링 모듈
- RAM 사용량
- 스왑/가상 메모리
"""

import psutil
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime


def bytes_to_gb(bytes_val: int) -> float:
    """바이트를 GB로 변환"""
    return bytes_val / (1024 ** 3)


@dataclass
class MemoryData:
    """메모리 데이터 구조체"""
    timestamp: datetime
    # RAM
    total_gb: float
    available_gb: float
    used_gb: float
    used_percent: float
    cached_gb: float
    # Swap
    swap_total_gb: float
    swap_used_gb: float
    swap_free_gb: float
    swap_percent: float


class MemoryMonitor:
    """메모리 모니터링 클래스"""
    
    def __init__(self):
        # 총 메모리 크기 캐시
        mem = psutil.virtual_memory()
        self._total_memory_gb = bytes_to_gb(mem.total)
    
    def get_total_memory_gb(self) -> float:
        """총 RAM 용량 (GB)"""
        return self._total_memory_gb
    
    def get_data(self) -> MemoryData:
        """현재 메모리 데이터 수집"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # cached 속성이 없을 수 있음 (Windows)
        cached = getattr(mem, 'cached', 0)
        
        return MemoryData(
            timestamp=datetime.now(),
            total_gb=bytes_to_gb(mem.total),
            available_gb=bytes_to_gb(mem.available),
            used_gb=bytes_to_gb(mem.used),
            used_percent=mem.percent,
            cached_gb=bytes_to_gb(cached),
            swap_total_gb=bytes_to_gb(swap.total),
            swap_used_gb=bytes_to_gb(swap.used),
            swap_free_gb=bytes_to_gb(swap.free),
            swap_percent=swap.percent
        )
    
    def get_top_processes(self, limit: int = 10) -> List[Dict]:
        """메모리 사용량 상위 프로세스 목록"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
            try:
                pinfo = proc.info
                mem_info = pinfo.get('memory_info')
                if pinfo['memory_percent'] is not None:
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'memory_percent': pinfo['memory_percent'],
                        'memory_mb': bytes_to_gb(mem_info.rss) * 1024 if mem_info else 0
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 메모리 사용률 기준 정렬
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        return processes[:limit]

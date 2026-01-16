"""
GPU 모니터링 모듈
- GPU 사용률
- VRAM 사용량
- GPU 온도
- GPU 전력
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# GPU 라이브러리 체크
HAS_GPUTIL = False
HAS_PYNVML = False

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    pass

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pass


@dataclass
class GPUData:
    """GPU 데이터 구조체"""
    timestamp: datetime
    gpu_count: int
    gpus: List[Dict] = field(default_factory=list)


@dataclass 
class SingleGPUData:
    """개별 GPU 데이터"""
    id: int
    name: str
    load_percent: float  # GPU 사용률
    memory_total_mb: float
    memory_used_mb: float
    memory_free_mb: float
    memory_percent: float
    temperature: Optional[float]
    power_draw: Optional[float]  # 와트
    power_limit: Optional[float]
    fan_speed: Optional[float]  # %


class GPUMonitor:
    """GPU 모니터링 클래스"""
    
    def __init__(self):
        self._available = False
        self._gpu_count = 0
        self._gpu_names = []
        
        # NVML 초기화 시도
        if HAS_PYNVML:
            try:
                pynvml.nvmlInit()
                self._gpu_count = pynvml.nvmlDeviceGetCount()
                self._available = self._gpu_count > 0
                
                for i in range(self._gpu_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    self._gpu_names.append(name)
            except:
                self._try_gputil_init()
        elif HAS_GPUTIL:
            self._try_gputil_init()
    
    def _try_gputil_init(self):
        """GPUtil로 초기화 시도"""
        if HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                self._gpu_count = len(gpus)
                self._available = self._gpu_count > 0
                self._gpu_names = [gpu.name for gpu in gpus]
            except:
                pass
    
    def is_available(self) -> bool:
        """GPU 모니터링 가능 여부"""
        return self._available
    
    def get_gpu_count(self) -> int:
        """GPU 개수"""
        return self._gpu_count
    
    def get_gpu_names(self) -> List[str]:
        """GPU 이름 목록"""
        return self._gpu_names
    
    def get_data(self) -> GPUData:
        """현재 GPU 데이터 수집"""
        gpus_data = []
        
        if HAS_PYNVML and self._available:
            gpus_data = self._get_data_pynvml()
        elif HAS_GPUTIL and self._available:
            gpus_data = self._get_data_gputil()
        
        return GPUData(
            timestamp=datetime.now(),
            gpu_count=self._gpu_count,
            gpus=gpus_data
        )
    
    def _get_data_pynvml(self) -> List[Dict]:
        """PYNVML을 통한 GPU 데이터 수집"""
        gpus = []
        
        try:
            for i in range(self._gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # 메모리 정보
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                # 사용률
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    load = util.gpu
                except:
                    load = 0
                
                # 온도
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = None
                
                # 전력
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
                except:
                    power = None
                
                try:
                    power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
                except:
                    power_limit = None
                
                # 팬 속도
                try:
                    fan = pynvml.nvmlDeviceGetFanSpeed(handle)
                except:
                    fan = None
                
                name = self._gpu_names[i] if i < len(self._gpu_names) else f"GPU {i}"
                
                gpus.append({
                    'id': i,
                    'name': name,
                    'load_percent': load,
                    'memory_total_mb': mem_info.total / (1024**2),
                    'memory_used_mb': mem_info.used / (1024**2),
                    'memory_free_mb': mem_info.free / (1024**2),
                    'memory_percent': (mem_info.used / mem_info.total) * 100,
                    'temperature': temp,
                    'power_draw': power,
                    'power_limit': power_limit,
                    'fan_speed': fan
                })
        except Exception as e:
            pass
        
        return gpus
    
    def _get_data_gputil(self) -> List[Dict]:
        """GPUtil을 통한 GPU 데이터 수집"""
        gpus = []
        
        try:
            gpu_list = GPUtil.getGPUs()
            for gpu in gpu_list:
                gpus.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load_percent': gpu.load * 100,
                    'memory_total_mb': gpu.memoryTotal,
                    'memory_used_mb': gpu.memoryUsed,
                    'memory_free_mb': gpu.memoryFree,
                    'memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal else 0,
                    'temperature': gpu.temperature,
                    'power_draw': None,
                    'power_limit': None,
                    'fan_speed': None
                })
        except:
            pass
        
        return gpus
    
    def __del__(self):
        """소멸자 - NVML 정리"""
        if HAS_PYNVML:
            try:
                pynvml.nvmlShutdown()
            except:
                pass

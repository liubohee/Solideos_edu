# 🖥️ 시스템 리소스 모니터링 시스템

실시간으로 시스템 리소스를 모니터링하고 PDF 리포트를 생성하는 데스크톱 애플리케이션입니다.

## ✨ 주요 기능

- **실시간 모니터링**
  - CPU 사용률 및 온도
  - 메모리(RAM) 사용량
  - GPU 사용률, 온도, VRAM
  - 디스크 I/O
  - 네트워크 트래픽

- **시각화**
  - 실시간 그래프 (PyQtGraph)
  - 게이지 위젯
  - 다크 모드 UI

- **PDF 리포트**
  - 5분간 데이터 수집
  - 자동 그래프 생성
  - 통계 요약

## 📋 요구 사항

- Python 3.10+
- Windows 10/11
- NVIDIA GPU (GPU 모니터링용, 선택)

## 🚀 설치 및 실행

### 1. 가상환경 생성 (권장)
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 실행
```bash
python main.py
```

## 📊 사용 방법

1. 애플리케이션을 실행하면 자동으로 시스템 모니터링이 시작됩니다.
2. **"⏱️ 5분 모니터링 시작"** 버튼을 클릭하여 데이터 녹화를 시작합니다.
3. 5분이 경과하면 자동으로 녹화가 종료됩니다.
4. **"📄 PDF 리포트 생성"** 버튼을 클릭하여 리포트를 생성합니다.

## 📁 프로젝트 구조

```
resource-monitor/
├── main.py                    # 진입점
├── requirements.txt           # 의존성
├── README.md                  # 문서
└── src/
    ├── core/                  # 모니터링 모듈
    │   ├── cpu_monitor.py
    │   ├── memory_monitor.py
    │   ├── gpu_monitor.py
    │   ├── disk_monitor.py
    │   ├── network_monitor.py
    │   └── system_info.py
    ├── data/                  # 데이터 처리
    │   └── collector.py
    ├── report/                # 리포트 생성
    │   └── pdf_generator.py
    └── ui/                    # UI 컴포넌트
        └── main_window.py
```

## 🔧 기술 스택

- **UI**: PyQt6, PyQtGraph
- **모니터링**: psutil, GPUtil, pynvml
- **PDF**: ReportLab, Matplotlib
- **데이터**: Pandas, NumPy

## ⚠️ 주의사항

- GPU 온도/전력 모니터링은 NVIDIA GPU에서만 지원됩니다.
- 일부 센서 데이터(온도)는 관리자 권한이 필요할 수 있습니다.

## 📄 라이선스

MIT License

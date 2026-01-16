"""
시스템 리소스 모니터링 시스템
메인 진입점
"""

import sys
import os

# 모듈 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui.main_window import MainWindow


def main():
    """메인 함수"""
    # High DPI 설정
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # 애플리케이션 생성
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 기본 폰트 설정
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 실행
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
시스템 모니터링 기능 테스트 스크립트
각 모니터링 모듈의 기본 기능을 테스트합니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import CPUMonitor, MemoryMonitor, DiskMonitor, NetworkMonitor, SystemInfo

def test_cpu_monitor():
    """CPU 모니터링 테스트"""
    print("\n=== CPU 모니터링 테스트 ===")
    monitor = CPUMonitor()
    data = monitor.get_data()

    print(f"CPU 사용률: {data.usage_percent:.1f}%")
    print(f"CPU 코어 수: {data.core_count}개 (논리: {data.thread_count}개)")
    if data.frequency_current:
        print(f"현재 주파수: {data.frequency_current:.0f} MHz")
    if data.temperature is not None:
        print(f"온도: {data.temperature:.1f}°C")
    print(f"코어별 사용률: {[f'{x:.1f}%' for x in data.usage_per_core[:4]]}...")

def test_memory_monitor():
    """메모리 모니터링 테스트"""
    print("\n=== 메모리 모니터링 테스트 ===")
    monitor = MemoryMonitor()
    data = monitor.get_data()

    print(f"RAM 사용률: {data.used_percent:.1f}%")
    print(f"사용 중: {data.used_gb:.2f} GB / 전체: {data.total_gb:.2f} GB")
    print(f"사용 가능: {data.available_gb:.2f} GB")
    if data.swap_total_gb > 0:
        print(f"스왑 사용률: {data.swap_percent:.1f}%")

def test_disk_monitor():
    """디스크 모니터링 테스트"""
    print("\n=== 디스크 모니터링 테스트 ===")
    monitor = DiskMonitor()
    data = monitor.get_data()

    if data.io:
        print(f"읽기 속도: {data.io.read_bytes_per_sec:.2f} bytes/s")
        print(f"쓰기 속도: {data.io.write_bytes_per_sec:.2f} bytes/s")
        print(f"읽기 IOPS: {data.io.read_count_per_sec:.1f}")
        print(f"쓰기 IOPS: {data.io.write_count_per_sec:.1f}")

    print("\n디스크 파티션:")
    for partition in data.partitions[:3]:
        print(f"  {partition.mountpoint}: {partition.used_percent:.1f}% 사용 중")
        print(f"    ({partition.used_gb:.1f} GB / {partition.total_gb:.1f} GB)")

def test_network_monitor():
    """네트워크 모니터링 테스트"""
    print("\n=== 네트워크 모니터링 테스트 ===")
    monitor = NetworkMonitor()
    data = monitor.get_data()

    if data.io:
        print(f"업로드 속도: {data.io.upload_mbps:.2f} Mbps")
        print(f"다운로드 속도: {data.io.download_mbps:.2f} Mbps")
        print(f"총 전송: {data.io.bytes_sent / (1024**2):.2f} MB (송신)")
        print(f"총 수신: {data.io.bytes_recv / (1024**2):.2f} MB (수신)")

    print(f"활성 연결: {data.connection_count}개")

    print("\n네트워크 인터페이스:")
    for interface in data.interfaces[:3]:
        status = "활성" if interface.is_up else "비활성"
        print(f"  {interface.name}: {status}")
        if interface.addresses:
            print(f"    주소: {', '.join(interface.addresses)}")

def test_system_info():
    """시스템 정보 테스트"""
    print("\n=== 시스템 정보 테스트 ===")
    monitor = SystemInfo()
    data = monitor.get_data()

    print(f"OS: {data.os_name} {data.os_release}")
    print(f"호스트명: {data.hostname}")
    print(f"아키텍처: {data.architecture}")
    print(f"부팅 시간: {data.boot_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"가동 시간: {data.uptime_str}")
    print(f"프로세스 수: {data.process_count}개")
    print(f"스레드 수: {data.thread_count}개")

    if data.battery:
        battery_status = "충전 중" if data.battery.is_plugged else "배터리"
        print(f"배터리: {data.battery.percent:.1f}% ({battery_status})")

def main():
    """메인 함수"""
    print("=" * 60)
    print("시스템 리소스 모니터링 시스템 - 기능 테스트")
    print("=" * 60)

    try:
        test_system_info()
        test_cpu_monitor()
        test_memory_monitor()
        test_disk_monitor()
        test_network_monitor()

        print("\n" + "=" * 60)
        print("✓ 모든 모니터링 기능이 정상적으로 작동합니다!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())

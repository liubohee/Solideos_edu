"""
PDF 리포트 생성 모듈
- 시스템 정보 요약
- 그래프 생성
- PDF 문서 생성
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import numpy as np
from io import BytesIO

from ..data.collector import DataPoint


# 한글 폰트 설정 (Windows)
try:
    font_path = "C:/Windows/Fonts/malgun.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Malgun', font_path))
        DEFAULT_FONT = 'Malgun'
    else:
        DEFAULT_FONT = 'Helvetica'
except:
    DEFAULT_FONT = 'Helvetica'

# Matplotlib 한글 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


class PDFReportGenerator:
    """PDF 리포트 생성기"""
    
    # 색상 테마
    COLORS = {
        'primary': colors.HexColor('#0f3460'),
        'secondary': colors.HexColor('#16213e'),
        'accent': colors.HexColor('#00d9ff'),
        'success': colors.HexColor('#00ff88'),
        'warning': colors.HexColor('#ffaa00'),
        'danger': colors.HexColor('#ff4444'),
        'text': colors.HexColor('#ffffff'),
        'text_dark': colors.HexColor('#1a1a2e'),
        'bg_light': colors.HexColor('#f5f5f5'),
    }
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self._temp_images: List[str] = []
    
    def _setup_styles(self):
        """스타일 설정"""
        # 제목 스타일
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            fontName=DEFAULT_FONT,
            fontSize=24,
            textColor=self.COLORS['primary'],
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        # 헤더 스타일
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName=DEFAULT_FONT,
            fontSize=16,
            textColor=self.COLORS['primary'],
            spaceBefore=20,
            spaceAfter=10
        ))
        
        # 본문 스타일
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            fontName=DEFAULT_FONT,
            fontSize=10,
            textColor=self.COLORS['text_dark'],
            spaceAfter=8
        ))
        
        # 테이블 헤더 스타일
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName=DEFAULT_FONT,
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER
        ))
    
    def _create_line_chart(
        self,
        data: List[DataPoint],
        y_key: str,
        title: str,
        ylabel: str,
        color: str = '#00d9ff',
        figsize: tuple = (10, 4)
    ) -> BytesIO:
        """라인 차트 생성"""
        fig, ax = plt.subplots(figsize=figsize, facecolor='#f8f9fa')
        ax.set_facecolor('#ffffff')
        
        times = [p.timestamp for p in data]
        values = [getattr(p, y_key) for p in data]
        
        ax.plot(times, values, color=color, linewidth=2, alpha=0.9)
        ax.fill_between(times, values, alpha=0.3, color=color)
        
        ax.set_title(title, fontsize=14, fontweight='bold', color='#1a1a2e')
        ax.set_ylabel(ylabel, fontsize=10, color='#1a1a2e')
        ax.set_xlabel('시간', fontsize=10, color='#1a1a2e')
        
        # X축 시간 포맷
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        
        # 그리드
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_ylim(bottom=0)
        
        plt.tight_layout()
        
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def _create_multi_line_chart(
        self,
        data: List[DataPoint],
        y_keys: List[tuple],  # [(key, label, color), ...]
        title: str,
        ylabel: str,
        figsize: tuple = (10, 4)
    ) -> BytesIO:
        """다중 라인 차트 생성"""
        fig, ax = plt.subplots(figsize=figsize, facecolor='#f8f9fa')
        ax.set_facecolor('#ffffff')
        
        times = [p.timestamp for p in data]
        
        for key, label, color in y_keys:
            values = [getattr(p, key) for p in data]
            ax.plot(times, values, color=color, linewidth=2, alpha=0.9, label=label)
        
        ax.set_title(title, fontsize=14, fontweight='bold', color='#1a1a2e')
        ax.set_ylabel(ylabel, fontsize=10, color='#1a1a2e')
        ax.set_xlabel('시간', fontsize=10, color='#1a1a2e')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(loc='upper right')
        ax.set_ylim(bottom=0)
        
        plt.tight_layout()
        
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def _create_stats_table(self, stats: Dict, title: str) -> Table:
        """통계 테이블 생성"""
        header = ['항목', '평균', '최소', '최대', '표준편차']
        rows = [header]
        
        for key, values in stats.items():
            if isinstance(values, dict) and 'avg' in values:
                rows.append([
                    key.upper(),
                    f"{values['avg']:.2f}",
                    f"{values['min']:.2f}",
                    f"{values['max']:.2f}",
                    f"{values['stdev']:.2f}"
                ])
        
        table = Table(rows, colWidths=[2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['bg_light']),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def generate_report(
        self,
        data: List[DataPoint],
        system_info: Dict,
        output_path: str,
        stats: Optional[Dict] = None
    ) -> str:
        """PDF 리포트 생성
        
        Args:
            data: 수집된 데이터 포인트 리스트
            system_info: 시스템 정보 딕셔너리
            output_path: 출력 PDF 경로
            stats: 통계 데이터 (없으면 계산)
        
        Returns:
            생성된 PDF 파일 경로
        """
        if not data:
            raise ValueError("No data to generate report")
        
        # 통계 계산
        if stats is None:
            stats = self._calculate_stats(data)
        
        # PDF 문서 생성
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # ===== 페이지 1: 요약 =====
        story.append(Paragraph("🖥️ 시스템 리소스 모니터링 리포트", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # 모니터링 기간
        start_time = data[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')
        end_time = data[-1].timestamp.strftime('%Y-%m-%d %H:%M:%S')
        duration = (data[-1].timestamp - data[0].timestamp).total_seconds()
        duration_min = int(duration // 60)
        duration_sec = int(duration % 60)
        
        story.append(Paragraph("📅 모니터링 기간", self.styles['SectionHeader']))
        period_data = [
            ['시작 시간', start_time],
            ['종료 시간', end_time],
            ['총 모니터링 시간', f'{duration_min}분 {duration_sec}초'],
            ['수집 데이터 포인트', f'{len(data)}개']
        ]
        period_table = Table(period_data, colWidths=[5*cm, 10*cm])
        period_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), self.COLORS['bg_light']),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(period_table)
        story.append(Spacer(1, 20))
        
        # 시스템 사양
        story.append(Paragraph("💻 시스템 사양", self.styles['SectionHeader']))
        sys_data = [
            ['운영체제', system_info.get('os', 'N/A')],
            ['CPU', system_info.get('cpu', 'N/A')],
            ['총 RAM', system_info.get('ram', 'N/A')],
            ['GPU', system_info.get('gpu', 'N/A')],
        ]
        sys_table = Table(sys_data, colWidths=[5*cm, 10*cm])
        sys_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), self.COLORS['bg_light']),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(sys_table)
        story.append(Spacer(1, 20))
        
        # 주요 지표 요약
        story.append(Paragraph("📊 주요 지표 요약", self.styles['SectionHeader']))
        story.append(self._create_stats_table(stats, "통계 요약"))
        
        story.append(PageBreak())
        
        # ===== 페이지 2: CPU 분석 =====
        story.append(Paragraph("🔥 CPU 분석", self.styles['CustomTitle']))
        story.append(Spacer(1, 10))
        
        # CPU 사용률 그래프
        cpu_chart = self._create_line_chart(
            data, 'cpu_usage', 
            'CPU 사용률 추이', 
            '사용률 (%)',
            '#ff6b6b'
        )
        story.append(Image(cpu_chart, width=16*cm, height=7*cm))
        story.append(Spacer(1, 15))
        
        # CPU 통계
        cpu_stats = stats.get('cpu', {})
        cpu_summary = [
            ['평균 사용률', f"{cpu_stats.get('avg', 0):.1f}%"],
            ['최대 사용률', f"{cpu_stats.get('max', 0):.1f}%"],
            ['최소 사용률', f"{cpu_stats.get('min', 0):.1f}%"],
        ]
        cpu_table = Table(cpu_summary, colWidths=[5*cm, 5*cm])
        cpu_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ffeeee')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(cpu_table)
        
        story.append(PageBreak())
        
        # ===== 페이지 3: 메모리 & GPU =====
        story.append(Paragraph("💾 메모리 & GPU 분석", self.styles['CustomTitle']))
        story.append(Spacer(1, 10))
        
        # 메모리 사용률 그래프
        mem_chart = self._create_line_chart(
            data, 'memory_percent',
            '메모리 사용률 추이',
            '사용률 (%)',
            '#4ecdc4'
        )
        story.append(Image(mem_chart, width=16*cm, height=6*cm))
        story.append(Spacer(1, 10))
        
        # GPU 사용률 그래프
        gpu_chart = self._create_line_chart(
            data, 'gpu_usage',
            'GPU 사용률 추이',
            '사용률 (%)',
            '#a855f7'
        )
        story.append(Image(gpu_chart, width=16*cm, height=6*cm))
        
        story.append(PageBreak())
        
        # ===== 페이지 4: 디스크 & 네트워크 =====
        story.append(Paragraph("💽 디스크 & 네트워크 분석", self.styles['CustomTitle']))
        story.append(Spacer(1, 10))
        
        # 디스크 I/O 그래프
        disk_chart = self._create_multi_line_chart(
            data,
            [
                ('disk_read_mb', '읽기', '#3b82f6'),
                ('disk_write_mb', '쓰기', '#f97316')
            ],
            '디스크 I/O 추이',
            '속도 (MB/s)'
        )
        story.append(Image(disk_chart, width=16*cm, height=6*cm))
        story.append(Spacer(1, 10))
        
        # 네트워크 그래프
        net_chart = self._create_multi_line_chart(
            data,
            [
                ('net_upload_mbps', '업로드', '#22c55e'),
                ('net_download_mbps', '다운로드', '#06b6d4')
            ],
            '네트워크 트래픽 추이',
            '속도 (Mbps)'
        )
        story.append(Image(net_chart, width=16*cm, height=6*cm))
        
        # 리포트 생성 정보
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            f"리포트 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['CustomBody']
        ))
        
        # PDF 빌드
        doc.build(story)
        
        return output_path
    
    def _calculate_stats(self, data: List[DataPoint]) -> Dict:
        """통계 계산"""
        import statistics
        
        def calc(values):
            if not values:
                return {'avg': 0, 'min': 0, 'max': 0, 'stdev': 0}
            return {
                'avg': statistics.mean(values),
                'min': min(values),
                'max': max(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0
            }
        
        return {
            'cpu': calc([p.cpu_usage for p in data]),
            'memory': calc([p.memory_percent for p in data]),
            'gpu': calc([p.gpu_usage for p in data])
        }

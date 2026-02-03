"""
实时音量波形图组件
"""

from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont


class VolumeGraph(QWidget):
    """实时音量波形图"""
    
    def __init__(self, parent=None, max_points: int = 300):
        """
        初始化波形图
        
        Args:
            parent: 父控件
            max_points: 最大数据点数（约等于显示的秒数 * 10）
        """
        super().__init__(parent)
        
        # 数据存储
        self._max_points = max_points
        self._volumes = deque(maxlen=max_points)
        self._threshold = 0.02
        self._noise_floor = 0.0
        
        # 显示设置
        self._max_volume = 0.1  # Y轴最大值，会自动调整
        self._auto_scale = True
        
        # 触发标记
        self._trigger_points = deque(maxlen=50)  # 记录触发时刻的索引
        
        # 颜色
        self._bg_color = QColor(30, 30, 30)
        self._grid_color = QColor(60, 60, 60)
        self._line_color = QColor(90, 200, 90)
        self._threshold_color = QColor(255, 100, 100)
        self._noise_color = QColor(100, 100, 255)
        self._trigger_color = QColor(255, 200, 0)
        self._text_color = QColor(180, 180, 180)
        
        # 设置最小尺寸
        self.setMinimumSize(400, 150)
        
        # 初始化数据
        for _ in range(max_points):
            self._volumes.append(0)
    
    def set_threshold(self, threshold: float) -> None:
        """设置阈值"""
        self._threshold = threshold
        self.update()
    
    def set_noise_floor(self, noise_floor: float) -> None:
        """设置噪音基准"""
        self._noise_floor = noise_floor
        self.update()
    
    def add_volume(self, volume: float) -> None:
        """添加音量数据点"""
        self._volumes.append(volume)
        
        # 自动调整Y轴范围
        if self._auto_scale and volume > self._max_volume * 0.8:
            self._max_volume = volume * 1.5
        
        self.update()
    
    def mark_trigger(self) -> None:
        """标记触发点"""
        self._trigger_points.append(len(self._volumes) - 1)
    
    def clear(self) -> None:
        """清空数据"""
        self._volumes.clear()
        self._trigger_points.clear()
        for _ in range(self._max_points):
            self._volumes.append(0)
        self._max_volume = 0.1
        self.update()
    
    def set_max_volume(self, max_vol: float) -> None:
        """手动设置Y轴最大值"""
        self._max_volume = max_vol
        self._auto_scale = False
        self.update()
    
    def enable_auto_scale(self, enabled: bool = True) -> None:
        """启用/禁用自动缩放"""
        self._auto_scale = enabled
    
    def paintEvent(self, event) -> None:
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        margin_left = 50
        margin_right = 10
        margin_top = 10
        margin_bottom = 25
        
        graph_width = width - margin_left - margin_right
        graph_height = height - margin_top - margin_bottom
        
        # 背景
        painter.fillRect(0, 0, width, height, self._bg_color)
        
        # 绘制网格
        painter.setPen(QPen(self._grid_color, 1))
        
        # 横向网格线（5条）
        for i in range(6):
            y = margin_top + int(graph_height * i / 5)
            painter.drawLine(margin_left, y, width - margin_right, y)
        
        # Y轴标签
        painter.setPen(QPen(self._text_color, 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        for i in range(6):
            y = margin_top + int(graph_height * i / 5)
            value = self._max_volume * (5 - i) / 5
            painter.drawText(5, y + 4, f"{value:.3f}")
        
        # 有效阈值线（阈值 + 噪音基准）
        effective_threshold = self._threshold + self._noise_floor
        if effective_threshold < self._max_volume:
            threshold_y = margin_top + int(graph_height * (1 - effective_threshold / self._max_volume))
            painter.setPen(QPen(self._threshold_color, 2, Qt.PenStyle.DashLine))
            painter.drawLine(margin_left, threshold_y, width - margin_right, threshold_y)
            painter.drawText(margin_left + 5, threshold_y - 5, f"阈值: {effective_threshold:.4f}")
        
        # 噪音基准线
        if self._noise_floor > 0 and self._noise_floor < self._max_volume:
            noise_y = margin_top + int(graph_height * (1 - self._noise_floor / self._max_volume))
            painter.setPen(QPen(self._noise_color, 1, Qt.PenStyle.DotLine))
            painter.drawLine(margin_left, noise_y, width - margin_right, noise_y)
        
        # 绘制音量波形
        if len(self._volumes) > 1:
            painter.setPen(QPen(self._line_color, 1.5))
            
            points_count = len(self._volumes)
            x_step = graph_width / (points_count - 1) if points_count > 1 else 1
            
            prev_x = margin_left
            prev_y = margin_top + graph_height
            
            for i, vol in enumerate(self._volumes):
                x = margin_left + int(i * x_step)
                # 限制音量值在范围内
                vol_clamped = min(vol, self._max_volume)
                y = margin_top + int(graph_height * (1 - vol_clamped / self._max_volume))
                
                if i > 0:
                    painter.drawLine(prev_x, prev_y, x, y)
                
                prev_x = x
                prev_y = y
        
        # 绘制触发标记
        painter.setPen(QPen(self._trigger_color, 2))
        current_idx = len(self._volumes)
        for trigger_idx in self._trigger_points:
            # 计算相对位置
            relative_idx = trigger_idx - (current_idx - self._max_points)
            if 0 <= relative_idx < self._max_points:
                x = margin_left + int(relative_idx * graph_width / self._max_points)
                painter.drawLine(x, margin_top, x, margin_top + graph_height)
        
        # 底部标签
        painter.setPen(QPen(self._text_color, 1))
        painter.drawText(margin_left, height - 5, "← 30秒前")
        painter.drawText(width - margin_right - 40, height - 5, "现在 →")
        
        # 当前音量值
        if self._volumes:
            current_vol = self._volumes[-1]
            painter.drawText(width - 100, margin_top + 15, f"当前: {current_vol:.4f}")
        
        # 图例
        legend_x = margin_left + 100
        legend_y = height - 8
        
        painter.setPen(QPen(self._line_color, 2))
        painter.drawLine(legend_x, legend_y, legend_x + 20, legend_y)
        painter.setPen(QPen(self._text_color, 1))
        painter.drawText(legend_x + 25, legend_y + 4, "音量")
        
        painter.setPen(QPen(self._threshold_color, 2))
        painter.drawLine(legend_x + 70, legend_y, legend_x + 90, legend_y)
        painter.setPen(QPen(self._text_color, 1))
        painter.drawText(legend_x + 95, legend_y + 4, "阈值")
        
        painter.setPen(QPen(self._trigger_color, 2))
        painter.drawLine(legend_x + 140, legend_y, legend_x + 160, legend_y)
        painter.setPen(QPen(self._text_color, 1))
        painter.drawText(legend_x + 165, legend_y + 4, "触发")

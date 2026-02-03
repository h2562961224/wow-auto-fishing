"""
主界面模块
PyQt6 图形界面实现
"""

import platform

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QLineEdit,
    QSlider, QSpinBox, QTextEdit, QProgressBar,
    QFrame, QGridLayout, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

from ..core.fishing_bot import FishingBot, FishingState, FishingStats
from ..core.sound_detector import SoundDetector
from ..utils.config import Config
from .volume_graph import VolumeGraph

IS_MACOS = platform.system() == "Darwin"


class SignalBridge(QObject):
    """信号桥接器，用于跨线程通信"""
    state_changed = pyqtSignal(object)
    stats_updated = pyqtSignal(object)
    log_received = pyqtSignal(str)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 加载配置
        self._config = Config.load()
        
        # 创建钓鱼机器人
        self._bot = FishingBot(self._config)
        
        # 信号桥接
        self._signals = SignalBridge()
        self._signals.state_changed.connect(self._on_state_changed)
        self._signals.stats_updated.connect(self._on_stats_updated)
        self._signals.log_received.connect(self._on_log_received)
        
        # 设置回调
        self._bot.set_state_callback(lambda s: self._signals.state_changed.emit(s))
        self._bot.set_stats_callback(lambda s: self._signals.stats_updated.emit(s))
        self._bot.set_log_callback(lambda s: self._signals.log_received.emit(s))
        
        # 初始化 UI
        self._init_ui()
        
        # 音量监控定时器
        self._volume_timer = QTimer()
        self._volume_timer.timeout.connect(self._update_volume_display)
        
        # 时间更新定时器
        self._time_timer = QTimer()
        self._time_timer.timeout.connect(self._update_time_display)
        self._time_timer.start(1000)
    
    def _init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle("WoW 自动钓鱼工具")
        self.setMinimumSize(550, 750)
        
        # 中央控件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        
        # 状态显示区
        layout.addWidget(self._create_status_group())
        
        # 音量波形图
        layout.addWidget(self._create_volume_graph_group())
        
        # 快捷键设置区
        layout.addWidget(self._create_hotkey_group())
        
        # 参数设置区
        layout.addWidget(self._create_settings_group())
        
        # 控制按钮区
        layout.addWidget(self._create_control_group())
        
        # 日志区
        layout.addWidget(self._create_log_group())
        
        # 应用样式
        self._apply_styles()
    
    def _create_status_group(self) -> QGroupBox:
        """创建状态显示组"""
        group = QGroupBox("状态")
        layout = QGridLayout(group)
        
        # 当前状态
        layout.addWidget(QLabel("当前状态:"), 0, 0)
        self._status_label = QLabel("空闲")
        self._status_label.setObjectName("statusLabel")
        layout.addWidget(self._status_label, 0, 1)
        
        # 运行时间
        layout.addWidget(QLabel("运行时间:"), 0, 2)
        self._time_label = QLabel("00:00:00")
        layout.addWidget(self._time_label, 0, 3)
        
        # 抛竿次数
        layout.addWidget(QLabel("抛竿次数:"), 1, 0)
        self._cast_label = QLabel("0")
        layout.addWidget(self._cast_label, 1, 1)
        
        # 成功次数
        layout.addWidget(QLabel("成功次数:"), 1, 2)
        self._success_label = QLabel("0")
        layout.addWidget(self._success_label, 1, 3)
        
        # 成功率
        layout.addWidget(QLabel("成功率:"), 2, 0)
        self._rate_label = QLabel("0%")
        layout.addWidget(self._rate_label, 2, 1)
        
        # 上饵次数
        layout.addWidget(QLabel("上饵次数:"), 2, 2)
        self._bait_label = QLabel("0")
        layout.addWidget(self._bait_label, 2, 3)
        
        return group
    
    def _create_volume_graph_group(self) -> QGroupBox:
        """创建音量波形图组"""
        group = QGroupBox("音量波形图（用于调试）")
        layout = QVBoxLayout(group)
        
        # 波形图控件
        self._volume_graph = VolumeGraph(max_points=300)  # 约30秒数据
        self._volume_graph.setMinimumHeight(150)
        layout.addWidget(self._volume_graph)
        
        # 控制按钮行1
        btn_layout1 = QHBoxLayout()
        
        # 测试音频按钮（重要！）
        self._test_audio_btn = QPushButton("▶ 开始监听音频")
        self._test_audio_btn.setStyleSheet("QPushButton { background-color: #2d5a27; }")
        self._test_audio_btn.clicked.connect(self._on_test_audio)
        btn_layout1.addWidget(self._test_audio_btn)
        
        # 清除按钮
        clear_btn = QPushButton("清除波形")
        clear_btn.clicked.connect(self._volume_graph.clear)
        btn_layout1.addWidget(clear_btn)
        
        # 模拟触发按钮
        test_btn = QPushButton("模拟触发")
        test_btn.clicked.connect(self._test_trigger)
        btn_layout1.addWidget(test_btn)
        
        btn_layout1.addStretch()
        layout.addLayout(btn_layout1)
        
        # 控制按钮行2
        btn_layout2 = QHBoxLayout()
        
        # Y轴范围调整
        btn_layout2.addWidget(QLabel("Y轴最大:"))
        self._y_max_spin = QSpinBox()
        self._y_max_spin.setRange(1, 1000)
        self._y_max_spin.setValue(100)
        self._y_max_spin.setSuffix(" (×0.001)")
        self._y_max_spin.valueChanged.connect(self._on_y_max_changed)
        btn_layout2.addWidget(self._y_max_spin)
        
        # 自动缩放
        auto_scale_btn = QPushButton("自动缩放")
        auto_scale_btn.clicked.connect(lambda: self._volume_graph.enable_auto_scale(True))
        btn_layout2.addWidget(auto_scale_btn)
        
        btn_layout2.addStretch()
        layout.addLayout(btn_layout2)
        
        return group
    
    def _on_test_audio(self) -> None:
        """测试音频按钮点击"""
        if self._volume_timer.isActive():
            # 停止监听
            self._volume_timer.stop()
            if not self._bot.is_running:
                self._bot.sound_detector.stop()
            self._test_audio_btn.setText("▶ 开始监听音频")
            self._test_audio_btn.setStyleSheet("QPushButton { background-color: #2d5a27; }")
            self._log_text.append("音频监听已停止")
        else:
            # 开始监听
            self._apply_config_to_bot()
            
            # 如果钓鱼没有运行，单独启动声音检测
            if not self._bot.is_running:
                if not self._bot.sound_detector.start():
                    if IS_MACOS:
                        QMessageBox.warning(
                            self, 
                            "音频监听失败", 
                            "无法启动音频监听。\n\n"
                            "请确保已选择正确的音频设备。\n"
                            "macOS 需要安装 BlackHole 等虚拟音频设备。"
                        )
                    else:
                        QMessageBox.warning(
                            self, 
                            "音频监听失败", 
                            "无法启动音频监听，请检查音频设备选择。"
                        )
                    return
            
            self._volume_timer.start(100)  # 每100ms更新一次
            self._test_audio_btn.setText("⏹ 停止监听")
            self._test_audio_btn.setStyleSheet("QPushButton { background-color: #8b2500; }")
            self._log_text.append("音频监听已开始，观察波形图...")
    
    def _test_trigger(self) -> None:
        """测试触发"""
        self._volume_graph.mark_trigger()
        self._log_text.append("[测试] 手动触发标记")
    
    def _on_y_max_changed(self, value: int) -> None:
        """Y轴最大值变化"""
        self._volume_graph.set_max_volume(value / 1000.0)
        self._volume_graph.enable_auto_scale(False)
    
    def _create_hotkey_group(self) -> QGroupBox:
        """创建快捷键设置组"""
        group = QGroupBox("快捷键设置")
        layout = QGridLayout(group)
        
        # 前置动作键
        layout.addWidget(QLabel("前置动作键 (上饵):"), 0, 0)
        self._pre_action_input = QLineEdit(self._config.pre_action_key)
        self._pre_action_input.setMaxLength(10)
        self._pre_action_input.setMaximumWidth(100)
        layout.addWidget(self._pre_action_input, 0, 1)
        
        # 钓鱼键
        layout.addWidget(QLabel("钓鱼键 (抛竿):"), 0, 2)
        self._fishing_input = QLineEdit(self._config.fishing_key)
        self._fishing_input.setMaxLength(10)
        self._fishing_input.setMaximumWidth(100)
        layout.addWidget(self._fishing_input, 0, 3)
        
        # 交互键
        layout.addWidget(QLabel("交互键 (收杆):"), 1, 0)
        self._interact_input = QLineEdit(self._config.interact_key)
        self._interact_input.setMaxLength(10)
        self._interact_input.setMaximumWidth(100)
        layout.addWidget(self._interact_input, 1, 1)
        
        # 提示
        hint = QLabel("提示: 支持单字符 (如 1, f) 或特殊键 (如 f1, space)")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint, 2, 0, 1, 4)
        
        return group
    
    def _create_settings_group(self) -> QGroupBox:
        """创建参数设置组"""
        group = QGroupBox("参数设置")
        layout = QGridLayout(group)
        
        # 音频设备选择
        layout.addWidget(QLabel("音频设备:"), 0, 0)
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(200)
        self._refresh_audio_devices()
        layout.addWidget(self._device_combo, 0, 1, 1, 2)
        
        # 刷新设备按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_audio_devices)
        layout.addWidget(refresh_btn, 0, 3)
        
        # 声音灵敏度
        layout.addWidget(QLabel("声音灵敏度:"), 1, 0)
        self._sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self._sensitivity_slider.setRange(0, 100)
        self._sensitivity_slider.setValue(self._config.sound_sensitivity)
        self._sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)
        layout.addWidget(self._sensitivity_slider, 1, 1)
        self._sensitivity_label = QLabel(f"{self._config.sound_sensitivity}%")
        self._sensitivity_label.setMinimumWidth(40)
        layout.addWidget(self._sensitivity_label, 1, 2)
        
        # 校准按钮
        self._calibrate_btn = QPushButton("校准")
        self._calibrate_btn.clicked.connect(self._on_calibrate)
        layout.addWidget(self._calibrate_btn, 1, 3)
        
        # 上饵间隔
        layout.addWidget(QLabel("上饵间隔 (分钟):"), 2, 0)
        self._bait_interval_spin = QSpinBox()
        self._bait_interval_spin.setRange(1, 60)
        self._bait_interval_spin.setValue(self._config.bait_interval // 60)
        layout.addWidget(self._bait_interval_spin, 2, 1)
        
        # 超时时间
        layout.addWidget(QLabel("超时时间 (秒):"), 2, 2)
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 60)
        self._timeout_spin.setValue(self._config.timeout)
        layout.addWidget(self._timeout_spin, 2, 3)
        
        # 收杆延迟
        layout.addWidget(QLabel("收杆延迟 (毫秒):"), 3, 0)
        delay_layout = QHBoxLayout()
        self._hook_delay_min = QSpinBox()
        self._hook_delay_min.setRange(0, 2000)
        self._hook_delay_min.setValue(self._config.hook_delay_min)
        delay_layout.addWidget(self._hook_delay_min)
        delay_layout.addWidget(QLabel("-"))
        self._hook_delay_max = QSpinBox()
        self._hook_delay_max.setRange(0, 2000)
        self._hook_delay_max.setValue(self._config.hook_delay_max)
        delay_layout.addWidget(self._hook_delay_max)
        layout.addLayout(delay_layout, 3, 1)
        
        # 抛竿延迟
        layout.addWidget(QLabel("抛竿延迟 (毫秒):"), 3, 2)
        cast_delay_layout = QHBoxLayout()
        self._cast_delay_min = QSpinBox()
        self._cast_delay_min.setRange(0, 3000)
        self._cast_delay_min.setValue(self._config.cast_delay_min)
        cast_delay_layout.addWidget(self._cast_delay_min)
        cast_delay_layout.addWidget(QLabel("-"))
        self._cast_delay_max = QSpinBox()
        self._cast_delay_max.setRange(0, 3000)
        self._cast_delay_max.setValue(self._config.cast_delay_max)
        cast_delay_layout.addWidget(self._cast_delay_max)
        layout.addLayout(cast_delay_layout, 3, 3)
        
        # macOS 提示
        if IS_MACOS:
            hint = QLabel("提示: macOS 需要安装 BlackHole 并配置多输出设备来捕获游戏声音")
            hint.setStyleSheet("color: #f0ad4e; font-size: 11px;")
            hint.setWordWrap(True)
            layout.addWidget(hint, 4, 0, 1, 4)
        
        return group
    
    def _refresh_audio_devices(self) -> None:
        """刷新音频设备列表"""
        self._device_combo.clear()
        
        devices = SoundDetector.get_audio_devices()
        recommended_idx, _ = SoundDetector.get_recommended_device()
        
        selected_index = 0
        for i, device in enumerate(devices):
            # 标记推荐设备和虚拟设备
            name = device['name']
            if device.get('is_virtual'):
                name = f"★ {name}"
            
            self._device_combo.addItem(name, device['index'])
            
            # 选中推荐设备
            if device['index'] == recommended_idx:
                selected_index = i
        
        if devices:
            self._device_combo.setCurrentIndex(selected_index)
        else:
            self._device_combo.addItem("未找到音频设备", None)
    
    def _create_control_group(self) -> QGroupBox:
        """创建控制按钮组"""
        group = QGroupBox("控制")
        layout = QHBoxLayout(group)
        
        # 开始/停止按钮
        self._start_btn = QPushButton("开始钓鱼")
        self._start_btn.setObjectName("startButton")
        self._start_btn.clicked.connect(self._on_start_stop)
        layout.addWidget(self._start_btn)
        
        # 暂停按钮
        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause)
        layout.addWidget(self._pause_btn)
        
        # 保存配置按钮
        self._save_btn = QPushButton("保存配置")
        self._save_btn.clicked.connect(self._on_save_config)
        layout.addWidget(self._save_btn)
        
        return group
    
    def _create_log_group(self) -> QGroupBox:
        """创建日志区组"""
        group = QGroupBox("日志")
        layout = QVBoxLayout(group)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(150)
        layout.addWidget(self._log_text)
        
        # 清除按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.clicked.connect(self._log_text.clear)
        layout.addWidget(clear_btn)
        
        return group
    
    def _apply_styles(self) -> None:
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QSpinBox {
                background-color: #3c3c3c;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 5px;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                padding: 8px 15px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton#startButton {
                background-color: #2d5a27;
                border-color: #3d7a37;
            }
            QPushButton#startButton:hover {
                background-color: #3d7a37;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                color: #b0b0b0;
                font-family: Consolas, monospace;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #3c3c3c;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -4px 0;
                background: #5a9bd5;
                border-radius: 8px;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #5a9bd5;
                border-radius: 2px;
            }
            QLabel#statusLabel {
                font-weight: bold;
                color: #5a9bd5;
            }
        """)
    
    def _apply_config_to_bot(self) -> None:
        """应用界面配置到机器人"""
        self._config.pre_action_key = self._pre_action_input.text() or "1"
        self._config.fishing_key = self._fishing_input.text() or "2"
        self._config.interact_key = self._interact_input.text() or "f"
        self._config.bait_interval = self._bait_interval_spin.value() * 60
        self._config.timeout = self._timeout_spin.value()
        self._config.sound_sensitivity = self._sensitivity_slider.value()
        self._config.hook_delay_min = self._hook_delay_min.value()
        self._config.hook_delay_max = self._hook_delay_max.value()
        self._config.cast_delay_min = self._cast_delay_min.value()
        self._config.cast_delay_max = self._cast_delay_max.value()
        
        # 设置音频设备
        device_index = self._device_combo.currentData()
        device_name = self._device_combo.currentText()
        self._bot.sound_detector.set_device(device_index, device_name)
        
        self._bot.set_config(self._config)
    
    def _on_start_stop(self) -> None:
        """开始/停止按钮点击"""
        if self._bot.is_running:
            self._bot.stop()
            self._start_btn.setText("开始钓鱼")
            self._start_btn.setStyleSheet("")
            self._pause_btn.setEnabled(False)
            # 停止钓鱼时也停止音频监听和波形显示
            self._volume_timer.stop()
            self._test_audio_btn.setText("▶ 开始监听音频")
            self._test_audio_btn.setStyleSheet("QPushButton { background-color: #2d5a27; }")
        else:
            self._apply_config_to_bot()
            if self._bot.start():
                self._start_btn.setText("停止")
                self._start_btn.setStyleSheet("""
                    QPushButton#startButton {
                        background-color: #8b2500;
                        border-color: #a03000;
                    }
                    QPushButton#startButton:hover {
                        background-color: #a03000;
                    }
                """)
                self._pause_btn.setEnabled(True)
                self._volume_timer.start(100)
                # 更新测试音频按钮状态
                self._test_audio_btn.setText("⏹ 停止监听")
                self._test_audio_btn.setStyleSheet("QPushButton { background-color: #8b2500; }")
            else:
                if IS_MACOS:
                    QMessageBox.warning(
                        self, 
                        "启动失败", 
                        "无法启动声音检测。\n\n"
                        "macOS 需要安装虚拟音频设备来捕获系统声音：\n"
                        "1. 安装 BlackHole (推荐): brew install blackhole-2ch\n"
                        "2. 打开「音频 MIDI 设置」\n"
                        "3. 创建「多输出设备」，包含扬声器和 BlackHole\n"
                        "4. 将多输出设备设为系统输出\n"
                        "5. 在本程序中选择 BlackHole 作为输入设备"
                    )
                else:
                    QMessageBox.warning(
                        self, 
                        "启动失败", 
                        "无法启动声音检测。\n\n"
                        "请检查是否启用了「立体声混音」设备。"
                    )
    
    def _on_pause(self) -> None:
        """暂停按钮点击"""
        self._bot.toggle_pause()
        if self._bot.is_paused:
            self._pause_btn.setText("继续")
        else:
            self._pause_btn.setText("暂停")
    
    def _on_save_config(self) -> None:
        """保存配置按钮点击"""
        self._apply_config_to_bot()
        if self._config.save():
            self._log_text.append("配置已保存")
        else:
            QMessageBox.warning(self, "错误", "配置保存失败")
    
    def _on_sensitivity_changed(self, value: int) -> None:
        """灵敏度滑块变化"""
        self._sensitivity_label.setText(f"{value}%")
        self._config.sound_sensitivity = value
        self._config.calculate_threshold_from_sensitivity()
        self._bot.sound_detector.threshold = self._config.sound_threshold
    
    def _on_calibrate(self) -> None:
        """校准按钮点击"""
        self._calibrate_btn.setEnabled(False)
        self._calibrate_btn.setText("校准中...")
        
        # 在后台线程中执行校准
        import threading
        def calibrate():
            self._bot.calibrate_sound(2.0)
            # 通过信号更新 UI
            self._signals.log_received.emit("校准完成")
        
        threading.Thread(target=calibrate, daemon=True).start()
        
        # 2秒后恢复按钮
        QTimer.singleShot(2500, lambda: (
            self._calibrate_btn.setEnabled(True),
            self._calibrate_btn.setText("校准")
        ))
    
    def _on_state_changed(self, state: FishingState) -> None:
        """状态变化回调"""
        state_names = {
            FishingState.IDLE: "空闲",
            FishingState.PRE_ACTION: "上饵中",
            FishingState.CASTING: "抛竿中",
            FishingState.WAITING: "等待上钩",
            FishingState.HOOKING: "收杆中",
            FishingState.PAUSED: "已暂停",
        }
        self._status_label.setText(state_names.get(state, "未知"))
        
        # 当检测到声音进入 HOOKING 状态时，在波形图上标记
        if state == FishingState.HOOKING:
            self._volume_graph.mark_trigger()
    
    def _on_stats_updated(self, stats: FishingStats) -> None:
        """统计更新回调"""
        self._cast_label.setText(str(stats.total_casts))
        self._success_label.setText(str(stats.successful_hooks))
        self._rate_label.setText(f"{stats.success_rate:.1f}%")
        self._bait_label.setText(str(stats.baits_applied))
    
    def _on_log_received(self, message: str) -> None:
        """日志接收回调"""
        self._log_text.append(message)
        # 滚动到底部
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _update_volume_display(self) -> None:
        """更新音量显示"""
        volume = self._bot.sound_detector.current_volume
        
        # 更新波形图
        self._volume_graph.add_volume(volume)
        self._volume_graph.set_threshold(self._config.sound_threshold)
        self._volume_graph.set_noise_floor(self._bot.sound_detector._noise_floor)
    
    def _update_time_display(self) -> None:
        """更新运行时间显示"""
        if self._bot.is_running:
            seconds = int(self._bot.stats.running_time)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            self._time_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")
    
    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        if self._bot.is_running:
            self._bot.stop()
        event.accept()
